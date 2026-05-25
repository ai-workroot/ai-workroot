"""Storage contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class StoredRecord:
    key: str
    value: dict[str, Any]
    version: str | None = None


@runtime_checkable
class KeyValueStore(Protocol):
    def get(self, key: str) -> StoredRecord | None:
        """Return a stored record by key."""

    def put(self, record: StoredRecord) -> None:
        """Persist a stored record."""
