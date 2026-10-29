import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import pytest

from app.agent.decision_review import ReviewRequest, run_decision_review
from app.agent.provider import Reply
from app.api.decision_store import DecisionStore
from app.api.decisions import (DecisionOption, DecisionRequest, DecisionResult,
                               EvidenceRow, VenueInput, evidence_fingerprint)
from app.api.engine import Engine
from app.main import create_app
from app.qloo.normalizer import NormalizedResult


def decision() -> DecisionResult:
    venue = VenueInput(id="v1", name="Room", region="Austin", budget_limit=500)
    evidence = [EvidenceRow(id="e1", operation="recommend", status="ok",
                            query={"target_type": "artist"}, source_id="artist-a",
                            name="Act A", correlation_id="corr-1", retrieved_at="today")]
    option = DecisionOption(id="o1", format="early_set", title="Early set",
                            description="Act A", evidence_ids=["e1"],
                            unknowns=["Artist availability and fee"], constraint_notes=[],
                            venue_ranks={"v1": 1})
    return DecisionResult(id="d1", status="ready", source_mode="live",
                          request=DecisionRequest(venue_name="Room", concept="bar",
                                                  region="Austin", audience="locals",
                                                  objective="Fill Thursday"),
                          venues=[venue], options=[option], evidence=evidence)


class Provider:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    async def chat(self, messages, tools=None):
        self.calls += 1
        return self.replies.pop(0)


def recommendation(**changes):
    return {**{"status": "recommend", "option_id": "o1", "venue_id": "v1",
               "evidence_ids": ["e1"], "scenario_id": None, "rationale": "Try the early set",
               "alternatives": [], "unknowns": ["Artist availability and fee"],
               "next_check": "Artist availability and fee"}, **changes}


@pytest.mark.asyncio
async def test_review_inspects_and_persists_without_selecting():
    d = decision()
    provider = Provider([
        Reply(tool_calls=[{"id": "t1", "name": "inspect_option", "args": {"option_id": "o1"}},
                          {"id": "t2", "name": "check_venue", "args": {"venue_id": "v1"}}]),
        Reply(content=json.dumps(recommendation(rationale="Qloo predicts 200% more sales"))),
    ])
    with TemporaryDirectory() as tmp:
        engine = Engine(provider_factory=lambda *_: provider,
                        decision_store=DecisionStore(Path(tmp) / "decisions.sqlite"))
        engine.save_decision(d)
        app = create_app(engine=engine)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http:
            started = await http.post("/api/decisions/d1/agent-reviews", json={
                "snapshot_fingerprint": evidence_fingerprint(d)})
            assert started.status_code == 202
            job = engine.agent_review_jobs[started.json()["review_id"]]
            await job.task
            assert job.status == "done"
            assert [a.tool for a in job.review.actions] == ["inspect_option", "check_venue"]
            saved = (await http.get("/api/decisions/d1/export")).json()
            assert saved["agent_reviews"][0]["option_id"] == "o1"
            assert saved["agent_reviews"][0]["rationale"].startswith("Qloo returned Act A")
            assert "200%" not in saved["agent_reviews"][0]["rationale"]
            assert saved["agent_reviews"][0]["next_check"] == "Verify artist availability and fee."
            assert saved["selected_option_id"] is None
            assert (await http.get(f"/api/decisions/d1/agent-reviews/{job.id}")).status_code == 200


@pytest.mark.asyncio
async def test_invalid_citation_repairs_then_abstains():
    d = decision()
    provider = Provider([Reply(content=json.dumps(recommendation(evidence_ids=["fake"]))),
                         Reply(content=json.dumps(recommendation(evidence_ids=["fake"])))])
    review = await run_decision_review(d, ReviewRequest(snapshot_fingerprint=evidence_fingerprint(d)), provider)
    assert review.status == "abstain"
    assert "grounded" in review.reason
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_review_rejects_nonready_and_stale_snapshot():
    d = decision()
    fp = evidence_fingerprint(d)
    d.status = "needs_input"
    with pytest.raises(ValueError, match="ready"):
        await run_decision_review(d, ReviewRequest(snapshot_fingerprint=fp), Provider([]))
    d.status = "ready"
    d.evidence[0].status = "empty"
    with pytest.raises(ValueError, match="changed"):
        await run_decision_review(d, ReviewRequest(snapshot_fingerprint=fp), Provider([]))


@pytest.mark.asyncio
async def test_replay_cannot_make_fresh_qloo_call():
    d = decision()
    d.source_mode = "replay"
    provider = Provider([Reply(tool_calls=[{"id": "t1", "name": "compare_scenario",
                                           "args": {"venue_id": "v1"}}]),
                         Reply(content=json.dumps({"status": "abstain", "reason": "No new rank on replay"}))])
    review = await run_decision_review(d, ReviewRequest(snapshot_fingerprint=evidence_fingerprint(d),
                                                        scenario_venue_id="v1", alternate_audience="visitors"),
                                       provider, client_factory=lambda: pytest.fail("Qloo called on replay"))
    assert review.status == "abstain"
    assert review.actions[0].outcome == "rejected"


