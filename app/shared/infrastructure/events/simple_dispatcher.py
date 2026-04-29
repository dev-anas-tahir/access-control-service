"""Simple in-memory event dispatcher implementation.

This dispatcher routes domain events to registered handlers synchronously.
It is suitable for single-process deployments and testing.
"""

from typing import Awaitable, Callable

from app.shared.domain.events import DomainEvent, EventDispatcher

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class SimpleEventDispatcher(EventDispatcher):
    """Simple event dispatcher that routes events to registered handlers.

    Handlers are registered by event type and are called sequentially
    when an event of that type is dispatched.
    """

    def __init__(self) -> None:
        """Initialize with empty handler registry."""
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = {}

    def register(
        self, event_type: type[DomainEvent], handler: EventHandler
    ) -> None:
        """Register a handler for a specific event type.

        Multiple handlers can be registered for the same event type.
        They will be called in registration order.

        Args:
            event_type: The domain event class to handle
            handler: Async callable that handles the event
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def register_many(
        self, event_types: list[type[DomainEvent]], handler: EventHandler
    ) -> None:
        """Register a handler for multiple event types.

        Args:
            event_types: List of domain event classes to handle
            handler: Async callable that handles the events
        """
        for event_type in event_types:
            self.register(event_type, handler)

    async def dispatch(self, event: DomainEvent) -> None:
        """Dispatch a domain event to its registered handlers.

        Args:
            event: The domain event to dispatch
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        for handler in handlers:
            await handler(event)

    async def dispatch_all(self, events: list[DomainEvent]) -> None:
        """Dispatch multiple domain events.

        Args:
            events: List of domain events to dispatch
        """
        for event in events:
            await self.dispatch(event)

    def clear_handlers(self, event_type: type[DomainEvent] | None = None) -> None:
        """Clear registered handlers.

        Useful for testing to ensure clean state between tests.

        Args:
            event_type: Specific event type to clear, or None to clear all
        """
        if event_type is None:
            self._handlers.clear()
        else:
            self._handlers.pop(event_type, None)
