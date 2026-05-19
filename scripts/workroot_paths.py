#!/usr/bin/env python3
"""Path resolution and Clean Mode boundary checks for AI Workroot."""

from __future__ import annotations

import os
import platform
from pathlib import Path


class CleanModeBoundaryError(ValueError):
    """Raised when Clean Mode managed state would live inside a user directory."""


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
    return ai_workroot_home / "workroots" / workroot_id


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