@pytest.mark.asyncio
async def test_one_qloo_comparison_limit_and_saved_rank_context():
    d = decision()
    d.evidence.extend([
        EvidenceRow(id="r1", operation="rank", status="ok", query={
            "options": ["artist-a", "artist-b"], "option_type": "artist",
            "signal_location": "Austin", "demographic": "locals"},
            source_id="artist-a", venue_id="v1", retrieved_at="today", correlation_id="c1"),
        EvidenceRow(id="r2", operation="rank", status="ok", query={
            "options": ["artist-a", "artist-b"], "option_type": "artist",
            "signal_location": "Austin", "demographic": "locals"},
            source_id="artist-b", venue_id="v1", retrieved_at="today", correlation_id="c1"),
    ])
    calls = []

    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def call_tool(self, operation, query):
            calls.append((operation, query))
            return NormalizedResult(status="ok", operation="rank", results=[
                {"entity_id": "artist-b", "name": "Act B"},
                {"entity_id": "artist-a", "name": "Act A"},
            ])

    provider = Provider([
        Reply(tool_calls=[{"id": "t1", "name": "compare_scenario", "args": {"venue_id": "v1"}},
                          {"id": "t2", "name": "compare_scenario", "args": {"venue_id": "v1"}}]),
        Reply(content=json.dumps({"status": "abstain", "reason": "Booking facts are missing"})),
    ])
    review = await run_decision_review(d, ReviewRequest(snapshot_fingerprint=evidence_fingerprint(d),
                                                        scenario_venue_id="v1", alternate_audience="visitors"),
                                       provider, client_factory=Client)
    assert len(calls) == 1
    assert calls[0][1]["options"] == ["artist-a", "artist-b"]
    assert calls[0][1]["demographic"] == "visitors"
    assert [a.outcome for a in review.actions] == ["ready", "rejected"]
    assert len(d.scenarios) == 1


@pytest.mark.asyncio
async def test_cancelled_review_never_persists_a_proposal():
    d = decision()
    entered = asyncio.Event()

    class SlowProvider:
        async def chat(self, messages, tools=None):
            entered.set()
            await asyncio.sleep(60)

    with TemporaryDirectory() as tmp:
        engine = Engine(provider_factory=lambda *_: SlowProvider(),
                        decision_store=DecisionStore(Path(tmp) / "decisions.sqlite"))
        engine.save_decision(d)
        job = engine.start_agent_review(d.id, ReviewRequest(snapshot_fingerprint=evidence_fingerprint(d)))
        await entered.wait()
        engine.cancel_agent_review(d.id, job.id)
        await job.task
        assert job.status == "cancelled"
        assert engine.get_decision(d.id).agent_reviews == []


@pytest.mark.asyncio
async def test_unavailable_model_keeps_deterministic_decision():
    d = decision()

    class UnavailableProvider:
        async def chat(self, messages, tools=None):
            raise RuntimeError("provider unavailable")

    with TemporaryDirectory() as tmp:
        engine = Engine(provider_factory=lambda *_: UnavailableProvider(),
                        decision_store=DecisionStore(Path(tmp) / "decisions.sqlite"))
        engine.save_decision(d)
        job = engine.start_agent_review(d.id, ReviewRequest(snapshot_fingerprint=evidence_fingerprint(d)))
        await job.task
        assert job.status == "error"
        assert "Review unavailable" in job.error
        saved = engine.get_decision(d.id)
        assert saved.status == "ready"
        assert saved.options[0].id == "o1"
        assert saved.agent_reviews == []


def test_fingerprint_ignores_review_and_selection_but_tracks_evidence():
    d = decision()
    original = evidence_fingerprint(d)
    d.selected_option_id = "o1"
    assert evidence_fingerprint(d) == original
    d.evidence[0].source_id = "changed"
    assert evidence_fingerprint(d) != original


@pytest.mark.asyncio
async def test_identity_only_source_labels_cultural_fit_unverified():
    d = decision()
    d.evidence[0].operation = "describe"
    d.options[0].venue_ranks = {"v1": None}
    provider = Provider([
        Reply(tool_calls=[{"id": "t1", "name": "inspect_option", "args": {"option_id": "o1"}},
                          {"id": "t2", "name": "check_venue", "args": {"venue_id": "v1"}}]),
        Reply(content=json.dumps(recommendation())),
    ])
    review = await run_decision_review(d, ReviewRequest(snapshot_fingerprint=evidence_fingerprint(d)), provider)
    assert review.status == "recommend"
    assert "Cultural fit for this venue is unverified" in review.rationale
