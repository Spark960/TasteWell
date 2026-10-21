"""Agent loop tests — scripted provider + fake MCP client, fully in-memory."""

from __future__ import annotations

import json

import pytest

from app.agent.loop import (
    AGGREGATE_DISCLAIMER,
    AgentRunner,
    BriefRequest,
    parse_brief_json,
)
from app.agent.provider import Reply
from app.agent.tools import GroundedTools
from app.qloo.normalizer import NormalizedResult
from app.trace import Trace

JAZZ_ID = "urn:tag:genre:music:jazz"
JAZZ = [{"id": JAZZ_ID, "name": "Jazz", "type": "urn:tag:genre:music",
         "popularity": 0.9997}]

OK_FIND_TAGS = NormalizedResult(
    status="ok", operation="find_tags", results=JAZZ, result_count=1,
    summary="1 tag for jazz", correlation_id="corr-9",
)

FINAL_BRIEF = {
    "audience_profile": f"People in this area tend to like jazz [{JAZZ_ID}].",
    "menu_tilt": [],
    "music_programming": [f"Live jazz sets before 8pm ({JAZZ_ID})"],
    "adjacent_brands": [],
    "tag_themes": [f"Jazz — {JAZZ_ID}"],
    "honest_absences": ["trends check skipped (no artist proxy)"],
}


