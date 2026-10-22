"""Agent tool surface: MCP-backed Qloo tools exposed to the LLM + result shaping.

Schemas come straight from the live `qloo mcp` list_tools response (always in
sync — task 3 in IMPLEMENTATION.md P2). Model-facing payloads are compacted;
full envelopes stay in trace + evidence.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable

from app.qloo.mcp_client import QlooMcpClient
from app.qloo.normalizer import NormalizedResult
from app.qloo.redact import redact
from app.trace import Trace

log = logging.getLogger("tastewell.agent.tools")

_MODEL_KEYS = (
    "id", "name", "type", "subtype", "entity_id", "popularity",
    "affinity", "affinity_rank", "description",
)


def compact_row(row: dict, depth: int = 0) -> dict:
    if depth > 1 or not isinstance(row, dict):
        return row if isinstance(row, (str, int, float)) else {}
    out: dict[str, Any] = {k: row[k] for k in _MODEL_KEYS if k in row}
    for k, v in row.items():
        if isinstance(v, dict) and k not in out:
            out[k] = {k2: compact_row(v2, depth + 1) if isinstance(v2, dict) else v2
                      for k2, v2 in list(v.items())[:6]}
        elif k not in out and isinstance(v, (str, int, float)):
            out[k] = v
    return out


class GroundedTools:
    """Registers LLM tool specs from live MCP tools; dispatches model calls."""

    def __init__(
        self,
        client: QlooMcpClient,
        trace: Trace | None = None,
        model_call: Callable[[str, str, dict], Awaitable[None]] | None = None,
    ) -> None:
        self.client = client
        self.trace = trace
        self._model_call = model_call
        self.evidence: list[dict] = []
        self.calls_made: list[tuple[str, dict]] = []
        # (tool, args) pairs that came back needs_input with zero candidates —
        # re-calling them cannot resolve the ambiguity (P2 live finding), so a
        # repeat gets an honest DEAD_END envelope instead of a fresh Qloo call.
        self._dead_ends: set[str] = set()

    def _call_key(self, name: str, args: dict) -> str:
        return f"{name}|{json.dumps(args, sort_keys=True, ensure_ascii=False)}"

    def llm_specs(self) -> list[dict]:
        specs = []
        for name in sorted(self.client.tools):
            if name == "qloo_capabilities":
                continue  # readiness is the harness's job, not the LLM's
            schema = self.client.tools[name]
            specs.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": _TOOL_DOCS.get(
                        name, f"Qloo {name} workflow"
                    ),
                    "parameters": schema,
                },
            })
        return specs

    async def dispatch(self, name: str, args: dict) -> dict:
        """Run a qloo_* tool; returns the compact model-facing dict."""
        operation = name.removeprefix("qloo_")
        call_key = self._call_key(name, args)
        unknown = (
            self.client.tools
            and name not in self.client.tools
            and name != "qloo_capabilities"
        )
        if call_key in self._dead_ends:
            result = NormalizedResult(
                status="error", operation=operation,
                error_code="DEAD_END", retryable=False,
                recovery=(
                    "This exact call already returned needs_input with no "
                    "candidates — re-calling it cannot help. Abstain from "
                    "this thread (list it in honest_absences) and continue "
                    "with other tools."
                ),
            )
        elif unknown:
            result = NormalizedResult(
                status="error", operation=operation,
                error_code="NO_SUCH_TOOL", retryable=False,
                recovery=f"{name} is not offered by the harness.",
            )
        else:
            result = await self.client.call_tool(operation, args)
            if result.status == "needs_input" and not result.candidates:
                self._dead_ends.add(call_key)
        self._trace_call(name, args, result)
        self.calls_made.append((name, args))
        self.evidence.append(self._evidence(result))
        return self.model_result(result)

    async def safe_dispatch(self, name: str, args: dict) -> dict:
        try:
            return await self.dispatch(name, args)
        except Exception as exc:  # keep the loop alive; honest error to model
            log.error("tool=%s dispatch-crash=%r", name, redact(str(exc)))
            return {
                "tool": name,
                "status": "error",
                "summary": None,
                "error": {
                    "code": "TOOL_CRASH",
                    "retryable": False,
                    "recovery": f"Tool execution crashed: {type(exc).__name__}",
                },
            }

    def _trace_call(
        self, name: str, args: dict, result: NormalizedResult
    ) -> None:
        if self.trace is None:
            return
        self.trace.log("tool_call", tool=name, args=args)
        self.trace.log(
            "tool_result",
            tool=name,
            status=result.status,
            result_count=result.result_count,
            summary=result.summary,
            error_code=result.error_code,
            candidates=[
                {k: c.get(k) for k in ("id", "name", "type", "popularity")}
                for c in result.candidates
            ],
            correlation_id=result.correlation_id,
        )
        if self._model_call is not None:
            pass  # reserved for SSE hooks (P3)

    def _extract_ids(self, result: NormalizedResult) -> list[str]:
        ids: list[str] = []
        for row in result.data:
            if not isinstance(row, dict):
                continue
            for k in ("entity_id", "id", "tag_id"):
                v = row.get(k)
                if isinstance(v, str):
                    ids.append(v)
                    break
            nested = row.get("entity")
            if isinstance(nested, dict):
                v = nested.get("entity_id")
                if isinstance(v, str):
                    ids.append(v)
        return ids[:8]

    def _evidence(self, result: NormalizedResult) -> dict:
        return {
            "tool": f"qloo_{result.operation}",
            "operation": result.operation,
            "status": result.status,
            "summary": result.summary,
            "ids": self._extract_ids(result),
            "result_count": result.result_count,
            "error_code": result.error_code,
            "correlation_id": result.correlation_id,
            "ts": None,
        }

    def model_result(self, result: NormalizedResult) -> dict:
        out: dict[str, Any] = {
            "tool": f"qloo_{result.operation}",
            "status": result.status,
            "summary": result.summary,
        }
        if result.status != "error":
            out["result_count"] = result.result_count
            data = [compact_row(r) if isinstance(r, dict) else r
                    for r in result.data]
            if data:
                out["results"] = data[:10]
            if result.candidates:
                out["candidates"] = [
                    {k: c.get(k) for k in ("id", "name", "type", "popularity",
                                           "description", "address")}
                    for c in result.candidates
                ]
            for w in result.raw.get("warnings") or []:
                out.setdefault("warnings", []).append(w)
        if result.status == "error":
            out["error"] = {
                "code": result.error_code,
                "retryable": result.retryable,
                "recovery": result.recovery,
            }
        return out

    def evidence_with_ts(self, stamp: str) -> list[dict]:
        return [{**e, "ts": stamp} for e in self.evidence]


_TOOL_DOCS = {
    "qloo_find_tags":
        "Resolve free-text vibe/genre words into Qloo tag URNs. Returns "
        "similarly-named tags of DIFFERENT types — candidates are options, "
        "not proof; pick by type + popularity.",
    "qloo_describe":
        "Describe one entity/name — characterization of a concept seed.",
    "qloo_recommend":
        "Recommend entities (artists/brands/...) for a target_type given "
        "tags/entities/location/demographic signals. Ranked by affinity.",
    "qloo_rank":
        "Score a SHORTLIST of concrete options against signals — options must "
        "be provided as a set; scores from separate calls are not comparable.",
    "qloo_where_popular":
        "Where an entity is popular (geohash rows) — catchment/neighborhood "
        "checks.",
    "qloo_compare_audiences":
        "Differences between two audience groups (entities, not raw "
        "demographics) — e.g. locals vs the target audience.",
    "qloo_audience_demographics":
        "Demographic affinities (signed −1..1 = under/over-index) for an "
        "entity — render with aggregate framing.",
    "qloo_entity_tags":
        "An entity's tags/affinities — build the taste profile of a seed.",
    "qloo_trends":
        "Rising/falling interest over time for artist/brand/locality — "
        "NEVER entity_type:'place' (unsupported).",
}
