#!/usr/bin/env python3
"""Compatibility wrapper for legacy SQLite FTS helpers."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_workroot.indexing.legacy_fts import (  # noqa: E402,F401
    TEXT_SUFFIXES,
    IndexResult,
    TextChunk,
    chunk_id_for,
    chunk_markdown,
    chunk_plain_text,
    chunks_for_path,
    content_hash,
    estimate_tokens,
    file_id_for,
    index_text_file,
    is_binary_file,
    is_supported_text_path,
    search_fts,
    split_bounded_text,
)
