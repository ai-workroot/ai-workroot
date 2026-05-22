#!/usr/bin/env python3
"""Compatibility wrapper for package-owned migration helpers."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_workroot.storage.migrations import (  # noqa: E402,F401
    Migration,
    MigrationRunner,
    append_migration_record,
    migration_lock,
    read_migration_records,
)
