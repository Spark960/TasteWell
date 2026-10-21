"""Agent loop — brief in, concept brief out, grounded in Qloo MCP tools.

Grounding contract (D10, plan task 4):
- aggregate framing only ("people in this segment/area tend to like…");
- every taste claim cites the tool result ids it came from;
- needs_input → stop and surface candidates (never guess);
- empty/degraded → honest absence / favorable-honest language, abstain
  from that section.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.agent.provider import LlmProvider, Reply
from app.agent.tools import GroundedTools
from app.trace import Trace, now_iso

log = logging.getLogger("tastewell.agent")

AGGREGATE_DISCLAIMER = (
    "Aggregate cultural affinity data — describes group tendencies, "
    "not individual behavior."
)

_SYSTEM_RULES = """\
You are Tastewell, a taste agent for venue & hospitality operators. You answer \
by running Qloo tools first, then writing a concept brief. Voice: concrete, \
practical, operator-facing.

HARD RULES:
1. AGGREGATE FRAMING ONLY — say "people in this segment/area tend to like…". \
Never claim an individual's behavior, never causal claims, never "will buy".
2. Every taste claim in each section must be traceable: cite the Qloo ids \
(tag URNs / entity ids) it came from. Claims that trace to no id are banned.
3. If a tool returns needs_input: STOP expanding that thread — put the \
candidates in "needs_input" (id, name, type, popularity) and say what choice \
would unblock.
4. If a tool returns empty/degraded: say so plainly ("no grounded result — \
the request came back empty") and OMIT that section rather than inventing.
5. Use section names exactly as given. Never mention tools in the prose \
except through citations.
"""


def _system_prompt(mode: str) -> str:
    if mode == "generic":
        return (
            "You are Tastewell but QLOO IS OFF — you have NO tools and NO "
            "taste data. Write the concept brief from general knowledge "
            "alone. Every claim is your guess; you have no evidence ids."
            "\n" + _SYSTEM_RULES.split("\n\n", 1)[1]
        )
    return _SYSTEM_RULES + """

