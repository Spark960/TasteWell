"""Decision slice: only returned Qloo rows may appear as grounded options."""

from __future__ import annotations

import unittest
import tempfile
import asyncio
from pathlib import Path

import httpx

from app.api.decisions import DecisionRequest, VenueInput, build_decision
from app.api.engine import Engine
from app.api.decision_store import DecisionStore
from app.main import create_app
from app.qloo.normalizer import NormalizedResult


TAG = "urn:tag:setting:qloo:listening_bar"


class Client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def call_tool(self, operation, query):
        self.calls.append((operation, query))
        return self.responses.pop(0)


def request(**changes):
    payload = dict(venue_name="The Room", concept="listening bar",
                   region="Williamsburg, Brooklyn", audience="millennials")
    return DecisionRequest(**(payload | changes))


def tags(*ids):
    return NormalizedResult(status="ok", operation="find_tags",
                            results=[{"id": x, "name": "Listening Bar"} for x in ids])


class DecisionTests(unittest.IsolatedAsyncioTestCase):
    async def test_ambiguous_tag_stops_before_recommendation(self):
        client = Client([tags(TAG, "urn:tag:other")])
        result = await build_decision(request(), client)
        self.assertEqual(result.status, "needs_input")
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(len(result.candidates), 2)

    async def test_unseen_selected_tag_cannot_be_used(self):
        client = Client([tags(TAG)])
        result = await build_decision(request(selected_tag_id="urn:tag:invented"), client)
        self.assertEqual(result.status, "needs_input")
        self.assertEqual(len(client.calls), 1)

    async def test_needs_input_candidates_can_be_selected(self):
        choice = NormalizedResult(status="needs_input", operation="find_tags",
                                  candidates=[{"id": TAG, "name": "Listening Bar"}])
        artist = NormalizedResult(status="ok", operation="recommend", results=[
            {"entity_id": "artist-1", "name": "First Act"}])
        brand = NormalizedResult(status="ok", operation="recommend", results=[])
        client = Client([choice, artist, brand])
        result = await build_decision(request(selected_tag_id=TAG), client)
        self.assertEqual(result.status, "ready")
        self.assertIn(TAG, [e.source_id for e in result.evidence])

    async def test_options_only_cite_ledger_rows(self):
        artists = NormalizedResult(status="ok", operation="recommend", results=[
            {"entity_id": "artist-1", "name": "First Act", "affinity": 0.8},
            {"entity_id": "artist-2", "name": "Second Act", "affinity": 0.7},
            {"entity_id": "artist-3", "name": "Third Act", "affinity": 0.6},
        ])
        brands = NormalizedResult(status="ok", operation="recommend", results=[
            {"entity_id": "brand-1", "name": "Brand One", "affinity": 0.5},
        ])
        rank = NormalizedResult(status="ok", operation="rank", results=[
            {"entity_id": "artist-2", "name": "Second Act", "affinity": 0.9},
            {"entity_id": "artist-1", "name": "First Act", "affinity": 0.8},
            {"entity_id": "artist-3", "name": "Third Act", "affinity": 0.7},
        ])
        client = Client([tags(TAG), artists, brands, rank])
        result = await build_decision(request(), client)
        self.assertEqual(result.status, "ready")
        self.assertEqual(len(result.options), 3)
        known = {row.id for row in result.evidence}
        self.assertTrue(all(set(option.evidence_ids) <= known for option in result.options))
        self.assertEqual([call[0] for call in client.calls],
                         ["find_tags", "recommend", "recommend", "rank"])
        self.assertEqual(client.calls[1][1]["signal_tags"], [TAG])
        self.assertEqual(client.calls[3][1]["options"],
                         ["artist-1", "artist-2", "artist-3"])
        self.assertEqual([option.artist_rank for option in result.options], [2, 1, 3])
        self.assertTrue(all("availability" in option.unknowns[0].lower()
                            for option in result.options))

    async def test_no_live_music_blocks_without_qloo(self):
        result = await build_decision(request(live_music_allowed=False), None)
        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.evidence, [])

    async def test_needs_input_from_recommendation_yields_no_options(self):
        client = Client([tags(TAG), NormalizedResult(
            status="needs_input", operation="recommend", results=[]),
            NormalizedResult(status="ok", operation="recommend", results=[]),
        ])
        result = await build_decision(request(), client)
        self.assertEqual(result.status, "no_evidence")
        self.assertEqual(result.options, [])

    async def test_operator_artist_shortlist_uses_describe_and_one_rank_call(self):
        first = NormalizedResult(status="ok", operation="describe", results=[
            {"entity_id": "a1", "name": "First Act"},
        ])
        second = NormalizedResult(status="ok", operation="describe", results=[
            {"entity_id": "a2", "name": "Second Act"},
        ])
        brand = NormalizedResult(status="ok", operation="recommend", results=[])
        rank = NormalizedResult(status="ok", operation="rank", results=[
            {"entity_id": "a2", "name": "Second Act"},
            {"entity_id": "a1", "name": "First Act"},
        ])
        client = Client([tags(TAG), first, second, brand, rank])
        result = await build_decision(request(artist_shortlist=["First Act", "Second Act"]), client)
        self.assertEqual(result.status, "ready")
        self.assertEqual([call[0] for call in client.calls],
                         ["find_tags", "describe", "describe", "recommend", "rank"])
        self.assertEqual(client.calls[-1][1]["options"], ["a1", "a2"])
        self.assertEqual(result.options[0].description.split(" with ")[1].split(" at ")[0],
                         "Second Act")

    async def test_ambiguous_artist_stops_before_ranking(self):
        ambiguous = NormalizedResult(status="needs_input", operation="describe",
                                     candidates=[{"id": "a1", "name": "First Act"},
                                                 {"id": "a2", "name": "First Act"}])
        client = Client([tags(TAG), ambiguous])
        result = await build_decision(request(artist_shortlist=["First Act"]), client)
        self.assertEqual(result.status, "needs_input")
        self.assertEqual(result.resolution_kind, "artist")
        self.assertEqual(result.resolution_key, "First Act")
        self.assertEqual(len(client.calls), 2)

    async def test_portfolio_ranks_same_shortlist_per_eligible_venue(self):
        artists = NormalizedResult(status="ok", operation="recommend", results=[
            {"entity_id": "a1", "name": "First"},
            {"entity_id": "a2", "name": "Second"},
        ])
        empty_brands = NormalizedResult(status="ok", operation="recommend", results=[])
        first_rank = NormalizedResult(status="ok", operation="rank", results=[
            {"entity_id": "a1", "name": "First"},
            {"entity_id": "a2", "name": "Second"},
        ])
        second_rank = NormalizedResult(status="ok", operation="rank", results=[
            {"entity_id": "a2", "name": "Second"},
            {"entity_id": "a1", "name": "First"},
        ])
        venues = [
            VenueInput(id="v1", name="First Room", region="Brooklyn"),
            VenueInput(id="v2", name="Second Room", region="Queens"),
            VenueInput(id="v3", name="Quiet Room", region="Harlem",
                       live_music_allowed=False),
        ]
        client = Client([tags(TAG), artists, empty_brands, first_rank, second_rank])
        result = await build_decision(request(venues=venues), client)
        self.assertEqual(result.status, "ready")
        self.assertEqual(result.options[0].venue_ranks, {"v1": 1, "v2": 2, "v3": None})
        self.assertEqual(result.options[1].venue_ranks, {"v1": 2, "v2": 1, "v3": None})
        ranks = [query for operation, query in client.calls if operation == "rank"]
        self.assertEqual([query["signal_location"] for query in ranks], ["Brooklyn", "Queens"])
        self.assertEqual(ranks[0]["options"], ranks[1]["options"])

    async def test_http_selection_requires_own_option_and_plan(self):
        class ManagedClient(Client):
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

        artist = NormalizedResult(status="ok", operation="recommend", results=[
            {"entity_id": "artist-1", "name": "First Act"},
        ])
        client = ManagedClient([tags(TAG), artist, NormalizedResult(
            status="ok", operation="recommend", results=[])])
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = DecisionStore(Path(temp.name) / "decisions.sqlite")
        engine = Engine(client_factory=lambda settings, req: client,
                        decision_store=store)
        app = create_app(engine=engine)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url="http://test") as http:
            made = await http.post("/api/decisions", json=request(budget_limit=100).model_dump())
            self.assertEqual(made.status_code, 200)
            decision = made.json()
            self.assertEqual(decision["status"], "ready")
            url = f"/api/decisions/{decision['id']}/select/"
            plan = {"owner": "Manager", "target_date": "Next Wednesday",
                    "success_measure": "Attendance against last four Wednesdays",
                    "next_action": "Ask the artist for a quote"}
            invalid = await http.post(url + "invented-option", json=plan)
            self.assertEqual(invalid.status_code, 422)
            over_budget = await http.post(url + decision["options"][0]["id"],
                                          json={**plan, "quoted_total_cost": 101})
            self.assertEqual(over_budget.status_code, 422)
            self.assertIn("exceeds", over_budget.json()["detail"])
            selected = await http.post(url + decision["options"][0]["id"], json=plan)
            self.assertEqual(selected.status_code, 200)
            saved = await http.get(f"/api/decisions/{decision['id']}")
            self.assertEqual(saved.json()["pilot_plan"]["owner"], "Manager")
            outcome = await http.post(f"/api/decisions/{decision['id']}/outcome", json={
                "metric": "Attendance", "baseline_value": 24,
                "actual_value": 31, "unit": "people", "period": "one event",
                "source": "Operator headcount",
            })
            self.assertEqual(outcome.status_code, 200)
            self.assertEqual(outcome.json()["outcome"]["actual_value"], 31)
            calls_before_replay = len(client.calls)
            exported = await http.get(f"/api/decisions/{decision['id']}/export")
            self.assertEqual(exported.status_code, 200)
            self.assertIn("attachment;", exported.headers["content-disposition"])
            self.assertEqual(exported.json()["evidence"], decision["evidence"])
            replayed = await http.post(f"/api/decisions/{decision['id']}/replay")
            self.assertEqual(replayed.status_code, 201)
            self.assertEqual(replayed.json()["source_mode"], "replay")
            self.assertEqual(replayed.json()["replay_of"], decision["id"])
            self.assertNotEqual(replayed.json()["id"], decision["id"])
            self.assertEqual(replayed.json()["evidence"], decision["evidence"])
            self.assertIsNone(replayed.json()["selected_option_id"])
            self.assertIsNone(replayed.json()["outcome"])
            self.assertEqual(len(client.calls), calls_before_replay)
        restarted = Engine(client_factory=lambda settings, req: client,
                           decision_store=store)
        recovered = restarted.get_decision(decision["id"])
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.pilot_plan.owner, "Manager")
        self.assertEqual(recovered.outcome.actual_value, 31)

    async def test_tag_resolution_updates_one_saved_decision(self):
        class ManagedClient(Client):
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

        candidates = tags(TAG, "urn:tag:other")
        artist = NormalizedResult(status="ok", operation="recommend", results=[
            {"entity_id": "artist-1", "name": "First Act"},
        ])
        brand = NormalizedResult(status="ok", operation="recommend", results=[])
        client = ManagedClient([candidates, candidates, artist, brand])
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        engine = Engine(client_factory=lambda settings, req: client,
                        decision_store=DecisionStore(Path(temp.name) / "decisions.sqlite"))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(engine=engine)),
                                     base_url="http://test") as http:
            created = await http.post("/api/decisions", json=request().model_dump())
            self.assertEqual(created.json()["status"], "needs_input")
            decision_id = created.json()["id"]
            invalid = await http.post(f"/api/decisions/{decision_id}/resolve",
                                      json={"candidate_id": "invented"})
            self.assertEqual(invalid.status_code, 422)
            resolved = await http.post(f"/api/decisions/{decision_id}/resolve",
                                       json={"candidate_id": TAG})
            self.assertEqual(resolved.status_code, 200)
            self.assertEqual(resolved.json()["status"], "ready")
            self.assertEqual(resolved.json()["id"], decision_id)
            history = await http.get("/api/decisions")
            self.assertEqual([item["id"] for item in history.json()], [decision_id])

    async def test_artist_resolution_verifies_id_and_updates_one_saved_decision(self):
        class ManagedClient(Client):
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

        ambiguous = NormalizedResult(status="needs_input", operation="describe",
                                     candidates=[{"id": "a1", "name": "First Act"},
                                                 {"id": "a2", "name": "First Act"}])
        verified = NormalizedResult(status="ok", operation="describe", results=[
            {"entity_id": "a2", "name": "First Act"},
        ])
        brand = NormalizedResult(status="ok", operation="recommend", results=[])
        client = ManagedClient([tags(TAG), ambiguous, tags(TAG), ambiguous,
                                verified, brand])
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        engine = Engine(client_factory=lambda settings, req: client,
                        decision_store=DecisionStore(Path(temp.name) / "decisions.sqlite"))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(engine=engine)),
                                     base_url="http://test") as http:
            created = await http.post("/api/decisions", json=request(
                artist_shortlist=["First Act"]).model_dump())
            self.assertEqual(created.status_code, 200)
            self.assertEqual(created.json()["resolution_kind"], "artist")
            decision_id = created.json()["id"]
            invalid = await http.post(f"/api/decisions/{decision_id}/resolve",
                                      json={"candidate_id": "invented"})
            self.assertEqual(invalid.status_code, 422)
            resolved = await http.post(f"/api/decisions/{decision_id}/resolve",
                                       json={"candidate_id": "a2"})
            self.assertEqual(resolved.status_code, 200)
            self.assertEqual(resolved.json()["status"], "ready")
            self.assertEqual(resolved.json()["id"], decision_id)
            self.assertEqual(resolved.json()["request"]["artist_resolution"],
                             {"First Act": "a2"})
            self.assertEqual(client.calls[4], ("describe", {"entity": "a2", "type": "artist"}))
            self.assertIn("a2", [row["source_id"] for row in resolved.json()["evidence"]])
            history = await http.get("/api/decisions")
            self.assertEqual([item["id"] for item in history.json()], [decision_id])

    async def test_scenario_holds_saved_artist_ids_and_persists_ordinal_change(self):
        class ManagedClient(Client):
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

        artists = NormalizedResult(status="ok", operation="recommend", results=[
            {"entity_id": "a1", "name": "First"},
            {"entity_id": "a2", "name": "Second"},
        ])
        empty_brand = NormalizedResult(status="ok", operation="recommend", results=[])
        initial_rank = NormalizedResult(status="ok", operation="rank", results=[
            {"entity_id": "a1", "name": "First"},
            {"entity_id": "a2", "name": "Second"},
        ])
        changed_rank = NormalizedResult(status="ok", operation="rank", results=[
            {"entity_id": "a2", "name": "Second"},
            {"entity_id": "a1", "name": "First"},
        ])
        client = ManagedClient([tags(TAG), artists, empty_brand,
                                initial_rank, changed_rank])
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = DecisionStore(Path(temp.name) / "decisions.sqlite")
        engine = Engine(client_factory=lambda settings, req: client, decision_store=store)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(engine=engine)),
                                     base_url="http://test") as http:
            created = await http.post("/api/decisions", json=request().model_dump())
            self.assertEqual(created.status_code, 200)
            decision = created.json()
            decision_id = decision["id"]
            venue_id = decision["venues"][0]["id"]
            unchanged = await http.post(f"/api/decisions/{decision_id}/scenarios", json={
                "venue_id": venue_id, "audience": "millennials",
                "region": "Williamsburg, Brooklyn",
            })
            self.assertEqual(unchanged.status_code, 422)
            changed = await http.post(f"/api/decisions/{decision_id}/scenarios", json={
                "venue_id": venue_id, "audience": "young professionals",
                "region": "Williamsburg, Brooklyn",
            })
            self.assertEqual(changed.status_code, 200)
            scenario = changed.json()["scenario"]
            self.assertEqual(scenario["artist_ids"], ["a1", "a2"])
            self.assertEqual(scenario["baseline_ranks"], {"a1": 1, "a2": 2})
            self.assertEqual(scenario["scenario_ranks"], {"a1": 2, "a2": 1})
            self.assertEqual(scenario["original_query"]["demographic"], "millennials")
            self.assertEqual(scenario["changed_query"]["demographic"], "young professionals")
            self.assertEqual(client.calls[-1][1]["options"], ["a1", "a2"])
            self.assertEqual(changed.json()["decision"]["options"], decision["options"])
        recovered = Engine(client_factory=lambda settings, req: client,
                           decision_store=store).get_decision(decision_id)
        self.assertEqual(recovered.scenarios[0].id, scenario["id"])

    async def test_decision_total_timeout_returns_504_without_saving(self):
        class SlowClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def call_tool(self, operation, query):
                await asyncio.sleep(0.1)
                return tags(TAG)

        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        engine = Engine(client_factory=lambda settings, req: SlowClient(),
                        decision_store=DecisionStore(Path(temp.name) / "decisions.sqlite"))
        from unittest.mock import patch
        with patch("app.api.engine.DECISION_TOTAL_TIMEOUT", 0.01):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(engine=engine)),
                                         base_url="http://test") as http:
                result = await http.post("/api/decisions", json=request().model_dump())
                self.assertEqual(result.status_code, 504)
                self.assertIn("total time budget", result.json()["detail"])
                self.assertEqual((await http.get("/api/decisions")).json(), [])

    async def test_decision_job_reports_result_and_can_cancel_inflight_qloo(self):
        class ManagedClient(Client):
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

        class SlowClient(ManagedClient):
            async def call_tool(self, operation, query):
                await asyncio.sleep(1)
                return tags(TAG)

        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        quick = ManagedClient([tags(TAG), NormalizedResult(
            status="ok", operation="recommend", results=[
                {"entity_id": "a1", "name": "First"}]), NormalizedResult(
            status="ok", operation="recommend", results=[])])
        current = [quick]
        engine = Engine(client_factory=lambda settings, req: current[0],
                        decision_store=DecisionStore(Path(temp.name) / "decisions.sqlite"))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(engine=engine)),
                                     base_url="http://test") as http:
            started = await http.post("/api/decision-jobs", json=request().model_dump())
            self.assertEqual(started.status_code, 202)
            job_id = started.json()["job_id"]
            await engine.decision_jobs[job_id].task
            finished = (await http.get(f"/api/decision-jobs/{job_id}")).json()
            self.assertEqual(finished["status"], "done")
            self.assertEqual(finished["decision"]["status"], "ready")
            self.assertEqual(finished["stage"], "complete")
            current[0] = SlowClient([])
            started = await http.post("/api/decision-jobs", json=request().model_dump())
            cancel_id = started.json()["job_id"]
            await asyncio.sleep(0)
            await http.delete(f"/api/decision-jobs/{cancel_id}")
            await engine.decision_jobs[cancel_id].task
            cancelled = (await http.get(f"/api/decision-jobs/{cancel_id}")).json()
            self.assertEqual(cancelled["status"], "cancelled")
            self.assertIsNone(cancelled["decision"])
            history = (await http.get("/api/decisions")).json()
            self.assertEqual(len(history), 1)


if __name__ == "__main__":
    unittest.main()
