"""Middleware for request ID tracking."""

import logging
import re
import time
import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.context import request_id

logger = logging.getLogger(__name__)


def validate_request_id(request_id: Optional[str]) -> bool:
    """Validate that the request ID is safe and follows expected format.

    Args:
        request_id: The request ID to validate

    Returns:
        True if the request ID is valid, False otherwise
    """
    if not request_id:
        return False

    # Check length (prevent resource exhaustion)
    if len(request_id) > 64:
        return False

    # Check that it contains only safe characters (alphanumeric, hyphens, underscores, dots)  # noqa: E501
    if not re.match(r"^[a-zA-Z0-9._-]+$", request_id):
        return False

    return True


class RequestResponseMiddleware(BaseHTTPMiddleware):
    """Middleware that adds a unique request ID to each request.

    The request ID is either:
    - Taken from the X-Request-ID header if present (with validation)
    - Generated as a new UUID4 if not present

    The request ID is stored in a ContextVar for access throughout the request
    lifecycle and is also added to the response headers for client-side tracing.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Log request details
        method = request.method
        url = str(request.url)
        client_ip = request.client.host if request.client else "unknown"
        start_time = time.perf_counter()

        # Get request ID from header or generate a new one
        client_request_id = request.headers.get("X-Request-ID")

        if validate_request_id(client_request_id):
            request_id_value = client_request_id
        else:
            # If invalid or not provided, generate a new UUID
            request_id_value = str(uuid.uuid4())

        # Set the request ID in the context variable
        token = request_id.set(request_id_value)

        try:
            # Call the next handler
            response = await call_next(request)

            # Log response details
            duration = (
                time.perf_counter() - start_time
            ) * 1000  # Convert to milliseconds
            status_code = response.status_code

            # Log the request/response details
            logger.info(
                f"Request: {method} {url} from {client_ip} - "
                f"Response: {status_code} in {duration:.2f}ms"
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id_value

            return response
        finally:
            # Reset the context variable to its previous value
            request_id.reset(token)
