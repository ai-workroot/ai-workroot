#!/usr/bin/env python3
"""Create an internal AI Workroot task and update the runtime registry."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from workroot_client import (
    OWNER_SCOPES,
    PROCESS_LEVELS,
    VISIBILITIES,
    WorkrootClient,
    normalize_instant,
    now_utc,
    slugify,
)


def unique_task_identity(
    root: Path,
    title: str,
    instant: str,
    requested_id: str | None,
) -> tuple[str, Path]:
    return WorkrootClient(root).unique_task_identity(title, instant, requested_id)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("title", help="Human-readable work title")
    parser.add_argument("--id", help="Stable task id. Defaults to timestamp plus slug.")
    parser.add_argument("--goal", default="What are we trying to accomplish?")
    parser.add_argument("--why", default="Why is this worth doing?")
    parser.add_argument("--expected", default="What should exist when this task is done?")
    parser.add_argument("--next", default="Define next step", help="Next action")
    parser.add_argument("--process-level", choices=sorted(PROCESS_LEVELS), default="L0")
    parser.add_argument("--owner-scope", choices=sorted(OWNER_SCOPES), default="personal")
    parser.add_argument("--visibility", choices=sorted(VISIBILITIES), default="internal")
    parser.add_argument(
        "--created-at",
        default=now_utc(),
        help="ISO-8601 instant with timezone. Stored as UTC, for example 2026-05-15T09:00:00Z or 2026-05-15T17:00:00+08:00.",
    )
    parser.add_argument(
        "--user-visible-output-path",
        default="",
        help="Optional repository-relative output path under space/work/",
    )
    args = parser.parse_args()

    created = WorkrootClient(Path.cwd()).create_task(
        title=args.title,
        task_id=args.id,
        process_level=args.process_level,
        goal=args.goal,
        why=args.why,
        expected=args.expected,
        next_action=args.next,
        owner_scope=args.owner_scope,
        visibility=args.visibility,
        created_at=args.created_at,
        user_visible_output_path=args.user_visible_output_path or None,
    )
    print(created.source_path)


if __name__ == "__main__":
    main()
