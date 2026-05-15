"""Logging configuration helpers for the application."""

import json
import logging
import sys
from datetime import datetime, timezone

from app.core.context import request_id

# Standard LogRecord attributes plus known third-party injections
# Used to identify explicitly passed extra={} attributes
STANDARD_LOGRECORD_ATTRS = frozenset(
    {
        # Standard LogRecord attributes
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "taskName",
        "asctime",
        # Known third-party injections
        "color_message",  # uvicorn
    }
)

LOGGERS_TO_SILENCE = [
    "sqlalchemy.engine",
    "sqlalchemy.engine.Engine",
    "httpx",
    "httpcore",
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
]


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging.

    Outputs logs in GCP-compatible JSON format with:
    - RFC 3339 timestamps
    - 'severity' instead of 'level' (GCP requirement)
    - request_id from ContextVar for request tracing
    - Extra attributes passed via extra={} by the caller
    """

    def formatTime(self, record: logging.LogRecord) -> str:
        """Override to emit RFC 3339 timestamps expected by GCP Cloud Logging."""
        return datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "severity": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "filename": record.filename,
            "lineno": record.lineno,
            "request_id": request_id.get(),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if record.stack_info:
            log_data["stack_info"] = self.formatStack(record.stack_info)

        # Include only explicitly passed extra={} attributes
        for key, value in record.__dict__.items():
            if key not in STANDARD_LOGRECORD_ATTRS:
                log_data[key] = value

        return json.dumps(log_data, default=str)


def setup_logging(log_level: str) -> None:
    """Configure root logger with a JSON stdout handler.

    Should be called once at application startup inside the lifespan.
    Clears any existing handlers before attaching a fresh one to
    prevent duplicate log lines across reloads.
    """
    root_logger = logging.getLogger()
    level = _resolve_log_level(log_level)

    formatter = JSONFormatter()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    for existing_handler in root_logger.handlers[:]:
        root_logger.removeHandler(existing_handler)
        existing_handler.close()

    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    # Silence noisy third-party loggers by setting their level to WARNING and propagating to root  # noqa: E501
    for logger_name in LOGGERS_TO_SILENCE:
        third_party_logger = logging.getLogger(logger_name)
        third_party_logger.handlers.clear()
        third_party_logger.setLevel(logging.WARNING)
        third_party_logger.propagate = True


def _resolve_log_level(log_level: str) -> int:
    """Convert a log level string to its logging module constant."""
    normalized = log_level.upper()
    level = getattr(logging, normalized, None)
    if level is None:
        raise ValueError(f"Invalid log level: {log_level!r}")
    return level