class FakeProvider:
    """Scripted Replies; records every chat() call."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.seen: list[tuple[tuple, object]] = []

    async def chat(self, messages, tools=None):
        self.seen.append((tuple(messages), tools))
        # no reply left → keep answering plainly (model hang safety in tests)
        return self.replies.pop(0) if self.replies else Reply(content="{}")


class FakeClient:
    tools = {"qloo_find_tags": {"type": "object", "properties": {}}}

    def __init__(self, results):
        self.results = list(results)
        self.ops: list[tuple[str, dict]] = []

    async def call_tool(self, operation, payload):
        self.ops.append((operation, dict(payload)))
        return self.results.pop(0)


def grounded_runner(provider, client, **kw):
    trace = Trace(run_id="r1")
    tools = GroundedTools(client=client, trace=trace)
    runner = AgentRunner(provider=provider, tools=tools, trace=trace, **kw)
    return runner, tools


@pytest.mark.asyncio
async def test_grounded_happy_path():
    provider = FakeProvider([
        Reply(tool_calls=[
            {"id": "t1", "name": "qloo_find_tags",
             "args": {"query": "jazz", "limit": 2}}
        ]),
        Reply(content=json.dumps(FINAL_BRIEF)),
    ])
    client = FakeClient([OK_FIND_TAGS])
    runner, tools = grounded_runner(provider, client, max_steps=5)
    outcome = await runner.run(BriefRequest("natural wine bar", "Brooklyn",
                                            "millennials"))
    assert outcome.status == "ok"
    assert client.ops == [("find_tags", {"query": "jazz", "limit": 2})]
    ev = outcome.brief["evidence"]
    assert ev and ev[0]["ids"] == [JAZZ_ID]
    assert ev[0]["tool"] == "qloo_find_tags"
    assert ev[0]["status"] == "ok"
    assert AGGREGATE_DISCLAIMER in outcome.brief["disclaimers"]
    assert outcome.brief["mode"] == "grounded"
    # the model saw the tool result as role:tool with compact data
    second_call_messages, second_call_tools = provider.seen[1]
    tool_msgs = [m for m in second_call_messages if m["role"] == "tool"]
    assert tool_msgs and JAZZ_ID in tool_msgs[0]["content"]
    assert tools.llm_specs()[0]["function"]["name"] == "qloo_find_tags"
    assert "qloo_capabilities" not in [s["function"]["name"]
                                       for s in tools.llm_specs()]


@pytest.mark.asyncio
async def test_tool_result_status_flow_and_no_such_tool():
    provider = FakeProvider([
        Reply(tool_calls=[
            {"id": "t1", "name": "qloo_bogus", "args": {}},
            {"id": "t2", "name": "qloo_find_tags", "args": {"query": "jazz"}},
        ]),
        Reply(content=json.dumps(FINAL_BRIEF)),
    ])
    client = FakeClient([OK_FIND_TAGS])
    runner, _ = grounded_runner(provider, client, max_steps=5)
    outcome = await runner.run(BriefRequest("x"))
    assert outcome.status == "ok"
    second_messages, _ = provider.seen[1]
    tool_msgs = [m for m in second_messages if m["role"] == "tool"]
    assert len(tool_msgs) == 2
    bogus = json.loads(tool_msgs[0]["content"])
    assert bogus["error"]["code"] == "NO_SUCH_TOOL"
    assert bogus["status"] == "error"


@pytest.mark.asyncio
async def test_needs_input_chooser_feeds_pick_and_loop_continues():
    NEEDED = {
        "audience_profile": "",
        "needs_input": {
            "reason": "five Jazzes",
            "candidates": [
                {"id": JAZZ_ID, "name": "Jazz",
                 "type": "urn:tag:genre:music", "popularity": 0.9997}
            ],
        },
    }
    picks: list[list[dict]] = []

    async def chooser(candidates):
        picks.append(candidates)
        return f"{JAZZ_ID} (name: Jazz)"

    provider = FakeProvider([
        Reply(content=json.dumps(NEEDED)),
        Reply(tool_calls=[
            {"id": "t9", "name": "qloo_find_tags", "args": {}}],
        ),
        Reply(content=json.dumps(FINAL_BRIEF)),
    ])
    client = FakeClient([NormalizedResult(
        status="ok", operation="find_tags", results=JAZZ, result_count=1,
        summary="resolved")])
    trace = Trace(run_id="r2")
    tools = GroundedTools(client=client, trace=trace)
    runner = AgentRunner(provider=provider, tools=tools, trace=trace,
                         chooser=chooser, max_steps=6)
    outcome = await runner.run(BriefRequest("jazz bar"))
    assert outcome.status == "ok"
    assert picks and picks[0][0]["id"] == JAZZ_ID
    first_resume, _ = provider.seen[1]
    assert any(JAZZ_ID in (m.get("content") or "")
               for m in first_resume if m["role"] == "user")
    kinds = [e["type"] for e in trace.events]
    assert "user_choice" in kinds and "final" in kinds


@pytest.mark.asyncio
async def test_generic_mode_never_runs_tools():
    provider = FakeProvider([
        Reply(tool_calls=[{"id": "t1", "name": "qloo_find_tags",
                           "args": {"query": "jazz"}}]),
        Reply(content=json.dumps(FINAL_BRIEF)),
    ])
    runner = AgentRunner(provider=provider, tools=None, max_steps=5)
    outcome = await runner.run(BriefRequest("x"))
    assert outcome.brief["mode"] == "generic"
    assert outcome.brief["evidence"] == []
    assert provider.seen[1][0][-1]["role"] == "user"
    assert "Tools are disabled" in provider.seen[1][0][-1]["content"]


@pytest.mark.asyncio
async def test_step_budget_aborts():
    provider = FakeProvider([
        Reply(tool_calls=[{"id": f"t{i}", "name": "qloo_find_tags",
                           "args": {}}]) for i in range(20)
    ])
    client = FakeClient([OK_FIND_TAGS] * 20)
    runner, _ = grounded_runner(provider, client, max_steps=3)
    outcome = await runner.run(BriefRequest("x"))
    assert outcome.status == "aborted"
    assert outcome.brief["disclaimers"] == [AGGREGATE_DISCLAIMER]


@pytest.mark.asyncio
async def test_unparseable_final_honest_abort():
    provider = FakeProvider([Reply(content="I wrote prose, no JSON")])
    client = FakeClient([])
    runner, _ = grounded_runner(provider, client, max_steps=3)
    outcome = await runner.run(BriefRequest("x"))
    assert outcome.status == "aborted"
    assert outcome.brief["raw"] == "I wrote prose, no JSON"


def test_parse_brief_json_variants():
    assert parse_brief_json('{"audience_profile": "x"}') == {
        "audience_profile": "x"
    }
    assert parse_brief_json(
        "```json\n{\"audience_profile\": \"x\"}\n```"
    ) == {"audience_profile": "x"}
    assert parse_brief_json(
        'Here it is: {"audience_profile": "x"} — thanks!'
    ) == {"audience_profile": "x"}
    assert parse_brief_json("not json") is None
