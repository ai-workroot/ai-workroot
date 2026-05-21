"""Reusable task scenarios for persona end-to-end tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskScenario:
    scenario_id: str
    title: str
    query: str
    summary: str
    body: str
    kind: str = "project"
    protection: str = "none"
    force_hard_trim: bool = False


SCENARIOS: tuple[TaskScenario, ...] = (
    TaskScenario(
        scenario_id="planning",
        title="Plan next milestone",
        query="next milestone plan",
        summary="Milestone plan with explicit next steps and risks.",
        body="Plan the next milestone, dependencies, owner notes, and review gates.",
        kind="planning",
    ),
    TaskScenario(
        scenario_id="debugging",
        title="Debug recurring failure",
        query="recurring failure root cause",
        summary="Root cause analysis with evidence and rollback path.",
        body="Investigate a recurring failure, compare traces, and isolate the source.",
        kind="debugging",
    ),
    TaskScenario(
        scenario_id="decision",
        title="Decision tradeoff",
        query="decision tradeoff",
        summary="Decision record with alternatives, rationale, and follow-up.",
        body="Compare options, choose a path, and preserve the decision.",
        kind="decision",
    ),
    TaskScenario(
        scenario_id="redaction",
        title="Protected redaction detail",
        query="protected redaction detail",
        summary="Safe summary for a sensitive item that requires redaction.",
        body="Exercise redaction filters without exposing sensitive details.",
        kind="release-control",
        protection="redacted",
    ),
    TaskScenario(
        scenario_id="deletion",
        title="Delete obsolete sensitive detail",
        query="deleted sensitive detail",
        summary="Safe companion for deleted sensitive detail.",
        body="Exercise deletion records while keeping ordinary context clean.",
        kind="release-control",
        protection="deleted",
    ),
    TaskScenario(
        scenario_id="tombstone",
        title="Outdated conclusion tombstone",
        query="outdated conclusion tombstone",
        summary="Tombstone marker for an outdated conclusion that may remain symbolic.",
        body="Keep the symbolic note while avoiding stale content as current truth.",
        kind="release-control",
        protection="tombstone",
    ),
    TaskScenario(
        scenario_id="large-context",
        title="Large context trim budget",
        query="large context trim budget",
        summary="Large context pressure case that must preserve debug trace under trim.",
        body=("large context trim budget " * 240).strip(),
        kind="context-control",
        force_hard_trim=True,
    ),
    TaskScenario(
        scenario_id="weak-query",
        title="Weak query current work",
        query="what should I do next",
        summary="Weak query should still recall the highest priority active context card.",
        body="A vague continuation request should recover active priority context.",
        kind="handoff",
    ),
)


def scenarios_for_persona(persona_slug: str, count: int) -> tuple[TaskScenario, ...]:
    if count <= 0:
        return ()
    offset = sum(ord(char) for char in persona_slug) % len(SCENARIOS)
    ordered = tuple(SCENARIOS[(offset + index) % len(SCENARIOS)] for index in range(len(SCENARIOS)))
    repeated: list[TaskScenario] = []
    while len(repeated) < count:
        repeated.extend(ordered)
    return tuple(repeated[:count])
