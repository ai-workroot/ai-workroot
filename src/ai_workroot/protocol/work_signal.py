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
PHASE_ALIASES = {
    "working": "executing",
    "running": "executing",
    "lookup": "orienting",
    "finding": "orienting",
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
INTENDED_ACTION_ALIASES = {
    "record": "preserve",
    "save": "preserve",
    "lookup": "inspect",
    "find": "inspect",
    "explain": "inspect",
    "rationale": "inspect",
    "evidence": "inspect",
    "source": "inspect",
    "proof": "inspect",
    "justify": "inspect",
}
EVIDENCE_INTENDED_ACTIONS = {"explain", "rationale", "evidence", "source", "proof", "justify"}
BOUNDARIES = {
    "continue_current",
    "separate_work",
    "uncertain",
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
REF_PREFIXES = {
    "asset",
    "candidate",
    "chunk",
    "decision",
    "handoff",
    "output_rule",
    "relationship",
    "run",
    "task",
}
MAX_REFS = 8
MAX_REF_LENGTH = 120


@dataclass(frozen=True)
class WorkSignal:
    phase: str = ""
    work_kind: str = ""
    intended_action: str = ""
    boundary: str = ""
    focus: str = ""
    concerns: tuple[str, ...] = ()
    refs: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "WorkSignal":
        if not isinstance(data, dict):
            return cls()
        raw_intended_action = str(data.get("intended_action") or "").strip().lower()
        concerns = list(_concerns(data.get("concerns")))
        if raw_intended_action in EVIDENCE_INTENDED_ACTIONS and "needs_evidence" not in concerns:
            concerns.append("needs_evidence")
        return cls(
            phase=_choice(data.get("phase"), PHASES, aliases=PHASE_ALIASES),
            work_kind=_choice(data.get("work_kind"), WORK_KINDS),
            intended_action=_choice(data.get("intended_action"), INTENDED_ACTIONS, aliases=INTENDED_ACTION_ALIASES),
            boundary=_choice(data.get("boundary"), BOUNDARIES),
            focus=str(data.get("focus") or "").strip(),
            concerns=tuple(concerns),
            refs=_refs(data.get("refs")),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "work_kind": self.work_kind,
            "intended_action": self.intended_action,
            "boundary": self.boundary,
            "focus": self.focus,
            "concerns": list(self.concerns),
            "refs": list(self.refs),
        }


def _choice(value: object, allowed: set[str], *, aliases: dict[str, str] | None = None) -> str:
    text = str(value or "").strip().lower()
    if aliases:
        text = aliases.get(text, text)
    return text if text in allowed else ""


def _refs(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    refs: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        ref = item.strip()
        if _valid_ref(ref):
            refs.append(_normalize_ref(ref))
        if len(refs) >= MAX_REFS:
            break
    return tuple(refs)


def _concerns(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    concerns: list[str] = []
    for item in value:
        concern = str(item or "").strip().lower()
        if concern in CONCERNS:
            concerns.append(concern)
    return tuple(concerns)


def _valid_ref(value: str) -> bool:
    if not value or len(value) > MAX_REF_LENGTH:
        return False
    if any(part in value for part in ("/", "\\", "..", "\n", "\r", "\t")):
        return False
    raw_prefix, separator, suffix = value.partition(":")
    prefix = raw_prefix.lower()
    if separator != ":" or prefix not in REF_PREFIXES:
        return False
    return bool(suffix.strip())


def _normalize_ref(value: str) -> str:
    prefix, _separator, suffix = value.partition(":")
    return f"{prefix.lower()}:{suffix.strip()}"
