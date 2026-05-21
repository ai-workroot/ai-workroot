#!/usr/bin/env python3
"""Compatibility wrapper for legacy Context Candidate helpers."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_workroot.indexing.legacy_candidates import (  # noqa: E402,F401
    ACTIVE_STATUS,
    AUTO_EXCLUDED_POLICIES,
    BLOCKED_SAFETY_POLICIES,
    REQUIRED_CANDIDATE_FTS_COLUMNS,
    ContextCandidate,
    candidate_from_row,
    candidate_fts_columns,
    ensure_candidate_fts_schema,
    mark_candidate_status,
    mark_candidates_used,
    query_context_candidates,
    upsert_context_candidate,
)
