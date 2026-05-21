#!/usr/bin/env python3
"""Compatibility wrapper for package-owned state helpers."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_workroot.runtime.state import (  # noqa: E402,F401
    CONFIG_VERSION,
    DEFAULT_RUNTIME_HINTS,
    GLOBAL_INDEX_FILES,
    REGISTRY_FILES,
    SCHEMA_VERSION,
    WORKROOT_DIRECTORIES,
    InitializedWorkroot,
    append_jsonl_unique,
    backup_malformed_config,
    initialize_ai_workroot_home,
    initialize_workroot_state,
    initialize_workroot_state_unlocked,
    read_jsonl,
    registry_lock,
    touch_jsonl,
    write_json,
)
