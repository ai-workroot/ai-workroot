#!/usr/bin/env python3
"""Lightweight usage-direction update for ordinary first-use interactions."""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path


PROFILE_PATH = Path("space/profile/profile.md")
MANAGED_START = "<!-- usage-direction:start -->"
MANAGED_END = "<!-- usage-direction:end -->"


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require_value(name: str, value: str) -> str:
    value = value.strip()
    if not value:
        raise SystemExit(f"--{name} is required and must not be empty")
    return value


def build_profile(direction: str, focus: str, avoid: str, timestamp: str) -> str:
    avoid_text = avoid or "Do not assume company, industry, team size, authority scope, employer, project, budget, or preferred technology stack until the user says so."
    return f"""{MANAGED_START}
## Usage Direction

### Subject

{direction}

### AI Role

Work with the user according to this usage direction.

### Current Context

Usage direction was updated at {timestamp}.

### Long-Term Direction

{focus}

### Avoid Misunderstanding

{avoid_text}
{MANAGED_END}
"""


def merge_profile(existing: str, managed: str) -> str:
    if not existing.strip():
        return f"# Profile\n\n{managed}"
    if MANAGED_START in existing and MANAGED_END in existing:
        before, rest = existing.split(MANAGED_START, 1)
        _, after = rest.split(MANAGED_END, 1)
        return before.rstrip() + "\n\n" + managed.strip() + "\n" + after
    if existing.startswith("# Profile"):
        return existing.rstrip() + "\n\n" + managed.strip() + "\n"
    return "# Profile\n\n" + managed.strip() + "\n\n" + existing.rstrip() + "\n"


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
    existing = PROFILE_PATH.read_text(encoding="utf-8") if PROFILE_PATH.exists() else ""
    PROFILE_PATH.write_text(merge_profile(existing, build_profile(direction, focus, avoid, now_utc())), encoding="utf-8")
    print("Usage direction updated.")


if __name__ == "__main__":
    main()
