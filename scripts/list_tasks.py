#!/usr/bin/env python3
"""List local AI Workroot tasks for user-facing history review."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


TASK_REGISTRY = Path(".workroot/runtime/index/task_registry.csv")
STATUSES = {"active", "paused", "blocked", "closed", "released"}


def plain_next_step(row: dict[str, str]) -> str:
    handoff = (row.get("handoff_path") or "").strip()
    if handoff:
        handoff_path = Path(handoff)
        if handoff_path.exists():
            text = handoff_path.read_text(encoding="utf-8")
            for marker in ("## Continue With", "## Next Useful Step", "## Next Step"):
                if marker not in text:
                    continue
                after = text.split(marker, 1)[1].strip()
                lines = [line.strip() for line in after.splitlines() if line.strip()]
                for line in lines:
                    if not line.startswith("#"):
                        return line.lstrip("- ").strip()
    return "Ask the AI to continue this task."


def visible_output(row: dict[str, str]) -> str:
    output = (row.get("user_visible_output_path") or "").strip()
    if not output:
        return "Not saved yet"
    if output.startswith("space/work/"):
        return output.removeprefix("space/work/")
    return output


def read_tasks(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise SystemExit(f"task registry not found: {TASK_REGISTRY}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sort_key(row: dict[str, str]) -> tuple[str, str]:
    updated = row.get("updated_at") or row.get("created_at") or ""
    task_id = row.get("task_id") or ""
    return (updated, task_id)


def filter_tasks(rows: list[dict[str, str]], status: str | None, limit: int) -> list[dict[str, str]]:
    if status:
        rows = [row for row in rows if row.get("status") == status]
    rows = sorted(rows, key=sort_key, reverse=True)
    return rows[:limit] if limit > 0 else rows


def render_markdown(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "No tasks found.\n"
    lines = [
        "# Task History",
        "",
        "| Updated | Status | Title | Output | Next |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        output = visible_output(row)
        next_step = plain_next_step(row)
        lines.append(
            "| {updated} | {status} | {title} | {output} | {handoff} |".format(
                updated=row.get("updated_at") or row.get("created_at") or "-",
                status=row.get("status") or "-",
                title=(row.get("title") or row.get("task_id") or "-").replace("|", "\\|"),
                output=output.replace("|", "\\|"),
                handoff=next_step.replace("|", "\\|"),
            )
        )
    return "\n".join(lines) + "\n"


def render_json(rows: list[dict[str, str]]) -> str:
    return json.dumps(rows, ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", choices=sorted(STATUSES), help="Only show tasks with this status")
    parser.add_argument("--limit", type=int, default=20, help="Maximum tasks to show. Use 0 for all tasks.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()

    rows = filter_tasks(read_tasks(TASK_REGISTRY), args.status, args.limit)
    if args.format == "json":
        print(render_json(rows), end="")
    else:
        print(render_markdown(rows), end="")


if __name__ == "__main__":
    main()
