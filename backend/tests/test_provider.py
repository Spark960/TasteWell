"""Provider shim tests — httpx MockTransport, wire-format parity."""

from __future__ import annotations

import json

import httpx
import pytest

from app.agent.provider import LlmProvider, ProviderConfigError, Reply


TOOL_REPLY_DATA = {
    "choices": [{
        "message": {
            "content": "",
            "tool_calls": [{
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "qloo_find_tags",
                    "arguments": '{"query":"jazz","semantic":false}',
                },
            }],
        }
    }]
}


def provider(handler, **kw) -> LlmProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return LlmProvider(provider="gemini", api_key="k" * 12,
                       model="gemini-2.5-flash", client=client, **kw)


@pytest.mark.asyncio
async def test_chat_with_tools_roundtrip():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json=TOOL_REPLY_DATA)

    p = provider(handler)
    reply = await p.chat(
        [{"role": "user", "content": "hi"}],
        tools=[{"type": "function", "function": {"name": "qloo_find_tags"}}],
    )
    assert reply.wants_tools
    assert reply.tool_calls[0] == {
        "id": "call_1", "name": "qloo_find_tags",
        "args": {"query": "jazz", "semantic": False},
    }
    assert seen["url"].endswith("/chat/completions")
    assert seen["auth"].startswith("Bearer ")
    assert seen["body"]["tool_choice"] == "auto"
    await p._client.aclose()


@pytest.mark.asyncio
async def test_extract_content_reply():
    data = {"choices": [{"message": {"content": "hello"}}]}
    p = provider(lambda req: httpx.Response(200, json=data))
    reply = await p.chat([{"role": "user", "content": "hi"}], tools=None)
    assert reply.content == "hello"
    assert not reply.wants_tools
    await p._client.aclose()


@pytest.mark.asyncio
async def test_unparseable_tool_arguments_tolerated():
    data = {
        "choices": [{"message": {"content": "",
                    "tool_calls": [{"id": "c2",
                                    "function": {"name": "x",
                                                 "arguments": "{oops"}}]}}]
    }
    p = LlmProvider(provider="gemini", api_key="k" * 12,
                    model="m", client=httpx.AsyncClient(
                        transport=httpx.MockTransport(
                            lambda req: httpx.Response(200, json=data))))
    reply = await p.chat([{"role": "user", "content": "hi"}])
    assert reply.tool_calls[0]["args"] == {}
    await p._client.aclose()


@pytest.mark.asyncio
async def test_http_401_is_config_error():
    def handler(req):
        assert req.headers["authorization"]
        return httpx.Response(401, json={"error": "bad key"})

    p = provider(handler)
    with pytest.raises(ProviderConfigError):
        await p.chat([{"role": "user", "content": "hi"}])
    await p._client.aclose()


@pytest.mark.asyncio
async def test_http_error_surfaces():
    def handler(req):
        return httpx.Response(502, text="bad gateway")

    p = provider(handler)

    async def fake_sleep(s: float) -> None:
        pass

    p._sleep = fake_sleep
    with pytest.raises(RuntimeError):
        await p.chat([{"role": "user", "content": "hi"}])
    await p._client.aclose()


@pytest.mark.asyncio
async def test_http_429_retries_then_succeeds():
    calls = {"n": 0}
    sleeps: list[float] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "7"},
                                  json={"error": "quota"})
        return httpx.Response(200, json={"choices": [
            {"message": {"content": "ok"}}]})

    p = provider(handler)

    async def fake_sleep(s: float) -> None:
        sleeps.append(s)

    p._sleep = fake_sleep
    reply = await p.chat([{"role": "user", "content": "hi"}])
    assert reply.content == "ok"
    assert calls["n"] == 2
    assert sleeps == [7.0]
    await p._client.aclose()


@pytest.mark.asyncio
async def test_http_429_budget_exhausted():
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429, json={"error": "quota"})

    p = provider(handler)

    async def fake_sleep(s: float) -> None:
        pass

    p._sleep = fake_sleep
    with pytest.raises(RuntimeError):
        await p.chat([{"role": "user", "content": "hi"}])
    assert calls["n"] == 4  # initial + 3 retries
    await p._client.aclose()


@pytest.mark.asyncio
async def test_transport_failure_raises_runtime():
    def handler(req):
        raise httpx.ConnectError("no dns")

    p = provider(handler)
    with pytest.raises(RuntimeError):
        await p.chat([{"role": "user", "content": "hi"}])
    await p._client.aclose()


def test_missing_choice_message_raises_extraction():
    p = LlmProvider(provider="gemini", api_key="k" * 12,
                    model="m", client=httpx.AsyncClient(
                        transport=httpx.MockTransport(
                            lambda req: httpx.Response(200, json={}))))
    with pytest.raises(RuntimeError):
        p._extract({})


def test_provider_config_validation():
    with pytest.raises(ProviderConfigError):
        LlmProvider(provider="nope", api_key="k" * 12)
    with pytest.raises(ProviderConfigError):
        LlmProvider(provider="gemini", api_key="")


@pytest.mark.asyncio
async def test_http_413_shrinks_history_then_succeeds():
    """Groq 8k TPM hard-rejects over-sized single requests (413); the retry
    must collapse older tool messages to envelope summaries and succeed
    without burning the 429 budget."""
    bodies: list[dict] = []

    def handler(req: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(req.content.decode("utf-8")))
        if len(bodies) == 1:
            return httpx.Response(413, json={"error": {"message": "too large"}})
        return httpx.Response(200, json={"choices": [
            {"message": {"content": "ok"}}]})

    p = provider(handler)
    old_tool = json.dumps({
        "status": "ok", "operation": "recommend", "result_count": 10,
        "summary": "Top ties for the audience.",
        "results": [{"name": f"row{i}", "description": "x" * 150}
                    for i in range(10)],
    })
    reply = await p.chat([
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "brief"},
        {"role": "assistant", "content": "", "tool_calls": []},
        {"role": "tool", "tool_call_id": "t-old", "name": "qloo_recommend",
         "content": old_tool},
        {"role": "tool", "tool_call_id": "t-new", "name": "qloo_find_tags",
         "content": json.dumps({"status": "ok", "operation": "find_tags",
                                "result_count": 10, "summary": "tags"})},
    ], tools=[{"type": "function", "function": {"name": "qloo_find_tags"}}])
    assert reply.content == "ok"
    assert len(bodies) == 2
    shrunken = bodies[1]["messages"]
    old = next(m for m in shrunken if m.get("tool_call_id") == "t-old")
    new = next(m for m in shrunken if m.get("tool_call_id") == "t-new")
    assert json.loads(old["content"]) == {
        "status": "ok", "operation": "recommend", "result_count": 10,
        "summary": "Top ties for the audience.",
    }
    assert new["content"] == bodies[0]["messages"][4]["content"]
    assert bodies[1]["tools"] == bodies[0]["tools"]
    await p._client.aclose()


@pytest.mark.asyncio
async def test_http_413_final_level_drops_tool_schemas():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(413, json={"error": {"message": "too large"}})

    p = provider(handler)
    with pytest.raises(RuntimeError, match="even shrunk"):
        await p.chat([
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "brief"},
            {"role": "tool", "tool_call_id": "t0", "name": "t",
             "content": json.dumps({"status": "ok", "summary": "s"})},
        ], tools=[{"type": "function", "function": {"name": "qloo_find_tags"}}])
    await p._client.aclose()


def test_shrink_levels_covers_no_tool_messages():
    from app.agent.provider import _shrink_levels

    body = {"messages": [{"role": "user", "content": "hi"}], "tools": [{}]}
    assert _shrink_levels(body) == []