Respond with ONLY a JSON object (no markdown fence, no prose) shaped:
{
  "audience_profile": string,          // aggregate framing
  "menu_tilt": [string],
  "music_programming": [string],
  "adjacent_brands": [string],
  "tag_themes": [string],              // each: "tag name — id"
  "needs_input": {                     // ONLY if a tool returned needs_input
    "reason": string,
    "candidates": [{"id","name","type","popularity"}]
  },
  "honest_absences": [string]          // sections you are abstaining on
}
Each string in a section may end with " (id:<id>)" citations; tag_themes "
entries must carry the tag URN. If nothing grounded, return mostly-empty
sections plus honest_absences."""


@dataclass
class BriefRequest:
    brief: str
    region: str = ""
    audience: str = ""
    extras: dict[str, str] = field(default_factory=dict)


@dataclass
class AgentOutcome:
    mode: str
    brief: dict = field(default_factory=dict)
    raw_final: str = ""
    needs_input: dict | None = None
    status: str = "ok"  # ok | needs_input | aborted
    steps: int = 0


def _user_prompt(req: BriefRequest) -> str:
    lines = [
        f"Venue concept brief: {req.brief}",
        f"Region / catchment: {req.region or 'not specified'}",
        f"Target audience: {req.audience or 'not specified'}",
    ]
    for k, v in req.extras.items():
        lines.append(f"{k}: {v}")
    return "\n".join(lines)


def wire_tool_call(reply: Reply) -> dict:
    """Serialize Reply.tool_calls back to the OpenAI wire format.

    Provider-specific opaque fields (Gemini `extra_content`) are echoed
    verbatim when present — required for Gemini 3.x thought signatures.
    """
    msg: dict = {
        "role": "assistant",
        "content": reply.content or "",
        "tool_calls": [
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": json.dumps(tc["args"], ensure_ascii=False),
                },
                **({"extra_content": tc["extra_content"]}
                   if tc.get("extra_content") is not None else {}),
            }
            for tc in reply.tool_calls
        ],
    }
    if reply.extra_content is not None:
        msg["extra_content"] = reply.extra_content
    return msg


_JSON_OBJ = re.compile(r"\{.*\}", re.DOTALL)


def parse_brief_json(content: str) -> dict | None:
    """Extract the concept brief. Tolerant to fences/prose wrappers."""
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[^\n]*\n?|\n?```\s*$", "", text).strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        m = _JSON_OBJ.search(text)
        if m:
            try:
                obj = json.loads(m.group(0))
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                return None
    return None


Chooser = Callable[[list[dict]], Awaitable[str | None]]


class AgentRunner:
    def __init__(
        self,
        provider: LlmProvider,
        tools: GroundedTools | None = None,
        trace: Trace | None = None,
        max_steps: int = 10,
        chooser: Chooser | None = None,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self.provider = provider
        self.tools = tools
        self.trace = trace
        self.max_steps = max_steps
        self.chooser = chooser
        self._clock = clock or (lambda: now_iso())

    @property
    def grounded(self) -> bool:
        return self.tools is not None and bool(self.tools.client.tools)

    async def run(self, req: BriefRequest) -> AgentOutcome:
        mode = "grounded" if self.grounded else "generic"
        if self.trace is not None:
            self.trace.log(
                "status", message="run_started", mode=mode, **{
                    "brief": req.brief, "region": req.region,
                    "audience": req.audience,
                }
            )
        specs = self.tools.llm_specs() if self.grounded else None
        messages: list[dict] = [
            {"role": "system", "content": _system_prompt(mode)},
            {"role": "user", "content": _user_prompt(req)},
        ]
        return await self._run_messages(req, mode, messages, specs)

    async def _run_messages(
        self,
        req: BriefRequest,
        mode: str,
        messages: list[dict],
        specs: list[dict] | None,
        budget: int | None = None,
    ) -> AgentOutcome:
        steps_left = budget if budget is not None else self.max_steps
        outcome = AgentOutcome(mode=mode)
        while steps_left > 0:
            steps_left -= 1
            outcome.steps += 1
            reply = await self.provider.chat(messages, tools=specs)
            self.trace and self.trace.log(
                "llm", step=outcome.steps,
                tool_calls=[tc["name"] for tc in reply.tool_calls],
            )
            if reply.wants_tools:
                if not self.grounded:
                    # Defensive: generic mode must never run tools.
                    messages.append({
                        "role": "user",
                        "content": "Tools are disabled (Qloo-off mode). "
                                   "Answer without them.",
                    })
                    continue
                messages.append(wire_tool_call(reply))
                for tc in reply.tool_calls:
                    result = await self.tools.safe_dispatch(
                        tc["name"], tc["args"]
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": tc["name"],
                        "content": json.dumps(result, ensure_ascii=False),
                    })
                continue
            # No tool calls → treat as the final answer.
            outcome.raw_final = reply.content or ""
            brief = parse_brief_json(outcome.raw_final)
            if brief is None:
                log.warning("final reply not parseable as JSON brief")
                outcome.status = "aborted"
                self.trace and self.trace.log(
                    "status", message="unparseable_final",
                    content=reply.content or "",
                )
                outcome.brief = {
                    "raw": outcome.raw_final,
                    "disclaimers": [AGGREGATE_DISCLAIMER],
                }
                return outcome
            ni = brief.get("needs_input")
            if isinstance(ni, dict) and ni.get("candidates") and self.chooser:
                pick = await self.chooser(
                    ni.get("candidates", [])
                )
                if pick:
                    self.trace and self.trace.log(
                        "user_choice", pick=pick
                    )
                    messages.append({
                        "role": "user",
                        "content": (
                            f"The user picked this Qloo candidate: {pick}. "
                            "Re-run the affected tool with this id, then "
                            "proceed to the final JSON brief."
                        ),
                    })
                    return await self._run_messages(
                        req, mode, messages, specs, budget=steps_left
                    )
            outcome.brief = self._finalize(brief)
            outcome.needs_input = (
                ni if isinstance(ni, dict) and ni.get("candidates") else None
            )
            if outcome.needs_input:
                outcome.status = "needs_input"
            self.trace and self.trace.log("final", brief=outcome.brief)
            return outcome
        outcome.status = "aborted"
        outcome.brief = {
            "raw": "agent step budget exhausted",
            "disclaimers": [AGGREGATE_DISCLAIMER],
        }
        self.trace and self.trace.log("status", message="step_budget_exhausted")
        return outcome

    def _finalize(self, brief: dict) -> dict:
        brief = dict(brief)
        brief.pop("needs_input", None)  # surfaced via outcome, not in doc
        brief["evidence"] = (
            self.tools.evidence_with_ts(self._clock())
            if self.tools else []
        )
        brief["disclaimers"] = [AGGREGATE_DISCLAIMER]
        brief["mode"] = "grounded" if self.grounded else "generic"
        return brief
