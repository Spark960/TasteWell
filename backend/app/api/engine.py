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
import time
import uuid
from typing import Any, Awaitable, Callable, Literal

from pydantic import BaseModel

from app.agent.loop import AgentOutcome, AgentRunner, BriefRequest
from app.agent.provider import LlmProvider, ProviderConfigError
from app.agent.tools import GroundedTools
from app.api.decisions import (DecisionRequest, DecisionResult, ScenarioRequest,
                               ScenarioResult, build_decision, compare_scenario, stamp)
from app.api.decision_store import DecisionStore
from app.qloo.mcp_client import QlooMcpClient
from app.qloo.redact import redact, register_secret
from app.settings import MissingCredential, Settings, get_settings
from app.trace import Trace, now_iso

log = logging.getLogger("tastewell.engine")

RunMode = Literal["grounded", "generic"]
MCP_READINESS_TIMEOUT = 90.0
DECISION_TOTAL_TIMEOUT = 180.0


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
        elif self.status in ("done", "error"):
            # Terminal after a crash/timeout (e.g. the 600s wall killed the
            # run) — surface so pollers don't treat the run as in-flight.
            out["exit_status"] = "done" if self.status == "done" else "error"
            if self.error:
                out["error"] = self.error
        return out


class DecisionJob:
    def __init__(self) -> None:
        self.id = f"job_{uuid.uuid4().hex[:12]}"
        self.status = "queued"
        self.stage = "queued"
        self.started = time.monotonic()
        self.result: DecisionResult | None = None
        self.error = ""
        self.task: asyncio.Task | None = None

    def summary(self) -> dict:
        return {
            "job_id": self.id, "status": self.status, "stage": self.stage,
            "elapsed_seconds": round(time.monotonic() - self.started, 1),
            "decision": self.result.model_dump() if self.result else None,
            "error": self.error or None,
        }


ProviderFactory = Callable[[Settings, RunRequest], Any]
ClientFactory = Callable[[Settings, RunRequest], Any]
Chooser = Callable[[list[dict]], Awaitable[str | None]]


