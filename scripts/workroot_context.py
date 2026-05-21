#!/usr/bin/env python3
"""Compatibility wrapper for package-owned legacy Context Guide helpers."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_workroot.runtime.legacy_context import *  # noqa: E402,F401,F403
