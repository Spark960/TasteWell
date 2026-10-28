"""Optional live smoke for the programming decision path.

Run with QLOO_LIVE=1 and QLOO_BIN set to the installed harness path.
No LLM call is made, and no credential or raw envelope is printed.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.api.decisions import DecisionRequest, build_decision
from app.qloo.mcp_client import QlooMcpClient
from app.settings import Settings


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_decision_has_only_returned_qloo_ids():
    if os.environ.get("QLOO_LIVE") != "1":
        pytest.skip("QLOO_LIVE not set")
    root = Path(__file__).parents[2]
    settings = Settings(_env_file=root / ".env")
    assert settings.qloo_api_key, "QLOO_API_KEY is required for live test"
    client = QlooMcpClient(
        qloo_bin=os.environ.get("QLOO_BIN", settings.qloo_bin),
        api_key=settings.qloo_api_key,
        base_urls=(settings.qloo_base_url, settings.qloo_trusted_base_url),
    )
    request = DecisionRequest(
        venue_name="Test listening room", concept="jazz",
        region="Brooklyn, New York", audience="millennials",
    )
    async with client:
        first = await build_decision(request, client)
        assert first.status == "needs_input"
        chosen = next((c for c in first.candidates
                       if c["id"] == "urn:tag:genre:music:jazz"), None)
        assert chosen is not None, "expected jazz music tag absent from live candidates"
        second = await build_decision(
            request.model_copy(update={"selected_tag_id": chosen["id"]}), client,
        )
    assert second.status == "ready", second.notes
    assert second.options
    evidence_ids = {row.id for row in second.evidence}
    for option in second.options:
        assert set(option.evidence_ids) <= evidence_ids
        assert "availability" in " ".join(option.unknowns).lower()
