"""SSE plumbing — per-run event bus + streaming trace (P3 file-map: api/stream.py).

Every Trace.log event is mirrored to subscriber asyncio.queues so any number
of SSE consumers can attach at any time; late subscribers replay the buffered
events first (run tasks buffer in trace.events regardless of listeners).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable

from app.qloo.redact import redact
from app.trace import Trace


def sse_line(event: dict) -> str:
    # Redaction filter per plan task 2: no credential-looking text leaves.
    payload = redact(json.dumps(event, ensure_ascii=False, default=str))
    return f"data: {payload}\n\n"


class SseBus:
    """Fan-out of trace events to any number of SSE subscribers."""

    def __init__(self) -> None:
        self._subs: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subs.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._subs:
            self._subs.remove(q)

    def publish(self, event: dict) -> None:
        for q in list(self._subs):
            q.put_nowait(event)

    def sub_count(self) -> int:
        return len(self._subs)


class StreamingTrace(Trace):
    """Trace that mirrors every logged event into a bus callback.

    log() is synchronous and always called from inside the run's event loop
    task, so put_nowait fan-out is race-free.
    """

    def __init__(self, run_id: str, on_event: Callable[[dict], None] | None = None,
                 **kwargs: Any) -> None:
        super().__init__(run_id=run_id, **kwargs)
        self.on_event = on_event

    def log(self, type_: str, **data: Any) -> dict:
        ev = super().log(type_, **data)
        if self.on_event is not None:
            self.on_event(ev)
        return ev
