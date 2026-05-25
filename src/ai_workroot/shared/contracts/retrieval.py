"""Retrieval contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class RetrievalQuery:
    query: str
    workroot_id: str
    limit: int = 20
    filters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    source_id: str
    title: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class RetrievalProvider(Protocol):
    def retrieve(self, query: RetrievalQuery) -> tuple[RetrievalResult, ...]:
        """Return ranked retrieval results."""
