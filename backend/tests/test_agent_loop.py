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
from fakes import FakeClient, FakeProvider, FINAL_BRIEF, JAZZ_ID, JAZZ, OK_FIND_TAGS


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


@pytest.mark.asyncio
async def test_needs_input_zero_candidates_repeat_is_dead_end():
    """Same tool+args twice, first returns needs_input with no candidates ->
    second call is short-circuited with an honest DEAD_END envelope and the
    fake client is not hit again (regression: agent looped on it, run hung)."""
    provider = FakeProvider([
        Reply(tool_calls=[{"id": "t1", "name": "qloo_audience_demographics",
                           "args": {"entity": "millennials", "limit": 5}}]),
        Reply(tool_calls=[{"id": "t2", "name": "qloo_audience_demographics",
                           "args": {"entity": "millennials", "limit": 5}}]),
        Reply(content=json.dumps(FINAL_BRIEF)),
    ])
    ni = NormalizedResult(
        status="needs_input", operation="audience_demographics",
        result_count=0, candidates=[],
        summary="Choose the intended Qloo entity.",
    )
    client = FakeClient([ni])
    client.tools["qloo_audience_demographics"] = {"type": "object"}
    runner, tools = grounded_runner(provider, client, max_steps=6)
    outcome = await runner.run(BriefRequest("natural wine bar"))
    assert outcome.status == "ok"
    # client hit exactly ONCE (repeat was short-circuited)
    assert len(client.ops) == 1
    dead = [
        ev for ev in tools.trace.events
        if ev.get("type") == "tool_result" and ev.get("error_code") == "DEAD_END"
    ]
    assert dead and dead[0]["status"] == "error"

@pytest.mark.asyncio
async def test_zero_candidate_needs_input_bans_tool_for_whole_run():
    """Any args for a tool that dead-ended once must short-circuit — the live
    failure used three different arg shapes for the same zero-candidate
    needs_input (exact-match guard was too narrow)."""
    provider = FakeProvider([
        Reply(tool_calls=[{"id": "t1", "name": "qloo_audience_demographics",
                           "args": {"entity": "millennials", "limit": 5}}]),
        Reply(tool_calls=[{"id": "t2", "name": "qloo_audience_demographics",
                           "args": {"entity": "gen z", "limit": 5}}]),
        Reply(content=json.dumps(FINAL_BRIEF)),
    ])
    ni = NormalizedResult(
        status="needs_input", operation="audience_demographics",
        result_count=0, candidates=[],
        summary="Choose the intended Qloo entity.",
    )
    client = FakeClient([ni])
    client.tools["qloo_audience_demographics"] = {"type": "object"}
    runner, tools = grounded_runner(provider, client, max_steps=6)
    outcome = await runner.run(BriefRequest("natural wine bar"))
    assert outcome.status == "ok"
    assert len(client.ops) == 1
    dead = [
        ev for ev in tools.trace.events
        if ev.get("type") == "tool_result" and ev.get("error_code") == "DEAD_END"
    ]
    assert dead


@pytest.mark.asyncio
async def test_tag_urn_in_entity_args_rejected_without_qloo_call():
    """urn:tag:* ids must never reach entity-only args (live-verified to
    always return zero-candidate needs_input and loop the model)."""
    provider = FakeProvider([
        Reply(tool_calls=[{"id": "t1", "name": "qloo_entity_tags",
                           "args": {"entities": [JAZZ_ID]}}]),
        Reply(content=json.dumps(FINAL_BRIEF)),
    ])
    client = FakeClient([])
    client.tools["qloo_entity_tags"] = {"type": "object"}
    runner, tools = grounded_runner(provider, client, max_steps=4)
    outcome = await runner.run(BriefRequest("x"))
    assert outcome.status == "ok"
    assert client.ops == []
    tool_msg = [
        m for m in provider.seen[1][0] if m["role"] == "tool"
    ][0]
    body = json.loads(tool_msg["content"])
    assert body["status"] == "error"
    assert body["error"]["code"] == "TAG_IN_ENTITY_ARGS"


def test_llm_specs_default_trimmed_to_budget_tools():
    client = FakeClient([])
    for name in (
        "qloo_find_tags", "qloo_describe", "qloo_recommend",
        "qloo_where_popular", "qloo_rank", "qloo_entity_tags",
        "qloo_audience_demographics", "qloo_compare_audiences",
        "qloo_trends", "qloo_capabilities",
    ):
        client.tools[name] = {"type": "object"}
    names = [s["function"]["name"] for s in GroundedTools(client=client).llm_specs()]
    assert names == sorted([
        "qloo_find_tags", "qloo_describe",
        "qloo_recommend", "qloo_where_popular",
    ])
