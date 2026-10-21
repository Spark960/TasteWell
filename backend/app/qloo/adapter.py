"""QlooAdapter — runs a workflow via `qloo exec` and returns a NormalizedResult.

Invocation verified live (P0): `qloo exec <operation> --input-file <path>` →
envelope JSON on stdout. Inline `--input` is unusable on PS 5.1 (npm shim),
hence the temp-file route. Env (QLOO_API_KEY etc.) forwards from os.environ.

Retries: only when the envelope's error.retryable is true (or the subprocess
itself fails/timeout), max 2 retries, exponential backoff — injectable so
tests don't sleep.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from typing import Callable

from app.qloo.cache import TTLCache
from app.qloo.normalizer import NormalizedResult, normalize_envelope
from app.qloo.redact import redact, register_secret

log = logging.getLogger("tastewell.qloo")

Runner = Callable[[str, str], "subprocess.CompletedProcess[str]"]


def resolve_qloo_bin(qloo_bin: str) -> str:
    """Bare `qloo` fails via subprocess on Windows (npm shims .cmd/.ps1) — resolve it."""
    if os.sep in qloo_bin or os.path.sep in qloo_bin or "/" in qloo_bin:
        return qloo_bin
    return shutil.which(qloo_bin) or qloo_bin


def subprocess_runner(
    qloo_bin: str,
    timeout_s: float,
    env: dict | None = None,
    base_urls: tuple[str, str] = ("https://hackathon.api.qloo.com",) * 2,
) -> Runner:
    qloo_bin = resolve_qloo_bin(qloo_bin)

    def run(operation: str, input_json: str) -> subprocess.CompletedProcess[str]:
        run_env = dict(env if env is not None else os.environ)
        # Hackathon keys only work against the hackathon host; shells that lack
        # $PROFILE-injected vars would otherwise get a misleading QLOO_AUTH.
        base, trusted = base_urls
        run_env.setdefault("QLOO_BASE_URL", base)
        run_env.setdefault("QLOO_TRUSTED_BASE_URL", trusted)
        fd, path = tempfile.mkstemp(prefix="qloo_in_", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(input_json)
            args = [qloo_bin, "exec", operation, "--input-file", path]
            return subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=run_env,
            )
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    return run


class QlooAdapter:
    def __init__(
        self,
        qloo_bin: str = "qloo",
        timeout_s: float = 60.0,
        max_retries: int = 2,
        cache_ttl_s: float = 600.0,
        api_key: str = "",
        sleep: Callable[[float], None] | None = None,
        runner: Runner | None = None,
    ) -> None:
        self.max_retries = max_retries
        self.cache = TTLCache(ttl=cache_ttl_s)
        if api_key:
            register_secret(api_key)
        self._runner = runner or subprocess_runner(qloo_bin, timeout_s)
        self._sleep = sleep or time.sleep

    def cache_key(self, operation: str, payload: dict) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
        return f"{operation}:{digest}"

    def run_workflow(self, operation: str, payload: dict, use_cache: bool = True) -> NormalizedResult:
        key = self.cache_key(operation, payload)
        if use_cache:
            hit = self.cache.get(key)
            if hit is not None:
                log.info("qloo=%s cache=hit key=%s", operation, key)
                return hit

        input_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        attempt = 0
        while True:
            result = self._attempt(operation, input_json)
            if result.status != "error" or not result.retryable or attempt >= self.max_retries:
                break
            attempt += 1
            backoff = 0.5 * (2 ** (attempt - 1))
            log.warning(
                "qloo=%s retryable-error=%s attempt=%d backoff=%.1fs",
                operation, result.error_code, attempt, backoff,
            )
            self._sleep(backoff)

        log.info(
            "qloo=%s status=%s count=%s corr=%s",
            operation,
            result.status,
            result.result_count if result.status != "error" else "-",
            result.correlation_id,
        )
        if use_cache and result.status != "error":
            self.cache.put(key, result)
        return result

    def _attempt(self, operation: str, input_json: str) -> NormalizedResult:
        try:
            proc = self._runner(operation, input_json)
        except (OSError, subprocess.TimeoutExpired) as exc:
            log.error("qloo=%s transport-failure=%r", operation, redact(str(exc)))
            return NormalizedResult(
                status="error",
                operation=operation,
                error_code="QLOO_TRANSPORT",
                retryable=True,
                recovery="Harness subprocess failed or timed out; retry once.",
            )
        raw = (proc.stdout or "").strip()
        if not raw and proc.stderr:
            raw = proc.stderr.strip()
        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError:
            log.error(
                "qloo=%s unparseable rc=%s out=%r err=%r",
                operation, proc.returncode,
                redact(raw[:300]), redact((proc.stderr or "")[:300]),
            )
            return NormalizedResult(
                status="error",
                operation=operation,
                error_code="HARNESS_UNPARSEABLE",
                retryable=False,
                recovery="qloo exec did not emit JSON; check harness install / PATH.",
            )
        return normalize_envelope(operation, envelope)
