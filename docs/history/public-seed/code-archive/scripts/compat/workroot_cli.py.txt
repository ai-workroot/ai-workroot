#!/usr/bin/env python3
"""Compatibility wrapper for the package-owned legacy Workroot CLI."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_workroot.cli.legacy_seed import build_parser, main  # noqa: E402,F401


if __name__ == "__main__":
    main()
