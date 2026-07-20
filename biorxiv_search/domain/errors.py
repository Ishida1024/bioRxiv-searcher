class SearcherError(Exception):
    """Base error with a stable code for interface adapters."""

    code = "searcher_error"
    retryable = False

    def __init__(self, message: str, *, provider: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider


class InvalidInputError(SearcherError):
    code = "invalid_input"


class NotFoundError(SearcherError):
    code = "not_found"


class UpstreamTimeoutError(SearcherError):
    code = "upstream_timeout"
    retryable = True


class UpstreamRateLimitedError(SearcherError):
    code = "upstream_rate_limited"
    retryable = True


class UpstreamUnavailableError(SearcherError):
    code = "upstream_unavailable"
    retryable = True


class UpstreamProtocolError(SearcherError):
    code = "upstream_protocol_error"