def default_provider_factory(settings: Settings, req: RunRequest) -> LlmProvider:
    key_map = {
        "gemini": settings.gemini_api_key,
        "openai": settings.openai_api_key,
        "groq": settings.groq_api_key,
        "openrouter": settings.openrouter_api_key,
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
        decision_store: DecisionStore | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._provider_factory = provider_factory or default_provider_factory
        self._client_factory = client_factory or default_client_factory
        self.runs: dict[str, RunState] = {}
        self.decisions: dict[str, DecisionResult] = {}
        self.decision_jobs: dict[str, DecisionJob] = {}
        self.decision_store = decision_store or DecisionStore()

    async def new_decision(self, req: DecisionRequest,
                           progress: Callable[[str], None] | None = None) -> DecisionResult:
        result = await self._build_decision(req, progress)
        self.decisions[result.id] = result
        self.decision_store.save(result)
        return result

    async def _build_decision(self, req: DecisionRequest,
                              progress: Callable[[str], None] | None = None) -> DecisionResult:
        has_live_venue = (any(venue.live_music_allowed for venue in req.venues)
                          if req.venues else req.live_music_allowed)
        if not has_live_venue:
            result = await build_decision(req, None, progress)
        else:
            if progress is not None:
                progress("connecting to Qloo")
            client = self._client_factory(self.settings, RunRequest(brief=req.concept))
            async with asyncio.timeout(DECISION_TOTAL_TIMEOUT):
                try:
                    await asyncio.wait_for(client.__aenter__(), timeout=MCP_READINESS_TIMEOUT)
                    result = await build_decision(req, client, progress)
                finally:
                    await asyncio.wait_for(client.__aexit__(None, None, None), timeout=5)
        return result

    async def new_scenario(self, decision_id: str,
                           request: ScenarioRequest) -> tuple[DecisionResult, ScenarioResult]:
        previous = self.get_decision(decision_id)
        if previous is None:
            raise KeyError(decision_id)
        if previous.status != "ready":
            raise ValueError("finish the decision before comparing a scenario")
        venue = next((venue for venue in previous.venues if venue.id == request.venue_id), None)
        if venue is None or not venue.live_music_allowed:
            raise ValueError("choose an eligible venue in this decision")
        original = next((row for row in previous.evidence
                         if row.operation == "rank" and row.venue_id == venue.id), None)
        if original is None:
            raise ValueError("this venue has no ranked artist shortlist to compare")
        if (original.query.get("signal_location") == request.region
                and original.query.get("demographic") == request.audience):
            raise ValueError("change the audience or region to compare a scenario")
        working = previous.model_copy(deep=True)
        client = self._client_factory(self.settings, RunRequest(brief=previous.request.concept))
        async with asyncio.timeout(DECISION_TOTAL_TIMEOUT):
            try:
                await asyncio.wait_for(client.__aenter__(), timeout=MCP_READINESS_TIMEOUT)
                scenario = await compare_scenario(working, request, client)
            finally:
                await asyncio.wait_for(client.__aexit__(None, None, None), timeout=5)
        self.save_decision(working)
        return working, scenario

    async def resolve_decision(self, decision_id: str, candidate_id: str,
                               progress: Callable[[str], None] | None = None) -> DecisionResult:
        previous = self.get_decision(decision_id)
        if previous is None:
            raise KeyError(decision_id)
        if previous.status != "needs_input" or not any(
            candidate.get("id") == candidate_id for candidate in previous.candidates
        ):
            raise ValueError("tag is not a candidate for this decision")
        if previous.resolution_kind == "tag":
            changes = {"selected_tag_id": candidate_id}
        elif previous.resolution_kind == "artist" and previous.resolution_key:
            changes = {"artist_resolution": {
                **previous.request.artist_resolution,
                previous.resolution_key: candidate_id,
            }}
        else:
            raise ValueError("decision has no resolvable candidate")
        result = await self._build_decision(previous.request.model_copy(update=changes), progress)
        result.id = previous.id
        result.created_at = previous.created_at
        self.save_decision(result)
        return result

    def start_decision_job(self, req: DecisionRequest) -> DecisionJob:
        job = DecisionJob()
        self.decision_jobs[job.id] = job
        job.task = asyncio.create_task(self._execute_decision_job(job, req=req))
        self._prune_decision_jobs()
        return job

    def start_resolution_job(self, decision_id: str, candidate_id: str) -> DecisionJob:
        previous = self.get_decision(decision_id)
        if previous is None:
            raise KeyError(decision_id)
        if previous.status != "needs_input" or not any(
            candidate.get("id") == candidate_id for candidate in previous.candidates
        ):
            raise ValueError("candidate is not available for this decision")
        job = DecisionJob()
        self.decision_jobs[job.id] = job
        job.task = asyncio.create_task(self._execute_decision_job(
            job, decision_id=decision_id, candidate_id=candidate_id))
        self._prune_decision_jobs()
        return job

    async def _execute_decision_job(self, job: DecisionJob,
                                    req: DecisionRequest | None = None,
                                    decision_id: str = "", candidate_id: str = "") -> None:
        try:
            job.status = "running"
            job.stage = "starting"
            if req is not None:
                job.result = await self.new_decision(req, progress=lambda value: setattr(job, "stage", value))
            else:
                job.result = await self.resolve_decision(
                    decision_id, candidate_id, progress=lambda value: setattr(job, "stage", value))
            job.status = "done"
            job.stage = "complete"
        except asyncio.CancelledError:
            job.status = "cancelled"
            job.stage = "cancelled"
        except TimeoutError:
            job.status = "error"
            job.stage = "timed out"
            job.error = "decision exceeded its total time budget"
        except Exception as exc:
            job.status = "error"
            job.stage = "failed"
            job.error = redact(f"{type(exc).__name__}: {exc}")
            log.exception("decision job=%s failed", job.id)

    def cancel_decision_job(self, job_id: str) -> DecisionJob:
        job = self.decision_jobs[job_id]
        if job.task is not None and not job.task.done():
            job.stage = "cancelling"
            job.task.cancel()
        return job

    def _prune_decision_jobs(self) -> None:
        if len(self.decision_jobs) <= 100:
            return
        for job_id, job in list(self.decision_jobs.items()):
            if job.task is not None and job.task.done():
                del self.decision_jobs[job_id]
            if len(self.decision_jobs) <= 100:
                break

    def get_decision(self, decision_id: str) -> DecisionResult | None:
        return self.decisions.get(decision_id) or self.decision_store.get(decision_id)

    def save_decision(self, result: DecisionResult) -> None:
        result.updated_at = now_iso()
        self.decisions[result.id] = result
        self.decision_store.save(result)

    def replay_decision(self, decision_id: str) -> DecisionResult:
        original = self.get_decision(decision_id)
        if original is None:
            raise KeyError(decision_id)
        replay = original.model_copy(deep=True)
        replay.id = f"dec_{uuid.uuid4().hex[:12]}"
        replay.created_at = stamp()
        replay.updated_at = replay.created_at
        replay.source_mode = "replay"
        replay.replay_of = original.replay_of or original.id
        replay.selected_option_id = None
        replay.selected_at = None
        replay.pilot_plan = None
        replay.outcome = None
        self.save_decision(replay)
        return replay

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
                state.trace.log(
                    "status", message="connecting_qloo_mcp", mode="mcp",
                )
                client = self._client_factory(self.settings, req)
                try:
                    await asyncio.wait_for(
                        client.__aenter__(), timeout=MCP_READINESS_TIMEOUT
                    )
                except asyncio.TimeoutError as exc:
                    raise RuntimeError(
                        "Qloo MCP connection timed out after "
                        f"{MCP_READINESS_TIMEOUT:g} seconds"
                    ) from exc
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
                # server runs get headroom: multi-tool batches + Groq
                # corrective-retry nudges each burn a step
                max_steps=18,
            )
            brief_req = BriefRequest(
                brief=req.brief, region=req.region, audience=req.audience,
                extras={"city": req.city} if req.city else {},
            )
            state.outcome = await asyncio.wait_for(
                runner.run(brief_req), timeout=600.0
            )
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

