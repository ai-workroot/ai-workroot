#!/usr/bin/env python3
"""Managed state initialization for AI Workroot Clean Mode."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

try:
    from workroot_paths import assert_clean_mode_boundary, validate_user_directory, workroot_state_dir
except ModuleNotFoundError:  # pragma: no cover - package import path for tests.
    from scripts.workroot_paths import assert_clean_mode_boundary, validate_user_directory, workroot_state_dir


CONFIG_VERSION = "0.9.529"
SCHEMA_VERSION = "0.1"
DEFAULT_RUNTIME_HINTS = {
    "contextGuide": {
        "defaultMode": "standard",
        "latency": {
            "targetMs": 1000,
            "standardSoftLimitMs": 2000,
            "qualitySoftLimitMs": 3000,
        },
        "agentBudgets": {
            "codex": {
                "targetTokens": 4000,
                "hardTokenLimit": 6000,
            },
            "claude": {
                "targetTokens": 5000,
                "hardTokenLimit": 8000,
            },
            "default": {
                "targetTokens": 4000,
                "hardTokenLimit": 6000,
            },
        },
        "modes": {
            "fast": {
                "targetTokens": 2500,
                "hardTokenLimit": 4000,
                "maxLatencyMs": 1000,
            },
            "standard": {
                "targetTokens": 4000,
                "hardTokenLimit": 6000,
                "targetLatencyMs": 1000,
                "softLatencyMs": 2000,
            },
            "quality": {
                "targetTokens": 8000,
                "hardTokenLimit": 12000,
                "softLatencyMs": 3000,
            },
            "deep": {
                "requiresExplicitRequest": True,
                "targetTokens": 12000,
                "hardTokenLimit": 20000,
            },
        },
        "hotPath": {
            "allowRemoteLlm": False,
            "allowRemoteEmbedding": False,
            "allowVectorSearch": False,
            "allowFullDirectoryScan": False,
            "allowIndexRebuild": False,
            "allowMaintenanceJob": False,
        },
    }
}
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
    config_path = home / "config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            if not isinstance(config, dict):
                config = {}
        except json.JSONDecodeError:
            config = {}
        config.setdefault("createdAt", now)
        config["version"] = CONFIG_VERSION
        config.setdefault("schemaVersion", SCHEMA_VERSION)
        config.setdefault("defaultMode", "clean")
    else:
        config = {
            "version": CONFIG_VERSION,
            "schemaVersion": SCHEMA_VERSION,
            "createdAt": now,
            "defaultMode": "clean",
        }
    write_json(config_path, config)
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
    canonical_user_directory = validate_user_directory(user_directory, home, create=True)
    state_directory = workroot_state_dir(home, workroot_id).resolve()
    assert_clean_mode_boundary(canonical_user_directory, state_directory)
    initialize_ai_workroot_home(home, now=now)
    existing = read_jsonl(home / "registry/workroots.jsonl")
    if any(record.get("workrootId") == workroot_id for record in existing):
        raise ValueError(f"Workroot ID already exists: {workroot_id}")

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
    write_json(state_directory / "state/runtime-hints.json", DEFAULT_RUNTIME_HINTS)

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
