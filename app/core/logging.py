"""Logging configuration helpers for the application."""

import json
import logging
import sys

from app.core.context import request_id


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs in JSON format."""

    def format(self, record: logging.LogRecord) -> str:
        # Create the base log data
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "severity": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "filename": record.filename,
            "lineno": record.lineno,
            "request_id": request_id.get(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add stack info if present
        if record.stack_info:
            log_data["stack_info"] = self.formatStack(record.stack_info)

        # Add any extra attributes passed to the logger
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message"
            ]:
                log_data[key] = value

        return json.dumps(log_data)


def setup_logging(log_level: str) -> None:
    """Configure the root logger with a stdout stream handler."""
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


def _resolve_log_level(log_level: str) -> int:
    """Convert a log level name to its logging module constant."""
    normalized_level = log_level.upper()
    level = getattr(logging, normalized_level, None)
    if level is None:
        raise ValueError(f"Invalid log level: {log_level}")
    return level
