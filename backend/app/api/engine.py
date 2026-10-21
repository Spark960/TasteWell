"""Run registry + background agent execution (P3 file-map addition).

Design:
- POST /api/agent/run creates a RunState and starts an asyncio task; the run
  continues even if every SSE subscriber disconnects (buffer lives in
  trace.events, plan "SSE disconnect resilience").
- Injectable factories (provider/client) make runs fully fakeable in tests;
  defaults mirror the CLI wiring (managed through settings).
- Run registry is in-memory (plan task 3) — a process restart loses runs,
  which is fine for demo; the trace file dump remains available for runs
  that set keep_trace.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Awaitable, Callable, Literal

from pydantic import BaseModel

from app.agent.loop import AgentOutcome, AgentRunner, BriefRequest
from app.agent.provider import LlmProvider, ProviderConfigError
from app.agent.tools import GroundedTools
from app.qloo.mcp_client import QlooMcpClient
from app.qloo.redact import redact, register_secret
from app.settings import MissingCredential, Settings, get_settings
from app.trace import Trace, now_iso

log = logging.getLogger("tastewell.engine")

RunMode = Literal["grounded", "generic"]


class RunRequest(BaseModel):
    brief: str
    region: str = ""
    audience: str = ""
    city: str = ""
    mode: RunMode = "grounded"
    # pre-answer a needs_input question with a Qloo candidate id (the UI
    # re-drives the run with `pick` instead of mid-run interactivity)
    pick: str = ""


class RunState:
    def __init__(self, run_id: str, request: RunRequest) -> None:
        self.run_id = run_id
        self.request = request
        self.bus = None  # set alongside StreamingTrace by Engine.new_run
        self.trace = Trace(run_id=run_id)
        self.status = "queued"  # queued | running | done | error
        self.outcome: AgentOutcome | None = None
        self.error: str = ""
        self.task: asyncio.Task | None = None

    def summary(self) -> dict:
        out: dict[str, Any] = {
            "run_id": self.run_id,
            "status": self.status,
            "exit_status": None,
            "needs_input": None,
            "brief": None,
            "events": len(self.trace.events),
        }
        if self.outcome is not None:
            out["exit_status"] = self.outcome.status
            out["needs_input"] = self.outcome.needs_input
            out["brief"] = self.outcome.brief
        elif self.error:
            out["error"] = self.error
        return out


ProviderFactory = Callable[[Settings, RunRequest], Any]
ClientFactory = Callable[[Settings, RunRequest], Any]
Chooser = Callable[[list[dict]], Awaitable[str | None]]


def default_provider_factory(settings: Settings, req: RunRequest) -> LlmProvider:
    key_map = {
        "gemini": settings.gemini_api_key,
        "openai": settings.openai_api_key,
        "groq": settings.groq_api_key,
    }
    key = key_map.get(settings.llm_provider, "")
    register_secret(key)
    return LlmProvider(
        provider=settings.llm_provider, model=settings.llm_model, api_key=key
    )


def default_client_factory(settings: Settings, req: RunRequest) -> QlooMcpClient:
    key = settings.require_qloo_key()
    register_secret(key)
    return QlooMcpClient(
        qloo_bin=settings.qloo_bin,
        api_key=key,
        base_urls=(settings.qloo_base_url, settings.qloo_trusted_base_url),
    )


def make_run_id() -> str:
    return f"{now_iso()[:19].replace(':', '')}-{uuid.uuid4().hex[:6]}"


class Engine:
    """Owns the run registry and turns RunRequest into AgentOutcomes."""

    def __init__(
        self,
        settings: Settings | None = None,
        provider_factory: ProviderFactory | None = None,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._provider_factory = provider_factory or default_provider_factory
        self._client_factory = client_factory or default_client_factory
        self.runs: dict[str, RunState] = {}

    async def new_run(self, req: RunRequest) -> RunState:
        from app.api.stream import SseBus, StreamingTrace

        bus = SseBus()
        state = RunState(make_run_id(), req)
        state.bus = bus
        state.trace = StreamingTrace(state.run_id, on_event=bus.publish)
        self.runs[state.run_id] = state
        state.task = asyncio.create_task(
            self._execute(state), name=f"tastewell-run-{state.run_id}"
        )
        return state

    async def wait_run(self, run_id: str) -> RunState:
        state = self.runs[run_id]
        if state.task is not None:
            await state.task
        return state

    async def _execute(self, state: RunState) -> None:
        client = None
        try:
            req = state.request
            state.status = "running"
            provider = self._provider_factory(self.settings, req)
            tools = None
            if req.mode == "grounded":
                client = self._client_factory(self.settings, req)
                await client.__aenter__()
                if not client.tools:
                    raise RuntimeError(
                        "Harness exposed no MCP tools — check qloo --version."
                    )
                state.trace.log(
                    "status", message="readiness_ok", mode="mcp",
                    tools=sorted(client.tools),
                )
                tools = GroundedTools(client=client, trace=state.trace)
            runner = AgentRunner(
                provider=provider,
                tools=tools,
                trace=state.trace,
                chooser=self._chooser(req),
            )
            brief_req = BriefRequest(
                brief=req.brief, region=req.region, audience=req.audience,
                extras={"city": req.city} if req.city else {},
            )
            state.outcome = await runner.run(brief_req)
            state.status = "done"
        except (ProviderConfigError, MissingCredential, RuntimeError) as exc:
            state.error = redact(str(exc))
            state.status = "error"
            log.error("run=%s fatal=%s", state.run_id, state.error)
            state.trace.log("status", message="run_error", error=state.error)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            state.error = redact(f"{type(exc).__name__}: {exc}")
            state.status = "error"
            log.exception("run=%s crashed", state.run_id)
            state.trace.log("status", message="run_error", error=state.error)
        finally:
            exit_status = (
                state.outcome.status if state.outcome is not None
                else ("done" if state.status == "done" else "error")
            )
            state.trace.log(
                "run_done", exit_status=exit_status,
                run_status=state.status,
                error=state.error or None,
            )
            if client is not None:
                try:
                    await client.__aexit__(None, None, None)
                except Exception:
                    log.exception("run=%s mcp teardown failed", state.run_id)

    def _chooser(self, req: RunRequest) -> Chooser | None:
        if not req.pick:
            return None

        async def choose(candidates: list[dict]) -> str | None:
            return f"{req.pick} (the user's pre-picked Qloo candidate id)"

        return choose

    async def qloo_status(self) -> dict:
        """Capabilities via a throwaway MCP connection — never raises."""
        settings = self.settings
        if not settings.qloo_api_key and settings.app_env != "dev":
            return {"ready": False, "reason": "QLOO_API_KEY not set"}
        client = None
        try:
            client = self._client_factory(settings, RunRequest(brief="status"))
            try:
                await asyncio.wait_for(client.__aenter__(), timeout=15.0)
            except asyncio.TimeoutError:
                return {"ready": False, "reason": "harness spawn timeout"}
            if not client.tools:
                return {"ready": False, "reason": "no MCP tools exposed"}
            caps = getattr(client, "capabilities", None)
            return {
                "ready": True,
                "tools": sorted(client.tools),
                "capabilities_status": caps.status if caps else "unknown",
            }
        except Exception as exc:
            log.warning("qloo_status failed: %s", redact(str(exc)))
            return {"ready": False, "reason": redact(str(exc))}
        finally:
            if client is not None:
                try:
                    await client.__aexit__(None, None, None)
                except Exception:
                    pass

