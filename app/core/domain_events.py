from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, List, Optional
import uuid

logger = logging.getLogger("app.domain_events")


class DomainEvent:
    """
    Base Domain Event class for ApnaERP.
    Represents immutable facts that occurred in the domain.
    """
    def __init__(self, event_name: str, payload: Dict[str, Any]):
        self.event_id = str(uuid.uuid4())
        self.event_name = event_name
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.payload = payload

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_name": self.event_name,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }


class DomainEventPublisher:
    """
    In-memory / Redis domain event publisher.
    Allows decoupling domain events from consumer modules (Procurement, Sales, Finance, Manufacturing).
    """

    def __init__(self):
        self._handlers: Dict[str, List[Callable[[DomainEvent], None]]] = {}

    def subscribe(self, event_name: str, handler: Callable[[DomainEvent], None]) -> None:
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        self._handlers[event_name].append(handler)

    def publish(self, event_name: str, payload: Dict[str, Any]) -> DomainEvent:
        event = DomainEvent(event_name, payload)
        logger.info(f"[DomainEventPublished] {event.event_name} (ID: {event.event_id}) -> {event.payload}")

        # Execute registered in-memory handlers
        if event_name in self._handlers:
            for handler in self._handlers[event_name]:
                try:
                    handler(event)
                except Exception as exc:
                    logger.error(f"Error handling event '{event_name}' in handler '{handler}': {exc}")

        return event


# Global singleton event publisher
domain_event_publisher = DomainEventPublisher()
