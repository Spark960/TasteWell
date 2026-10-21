"""Shared in-memory fakes for agent/API tests — scripted LLM + fake MCP client."""

from __future__ import annotations

from app.agent.provider import Reply
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
    """Stand-in for QlooMcpClient: usable as an async CM + tool registry."""

    tools = {"qloo_find_tags": {"type": "object", "properties": {}}}
    capabilities = NormalizedResult(
        status="ok", operation="capabilities", result_count=9
    )

    def __init__(self, results):
        self.results = list(results)
        self.ops: list[tuple[str, dict]] = []
        self.entered = 0
        self.closed = 0

    async def __aenter__(self):
        self.entered += 1
        return self

    async def __aexit__(self, *exc):
        self.closed += 1
        return False

    async def call_tool(self, operation, payload):
        self.ops.append((operation, dict(payload)))
        return self.results.pop(0)


def grounded_tools(client, trace: Trace | None = None):
    from app.agent.tools import GroundedTools

    return GroundedTools(client=client, trace=trace or Trace(run_id="fake"))
