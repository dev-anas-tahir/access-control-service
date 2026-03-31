"""Context variables for request-scoped data."""

from contextvars import ContextVar

request_id: ContextVar[str] = ContextVar("request_id", default="-")
