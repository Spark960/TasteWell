"""MCP transport/protocol-layer tests — typed fake session, no spawn."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.qloo.mcp_client import QlooMcpClient, parse_content
from app.qloo.normalizer import normalize_envelope

JAZZ = [
    {"id": "urn:tag:genre:music:jazz", "name": "Jazz",
     "type": "urn:tag:genre:music", "popularity": 0.9997},
    {"id": "urn:tag:genre:media:jazz", "name": "Jazz",
     "type": "urn:tag:genre:media", "popularity": 0.997},
]

OK_FIND_TAGS = {
    "schema_version": "1.0-preview.1",
    "operation": "find_tags",
    "status": "ok",
    "results": JAZZ,
    "result_count": 2,
    "summary": "2 tags for jazz",
    "execution": {"correlation_id": "corr-1"},
}

RETRYABLE_ERR = {
    "error": {"code": "QLOO_BUSY", "layer": "upstream", "retryable": True,
              "recovery": "retry"},
    "operation": "find_tags",
    "correlation_id": "corr-0",
}


class FakeSession:
    def __init__(self, envelopes, tools=("qloo_find_tags",)):
        self._envelopes = list(envelopes)
        self._tool_list = SimpleNamespace(
            tools=[
                SimpleNamespace(
                    name=t,
                    input_schema={"type": "object", "properties": {}},
                )
                for t in tools
            ]
        )
        self.calls: list[tuple[str, dict]] = []

    async def list_tools(self):
        return self._tool_list

    async def call_tool(self, tool, args):
        self.calls.append((tool, dict(args)))
        env = self._envelopes.pop(0)
        if isinstance(env, Exception):
            raise env
        return SimpleNamespace(
            content=[SimpleNamespace(text=json.dumps(env))], is_error=False
        )


def client_with(session, **kw) -> QlooMcpClient:
    return QlooMcpClient(session=session, **kw)


@pytest.mark.asyncio
async def test_roundtrip_and_tool_list():
    session = FakeSession([OK_FIND_TAGS])
    async with client_with(session) as c:
        assert sorted(c.tools) == ["qloo_find_tags"]
        res = await c.call_tool("find_tags", {"query": "jazz", "limit": 2})
    assert res.status == "ok"
    assert res.result_count == 2
    assert res.data[0]["id"] == "urn:tag:genre:music:jazz"
    assert res.correlation_id == "corr-1"
    assert session.calls == [("qloo_find_tags", {"query": "jazz", "limit": 2})]


@pytest.mark.asyncio
async def test_none_payload_values_dropped():
    session = FakeSession([OK_FIND_TAGS])
    async with client_with(session) as c:
        await c.call_tool("find_tags", {"query": "jazz", "semantic": None})
    assert session.calls[0][1] == {"query": "jazz"}


@pytest.mark.asyncio
async def test_unknown_tool_honest_error():
    session = FakeSession([])
    async with client_with(session) as c:
        res = await c.call_tool("rank", {"options": ["a"]})
    assert res.status == "error"
    assert res.error_code == "NO_SUCH_TOOL"
    assert "qloo_rank" in res.recovery


@pytest.mark.asyncio
async def test_unparseable_content():
    res = await parse_content("find_tags", SimpleNamespace(
        content=[SimpleNamespace(text="boom not json")], is_error=True))
    assert res.status == "error"
    assert res.error_code == "HARNESS_UNPARSEABLE"
    assert res.retryable is False


@pytest.mark.asyncio
async def test_no_content_parts():
    res = await parse_content("find_tags", SimpleNamespace(content=[]))
    assert res.error_code == "HARNESS_UNPARSEABLE"


@pytest.mark.asyncio
async def test_retryable_error_then_success(monkeypatch):
    sleeps: list[float] = []

    async def fake_to_thread(f, *a):
        sleeps.append(a[0])

    monkeypatch.setattr("asyncio.to_thread", fake_to_thread)
    session = FakeSession([RETRYABLE_ERR, dict(OK_FIND_TAGS)])
    async with client_with(session, max_retries=2,
                           sleep=lambda s: None) as c:
        res = await c.call_tool("find_tags", {"query": "jazz"})
    assert res.status == "ok"
    assert len(session.calls) == 2
    assert sleeps == [0.5]


@pytest.mark.asyncio
async def test_retry_budget_exhausted():
    session = FakeSession([dict(RETRYABLE_ERR)] * 3)
    async with client_with(session, max_retries=2,
                           sleep=lambda s: None) as c:
        res = await c.call_tool("find_tags", {"query": "jazz"})
    assert res.status == "error"
    assert res.error_code == "QLOO_BUSY"
    assert len(session.calls) == 3  # initial + 2 retries


@pytest.mark.asyncio
async def test_nonretryable_error_no_retry():
    env = {"error": {"code": "TOOL_INPUT", "retryable": False},
           "operation": "find_tags"}
    session = FakeSession([env])
    async with client_with(session, max_retries=2) as c:
        res = await c.call_tool("find_tags", {"query": ""})
    assert res.error_code == "TOOL_INPUT"
    assert len(session.calls) == 1


@pytest.mark.asyncio
async def test_transport_failure_retryable():
    session = FakeSession([OSError("pipe died"), dict(OK_FIND_TAGS)])
    async with client_with(session, max_retries=1) as c:
        res = await c.call_tool("find_tags", {"query": "jazz"})
    assert res.status == "ok"
    assert len(session.calls) == 2


@pytest.mark.asyncio
async def test_dns_error_retried_despite_nonretryable_flag():
    """QLOO_DNS is transient (live 2026-10-22 killed a grounded run's last
    tool call); retry it even when the envelope says retryable=false."""
    env = {
        "error": {"code": "QLOO_DNS", "layer": "network",
                  "retryable": False, "recovery": "retry"},
        "operation": "find_tags",
    }
    session = FakeSession([env, dict(OK_FIND_TAGS)])
    async with client_with(session, max_retries=1,
                           sleep=lambda s: None) as c:
        res = await c.call_tool("find_tags", {"query": "jazz"})
    assert res.status == "ok"
    assert len(session.calls) == 2
