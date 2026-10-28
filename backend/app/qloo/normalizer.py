"""Envelope normalization — maps the harness 6-status envelope to a dataclass.

Live-verified shapes (docs/qloo-contract.md):
- success envelope: {schema_version, operation, status, summary?, results?,
  result_count?, provenance, query_intent, execution}
- error envelope:   {error:{code, layer, retryable, recovery}, operation,
  correlation_id} — no `status` field
- needs_input:      resolution.issues[].candidates[] {id, name, type,
  popularity, description?, address?}
- compare_audiences: `results` is ONE object (not a list), no result_count
- trends:           top-level `series[]`, no results
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

STATUSES = ("ok", "empty", "needs_input", "partial", "degraded", "error")


@dataclass(frozen=True)
class NormalizedResult:
    status: str
    operation: str
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    results: list[dict] = field(default_factory=list)
    result_count: int | None = None
    summary: str | None = None
    candidates: list[dict] = field(default_factory=list)
    series: list[dict] = field(default_factory=list)
    error_code: str | None = None
    retryable: bool = False
    recovery: str | None = None
    correlation_id: str | None = None
    raw: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """Has usable data (ok with 0 results is an honest empty, not ok-data)."""
        return self.status in ("ok", "partial", "degraded") and bool(self.results)

    @property
    def abstain(self) -> bool:
        return self.status in ("empty", "needs_input", "error") or (
            self.status in ("ok", "partial", "degraded") and not self.results
        )

    @property
    def data(self) -> list[dict]:
        return self.results or self.series


def normalize_envelope(operation: str, envelope: dict) -> NormalizedResult:
    err = envelope.get("error")
    status = envelope.get("status")

    if err is not None or status is None:
        # Bare error envelope (QLOO_AUTH/QLOO_CONTRACT/TOOL_INPUT): no `status`.
        if err is None:
            return NormalizedResult(
                status="error",
                operation=operation,
                error_code="UNPARSEABLE",
                retryable=False,
                recovery="Envelope had neither `status` nor `error`.",
                raw=envelope,
            )
        return NormalizedResult(
            status="error",
            operation=operation,
            error_code=str(err.get("code", "UNKNOWN")),
            retryable=bool(err.get("retryable", False)),
            recovery=err.get("recovery"),
            correlation_id=envelope.get("correlation_id"),
            raw=envelope,
        )

    if status not in STATUSES:
        return NormalizedResult(
            status="error",
            operation=operation,
            error_code=f"BAD_STATUS:{status}",
            retryable=False,
            recovery=f"Unknown envelope status {status!r}.",
            raw=envelope,
        )

    results = envelope.get("results", [])
    if isinstance(results, dict):
        # compare_audiences shape: single object, no result_count
        results = [results]
    if not isinstance(results, list):
        results = []

    candidates: list[dict] = []
    for issue in envelope.get("resolution", {}).get("issues", []):
        candidates.extend(issue.get("candidates", []))

    series = envelope.get("series", [])
    if not isinstance(series, list):
        series = []

    count = envelope.get("result_count")
    if count is None:
        count = len(results) if results else (len(series) if series else 0)
        if not results and not series:
            count = 0

    return NormalizedResult(
        status=status,
        operation=operation,
        results=results,
        result_count=int(count) if count is not None else None,
        summary=envelope.get("summary"),
        candidates=candidates,
        series=series,
        correlation_id=envelope.get("execution", {}).get("correlation_id"),
        raw=envelope,
    )
