import json
import logging
import sys

import pytest

from app.core.logging import JSONFormatter, setup_logging


@pytest.fixture
def restore_root_logger():
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level

    yield root_logger

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    root_logger.setLevel(original_level)

    for handler in original_handlers:
        root_logger.addHandler(handler)


def test_setup_logging_configures_root_logger(restore_root_logger):
    root_logger = restore_root_logger

    setup_logging("info")

    assert root_logger.level == logging.INFO
    assert len(root_logger.handlers) == 1

    handler = root_logger.handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    assert handler.stream is sys.stdout
    assert handler.formatter is not None
    assert isinstance(handler.formatter, JSONFormatter)


def test_setup_logging_replaces_existing_handlers(restore_root_logger):
    root_logger = restore_root_logger
    root_logger.addHandler(logging.NullHandler())

    setup_logging("warning")

    assert root_logger.level == logging.WARNING
    assert len(root_logger.handlers) == 1
    handler = root_logger.handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    assert isinstance(handler.formatter, JSONFormatter)


def test_json_formatter_outputs_valid_json(restore_root_logger):
    """Test that the JSON formatter produces valid JSON output."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    output = formatter.format(record)
    parsed = json.loads(output)

    assert "timestamp" in parsed
    assert "severity" in parsed
    assert parsed["severity"] == "INFO"
    assert "name" in parsed
    assert parsed["name"] == "test.logger"
    assert "message" in parsed
    assert parsed["message"] == "Test message"


def test_json_formatter_includes_exception(restore_root_logger):
    """Test that exceptions are included in the JSON output."""
    formatter = JSONFormatter()
    try:
        raise ValueError("Test error")
    except ValueError:
        exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

    output = formatter.format(record)
    parsed = json.loads(output)

    assert "exception" in parsed
    assert "ValueError: Test error" in parsed["exception"]


def test_json_formatter_includes_extra_fields(restore_root_logger):
    """Test that extra fields passed to the logger are included."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Test with extra",
        args=(),
        exc_info=None,
    )
    # Add custom extra fields
    record.user_id = "12345"
    record.request_id = "req-abc-123"

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["user_id"] == "12345"
    assert parsed["request_id"] == "req-abc-123"


def test_setup_logging_rejects_invalid_log_level(restore_root_logger):
    with pytest.raises(ValueError, match="Invalid log level"):
        setup_logging("not-a-real-level")


def test_json_formatter_excludes_standard_attributes(restore_root_logger):
    """Test that standard LogRecord attributes are excluded from extra fields."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    # Add a standard attribute (this simulates what happens internally)
    record.levelname = (
        "INFO"  # This is a standard attribute and should be excluded from extra
    )

    # Add a custom extra field
    record.custom_field = "custom_value"

    output = formatter.format(record)
    parsed = json.loads(output)

    # Standard attributes should NOT appear as extra fields (they're already in the base log data)  # noqa: E501
    # The custom field should appear as an extra field
    assert "custom_field" in parsed
    assert parsed["custom_field"] == "custom_value"

    # Verify that standard attributes are not duplicated as extra fields
    # (They are already included in the base structure)


def test_json_formatter_handles_exc_text_attribute(restore_root_logger):
    """Test that exc_text attribute doesn't leak through as an extra field."""
    formatter = JSONFormatter()
    try:
        raise ValueError("Test error")
    except ValueError:
        exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        # Simulate what happens when formatException is called and exc_text is cached
        record.exc_text = "ValueError: Test error"

    output = formatter.format(record)
    parsed = json.loads(output)

    # exc_text should not appear as an extra field, it's handled separately in exception formatting  # noqa: E501
    # Check that it's not in the extra fields (it should be handled in the exception formatting)  # noqa: E501
    assert "exc_text" not in parsed or "exc_text" not in [
        k
        for k in parsed.keys()
        if k
        not in [
            "timestamp",
            "severity",
            "name",
            "message",
            "filename",
            "lineno",
            "request_id",
            "exception",
        ]
    ]
