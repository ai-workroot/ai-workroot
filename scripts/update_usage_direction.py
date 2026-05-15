#!/usr/bin/env python3
"""Lightweight usage-direction update for ordinary first-use interactions."""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path


PROFILE_PATH = Path("space/profile/profile.md")


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require_value(name: str, value: str) -> str:
    value = value.strip()
    if not value:
        raise SystemExit(f"--{name} is required and must not be empty")
    return value


def build_profile(direction: str, focus: str, avoid: str, timestamp: str) -> str:
    avoid_text = avoid or "Do not assume company, industry, team size, authority scope, employer, project, budget, or preferred technology stack until the user says so."
    return f"""# Profile

## Subject

{direction}

## AI Role

Work with the user according to this usage direction.

## Current Context

Usage direction was updated at {timestamp}.

## Long-Term Direction

{focus}

## Avoid Misunderstanding

{avoid_text}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direction", required=True, help="Plain-language usage direction, such as 'The user wants CTO-level technical collaboration.'")
    parser.add_argument("--focus", required=True, help="The main help areas the AI should focus on.")
    parser.add_argument("--avoid", default="", help="What the AI should not assume.")
    args = parser.parse_args()

    direction = require_value("direction", args.direction)
    focus = require_value("focus", args.focus)
    avoid = args.avoid.strip()

    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(build_profile(direction, focus, avoid, now_utc()), encoding="utf-8")
    print("Usage direction updated.")


if __name__ == "__main__":
    main()
