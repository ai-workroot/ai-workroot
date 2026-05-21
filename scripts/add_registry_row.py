#!/usr/bin/env python3
"""Compatibility wrapper for legacy registry row maintenance."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_workroot.runtime.legacy_seed.registry_tools import *  # noqa: E402,F401,F403
from ai_workroot.runtime.legacy_seed.registry_tools import main  # noqa: E402


if __name__ == "__main__":
    main()
