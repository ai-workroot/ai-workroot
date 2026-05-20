"""Event contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class EventRecord:
    event_type: str
    payload: dict[str, Any]
    occurred_at: str | None = None


@runtime_checkable
class EventPublisher(Protocol):
    def publish(self, event: EventRecord) -> None:
        """Publish an event record."""
