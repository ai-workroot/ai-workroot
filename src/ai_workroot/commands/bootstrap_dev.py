"""bootstrap-dev command for Clean Workroot dogfood."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from ai_workroot.agent_entry.native import sync_native_agent_entry
from ai_workroot.state.environment import WorkrootRegistration, initialize_environment, register_workroot_unlocked
from ai_workroot.state.jsonl import read_jsonl
from ai_workroot.state.layout import resolve_ai_workroot_home
from ai_workroot.state.locks import file_lock
from ai_workroot.state.sqlite import initialize_workroot_sqlite


PROJECT_MARKER = "workroot.project.json"
LOCAL_DIR = ".ai-workroot-local"
VERSION = "0.9.531"


@dataclass(frozen=True)
class BootstrapResult:
    status: str
    workroot_id: str
    state_directory: str
    user_directory: str

    def message(self) -> str:
        return f"bootstrap-dev {self.status} {self.workroot_id}"


def bootstrap_dev(
    repo: Path | str,
    *,
    ai_workroot_home: Path | str | None = None,
    dry_run: bool = False,
) -> BootstrapResult:
    repo_path = Path(repo).expanduser().resolve()
    project = _load_project_marker(repo_path)
    workroot_id = _bootstrap_workroot_id(project)
    home = resolve_ai_workroot_home(ai_workroot_home)

    if dry_run:
        return BootstrapResult(
            status="preflight ok",
            workroot_id=workroot_id,
            state_directory=str(home / "workroots" / workroot_id),
            user_directory=str(repo_path),
        )

    initialize_environment(home)
    lock_path = home / "registry/.registry.lock"
    with file_lock(lock_path):
        existing = _find_existing_registration(home, workroot_id, repo_path)
        if existing is None:
            registration = register_workroot_unlocked(
                home,
                workroot_id=workroot_id,
                name="AI Workroot Project",
                user_directory=repo_path,
            )
            status = "initialized"
        else:
            registration = existing
            status = "reused"
        _ensure_bootstrap_side_effects(repo_path, Path(registration.state_directory))

    return BootstrapResult(
        status=status,
        workroot_id=workroot_id,
        state_directory=registration.state_directory,
        user_directory=registration.user_directory,
    )


def _load_project_marker(repo: Path) -> dict[str, Any]:
    marker = repo / PROJECT_MARKER
    if not marker.is_file():
        raise ValueError(f"bootstrap-dev requires {PROJECT_MARKER}")
    try:
        project = json.loads(marker.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {PROJECT_MARKER}: {exc}") from exc
    if not isinstance(project, dict):
        raise ValueError(f"{PROJECT_MARKER} must contain a JSON object")
    required = {
        "project": "ai-workroot",
        "bootstrapDevSupported": True,
        "architecture": "clean-workroot",
    }
    for field, expected in required.items():
        if project.get(field) != expected:
            raise ValueError(f"{PROJECT_MARKER} field {field!r} must be {expected!r}")
    return project


def _bootstrap_workroot_id(project: dict[str, Any]) -> str:
    name = str(project.get("project") or "ai-workroot")
    return f"wr_{_slug(name)}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "workroot"


def _find_existing_registration(home: Path, workroot_id: str, repo: Path) -> WorkrootRegistration | None:
    for record in read_jsonl(home / "registry/workroots.jsonl"):
        if record.get("workroot_id") != workroot_id:
            continue
        state_directory = Path(str(record.get("state_directory", ""))).expanduser().resolve()
        workroot_json = _read_workroot_json(state_directory)
        registered_dir = Path(str(workroot_json.get("user_directory") or "")).expanduser().resolve()
        if registered_dir != repo:
            raise ValueError(
                f"bootstrap-dev Workroot ID {workroot_id} already exists for a different directory: {registered_dir}"
            )
        return WorkrootRegistration(
            workroot_id=workroot_id,
            name=str(record.get("name") or "AI Workroot Project"),
            user_directory=str(registered_dir),
            state_directory=str(state_directory),
        )
    return None


def _read_workroot_json(state_directory: Path) -> dict[str, Any]:
    path = state_directory / "workroot.json"
    if not path.is_file():
        raise ValueError(f"registered Workroot state is missing workroot.json: {state_directory}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"invalid Workroot metadata: {path}")
    return data


def _ensure_bootstrap_side_effects(repo: Path, state_directory: Path) -> None:
    initialize_workroot_sqlite(state_directory / "cache/workroot.sqlite")
    for rel in ("drafts", "reviews", "patches", "context-packages"):
        (repo / LOCAL_DIR / rel).mkdir(parents=True, exist_ok=True)
    _ensure_gitignore_entries(repo / ".gitignore", ("/AGENTS.md", "/CLAUDE.md", f"/{LOCAL_DIR}/"))
    sync_native_agent_entry(repo / "AGENTS.md", "codex")
    sync_native_agent_entry(repo / "CLAUDE.md", "claude")


def _ensure_gitignore_entries(path: Path, entries: tuple[str, ...]) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = existing.splitlines()
    changed = False
    for entry in entries:
        if entry not in lines:
            lines.append(entry)
            changed = True
    if changed:
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
