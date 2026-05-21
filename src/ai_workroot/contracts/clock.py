"""Clock contract."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    def now_utc(self) -> str:
        """Return current UTC instant as an ISO-8601 string."""
