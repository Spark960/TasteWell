"""Key-redaction helpers — nothing resembling a credential may hit logs/traces."""

from __future__ import annotations

import re
import threading

_REDACTED = "«redacted»"

_lock = threading.Lock()
_secrets: set[str] = set()

_BEARER = re.compile(r"(?i)(bearer\s+)\S+")
_KEYISH = re.compile(
    r"(?i)((?:api[_-]?key|token|authorization|password)\s*[=:]\s*)\S+"
)


def register_secret(value: str) -> None:
    if value and len(value) >= 8:
        with _lock:
            _secrets.add(value)


def redact(text: str) -> str:
    with _lock:
        secrets = sorted(_secrets, key=len, reverse=True)
    out = text or ""
    for s in secrets:
        out = out.replace(s, _REDACTED)
    out = _BEARER.sub(rf"\g<1>{_REDACTED}", out)
    out = _KEYISH.sub(rf"\g<1>{_REDACTED}", out)
    return out
