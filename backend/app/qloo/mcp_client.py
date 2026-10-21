"""Stdio MCP client around `qloo mcp` — the shipped agent path (D5).

Live-verified (P2 probe): `qloo.CMD mcp` spawns via anyio/stdio from Python
3.12 on Windows, answers initialize, and exposes the 10 expected tools
(qloo_capabilities + 9 qloo_<workflow>). Every tool call returns the SAME
envelope as `qloo exec` (status/summary/results/result_count/error...), so we
reuse normalize_envelope.

Env rule (kit §2.1): the subprocess must see QLOO_API_KEY — we build
env = dict(os.environ) ourselves, never bare.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import shutil
import time
from typing import Any, Awaitable, Callable

from app.qloo.normalizer import NormalizedResult, normalize_envelope
from app.qloo.redact import redact, register_secret

log = logging.getLogger("tastewell.qloo.mcp")


def resolve_qloo_bin(qloo_bin: str) -> str:
    if "/" in qloo_bin or os.sep in qloo_bin:
        return qloo_bin
    return shutil.which(qloo_bin) or qloo_bin


async def parse_content(operation: str, result: Any) -> NormalizedResult:
    """Extract the JSON envelope from CallToolResult content parts.

    isError=True only for protocol-level failures; valid envelopes (including
    `error` status ones) come through normally, so try to parse text first.
    """
    parts = list(getattr(result, "content", None) or [])
    parsed: dict | None = None
    for part in parts:
        text = getattr(part, "text", None)
        if not text:
            continue
        try:
            parsed = json.loads(text)
            break
        except json.JSONDecodeError:
            continue
    if parsed is None:
        raw = " ".join(getattr(p, "text", "") for p in parts)[:300]
        log.error("mcp=%s unparseable result=%r", operation, redact(raw))
        return NormalizedResult(
            status="error",
            operation=operation,
            error_code="HARNESS_UNPARSEABLE",
            retryable=False,
            recovery="qloo mcp returned no JSON content; check harness/PATH.",
        )
    return normalize_envelope(operation, parsed)


class QlooMcpClient:
    """Async context manager. `call_tool(op, payload) -> NormalizedResult`.

    `session` may be injected (tests); anything with `list_tools` and
    `call_tool` coroutines works.
    """

    def __init__(
        self,
        qloo_bin: str = "qloo",
        api_key: str = "",
        base_urls: tuple[str, str] = ("https://hackathon.api.qloo.com",) * 2,
        env: dict[str, str] | None = None,
        max_retries: int = 2,
        sleep: Callable[[float], None] = time.sleep,
        session: Any = None,
    ) -> None:
        self.qloo_bin = resolve_qloo_bin(qloo_bin)
        self.max_retries = max_retries
        self._sleep = sleep
        self._session = session
        self._api_key = api_key
        self._base, self._trusted = base_urls
        self._env = env
        if api_key:
            register_secret(api_key)
        self._cm_stack: contextlib.AsyncExitStack | None = None
        self.read_stream = None
        self.write_stream = None
        self.tools: dict[str, dict] = {}
        self.capabilities: NormalizedResult | None = None

    async def __aenter__(self) -> "QlooMcpClient":
        if self._session is not None:
            tools = await self._session.list_tools()
            self._absorb_tools(getattr(tools, "tools", tools))
            return self
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        run_env = dict(self._env if self._env is not None else os.environ)
        # Hackathon keys only work against the hackathon host; shells lacking
        # the $PROFILE vars would otherwise give a misleading QLOO_AUTH.
        if self._api_key:
            run_env.setdefault("QLOO_API_KEY", self._api_key)
        run_env.setdefault("QLOO_BASE_URL", self._base)
        run_env.setdefault("QLOO_TRUSTED_BASE_URL", self._trusted)
        params = StdioServerParameters(
            command=self.qloo_bin, args=["mcp"], env=run_env
        )
        self._cm_stack = contextlib.AsyncExitStack()
        read, write = await self._cm_stack.enter_async_context(
            stdio_client(params)
        )
        session = await self._cm_stack.enter_async_context(
            ClientSession(read, write)
        )
        self._session = session
        self.read_stream, self.write_stream = read, write
        init = await session.initialize()
        log.info(
            "mcp connected server=%s v=%s",
            init.server_info.name,
            init.server_info.version,
        )
        tools = await session.list_tools()
        self._absorb_tools(getattr(tools, "tools", tools))
        if "qloo_capabilities" in self.tools:
            # Readiness check without any Qloo data call (plan task 2).
            self.capabilities = await self.call_tool("capabilities", {})
            log.info(
                "mcp readiness status=%s contract=%s",
                self.capabilities.status,
                self.capabilities.raw.get("contract_version", "?"),
            )
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self._session = None
        if self._cm_stack is not None:
            await self._cm_stack.aclose()
            self._cm_stack = None
        self.read_stream = self.write_stream = None
        self.tools = {}

    def _absorb_tools(self, tool_list: Any) -> None:
        for t in tool_list:
            self.tools[t.name] = dict(t.input_schema or {})

    async def tool_specs(self) -> dict[str, dict]:
        return dict(self.tools)

    def _clean_payload(self, payload: dict) -> dict:
        return {k: v for k, v in payload.items() if v is not None}

    async def call_once(self, operation: str, payload: dict) -> NormalizedResult:
        tool = f"qloo_{operation}"
        if tool not in self.tools:
            return NormalizedResult(
                status="error",
                operation=operation,
                error_code="NO_SUCH_TOOL",
                retryable=False,
                recovery=(
                    f"{tool} not offered by server; available: "
                    f"{sorted(self.tools)}"
                ),
            )
        try:
            result = await self._session.call_tool(
                tool, self._clean_payload(payload)
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # transport-level (spawn/pipe/timeout)
            log.error("mcp=%s transport-failure=%r", operation, redact(str(exc)))
            return NormalizedResult(
                status="error",
                operation=operation,
                error_code="QLOO_TRANSPORT",
                retryable=True,
                recovery="MCP transport failed; retry once.",
            )
        if operation == "capabilities":
            # qloo_capabilities returns the raw contract manifest, not a
            # 6-status envelope — treat manifest presence as ok.
            try:
                manifest = json.loads(result.content[0].text)
            except (json.JSONDecodeError, IndexError, AttributeError):
                return NormalizedResult(
                    status="error", operation=operation,
                    error_code="HARNESS_UNPARSEABLE", retryable=False,
                    recovery="qloo_capabilities returned no JSON manifest.",
                )
            if "manifest_schema_version" not in manifest:
                return NormalizedResult(
                    status="error", operation=operation,
                    error_code="CAPABILITY_NO_MANIFEST", retryable=False,
                    recovery="qloo_capabilities JSON lacks manifest fields.",
                )
            return NormalizedResult(
                status="ok",
                operation="capabilities",
                result_count=len(manifest.get("operations") or []),
                raw=manifest,
            )
        return await parse_content(operation, result)

    async def call_tool(
        self, operation: str, payload: dict
    ) -> NormalizedResult:
        attempt = 0
        result = await self.call_once(operation, payload)
        while (
            result.status == "error"
            and result.retryable
            and attempt < self.max_retries
        ):
            attempt += 1
            backoff = 0.5 * (2 ** (attempt - 1))
            log.warning(
                "mcp=%s retryable-error=%s attempt=%d backoff=%.1fs",
                operation, result.error_code, attempt, backoff,
            )
            await asyncio.to_thread(self._sleep, backoff)
            result = await self.call_once(operation, payload)
        log.info(
            "mcp=%s status=%s count=%s corr=%s",
            operation,
            result.status,
            result.result_count if result.status != "error" else "-",
            result.correlation_id,
        )
        return result


type McpSessionFactory = Callable[[], Awaitable[Any]]
