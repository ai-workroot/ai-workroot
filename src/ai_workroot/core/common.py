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
class DomainEvent:
    event_type: str
    source_ref: SourceRef
    occurred_at: str
