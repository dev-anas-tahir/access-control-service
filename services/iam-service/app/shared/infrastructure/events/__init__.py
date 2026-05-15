"""Event dispatching infrastructure.

This module provides the concrete implementation of the EventDispatcher port,
routing domain events to appropriate handlers (e.g., audit logging).
"""

from app.shared.infrastructure.events.simple_dispatcher import SimpleEventDispatcher
from app.shared.infrastructure.events.audit_handler import AuditLoggingHandler

__all__ = ["SimpleEventDispatcher", "AuditLoggingHandler"]
