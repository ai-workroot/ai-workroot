"""Shared core value objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActorRef:
    actor_type: str
    actor_id: str


@dataclass(frozen=True)
class SourceRef:
    source_type: str
    source_id: str


@dataclass(frozen=True)
class EvidenceRef:
    evidence_type: str
    evidence_id: str


@dataclass(frozen=True)
class PolicyRef:
    policy_type: str
    policy_id: str
    policy_version: str | None = None


@dataclass(frozen=True)
class TimeRange:
    start: str
    end: str

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("time range end must be greater than or equal to start")

    def contains(self, instant: str) -> bool:
        return self.start <= instant <= self.end


@dataclass(frozen=True)
class TemporalScope:
    scope_type: str
    scope_id: str
    time_range: TimeRange


@dataclass(frozen=True)
class DomainEvent:
    event_type: str
    source_ref: SourceRef
    occurred_at: str
