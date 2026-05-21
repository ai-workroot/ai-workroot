#!/usr/bin/env python3
"""Compatibility wrapper for legacy SQLite helpers."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_workroot.storage.legacy_sqlite import (  # noqa: E402,F401
    CANDIDATE_SCHEMA,
    FTS_SCHEMA,
    GRAPH_SCHEMA,
    MANAGEMENT_SCHEMA,
    MIGRATION_SCHEMA,
    SCHEMA_MIGRATIONS,
    ensure_context_candidate_columns,
    ensure_schema_migrations,
    initialize_workroot_sqlite,
    open_sqlite,
    required_tables,
    sqlite_table_names,
    verify_workroot_sqlite,
)
