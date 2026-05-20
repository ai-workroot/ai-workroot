"""WorkrootEnvironment runtime flows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_workroot.core.environment import WorkrootEnvironment
from ai_workroot.storage.jsonl_registry import append_jsonl, read_jsonl, write_json
from ai_workroot.storage.locks import file_lock


REGISTRY_FILES = (
    "workroots.jsonl",
    "directory-bindings.jsonl",
    "aliases.jsonl",
    "relationships.jsonl",
)
PER_WORKROOT_DIRS = (
    "charter",
    "state",
    "tasks",
    "handoffs",
    "assets",
    "release",
    "relationships",
    "indexes",
    "context",
    "diagnostics",
    "maintenance",
    "cache",
    "logs",
)


@dataclass(frozen=True)
class WorkrootRegistration:
    workroot_id: str
    name: str
    user_directory: str
    state_directory: str


def initialize_environment(home: Path) -> WorkrootEnvironment:
    home = home.expanduser().resolve()
    for rel in (
        "registry",
        "preferences/agent-defaults",
        "global-index",
        "global-cache",
        "migrations/history",
        "migrations/locks",
        "concurrency/locks",
        "workroots",
    ):
        (home / rel).mkdir(parents=True, exist_ok=True)

    write_json(home / "config.json", {"version": "0.9.530", "kind": "WorkrootEnvironment"})
    write_json(home / "preferences/operator-preferences.json", {"version": "0.9.530"})
    write_json(home / "preferences/policy-defaults.json", {"version": "0.9.530"})

    for filename in REGISTRY_FILES:
        path = home / "registry" / filename
        path.touch(exist_ok=True)
    (home / "registry/.registry.lock").touch(exist_ok=True)

    return WorkrootEnvironment(home=str(home))


def register_workroot(home: Path, workroot_id: str, name: str, user_directory: Path) -> WorkrootRegistration:
    home = home.expanduser().resolve()
    user_directory = user_directory.expanduser().resolve()
    initialize_environment(home)
    lock_path = home / "registry/.registry.lock"

    with file_lock(lock_path):
        registration = register_workroot_unlocked(home, workroot_id, name, user_directory)

    return registration


def register_workroot_unlocked(home: Path, workroot_id: str, name: str, user_directory: Path) -> WorkrootRegistration:
    home = home.expanduser().resolve()
    user_directory = user_directory.expanduser().resolve()
    workroots_path = home / "registry/workroots.jsonl"
    bindings_path = home / "registry/directory-bindings.jsonl"
    workroots = read_jsonl(workroots_path)
    bindings = read_jsonl(bindings_path)

    if any(record.get("workroot_id") == workroot_id for record in workroots):
        raise ValueError(f"duplicate workroot_id: {workroot_id}")
    for record in bindings:
        if record.get("user_directory") == str(user_directory):
            raise ValueError(f"user directory already registered: {user_directory}")

    state_directory = home / "workroots" / workroot_id
    for rel in PER_WORKROOT_DIRS:
        (state_directory / rel).mkdir(parents=True, exist_ok=True)

    write_json(
        state_directory / "workroot.json",
        {
            "workroot_id": workroot_id,
            "name": name,
            "user_directory": str(user_directory),
            "state_directory": str(state_directory),
            "version": "0.9.530",
        },
    )
    append_jsonl(
        workroots_path,
        {
            "workroot_id": workroot_id,
            "name": name,
            "state_directory": str(state_directory),
            "version": "0.9.530",
        },
    )
    append_jsonl(
        bindings_path,
        {
            "workroot_id": workroot_id,
            "user_directory": str(user_directory),
        },
    )

    return WorkrootRegistration(
        workroot_id=workroot_id,
        name=name,
        user_directory=str(user_directory),
        state_directory=str(state_directory),
    )
