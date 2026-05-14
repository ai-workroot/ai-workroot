#!/usr/bin/env python3
"""Create an internal AI Workroot task and update the runtime registry."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import shutil
import unicodedata
from pathlib import Path


TASK_STATUSES = {"active", "paused", "blocked", "closed", "released"}
OWNER_SCOPES = {"personal", "team", "role", "organization"}
VISIBILITIES = {"internal", "shared", "public", "private"}
TEMPLATE_DIR = Path(".workroot/runtime/work/_templates")
TASK_REGISTRY = Path(".workroot/runtime/index/task_registry.csv")
WORK_ROOT = Path(".workroot/runtime/work")
MAX_SLUG_LENGTH = 64


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip().casefold()
    chars: list[str] = []
    previous_dash = False
    for char in value:
        category = unicodedata.category(char)
        if category[0] in {"L", "N", "M"}:
            chars.append(char)
            previous_dash = False
        elif not previous_dash:
            chars.append("-")
            previous_dash = True
    value = "".join(chars).strip("-")
    value = re.sub(r"-+", "-", value)
    if len(value) > MAX_SLUG_LENGTH:
        value = value[:MAX_SLUG_LENGTH].rstrip("-")
    return value or "task"


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_instant(value: str) -> str:
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"invalid --created-at value; use ISO-8601 with timezone, such as 2026-05-15T09:00:00Z or 2026-05-15T17:00:00+08:00: {value}") from exc
    if parsed.tzinfo is None:
        raise SystemExit(f"invalid --created-at value; timezone is required for precise instants: {value}")
    return parsed.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_slug(instant: str) -> str:
    return instant.replace("-", "").replace(":", "").replace("T", "-").replace("Z", "")


def read_registry(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def append_registry(path: Path, row: dict[str, str]) -> None:
    fieldnames, rows = read_registry(path)
    if any(existing.get("task_id") == row["task_id"] for existing in rows):
        raise SystemExit(f"task_id already exists in registry: {row['task_id']}")
    if not fieldnames:
        fieldnames = [
            "task_id",
            "title",
            "status",
            "owner_scope",
            "visibility",
            "created_at",
            "updated_at",
            "user_visible_output_path",
            "source_path",
            "handoff_path",
        ]
    full_row = {field: "" for field in fieldnames}
    for key, value in row.items():
        if key in full_row:
            full_row[key] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(full_row)


def unique_task_identity(
    root: Path,
    title: str,
    instant: str,
    requested_id: str | None,
) -> tuple[str, Path]:
    slug = slugify(title)
    base_id = requested_id or f"task-{timestamp_slug(instant)}-{slug}"
    task_base = root / WORK_ROOT / "active" / base_id
    _, rows = read_registry(root / TASK_REGISTRY)
    existing_ids = {row.get("task_id", "") for row in rows}

    if requested_id:
        if requested_id in existing_ids:
            raise SystemExit(f"task_id already exists in registry: {requested_id}")
        if task_base.exists():
            raise SystemExit(f"task directory already exists: {task_base}")
        return requested_id, task_base

    task_id = base_id
    task_dir = task_base
    suffix = 2
    while task_id in existing_ids or task_dir.exists():
        task_id = f"{base_id}-{suffix}"
        task_dir = root / WORK_ROOT / "active" / task_id
        suffix += 1
    return task_id, task_dir


def replace_in_file(path: Path, replacements: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def write_task_json(
    task_dir: Path,
    task_id: str,
    title: str,
    status: str,
    owner_scope: str,
    visibility: str,
    instant: str,
    user_visible_output_path: str | None,
) -> None:
    payload = {
        "task_id": task_id,
        "title": title,
        "status": status,
        "created_at": instant,
        "updated_at": instant,
        "owner_scope": owner_scope,
        "visibility": visibility,
        "user_visible_output_path": user_visible_output_path,
    }
    (task_dir / "task.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("title", help="Human-readable work title")
    parser.add_argument("--id", help="Stable task id. Defaults to timestamp plus slug.")
    parser.add_argument("--goal", default="What are we trying to accomplish?")
    parser.add_argument("--why", default="Why is this worth doing?")
    parser.add_argument("--expected", default="What should exist when this task is done?")
    parser.add_argument("--next", default="Define next step", help="Next action")
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

    root = Path.cwd()
    template_dir = root / TEMPLATE_DIR
    if not template_dir.exists():
        raise SystemExit(f"template directory not found: {TEMPLATE_DIR}")

    created_at = normalize_instant(args.created_at)
    task_id, task_dir = unique_task_identity(root, args.title, created_at, args.id)
    task_dir.mkdir(parents=True)
    (task_dir / "outputs").mkdir()
    (task_dir / "archive").mkdir()

    for template in template_dir.glob("*.md"):
        shutil.copyfile(template, task_dir / template.name)

    user_visible_output_path = args.user_visible_output_path or None
    write_task_json(
        task_dir,
        task_id,
        args.title,
        "active",
        args.owner_scope,
        args.visibility,
        created_at,
        user_visible_output_path,
    )

    replace_in_file(
        task_dir / "brief.md",
        {
            "Short summary of the current effective state.": "Task created; no work completed yet.",
            "What has been completed or learned?": "Nothing yet.",
            "What should happen next?": args.next,
        },
    )
    replace_in_file(
        task_dir / "todo.md",
        {
            "Define next step": args.next,
            "Clear next action": "Next action is clear.",
        },
    )
    if (task_dir / "task.md").exists():
        replace_in_file(
            task_dir / "task.md",
            {
                "# Task": f"# {args.title}",
                "What are we trying to accomplish?": args.goal,
                "Why is this worth doing?": args.why,
                "What should exist when this task is done?": args.expected,
            },
        )

    rel_path = task_dir.relative_to(root).as_posix()
    append_registry(
        root / TASK_REGISTRY,
        {
            "task_id": task_id,
            "title": args.title,
            "status": "active",
            "owner_scope": args.owner_scope,
            "visibility": args.visibility,
            "created_at": created_at,
            "updated_at": created_at,
            "user_visible_output_path": user_visible_output_path or "",
            "source_path": rel_path,
            "handoff_path": f"{rel_path}/handoff.md",
        },
    )

    print(rel_path)


if __name__ == "__main__":
    main()
