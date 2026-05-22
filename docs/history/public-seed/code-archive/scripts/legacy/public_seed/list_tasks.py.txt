#!/usr/bin/env python3
"""Compatibility wrapper for legacy task listing."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_workroot.runtime.legacy_seed.task_listing import *  # noqa: E402,F401,F403
from ai_workroot.runtime.legacy_seed.task_listing import main  # noqa: E402


if __name__ == "__main__":
    main()
