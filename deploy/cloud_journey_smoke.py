"""Opt-in live Qloo and agent journey for a private production deployment.

Run inside the backend container with the repository copy supplied on stdin:
    docker compose ... exec -T backend python - < deploy/cloud_journey_smoke.py

Creates one synthetic decision. Prints IDs and statuses, never credentials or
raw Qloo responses. This is a deployment check, not a benchmark of usefulness.
"""

from __future__ import annotations

import http.cookiejar
import json
import time
import urllib.error
import urllib.request


BASE = "http://127.0.0.1:8000"
cookies = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))


def api(method: str, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    try:
        with opener.open(request, timeout=145) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{method} {path} returned HTTP {exc.code}") from exc


assert api("GET", "/api/health")["status"] == "ok"
assert api("GET", "/api/qloo/status")["ready"] is True

decision = api("POST", "/api/decisions", {
    "venue_name": "Tastewell synthetic listening room",
    "concept": "jazz",
    "region": "Brooklyn, New York",
    "audience": "millennials",
    "objective": "Choose a small midweek live music pilot for this synthetic venue",
})
decision_id = decision["id"]
if decision["status"] == "needs_input":
    chosen = next((candidate for candidate in decision["candidates"]
                   if candidate.get("id") == "urn:tag:genre:music:jazz"), None)
    assert chosen is not None, "expected Qloo jazz tag was absent"
    decision = api("POST", f"/api/decisions/{decision_id}/resolve",
                   {"candidate_id": chosen["id"]})

assert decision["status"] == "ready", f"decision status: {decision['status']}"
assert decision["source_mode"] == "live"
assert decision["options"] and decision["evidence"]
assert decision["selected_option_id"] is None
evidence_ids = {row["id"] for row in decision["evidence"]}
assert all(set(option["evidence_ids"]) <= evidence_ids
           for option in decision["options"])

job = api("POST", f"/api/decisions/{decision_id}/agent-reviews", {
    "snapshot_fingerprint": decision["snapshot_fingerprint"],
})
review_id = job["review_id"]
deadline = time.monotonic() + 110
while job["status"] not in {"done", "error", "cancelled"} and time.monotonic() < deadline:
    time.sleep(2)
    job = api("GET", f"/api/decisions/{decision_id}/agent-reviews/{review_id}")

assert job["status"] == "done", f"review job status: {job['status']}; stage: {job['stage']}"
review = job["review"]
assert review is not None and review["status"] in {"recommend", "needs_input", "abstain"}
if review["status"] == "recommend":
    assert review["option_id"] in {option["id"] for option in decision["options"]}
    assert set(review["evidence_ids"]) <= evidence_ids
    assert review["actions"] and review["next_check"]
else:
    assert review["reason"], "no-choice review must give a reason"

reopened = api("GET", f"/api/decisions/{decision_id}")
assert any(item["id"] == review["id"] for item in reopened["agent_reviews"])
assert reopened["selected_option_id"] is None
print(f"CLOUD_JOURNEY_OK decision={decision_id} review={review_id} "
      f"review_status={review['status']} options={len(decision['options'])} "
      f"evidence_rows={len(decision['evidence'])}")
