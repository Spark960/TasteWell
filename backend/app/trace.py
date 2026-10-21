"""Trace log — every tool call/result + statuses, redacted, saveable.

P2: written to trace.json via the CLI. P3 will turn this into the SSE bus.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any


def now_iso(clock: Any | None = None) -> str:
    if clock is not None:
        return clock()
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"


@dataclass
class Trace:
    run_id: str
    events: list[dict] = field(default_factory=list)
    clock: Any | None = None

    def log(self, type_: str, **data: Any) -> dict:
        ev = {"ts": now_iso(self.clock), "type": type_, **data}
        self.events.append(ev)
        return ev

    def to_dict(self) -> dict:
        return {"run_id": self.run_id, "events": self.events}

    def dump(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def full_text(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
