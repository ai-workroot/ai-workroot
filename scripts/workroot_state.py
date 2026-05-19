#!/usr/bin/env python3
"""Managed state initialization for AI Workroot Clean Mode."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

try:
    from workroot_paths import assert_clean_mode_boundary, workroot_state_dir
except ModuleNotFoundError:  # pragma: no cover - package import path for tests.
    from scripts.workroot_paths import assert_clean_mode_boundary, workroot_state_dir


CONFIG_VERSION = "0.9.529"
SCHEMA_VERSION = "0.1"
REGISTRY_FILES = {
    "workroots.jsonl",
    "directory-bindings.jsonl",
    "aliases.jsonl",
    "relationships.jsonl",
}
GLOBAL_INDEX_FILES = {
    "workroots.index.jsonl",
    "tasks.index.jsonl",
    "assets.index.jsonl",
    "knowledge.index.jsonl",
    "decisions.index.jsonl",
    "handoffs.index.jsonl",
    "time.index.jsonl",
}
WORKROOT_DIRECTORIES = [
    "agent",
    "state",
    "tasks/daily",
    "tasks/subtasks",
    "handoffs",
    "assets/summaries",
    "knowledge/facts",
    "knowledge/inbox",
    "knowledge/domains",
    "knowledge/links",
    "graph/exports",
    "graph/backups",
    "indexes",
    "context/packages/history",
    "context/debug/history",
    "maintenance/proposals",
    "concurrency/locks",
    "concurrency/pending",
    "concurrency/merges",
    "logs",
    "cache",
]


@dataclass(frozen=True)
class InitializedWorkroot:
    workroot_id: str
    name: str
    user_directory: Path
    state_directory: Path


def read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl_unique(path: Path, key: str, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = read_jsonl(path)
    value = payload[key]
    if not any(record.get(key) == value for record in records):
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def touch_jsonl(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)


def initialize_ai_workroot_home(home: Path, now: str) -> None:
    home.mkdir(parents=True, exist_ok=True)
    write_json(
        home / "config.json",
        {
            "version": CONFIG_VERSION,
            "schemaVersion": SCHEMA_VERSION,
            "createdAt": now,
            "defaultMode": "clean",
        },
    )
    for name in REGISTRY_FILES:
        touch_jsonl(home / "registry" / name)
    for name in GLOBAL_INDEX_FILES:
        touch_jsonl(home / "global-index" / name)
    (home / "global-index/levels").mkdir(parents=True, exist_ok=True)
    for name in ("l1.jsonl", "l2.jsonl", "l3.jsonl"):
        touch_jsonl(home / "global-index/levels" / name)
    (home / "global-cache").mkdir(parents=True, exist_ok=True)
    for rel in (
        "agent-guides/common.md",
        "agent-guides/codex.md",
        "agent-guides/claude-code.md",
        "user/profile.md",
        "user/preferences.md",
        "user/global-principles.md",
        "user/agent-overrides/common.md",
        "user/agent-overrides/codex.md",
        "user/agent-overrides/claude-code.md",
    ):
        path = home / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)


def initialize_workroot_state(
    home: Path,
    workroot_id: str,
    name: str,
    user_directory: Path,
    now: str,
) -> InitializedWorkroot:
    initialize_ai_workroot_home(home, now=now)
    canonical_user_directory = user_directory.resolve()
    state_directory = workroot_state_dir(home, workroot_id).resolve()
    assert_clean_mode_boundary(canonical_user_directory, state_directory)

    for rel in WORKROOT_DIRECTORIES:
        (state_directory / rel).mkdir(parents=True, exist_ok=True)

    metadata = {
        "version": CONFIG_VERSION,
        "schemaVersion": SCHEMA_VERSION,
        "workrootId": workroot_id,
        "name": name,
        "mode": "clean",
        "userDirectory": str(canonical_user_directory),
        "stateDirectory": str(state_directory),
        "createdAt": now,
        "updatedAt": now,
    }
    write_json(state_directory / "workroot.json", metadata)
    write_json(
        state_directory / "state/current.json",
        {
            "currentFocus": "",
            "activeTaskId": None,
            "nextSuggestedAction": "",
            "contextVersion": 1,
            "lastActivityAt": now,
        },
    )
    (state_directory / "state/continue.md").write_text("# Continue\n\nNo active work yet.\n", encoding="utf-8")
    write_json(
        state_directory / "state/runtime-hints.json",
        {
            "contextGuide": {
                "targetLatencyMs": 1000,
                "defaultTokenBudget": 4000,
                "hardTokenBudget": 6000,
                "allowRemoteCallsInHotPath": False,
                "allowVectorSearch": False,
            }
        },
    )

    append_jsonl_unique(
        home / "registry/workroots.jsonl",
        "workrootId",
        {
            "workrootId": workroot_id,
            "name": name,
            "mode": "clean",
            "userDirectory": str(canonical_user_directory),
            "stateDirectory": str(state_directory),
            "status": "active",
            "createdAt": now,
            "lastActiveAt": now,
        },
    )
    append_jsonl_unique(
        home / "registry/directory-bindings.jsonl",
        "workrootId",
        {
            "workrootId": workroot_id,
            "canonicalUserDirectory": str(canonical_user_directory),
            "bindingType": "exact",
            "createdAt": now,
        },
    )
    return InitializedWorkroot(workroot_id, name, canonical_user_directory, state_directory)
