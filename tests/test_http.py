import httpx
import pytest

from biorxiv_search.domain import UpstreamProtocolError, UpstreamUnavailableError
from biorxiv_search.infrastructure.http import PoliteHttpClient


@pytest.mark.asyncio
async def test_http_client_rejects_invalid_json_without_leaking_response():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text="not-json"))
    client = PoliteHttpClient(
        user_agent="test",
        client=httpx.AsyncClient(transport=transport),
        max_retries=0,
        min_interval=0,
    )
    with pytest.raises(UpstreamProtocolError, match="invalid JSON"):
        await client.request_json("GET", "https://example.test")


@pytest.mark.asyncio
async def test_http_client_does_not_retry_client_errors():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"error": "bad request"})

    client = PoliteHttpClient(
        user_agent="test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        max_retries=2,
        min_interval=0,
    )
    with pytest.raises(UpstreamProtocolError):
        await client.request_json("GET", "https://example.test")
    assert calls == 1


@pytest.mark.asyncio
async def test_http_client_retries_server_errors(monkeypatch):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(503 if calls == 1 else 200, json={"ok": True})

    async def no_sleep(delay):
        return None

    monkeypatch.setattr("biorxiv_search.infrastructure.http.asyncio.sleep", no_sleep)
    client = PoliteHttpClient(
        user_agent="test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        max_retries=1,
        min_interval=0,
    )
    assert await client.request_json("GET", "https://example.test") == {"ok": True}
    assert calls == 2
