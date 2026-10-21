"""Tiny LRU+TTL cache for envelope results (quota hygiene, IMPLEMENTATION.md §5-P1.4)."""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any, Callable


class TTLCache:
    def __init__(
        self,
        maxsize: int = 128,
        ttl: float = 600.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._maxsize = maxsize
        self._ttl = ttl
        self._clock = clock
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any | None:
        try:
            at, value = self._store[key]
        except KeyError:
            self.misses += 1
            return None
        if self._clock() - at > self._ttl:
            del self._store[key]
            self.misses += 1
            return None
        self._store.move_to_end(key)
        self.hits += 1
        return value

    def put(self, key: str, value: Any) -> None:
        self._store[key] = (self._clock(), value)
        self._store.move_to_end(key)
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()
        self.hits = 0
        self.misses = 0
