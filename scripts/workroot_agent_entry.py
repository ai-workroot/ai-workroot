#!/usr/bin/env python3
"""Compatibility wrapper for package-owned Native Agent Entry helpers."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_workroot.agent.native_entry import (  # noqa: E402,F401
    BEGIN,
    END,
    MANAGED_BLOCK_BEGIN,
    MANAGED_BLOCK_END,
    NativeAgentEntryError,
    apply_managed_block,
    claude_block,
    codex_block,
    render_native_agent_entry,
    sync_native_agent_entry,
    validate_entry_content,
    validate_managed_block,
    validate_managed_blocks,
)
