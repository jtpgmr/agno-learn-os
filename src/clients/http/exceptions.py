from collections.abc import Mapping

_BODY_SNIPPET_CHARS = 500


class HttpClientError(Exception):
    """Base for every failure raised by the HTTP client layer."""

    def __init__(self, message: str, *, method: str, url: str) -> None:
        super().__init__(message)
        self.method = method
        self.url = url


class HttpTransportError(HttpClientError):
    """No response received: DNS, TLS, connect/read timeout, reset."""


class HttpStatusError(HttpClientError):
    """A response arrived carrying a non-2xx status."""

    def __init__(
        self,
        *,
        method: str,
        url: str,
        status_code: int,
        response_body: str | None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.response_body = response_body
        self.headers: Mapping[str, str] = headers or {}
        super().__init__(
            f"{method} {url} -> {status_code}: {self.body_snippet}",
            method=method,
            url=url,
        )

    @property
    def body_snippet(self) -> str:
        return (self.response_body or "")[:_BODY_SNIPPET_CHARS]

    @property
    def is_retryable(self) -> bool:
        return self.status_code == 429 or 500 <= self.status_code < 600

    @property
    def retry_after_seconds(self) -> float | None:
        raw = self.headers.get("retry-after")
        return float(raw) if raw and raw.isdigit() else None
