"""Public demo browsers cannot read or mutate each other's decisions."""

from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import pytest

from app.api.decision_store import DecisionStore
from app.api.engine import Engine
from app.main import create_app
from app.settings import Settings


def public_app(path: Path):
    settings = Settings(app_env="production", session_secret="test-secret-with-at-least-thirty-two-characters")
    return create_app(engine=Engine(settings=settings, decision_store=DecisionStore(path)))


@pytest.mark.asyncio
async def test_public_sessions_isolate_decisions_and_jobs():
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "decisions.sqlite"
        app = public_app(path)
        transport = httpx.ASGITransport(app=app)
        async with (httpx.AsyncClient(transport=transport, base_url="https://tastewell.test") as alice,
                    httpx.AsyncClient(transport=transport, base_url="https://tastewell.test") as bob):
            payload = {"venue_name": "Private venue", "concept": "private concept",
                       "region": "Mumbai", "audience": "locals", "live_music_allowed": False}
            made = await alice.post("/api/decisions", json=payload)
            assert made.status_code == 200
            decision_id = made.json()["id"]
            assert "secure" in made.headers["set-cookie"]
            assert "httponly" in made.headers["set-cookie"]
            assert len((await alice.get("/api/decisions")).json()) == 1
            assert (await bob.get("/api/decisions")).json() == []

            private_paths = [
                f"/api/decisions/{decision_id}",
                f"/api/decisions/{decision_id}/export",
                f"/api/decisions/{decision_id}/agent-reviews/fake",
            ]
            for url in private_paths:
                assert (await bob.get(url)).status_code == 404
            for url, body in [
                (f"/api/decisions/{decision_id}/replay", None),
                (f"/api/decisions/{decision_id}/resolve", {"candidate_id": "fake"}),
                (f"/api/decisions/{decision_id}/scenarios",
                 {"venue_id": "fake", "audience": "locals", "region": "Pune"}),
                (f"/api/decisions/{decision_id}/agent-reviews", {"snapshot_fingerprint": "fake"}),
                (f"/api/decisions/{decision_id}/select/fake",
                 {"owner": "Test", "target_date": "Friday", "success_measure": "Visitors",
                  "next_action": "Check quote"}),
                (f"/api/decisions/{decision_id}/outcome",
                 {"metric": "Visitors", "baseline_value": 1, "actual_value": 2,
                  "unit": "people", "period": "day", "source": "Count"}),
            ]:
                assert (await bob.post(url, json=body)).status_code == 404

            started = await alice.post("/api/decision-jobs", json=payload)
            assert started.status_code == 202
            job_id = started.json()["job_id"]
            assert (await bob.get(f"/api/decision-jobs/{job_id}")).status_code == 404
            assert (await bob.delete(f"/api/decision-jobs/{job_id}")).status_code == 404
            assert (await alice.get(f"/api/decision-jobs/{job_id}")).status_code == 200

            replay = await alice.post(f"/api/decisions/{decision_id}/replay")
            assert replay.status_code == 201
            replay_id = replay.json()["id"]
            assert (await bob.get(f"/api/decisions/{replay_id}")).status_code == 404

            restarted = public_app(path)
            restart_transport = httpx.ASGITransport(app=restarted)
            async with httpx.AsyncClient(transport=restart_transport,
                                        base_url="https://tastewell.test",
                                        cookies=alice.cookies) as same_browser:
                assert (await same_browser.get(f"/api/decisions/{decision_id}")).status_code == 200
                assert len((await same_browser.get("/api/decisions")).json()) >= 2


def test_public_app_requires_session_secret():
    with TemporaryDirectory() as tmp:
        settings = Settings(app_env="production", session_secret="short")
        with pytest.raises(RuntimeError, match="SESSION_SECRET"):
            create_app(engine=Engine(settings=settings,
                                     decision_store=DecisionStore(Path(tmp) / "test.sqlite")))
