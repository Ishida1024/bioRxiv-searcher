import asyncio
import random
import time
from collections.abc import Mapping
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from ..domain.errors import (
    UpstreamProtocolError,
    UpstreamRateLimitedError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)


class PoliteHttpClient:
    def __init__(
        self,
        *,
        user_agent: str,
        client: httpx.AsyncClient | None = None,
        min_interval: float = 0.1,
        max_retries: int = 2,
    ) -> None:
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None
        self._user_agent = user_agent
        self._min_interval = min_interval
        self._max_retries = max_retries
        self._last_request = 0.0
        self._rate_lock = asyncio.Lock()

    async def request_json(self, method: str, url: str, **kwargs: Any) -> dict:
        headers = dict(kwargs.pop("headers", {}))
        headers.setdefault("User-Agent", self._user_agent)
        kwargs["headers"] = headers

        for attempt in range(self._max_retries + 1):
            await self._wait_for_rate_limit()
            try:
                response = await self._client.request(method, url, **kwargs)
            except httpx.TimeoutException as exc:
                if attempt < self._max_retries:
                    await self._backoff(attempt)
                    continue
                raise UpstreamTimeoutError("Upstream request timed out") from exc
            except httpx.HTTPError as exc:
                if attempt < self._max_retries:
                    await self._backoff(attempt)
                    continue
                raise UpstreamUnavailableError("Upstream request failed", provider=url) from exc

            if response.status_code == 429:
                if attempt < self._max_retries:
                    await asyncio.sleep(self._retry_after(response, attempt))
                    continue
                raise UpstreamRateLimitedError("Upstream rate limit exceeded", provider=url)
            if response.status_code in {502, 503, 504} and attempt < self._max_retries:
                await asyncio.sleep(self._retry_after(response, attempt))
                continue
            if response.status_code >= 500:
                raise UpstreamUnavailableError(
                    f"Upstream returned HTTP {response.status_code}", provider=url
                )
            if response.status_code >= 400:
                raise UpstreamProtocolError(
                    f"Upstream returned HTTP {response.status_code}", provider=url
                )
            try:
                payload = response.json()
            except ValueError as exc:
                raise UpstreamProtocolError("Upstream returned invalid JSON", provider=url) from exc
            if not isinstance(payload, dict):
                raise UpstreamProtocolError("Upstream JSON response must be an object", provider=url)
            return payload
        raise AssertionError("retry loop must return or raise")

    async def _wait_for_rate_limit(self) -> None:
        async with self._rate_lock:
            delay = self._min_interval - (time.monotonic() - self._last_request)
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_request = time.monotonic()

    async def _backoff(self, attempt: int) -> None:
        await asyncio.sleep((0.25 * (2**attempt)) + random.uniform(0, 0.1))

    @staticmethod
    def _retry_after(response: httpx.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return max(0.0, float(value))
            except ValueError:
                try:
                    target = parsedate_to_datetime(value).timestamp()
                    return max(0.0, target - time.time())
                except (TypeError, ValueError, OverflowError):
                    pass
        return 0.25 * (2**attempt) + random.uniform(0, 0.1)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
