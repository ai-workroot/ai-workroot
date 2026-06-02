"""Runtime-only high-level Work Signal parsing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PHASES = {
    "starting",
    "orienting",
    "planning",
    "executing",
    "checking",
    "deciding",
    "summarizing",
    "preserving",
    "switching",
    "recovering",
}
WORK_KINDS = {
    "quick",
    "inbox",
    "task",
    "continuation",
    "investigation",
    "implementation",
    "review",
    "decision",
    "learning",
    "authoring",
    "operations",
}
INTENDED_ACTIONS = {
    "answer",
    "clarify",
    "plan",
    "execute",
    "inspect",
    "diagnose",
    "edit",
    "test",
    "review",
    "decide",
    "summarize",
    "preserve",
    "publish",
}
CONCERNS = {
    "needs_evidence",
    "needs_user_decision",
    "may_change_user_assets",
    "may_publish",
    "may_be_sensitive",
    "uncertain_task_boundary",
    "blocked",
    "recovering_from_interruption",
}


@dataclass(frozen=True)
class WorkSignal:
    phase: str = ""
    work_kind: str = ""
    intended_action: str = ""
    focus: str = ""
    concerns: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "WorkSignal":
        if not isinstance(data, dict):
            return cls()
        return cls(
            phase=_choice(data.get("phase"), PHASES),
            work_kind=_choice(data.get("work_kind"), WORK_KINDS),
            intended_action=_choice(data.get("intended_action"), INTENDED_ACTIONS),
            focus=str(data.get("focus") or "").strip(),
            concerns=tuple(
                concern
                for concern in (str(value).strip() for value in data.get("concerns") or [])
                if concern in CONCERNS
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "work_kind": self.work_kind,
            "intended_action": self.intended_action,
            "focus": self.focus,
            "concerns": list(self.concerns),
        }


def _choice(value: object, allowed: set[str]) -> str:
    text = str(value or "").strip()
    return text if text in allowed else ""
