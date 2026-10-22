"""LLM provider shim (D4): OpenAI-compatible chat completions.

Gemini Flash free tier is the default via Google's OpenAI-compat endpoint;
LLM_PROVIDER swaps openai / groq / any base_url in one env line — the wire
format (messages, tools, tool_calls) stays identical.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.qloo.redact import redact, register_secret

log = logging.getLogger("tastewell.llm")

_MAX_429_RETRIES = 3
# Free-tier quota reality (Oct 2026): Groq gpt-oss-120b on-demand = 8k TPM
# but also a rolling ~200k TPD; retry-after can demand minutes when the
# steady-burn release rate is slow. Cap each wait so no single step eats the
# whole 600s run deadline, but let it cover a TPD window (~4 min).
_MAX_429_WAIT = 240.0

_TOOL_VALIDATION = "Tool call validation failed"

_SCHEMA_NUDGE = (
    "Your previous tool call was rejected because its arguments did not "
    "match the tool's declared input schema. Re-issue the tool call with "
    "arguments matching the schema exactly: use only the listed enum values "
    "(e.g. entity_type must be one of artist/book/brand/movie/person/place/"
    "podcast/tv_show/videogame/locality) and include every required field. "
    "If unsure, omit optional fields rather than guessing."
)


@dataclass
class Reply:
    content: str = ""
    tool_calls: list[dict] = field(default_factory=list)  # {id, name, args: dict}
    # Gemini 3.x requires its `extra_content.google.thought_signature` to be
    # echoed back verbatim (message- and tool_call-level) or the next call
    # 400s with "Function call is missing a thought_signature".
    extra_content: Any = None

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


class ProviderConfigError(RuntimeError):
    pass


PROVIDERS: dict[str, dict[str, str]] = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-3.8-flash",
        "key_field": "gemini_api_key",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4.1-mini",
        "key_field": "openai_api_key",
    },
        "groq": {
            "base_url": "https://api.groq.com/openai/v1",
            "default_model": "openai/gpt-oss-120b",
            "key_field": "groq_api_key",
        },
}


class LlmProvider:
    def __init__(
        self,
        provider: str = "gemini",
        api_key: str = "",
        model: str = "",
        base_url: str = "",
        client: httpx.AsyncClient | None = None,
        max_tokens: int = 4096,
        reasoning_effort: str = "low",
    ) -> None:
        # NB: Gemini 3.x counts hidden thinking tokens against max_tokens —
        # a 2k cap truncates output mid-string (finish_reason: length).
        if provider not in PROVIDERS and not base_url:
            raise ProviderConfigError(f"unknown LLM_PROVIDER {provider!r}")
        conf = PROVIDERS.get(provider, {})
        self.base_url = base_url or conf.get("base_url", "")
        self.model = model or conf.get("default_model", "")
        self.api_key = api_key
        if not self.api_key:
            raise ProviderConfigError(
                f"no API key for provider {provider!r} "
                f"(expected env {conf.get('key_field', 'LLM_API_KEY')})"
            )
        register_secret(self.api_key)
        self.max_tokens = max_tokens
        # gpt-oss reasoning burn: full 'high' thinking both adds wall-clock
        # latency and burns daily token quota output-side; low is plenty for
        # a schema-shaped JSON brief.
        self.reasoning_effort = (
            reasoning_effort if "gpt-oss" in self.model else None
        )
        self._client = client or httpx.AsyncClient(timeout=120)
        self._sleep: Any = asyncio.sleep

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def chat(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> Reply:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
        }
        if self.reasoning_effort:
            body["reasoning_effort"] = self.reasoning_effort
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        resp = await self._post(body)
        # Groq validates the model's proposed tool args against the schema
        # and 400s strict (Gemini tolerates slips) — these are random model
        # mistakes: bounded corrective retries, never a user-visible abort.
        if resp.status_code == 400 and _TOOL_VALIDATION in resp.text:
            for attempt in range(2):
                log.warning(
                    "llm tool-args schema slip — corrective retry %d/2",
                    attempt + 1,
                )
                nudged = {
                    **body,
                    "messages": [
                        *messages, {"role": "user", "content": _SCHEMA_NUDGE},
                    ],
                }
                resp = await self._post(nudged)
                if not (resp.status_code == 400
                        and _TOOL_VALIDATION in resp.text):
                    break
        if resp.status_code in (401, 403):
            raise ProviderConfigError(
                f"LLM rejected credentials (HTTP {resp.status_code})"
            )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"LLM HTTP {resp.status_code}: {redact(resp.text[:300])}"
            )
        return self._extract(resp.json())

    async def _post(self, body: dict) -> httpx.Response:
        """POST with bounded backoff for 429 (free-tier caps) and transient
        5xx (free-tier 'high demand' 503s are routine)."""
        attempt = 0
        while True:
            try:
                resp = await self._client.post(
                    f"{self.base_url}/chat/completions",
                    json=body,
                    headers=self._headers(),
                )
            except (httpx.HTTPError, OSError) as exc:
                log.error("llm transport-failure=%r", redact(str(exc)))
                raise RuntimeError(f"LLM transport failure: {exc}") from exc
            wait: float | None = None
            if resp.status_code == 429:
                try:
                    wait = float(resp.headers.get("retry-after", "25"))
                except ValueError:
                    wait = 25.0
                wait = min(wait, _MAX_429_WAIT)
            elif resp.status_code in (500, 502, 503):
                wait = 10.0 * (attempt + 1)
            if wait is None or attempt >= _MAX_429_RETRIES:
                return resp
            attempt += 1
            log.warning(
                "llm HTTP %d — retry %d/%d in %.0fs",
                resp.status_code, attempt, _MAX_429_RETRIES, wait,
            )
            await self._sleep(wait)

    def _extract(self, data: dict) -> Reply:
        try:
            msg = data["choices"][0]["message"]
        except (KeyError, IndexError) as exc:
            raise RuntimeError(
                f"LLM response missing choices[0].message: "
                f"{redact(json.dumps(data)[:300])}"
            ) from exc
        reply = Reply(content=msg.get("content") or "",
                      extra_content=msg.get("extra_content"))
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                log.warning("llm tool_arguments unparseable — treated as {}")
                args = {}
            call = {
                "id": tc.get("id") or f"call_{len(reply.tool_calls)}",
                "name": fn.get("name", ""),
                "args": args,
            }
            if tc.get("extra_content") is not None:
                call["extra_content"] = tc["extra_content"]
            reply.tool_calls.append(call)
        return reply
