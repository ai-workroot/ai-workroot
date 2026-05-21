"""Core Work model."""

from __future__ import annotations

from dataclasses import dataclass


TASK_STATUSES = {"active", "paused", "blocked", "closed", "released"}
TASK_TRANSITIONS = {
    "active": {"paused", "blocked", "closed", "released"},
    "paused": {"active", "closed", "released"},
    "blocked": {"active", "paused", "closed", "released"},
    "closed": {"released"},
    "released": set(),
}


@dataclass
class Task:
    task_id: str
    title: str
    status: str = "active"
    task_kind: str = "project"
    process_level: str = "L1"

    def can_transition_to(self, status: str) -> bool:
        if status not in TASK_STATUSES:
            return False
        return status in TASK_TRANSITIONS.get(self.status, set())

    def close(self) -> None:
        if not self.can_transition_to("closed"):
            raise ValueError(f"cannot close task from status {self.status!r}")
        self.status = "closed"

    def should_request_decomposition(self) -> bool:
        return self.process_level == "L2" or self.task_kind == "project"


@dataclass(frozen=True)
class AgentRun:
    run_id: str
    task_id: str
    status: str
    validity: str = "unknown"


@dataclass(frozen=True)
class WorkAction:
    action_id: str
    task_id: str
    action_type: str
    risk_level: str = "normal"


@dataclass(frozen=True)
class WorkCheckpoint:
    checkpoint_id: str
    task_id: str
    current_status: str


@dataclass(frozen=True)
class RetrievalCard:
    card_id: str
    task_id: str
    source_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class InvalidationRecord:
    invalidation_id: str
    invalidated_claim: str
    reason: str


@dataclass(frozen=True)
class OperationTransaction:
    transaction_id: str
    status: str = "active"

    def is_rolled_back(self) -> bool:
        return self.status == "rolled_back"
