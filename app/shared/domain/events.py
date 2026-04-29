"""Domain events infrastructure for event-driven decoupling.

This module provides the base class for domain events and the event dispatcher protocol.
Domain events allow bounded contexts to communicate without direct coupling.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base class for all domain events.

    All domain events are immutable (frozen dataclasses) and contain:
    - event_id: Unique identifier for this event occurrence
    - occurred_at: Timestamp when the event occurred
    - actor_id: Optional UUID of the user/system that triggered the event
    """

    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    actor_id: uuid.UUID | None = None

    @property
    def event_type(self) -> str:
        """Return the event type name (defaults to class name)."""
        return self.__class__.__name__


@dataclass(frozen=True)
class EventEnvelope:
    """Wrapper for domain events with metadata.

    This envelope adds routing and tracing information to events
    as they move through the system.
    """

    event: DomainEvent
    correlation_id: uuid.UUID | None = None
    causation_id: uuid.UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class EventDispatcher(Protocol):
    """Port for dispatching domain events to handlers.

    Implementations route events to appropriate handlers based on event type.
    The dispatcher is typically called by the Unit of Work after commit.
    """

    async def dispatch(self, event: DomainEvent) -> None:
        """Dispatch a single domain event to its handlers.

        Args:
            event: The domain event to dispatch
        """
        ...

    async def dispatch_all(self, events: list[DomainEvent]) -> None:
        """Dispatch multiple domain events.

        Default implementation dispatches sequentially. Implementations
        may override for batch processing or transaction semantics.

        Args:
            events: List of domain events to dispatch
        """
        for event in events:
            await self.dispatch(event)


class EventHandler(Protocol):
    """Port for handling a specific type of domain event.

    Handlers are registered with the EventDispatcher and process
    events of a specific type.
    """

    async def handle(self, event: DomainEvent) -> None:
        """Handle a domain event.

        Args:
            event: The domain event to handle
        """
        ...
