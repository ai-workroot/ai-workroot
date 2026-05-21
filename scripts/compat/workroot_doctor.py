#!/usr/bin/env python3
"""Compatibility wrapper for package-owned managed-state doctor checks."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_workroot.runtime.legacy_doctor import (  # noqa: E402,F401
    DoctorCheck,
    DoctorResult,
    check_clean_mode,
    check_context_directories,
    check_context_runtime_hints,
    check_managed_layout,
    check_migration_records,
    check_native_agent_entry,
    check_resolution,
    check_sqlite_schema,
    fail_check,
    pass_check,
    read_workroot_json,
    render_json,
    render_text,
    resolve_state_record,
    run_doctor,
    warn_check,
)
