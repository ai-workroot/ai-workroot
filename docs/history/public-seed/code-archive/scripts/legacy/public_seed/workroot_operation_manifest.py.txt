#!/usr/bin/env python3
"""Compatibility wrapper for package-owned operation manifest helpers."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_workroot.runtime.legacy_seed.operation_manifest import (  # noqa: E402,F401
    ACTION_TYPES,
    ARTIFACT_AUDIENCES,
    BATCH_OPERATIONS,
    MIND_TYPES,
    OWNER_SCOPES,
    PATH_LIST_DESCRIPTION,
    PROCESS_LEVELS,
    RECIPES,
    TASK_STATUSES,
    VISIBILITIES,
    batch_12_tasks_recipe,
    field,
    manifest,
    recipe,
    recipes,
    schema,
)
