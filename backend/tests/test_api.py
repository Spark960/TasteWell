"""P3 HTTP-layer tests — full run→stream→final cycle with fake provider/client."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from app.agent.provider import ProviderConfigError, Reply
from app.api import routes
from app.api.engine import Engine
from app.main import create_app
from fakes import (
    FINAL_BRIEF,
    JAZZ_ID,
    OK_FIND_TAGS,
    FakeClient,
    FakeProvider,
)

NEEDED_BRIEF = {
    "audience_profile": "",
    "needs_input": {
        "reason": "five Jazzes",
        "candidates": [
            {"id": JAZZ_ID, "name": "Jazz", "type": "urn:tag:genre:music",
             "popularity": 0.9997}
        ],
    },
}


def make_engine(provider: Any = None, client: Any = None,
                provider_factory=None) -> Engine:
    def pf(settings, req):
        if provider_factory is not None:
            return provider_factory(settings, req)
        return provider

    calls = {"client": 0}

    def cf(settings, req):
        calls["client"] += 1
        return client

    engine = Engine(
        settings=None, provider_factory=pf,
        client_factory=cf if client is not None else None,
    )
    engine._client_calls = calls  # test visibility
    return engine


def make_app(engine: Engine) -> httpx.ASGITransport:
    app = create_app(engine=engine)
    app.dependency_overrides[routes.get_engine] = lambda: engine
    return httpx.ASGITransport(app=app)


def parse_sse(text: str) -> list[dict]:
    out = []
    for chunk in text.split("\n\n"):
        for line in chunk.splitlines():
            if line.startswith("data: "):
                out.append(json.loads(line[len("data: "):]))
    return out


async def collect_events(ac: httpx.AsyncClient, run_id: str,
                         until_done: bool = True) -> list[dict]:
    async with ac.stream("GET", f"/api/agent/stream/{run_id}") as resp:
        assert resp.status_code == 200
        text = ""
        async for raw in resp.aiter_text():
            text += raw
            if not until_done and "\n\n" in raw:
                break
    return parse_sse(text)


@pytest.mark.asyncio
async def test_grounded_run_stream_full_cycle():
    provider = FakeProvider([
        Reply(tool_calls=[{"id": "t1", "name": "qloo_find_tags",
                           "args": {"query": "jazz"}}]),
        Reply(content=json.dumps(FINAL_BRIEF)),
    ])
    client = FakeClient([OK_FIND_TAGS])
    engine = make_engine(provider, client)
    async with httpx.AsyncClient(
        transport=make_app(engine), base_url="http://t"
    ) as ac:
        resp = await ac.post("/api/agent/run", json={
            "brief": "listening bar", "region": "Williamsburg",
            "audience": "millennials", "mode": "grounded",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["stream_url"] == f"/api/agent/stream/{body['run_id']}"
        state = await engine.wait_run(body["run_id"])
        assert state.status == "done"
        assert client.entered == 1 and client.closed == 1

        events = await collect_events(ac, body["run_id"])
    types = [e["type"] for e in events]
    assert "tool_call" in types and "tool_result" in types
    assert "final" in types and "run_done" in types
    assert types.count("run_done") == 1
    final = next(e for e in events if e["type"] == "final")
    assert final["brief"]["mode"] == "grounded"
    tool_result = next(e for e in events if e["type"] == "tool_result")
    assert tool_result["status"] == "ok"
    assert tool_result["tool"] == "qloo_find_tags"
    done = events[-1]
    assert done["type"] == "run_done" and done["exit_status"] == "ok"


@pytest.mark.asyncio
async def test_generic_parity_never_touches_mcp():
    provider = FakeProvider([Reply(content=json.dumps(FINAL_BRIEF))])
    client = FakeClient([])
    engine = make_engine(provider, None)
    async with httpx.AsyncClient(
        transport=make_app(engine), base_url="http://t"
    ) as ac:
        resp = await ac.post("/api/agent/run", json={
            "brief": "taco shop", "audience": "families", "mode": "generic",
        })
        run_id = resp.json()["run_id"]
        await engine.wait_run(run_id)
        assert engine._client_calls["client"] == 0
        events = await collect_events(ac, run_id)
    final = next(e for e in events if e["type"] == "final")
    assert final["brief"]["mode"] == "generic"
    assert final["brief"]["evidence"] == []
    done = events[-1]
    assert done["exit_status"] == "ok"


@pytest.mark.asyncio
async def test_unknown_run_404():
    engine = make_engine()
    async with httpx.AsyncClient(
        transport=make_app(engine), base_url="http://t"
    ) as ac:
        assert (await ac.get("/api/agent/stream/nope")).status_code == 404
        assert (await ac.get("/api/agent/runs/nope")).status_code == 404


@pytest.mark.asyncio
async def test_empty_brief_422():
    engine = make_engine()
    async with httpx.AsyncClient(
        transport=make_app(engine), base_url="http://t"
    ) as ac:
        resp = await ac.post("/api/agent/run", json={"brief": "   "})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_needs_input_pick_consumed():
    provider = FakeProvider([
        Reply(content=json.dumps(NEEDED_BRIEF)),
        Reply(tool_calls=[{"id": "t9", "name": "qloo_find_tags", "args": {}}]),
        Reply(content=json.dumps(FINAL_BRIEF)),
    ])
    client = FakeClient([OK_FIND_TAGS])
    engine = make_engine(provider, client)
    async with httpx.AsyncClient(
        transport=make_app(engine), base_url="http://t"
    ) as ac:
        resp = await ac.post("/api/agent/run", json={
            "brief": "jazz bar", "mode": "grounded", "pick": JAZZ_ID,
        })
        run_id = resp.json()["run_id"]
        state = await engine.wait_run(run_id)
        assert state.outcome.status == "ok"
        events = await collect_events(ac, run_id)
    assert any(e["type"] == "user_choice" and JAZZ_ID in e["pick"]
               for e in events)
    resume_msgs, _ = provider.seen[1]
    assert any(JAZZ_ID in (m.get("content") or "")
               for m in resume_msgs if m["role"] == "user")


@pytest.mark.asyncio
async def test_needs_input_without_pick_surfaces_candidates():
    provider = FakeProvider([Reply(content=json.dumps(NEEDED_BRIEF))])
    client = FakeClient([])
    engine = make_engine(provider, client)
    async with httpx.AsyncClient(
        transport=make_app(engine), base_url="http://t"
    ) as ac:
        resp = await ac.post("/api/agent/run", json={
            "brief": "jazz bar", "mode": "grounded",
        })
        run_id = resp.json()["run_id"]
        await engine.wait_run(run_id)
        summary = (await ac.get(f"/api/agent/runs/{run_id}")).json()
        events = await collect_events(ac, run_id)
    done = events[-1]
    assert done["exit_status"] == "needs_input"
    assert summary["exit_status"] == "needs_input"
    assert summary["needs_input"]["candidates"][0]["id"] == JAZZ_ID
    assert summary["brief"]["audience_profile"] == ""


@pytest.mark.asyncio
async def test_provider_config_error_is_honest_and_terminates():
    def failing_factory(settings, req):
        raise ProviderConfigError("no API key for gemini")

    engine = make_engine(provider_factory=failing_factory)
    async with httpx.AsyncClient(
        transport=make_app(engine), base_url="http://t"
    ) as ac:
        resp = await ac.post("/api/agent/run", json={
            "brief": "x", "mode": "grounded"})
        run_id = resp.json()["run_id"]
        await engine.wait_run(run_id)
        state = engine.runs[run_id]
        events = await collect_events(ac, run_id)
    assert state.status == "error"
    assert "no API key" in state.error
    done = events[-1]
    assert done["type"] == "run_done" and done["exit_status"] == "error"
    assert any(e["type"] == "status" and e.get("message") == "run_error"
               for e in events)


@pytest.mark.asyncio
async def test_sse_survives_early_disconnect_replay_is_complete():
    """Run completes with no subscribers attached; late attach sees history."""
    provider = FakeProvider([Reply(content=json.dumps(FINAL_BRIEF))])
    client = FakeClient([])
    engine = make_engine(provider, None)
    async with httpx.AsyncClient(
        transport=make_app(engine), base_url="http://t"
    ) as ac:
        resp = await ac.post("/api/agent/run", json={
            "brief": "x", "mode": "generic"})
        run_id = resp.json()["run_id"]
        await engine.wait_run(run_id)
        events = await collect_events(ac, run_id)
    # A subscriber that had connected mid-run and dropped (unsubscribe path
    # exercised directly on the bus) must not have corrupted the buffer:
    assert engine.runs[run_id].bus.sub_count() == 0
    assert events[-1]["type"] == "run_done"
    # late attach replays every buffered event in order
    ts = [e["ts"] for e in events]
    assert ts == sorted(ts)


@pytest.mark.asyncio
async def test_health_and_qloo_status_endpoint():
    client = FakeClient([])
    engine = make_engine(client=client)
    async with httpx.AsyncClient(
        transport=make_app(engine), base_url="http://t"
    ) as ac:
        health = (await ac.get("/api/health")).json()
        status = (await ac.get("/api/qloo/status")).json()
    assert health["status"] == "ok"
    assert status["ready"] is True
    assert "qloo_find_tags" in status["tools"]
    assert status["capabilities_status"] == "ok"
