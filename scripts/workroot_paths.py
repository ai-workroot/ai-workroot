#!/usr/bin/env python3
"""Path resolution and Clean Mode boundary checks for AI Workroot."""

from __future__ import annotations

import os
import platform
from pathlib import Path
import re
import uuid


class CleanModeBoundaryError(ValueError):
    """Raised when Clean Mode managed state would live inside a user directory."""


WORKROOT_ID_RE = re.compile(r"^wr_[a-z0-9][a-z0-9_]{0,80}$")


def ensure_workroot_id(workroot_id: str) -> str:
    if not WORKROOT_ID_RE.fullmatch(workroot_id):
        raise ValueError(
            "invalid Workroot ID: use wr_ followed by lowercase letters, numbers, or underscores, "
            "with no path separators"
        )
    return workroot_id


def resolve_ai_workroot_home(home: Path | None = None) -> Path:
    override = os.environ.get("AI_WORKROOT_HOME")
    if override:
        return Path(override).expanduser().resolve()
    if platform.system() == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(f"{local_app_data}\\AIWorkroot")
        return Path.home() / "AppData" / "Local" / "AIWorkroot"
    base = home or Path.home()
    return base / ".ai-workroot"


def workroot_state_dir(ai_workroot_home: Path, workroot_id: str) -> Path:
    safe_workroot_id = ensure_workroot_id(workroot_id)
    home = ai_workroot_home.expanduser()
    state_directory = home / "workroots" / safe_workroot_id
    resolved_state_directory = state_directory.resolve()
    workroots_dir = (home / "workroots").resolve()
    try:
        resolved_state_directory.relative_to(workroots_dir)
    except ValueError as exc:
        raise CleanModeBoundaryError(f"Workroot state directory escaped AI_WORKROOT_HOME/workroots: {resolved_state_directory}") from exc
    return state_directory


def workroot_sqlite_path(state_directory: Path) -> Path:
    return state_directory / "cache/workroot.sqlite"


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def assert_clean_mode_boundary(user_directory: Path, state_directory: Path) -> None:
    if is_relative_to(state_directory, user_directory):
        raise CleanModeBoundaryError(
            f"Clean Mode violation: managed state would be written inside the user directory: {state_directory}"
        )


def validate_user_directory(user_directory: Path, ai_workroot_home: Path, create: bool = True) -> Path:
    expanded = user_directory.expanduser()
    if expanded.exists() and not expanded.is_dir():
        raise ValueError(f"user directory is not a directory: {expanded}")
    resolved = expanded.resolve() if expanded.exists() else expanded.parent.resolve() / expanded.name
    home = ai_workroot_home.expanduser().resolve()
    if resolved == home or is_relative_to(resolved, home):
        raise ValueError("user directory must not be AI_WORKROOT_HOME or inside AI_WORKROOT_HOME")
    obvious_system_dirs = {Path(Path.home().resolve().anchor).resolve()}
    if resolved == Path.home().resolve():
        raise ValueError(f"user directory looks like a system directory: {resolved}")
    if platform.system() != "Windows":
        obvious_system_dirs.update(Path(path).resolve() for path in ("/bin", "/sbin", "/usr", "/etc", "/var", "/System", "/Library"))
    if resolved in obvious_system_dirs:
        raise ValueError(f"user directory looks like a system directory: {resolved}")
    if not expanded.exists():
        if not create:
            raise ValueError(f"user directory does not exist: {expanded}")
        expanded.mkdir(parents=True)
        resolved = expanded.resolve()
    probe = resolved / f".ai-workroot-write-probe-{uuid.uuid4().hex}"
    try:
        probe.write_text("probe", encoding="utf-8")
        _ = probe.read_text(encoding="utf-8")
    finally:
        if probe.exists():
            probe.unlink()
    return resolved
