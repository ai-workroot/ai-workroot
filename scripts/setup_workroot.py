#!/usr/bin/env python3
"""Guided first-use setup for AI Workroot identity files."""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path


PROFILE_DIR = Path("space/profile")
PROFILE_PATH = PROFILE_DIR / "profile.md"
ROLES_PATH = PROFILE_DIR / "roles.md"
VALUES_PATH = PROFILE_DIR / "values.md"
PREFERENCES_PATH = PROFILE_DIR / "preferences.md"
CURRENT_CONTEXT_PATH = Path(".workroot/runtime/context/current.md")
CONTINUE_PATH = Path("space/work/continue.md")
SEED_TEMPLATE_MARKERS = {
    PROFILE_PATH: [
        "Describe who this Workroot represents.",
        "This Workroot represents ...",
    ],
    ROLES_PATH: [
        "List the roles this Workroot supports.",
        "Start with at least one role, even if it is broad.",
    ],
    VALUES_PATH: [
        "Start with a few plain statements. They can evolve later.",
    ],
    PREFERENCES_PATH: [
        "Start small. Preferences should help the AI serve the subject better without making first use complicated.",
    ],
    CURRENT_CONTEXT_PATH: [
        "No active context yet.",
    ],
    CONTINUE_PATH: [
        "No work has been started yet.",
    ],
}


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require_value(name: str, value: str) -> str:
    value = value.strip()
    if not value:
        raise SystemExit(f"--{name} is required and must not be empty")
    return value


def write_file(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        existing = path.read_text(encoding="utf-8")
        markers = SEED_TEMPLATE_MARKERS.get(path, [])
        if markers and not any(marker in existing for marker in markers):
            raise SystemExit(f"{path.as_posix()} already appears customized; use --force to overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_profile(subject: str, ai_role: str, direction: str, avoid: str, timestamp: str) -> str:
    return f"""# Profile

## Subject

{subject}

## AI Role

{ai_role}

## Current Context

This Workroot was initialized through guided setup at {timestamp}.

## Long-Term Direction

{direction}

## Avoid Misunderstanding

{avoid or "No special misunderstanding boundary has been defined yet."}
"""


def build_roles(ai_role: str) -> str:
    return f"""# Roles

| Role | Purpose | Description |
| --- | --- | --- |
| primary-ai-role | Serve this Workroot subject | {ai_role} |
"""


def build_values(values: str) -> str:
    return f"""# Values

Record durable values and boundaries.

## Initial Values

{values}
"""


def build_preferences(language: str) -> str:
    return f"""# Preferences

Record durable working preferences.

## Language

{language}

## Working Style

Start simple. Keep ordinary user interaction clear. Preserve useful results without exposing internal mechanics.
"""


def build_current_context(subject: str, direction: str, timestamp: str) -> str:
    return f"""# Current Context

Initialized at {timestamp}.

This Workroot represents:

{subject}

Current direction:

{direction}
"""


def build_continue(subject: str, direction: str) -> str:
    return f"""# Continue

This Workroot has been initialized.

## What This Workspace Represents

{subject}

## Current Direction

{direction}

## Next Useful Step

Start the first real task.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True, help="Who or what this Workroot represents")
    parser.add_argument("--ai-role", required=True, help="What role the AI should play")
    parser.add_argument("--direction", required=True, help="What work or life area this Workroot supports")
    parser.add_argument("--values", required=True, help="Durable values, preferences, or boundaries")
    parser.add_argument("--language", default="Respond in the language the user is currently using, unless the user explicitly requests another language. Keep repository docs and machine keys in English.")
    parser.add_argument("--avoid", default="", help="What the AI should not assume")
    parser.add_argument("--force", action="store_true", help="Overwrite existing profile files")
    args = parser.parse_args()

    subject = require_value("subject", args.subject)
    ai_role = require_value("ai-role", args.ai_role)
    direction = require_value("direction", args.direction)
    values = require_value("values", args.values)
    language = require_value("language", args.language)
    avoid = args.avoid.strip()
    timestamp = now_utc()

    write_file(PROFILE_PATH, build_profile(subject, ai_role, direction, avoid, timestamp), args.force)
    write_file(ROLES_PATH, build_roles(ai_role), args.force)
    write_file(VALUES_PATH, build_values(values), args.force)
    write_file(PREFERENCES_PATH, build_preferences(language), args.force)
    write_file(CURRENT_CONTEXT_PATH, build_current_context(subject, direction, timestamp), args.force)
    write_file(CONTINUE_PATH, build_continue(subject, direction), args.force)

    print("AI Workroot guided setup complete.")
    print(PROFILE_PATH.as_posix())
    print("Next, say: Help me start my first real task.")


if __name__ == "__main__":
    main()
