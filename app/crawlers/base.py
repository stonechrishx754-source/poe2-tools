"""Base crawler — token-bucket rate limiting, retry logic, HTTP client."""

import asyncio
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TokenBucket:
    """Async-safe token bucket rate limiter."""

    def __init__(self, rate: float, burst: int = 5):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        """Wait for a token and return the wait time in seconds."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return 0.0

            wait_time = (1.0 - self.tokens) / self.rate if self.rate > 0 else 1.0
            self.tokens = 0.0
            self.last_refill += wait_time

        await asyncio.sleep(wait_time)
        return wait_time


class BaseCrawler:
    """Base class for all data source crawlers.

    Provides:
    - TokenBucket rate limiting per source
    - httpx.AsyncClient with timeouts
    - Retry with exponential backoff
    - Structured logging
    """

    source_name: str = "base"
    rate_limit_per_second: float = 1.0
    burst_size: int = 5
    max_retries: int = 3
    retry_delay: float = 5.0
    request_timeout: float = 30.0

    def __init__(self):
        self._bucket = TokenBucket(rate=self.rate_limit_per_second, burst=self.burst_size)
        self._client: httpx.AsyncClient | None = None
        self._stats = {"requests": 0, "errors": 0, "last_error": None}

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.request_timeout,
                headers={"User-Agent": "POE2-Analytics/0.1"},
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def fetch(self, url: str, **kwargs) -> dict[str, Any] | list[Any]:
        """Make a rate-limited GET request with retry logic.

        Returns parsed JSON (dict or list).
        Raises on final failure after exhausting retries.
        """
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            # Rate limit wait
            await self._bucket.acquire()
            self._stats["requests"] += 1

            try:
                response = await self.client.get(url, **kwargs)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    logger.warning(
                        "%s: 429 rate limited, waiting %ds (attempt %d/%d)",
                        self.source_name, retry_after, attempt, self.max_retries,
                    )
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self.max_retries:
                    wait = self.retry_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "%s: HTTP %d, retrying in %.0fs (attempt %d/%d)",
                        self.source_name, e.response.status_code, wait,
                        attempt, self.max_retries,
                    )
                    await asyncio.sleep(wait)
                    last_error = e
                    continue
                self._stats["errors"] += 1
                self._stats["last_error"] = str(e)
                raise

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                wait = self.retry_delay * (2 ** (attempt - 1))
                logger.warning(
                    "%s: network error, retrying in %.0fs (attempt %d/%d): %s",
                    self.source_name, wait, attempt, self.max_retries, e,
                )
                await asyncio.sleep(wait)
                last_error = e
                continue

        self._stats["errors"] += 1
        self._stats["last_error"] = str(last_error)
        raise last_error  # type: ignore[misc]

    def get_stats(self) -> dict:
        return dict(self._stats)
