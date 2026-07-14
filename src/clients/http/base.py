"""Resilient async HTTP client shared by the source toolkits.

A thin wrapper over ``httpx.AsyncClient`` that centralizes the concerns each
source would otherwise duplicate: a bounded timeout, a browser-ish
User-Agent, retry-with-backoff for idempotent GETs (honoring ``Retry-After``
on 429), ``raise_for_status``, and error bodies surfaced on failure.

Lifecycle follows the project convention: cheap constructor, resource built
on ``__aenter__`` and disposed on ``__aexit__``. An ``httpx.AsyncClient`` may
be injected for connection pooling across calls or for testing; an injected
client is never closed by this wrapper (``_owns_client``).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 10.0
_DEFAULT_MAX_RETRIES = 2
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class HttpClientError(Exception):
    """An HTTP request failed after exhausting retries.

    Surfaces the response body so a failing call is debuggable rather than
    hiding behind a bare status code.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class APIAuthInterface(Protocol):
    def getAccessToken(self) -> str: ...

    async def getNewAccessToken(self) -> str:
        """Return a currently-valid access token (refreshing if needed)."""
        ...

    async def handleAccessToken(self, access_token) -> None: ...


class AsyncHttpClient:
    """Async GET client with retry/backoff and context-managed lifecycle.

    Args:
        client: Optional ``httpx.AsyncClient`` for pooling/testing. When
            provided it is used as-is and never closed here.
        timeout: Per-request timeout in seconds.
        max_retries: Retry attempts for idempotent GETs on transient errors.
        base_headers: Default headers merged into every request; defaults to
            a browser-like User-Agent (some sources 403 default clients).
    """

    def __init__(
        self,
        *,
        base_url: str,
        client: httpx.AsyncClient | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        base_headers: dict[str, str] | None = None,
        auth: APIAuthInterface | None = None,
    ) -> None:
        self.base_url = base_url
        self._client = client
        self._owns_client = client is None
        self._timeout = timeout
        self._max_retries = max_retries
        self._base_headers = base_headers or {"User-Agent": _DEFAULT_USER_AGENT}

        self._auth = auth

    async def __aenter__(self) -> AsyncHttpClient:
        self._getClient()
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _getClient(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self._timeout,
                follow_redirects=True,
                headers=self._base_headers,
            )

            self._owns_client = True
        return self._client

    async def call(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        params: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        client = self._getClient()
        last_exc: httpx.HTTPError | None = None
        method = method.upper()
        headers = {**(headers or {}), **self._base_headers}
        url = self.base_url + endpoint

        if self._auth is not None:
            headers["Authorization"] = f"Bearer {self._auth.getAccessToken()}"

        token_refreshed = False

        for attempt in range(self._max_retries + 1):
            try:
                response: httpx.Response = await client.request(
                    url=url, method=method, params=params, headers=headers
                )

            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt == self._max_retries:
                    break
                await asyncio.sleep(self._requestDelay(attempt))
                continue

            if response.status_code == 401 and self._auth is not None and not token_refreshed:
                token_refreshed = True
                logger.warning("%s %s -> 401, refreshing token once", method, url)

                new_token = await self._auth.getNewAccessToken()

                if self._auth.handleAccessToken:
                    await self._auth.handleAccessToken(new_token)

                headers["Authorization"] = f"Bearer {self._auth.getAccessToken()}"

                continue

            if response.status_code in _RETRYABLE_STATUS and attempt < self._max_retries:
                delay = self._getRetryAfter(response) or self._requestDelay(attempt)
                logger.warning(
                    f"{method} %s -> %d, retry %d/%d in %.1fs",
                    url,
                    response.status_code,
                    attempt + 1,
                    self._max_retries,
                    delay,
                )
                await asyncio.sleep(delay)
                continue

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise HttpClientError(
                    f"{method} {url} failed: {exc.response.status_code}",
                    status_code=exc.response.status_code,
                    response_body=exc.response.text,
                ) from exc

            return response

        raise HttpClientError(f"{method} {url} failed after retries: {last_exc}") from last_exc

    @staticmethod
    def _requestDelay(attempt: int) -> float:
        return 0.5 * (2**attempt)

    @staticmethod
    def _getRetryAfter(response: httpx.Response) -> float | None:
        raw = response.headers.get("Retry-After")
        if raw is None:
            return None
        try:
            return float(raw)
        except ValueError:
            return None
