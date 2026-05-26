"""Protocol directive builders."""

from __future__ import annotations

from typing import Any, Optional


DIRECTIVE_TYPES = {
    "continue_task",
    "ask_user",
    "commit_required",
    "handoff_required",
    "resync_required",
    "promote_candidate",
    "archive_candidate",
    "blocked",
    "safe_to_stop",
    "no_persistent_work",
}


def directive(
    directive_type: str,
    *,
    goal: Optional[str] = None,
    next_action: Optional[str] = None,
    expected_events: Optional[list[str]] = None,
    required_before_stop: Optional[list[str]] = None,
    must_not: Optional[list[str]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if directive_type not in DIRECTIVE_TYPES:
        raise ValueError(f"unknown directive type: {directive_type}")
    return {
        "type": directive_type,
        "goal": goal,
        "next_action": next_action,
        "expected_events": expected_events or [],
        "required_before_stop": required_before_stop or [],
        "must_not": must_not or [],
        "ask_user_when": [],
        "metadata": metadata or {},
    }


def resync_required(next_action: str = "Call sync and retry if still relevant.") -> dict[str, Any]:
    return directive("resync_required", next_action=next_action, expected_events=[])
