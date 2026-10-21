"""Live smoke for the HTTP layer — skipped unless QLOO_LIVE=1 + keys in env.

Cost hygiene (IMPLEMENTATION.md §10): the generic run burns ~1 LLM request;
the grounded run burns ~6–8 requests. This smoke deliberately runs the
GENERIC brief only so a live check never drains a quota bucket.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from app.main import create_app

pytestmark = [
    pytest.mark.live,
    pytest.mark.asyncio,
]


@pytest.mark.live
async def test_live_health_qloo_status_and_generic_brief():
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as ac:
        health = (await ac.get("/api/health")).json()
        assert health["status"] == "ok"

        status = (await ac.get("/api/qloo/status")).json()
        assert status["ready"] is True, status
        assert "qloo_find_tags" in status["tools"]

        resp = await ac.post("/api/agent/run", json={
            "brief": "taco shop", "audience": "families",
            "region": "Austin", "mode": "generic",
        })
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]

        s = {"status": "queued"}
        for _ in range(24):  # ≤ 120 s — one LLM turn incl. provider retries
            await asyncio.sleep(5)
            s = (await ac.get(f"/api/agent/runs/{run_id}")).json()
            if s["status"] in ("done", "error"):
                break
        assert s["exit_status"] is not None, s  # honest termination either way

        # full stream replay terminates exactly on run_done
        events_raw = ""
        async with ac.stream("GET", f"/api/agent/stream/{run_id}") as stream:
            async for chunk in stream.aiter_text():
                events_raw += chunk
        assert '"type": "run_done"' in events_raw
        assert events_raw.count('"type": "run_done"') == 1
