#!/usr/bin/env python3
"""File-first client for AI Workroot task process records."""

from __future__ import annotations

import csv
import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import unicodedata
import uuid
from pathlib import Path


TASK_STATUSES = {"active", "paused", "blocked", "closed", "released"}
PROCESS_LEVELS = {"L0", "L1", "L2"}
OWNER_SCOPES = {"personal", "team", "role", "organization"}
VISIBILITIES = {"internal", "shared", "public", "private"}
TASK_REGISTRY = Path(".workroot/runtime/index/task_registry.csv")
WORK_ROOT = Path(".workroot/runtime/work")
TEMPLATE_DIR = WORK_ROOT / "_templates"
MAX_SLUG_LENGTH = 64
FUTURE_TIMESTAMP_TOLERANCE = dt.timedelta(minutes=5)
MIND_TYPES = {
    "memory",
    "knowledge",
    "principle",
    "decision",
    "pattern",
    "reflection",
    "invalidated",
    "released",
    "tombstone",
}
MIND_DIRS = {
    "memory": "memory",
    "knowledge": "knowledge",
    "principle": "principles",
    "decision": "decisions",
    "pattern": "patterns",
    "reflection": "reflections",
    "invalidated": "invalidated",
    "released": "released",
    "tombstone": "released",
}

REGISTRY_HEADERS = {
    ".workroot/runtime/index/task_registry.csv": [
        "task_id",
        "title",
        "status",
        "process_level",
        "owner_scope",
        "visibility",
        "priority",
        "created_at",
        "updated_at",
        "user_visible_output_path",
        "source_path",
        "brief_path",
        "handoff_path",
        "next_action",
    ],
    ".workroot/runtime/index/run_registry.csv": [
        "run_id",
        "task_id",
        "title",
        "status",
        "validity",
        "validity_reason",
        "superseded_by",
        "started_at",
        "completed_at",
        "output_dir",
        "primary_artifact",
        "validation",
        "conclusion_preview",
        "updated_at",
    ],
    ".workroot/runtime/index/action_registry.csv": [
        "action_id",
        "task_id",
        "run_id",
        "type",
        "status",
        "summary",
        "tool",
        "input_ref",
        "output_ref",
        "approval_ref",
        "risk_level",
        "created_at",
        "updated_at",
    ],
    ".workroot/runtime/index/artifact_registry.csv": [
        "artifact_id",
        "task_id",
        "run_id",
        "action_id",
        "type",
        "path",
        "audience",
        "status",
        "size",
        "checksum",
        "created_at",
        "updated_at",
    ],
    ".workroot/runtime/index/decision_registry.csv": [
        "decision_id",
        "task_id",
        "path",
        "title",
        "status",
        "created_at",
        "updated_at",
        "promoted_path",
    ],
    ".workroot/runtime/index/retrieval_card_registry.csv": [
        "card_id",
        "task_id",
        "path",
        "freshness",
        "source_paths",
        "created_at",
        "updated_at",
    ],
    ".workroot/runtime/index/checkpoint_registry.csv": [
        "checkpoint_id",
        "task_id",
        "path",
        "created_at",
        "current_status",
        "last_valid_run_id",
        "next_action",
        "required_context_paths",
    ],
    ".workroot/runtime/index/invalidation_registry.csv": [
        "invalidation_id",
        "task_id",
        "run_id",
        "artifact_id",
        "invalidated_claim",
        "reason",
        "replacement_ref",
        "path",
        "created_at",
        "updated_at",
    ],
    ".workroot/runtime/index/mind_registry.csv": [
        "mind_id",
        "title",
        "type",
        "status",
        "temperature",
        "privacy_level",
        "release_level",
        "retrieval_rule",
        "created_at",
        "updated_at",
        "source_path",
        "related_task_id",
        "replaces_mind_id",
    ],
    ".workroot/runtime/index/link_registry.csv": [
        "link_id",
        "source_type",
        "source_id",
        "target_type",
        "target_id",
        "relation",
        "created_at",
        "updated_at",
    ],
}


class CreatedTask:
    def __init__(self, task_id: str, process_level: str, source_path: str) -> None:
        self.task_id = task_id
        self.process_level = process_level
        self.source_path = source_path


class ProcessRecord:
    def __init__(self, record_id: str, path: str, **aliases: str) -> None:
        self.id = record_id
        self.path = path
        for name, value in aliases.items():
            setattr(self, name, value)


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_instant(value: str, reject_future: bool = True) -> str:
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"invalid instant; use ISO-8601 with timezone: {value}") from exc
    if parsed.tzinfo is None:
        raise SystemExit(f"invalid instant; timezone is required: {value}")
    normalized = parsed.astimezone(dt.timezone.utc).replace(microsecond=0)
    if reject_future and normalized - dt.datetime.now(dt.timezone.utc) > FUTURE_TIMESTAMP_TOLERANCE:
        raise SystemExit(f"invalid instant; future timestamps are not allowed: {value}")
    return normalized.isoformat().replace("+00:00", "Z")


def timestamp_slug(instant: str) -> str:
    return instant.replace("-", "").replace(":", "").replace("T", "-").replace("Z", "")


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


def read_registry(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def optional_str(value: object, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def optional_path_list(value: object, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, list):
        return ";".join(str(item) for item in value if item is not None and str(item))
    return str(value)


@contextlib.contextmanager
def file_lock(path: Path, timeout: float = 10.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            payload = f"pid={os.getpid()}\ncreated_at={now_utc()}\n"
            os.write(fd, payload.encode("utf-8"))
            os.close(fd)
            break
        except FileExistsError:
            if time.monotonic() - start > timeout:
                raise SystemExit(f"timed out waiting for Workroot lock: {path}; inspect the lock file before removing it")
            time.sleep(0.02)
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def write_registry_atomic(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", dir=path.parent, delete=False) as f:
        tmp_name = f.name
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp_name, path)


def copy_tree_or_file(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst)
    elif src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def restore_tree_or_file(src: Path, dst: Path) -> None:
    if dst.is_dir():
        shutil.rmtree(dst)
    elif dst.exists():
        dst.unlink()
    copy_tree_or_file(src, dst)


def remove_tree_or_file(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def replace_in_file(path: Path, replacements: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def markdown_sections(title: str, sections: dict[str, str]) -> str:
    lines = [f"# {title}", ""]
    for heading, body in sections.items():
        lines.extend([f"## {heading}", "", body or "", ""])
    return "\n".join(lines).rstrip() + "\n"


def append_unique_lines(path: Path, heading: str, values: list[str]) -> None:
    values = [value for value in values if value]
    if not values:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8") if path.exists() else f"# {path.stem.title()}\n"
    if heading not in text:
        text = text.rstrip() + f"\n\n{heading}\n"
    existing = set(text.splitlines())
    additions = [f"- `{value}`" for value in values if f"- `{value}`" not in existing]
    if additions:
        text = text.rstrip() + "\n\n" + "\n".join(additions) + "\n"
        path.write_text(text, encoding="utf-8")


class WorkrootClient:
    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root)
        self._lock_depth = 0

    def registry_path(self, rel: str) -> Path:
        return self.root / rel

    def lock_path(self) -> Path:
        return self.root / ".workroot/runtime/locks/workroot.lock"

    def ensure_registry(self, rel: str) -> None:
        headers = REGISTRY_HEADERS[rel]
        path = self.registry_path(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(",".join(headers) + "\n", encoding="utf-8")
            return
        fieldnames, rows = read_registry(path)
        if fieldnames != headers and not rows:
            path.write_text(",".join(headers) + "\n", encoding="utf-8")

    def ensure_registries(self) -> None:
        for rel in REGISTRY_HEADERS:
            self.ensure_registry(rel)

    def append_registry(self, rel: str, id_fields: list[str], row: dict[str, str]) -> None:
        if self._lock_depth:
            self._append_registry_unlocked(rel, id_fields, row)
            return
        with file_lock(self.lock_path()):
            self._lock_depth += 1
            try:
                self._append_registry_unlocked(rel, id_fields, row)
            finally:
                self._lock_depth -= 1

    def _append_registry_unlocked(self, rel: str, id_fields: list[str], row: dict[str, str]) -> None:
        headers = REGISTRY_HEADERS[rel]
        self.ensure_registry(rel)
        path = self.registry_path(rel)
        fieldnames, rows = read_registry(path)
        if fieldnames != headers:
            raise SystemExit(f"{rel}: header mismatch. expected {headers}, got {fieldnames}")

        full_row = {field: "" for field in headers}
        for key, value in row.items():
            if key not in full_row:
                raise SystemExit(f"unknown field for {rel}: {key}")
            full_row[key] = value

        missing = [field for field in id_fields if not full_row.get(field)]
        if missing:
            raise SystemExit(f"missing key fields for {rel}: {', '.join(missing)}")

        new_key = tuple(full_row[field] for field in id_fields)
        for existing in rows:
            existing_key = tuple(existing.get(field, "") for field in id_fields)
            if existing_key == new_key:
                raise SystemExit(f"registry row already exists: {new_key}")

        rows.append(full_row)
        write_registry_atomic(path, headers, rows)

    def update_registry_row(self, rel: str, id_field: str, id_value: str, updates: dict[str, str]) -> dict[str, str]:
        if self._lock_depth:
            return self._update_registry_row_unlocked(rel, id_field, id_value, updates)
        with file_lock(self.lock_path()):
            self._lock_depth += 1
            try:
                return self._update_registry_row_unlocked(rel, id_field, id_value, updates)
            finally:
                self._lock_depth -= 1

    def _update_registry_row_unlocked(self, rel: str, id_field: str, id_value: str, updates: dict[str, str]) -> dict[str, str]:
        headers = REGISTRY_HEADERS[rel]
        self.ensure_registry(rel)
        path = self.registry_path(rel)
        fieldnames, rows = read_registry(path)
        if fieldnames != headers:
            raise SystemExit(f"{rel}: header mismatch. expected {headers}, got {fieldnames}")
        for key in updates:
            if key not in headers:
                raise SystemExit(f"unknown field for {rel}: {key}")

        updated_row: dict[str, str] | None = None
        for row in rows:
            if row.get(id_field) != id_value:
                continue
            for key, value in updates.items():
                if value is not None:
                    row[key] = value
            updated_row = row
            break
        if updated_row is None:
            raise SystemExit(f"registry row not found: {id_field}={id_value}")

        write_registry_atomic(path, headers, rows)
        return updated_row

    def task_row(self, task_id: str) -> dict[str, str]:
        _, rows = read_registry(self.root / TASK_REGISTRY)
        for row in rows:
            if row.get("task_id") == task_id:
                return row
        raise SystemExit(f"task not found: {task_id}")

    def repo_path(self, rel: str) -> Path:
        if not rel:
            raise SystemExit("path is required")
        path = Path(rel)
        if path.is_absolute() or ".." in path.parts:
            raise SystemExit(f"path must be repository-relative: {rel}")
        return self.root / path

    def existing_task_ids(self) -> set[str]:
        _, rows = read_registry(self.root / TASK_REGISTRY)
        return {row.get("task_id", "") for row in rows}

    def task_id_exists_as_directory(self, task_id: str) -> bool:
        for prefix in ("tasks", "active", "closed"):
            if (self.root / WORK_ROOT / prefix / task_id).exists():
                return True
        return False

    def unique_task_identity(self, title: str, instant: str, requested_id: str | None) -> tuple[str, Path]:
        slug = slugify(title)
        base_id = requested_id or f"task-{timestamp_slug(instant)}-{slug}"
        tasks_root = self.root / WORK_ROOT / "tasks"
        task_base = tasks_root / base_id
        existing_ids = self.existing_task_ids()

        if requested_id:
            if requested_id in existing_ids:
                raise SystemExit(f"task_id already exists in registry: {requested_id}")
            if self.task_id_exists_as_directory(requested_id):
                raise SystemExit(f"task directory already exists: {task_base}")
            return requested_id, task_base

        task_id = base_id
        task_dir = task_base
        suffix = 2
        while task_id in existing_ids or self.task_id_exists_as_directory(task_id):
            task_id = f"{base_id}-{suffix}"
            task_dir = tasks_root / task_id
            suffix += 1
        return task_id, task_dir

    def write_task_json(
        self,
        task_dir: Path,
        task_id: str,
        title: str,
        status: str,
        process_level: str,
        owner_scope: str,
        visibility: str,
        instant: str,
        user_visible_output_path: str | None,
    ) -> None:
        payload = {
            "task_id": task_id,
            "title": title,
            "status": status,
            "process_level": process_level,
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

    def create_level_dirs(self, task_dir: Path, process_level: str) -> None:
        names = ["outputs", "archive"]
        if process_level in {"L1", "L2"}:
            names.extend(["plans", "runs", "retrieval_cards", "checkpoints"])
        if process_level == "L2":
            names.extend(["actions", "recipes", "data", "validation", "invalidations"])
        for name in names:
            (task_dir / name).mkdir(parents=True, exist_ok=True)

    def copy_base_templates(self, task_dir: Path) -> None:
        template_dir = self.root / TEMPLATE_DIR
        if not template_dir.exists():
            raise SystemExit(f"template directory not found: {TEMPLATE_DIR}")
        for template in template_dir.glob("*.md"):
            shutil.copyfile(template, task_dir / template.name)

    def create_task(
        self,
        title: str,
        task_id: str | None = None,
        process_level: str = "L0",
        goal: str = "What are we trying to accomplish?",
        why: str = "Why is this worth doing?",
        expected: str = "What should exist when this task is done?",
        next_action: str = "Define next step",
        owner_scope: str = "personal",
        visibility: str = "internal",
        priority: str = "",
        created_at: str | None = None,
        user_visible_output_path: str | None = None,
    ) -> CreatedTask:
        if process_level not in PROCESS_LEVELS:
            raise SystemExit(f"invalid process_level: {process_level}")
        if owner_scope not in OWNER_SCOPES:
            raise SystemExit(f"invalid owner_scope: {owner_scope}")
        if visibility not in VISIBILITIES:
            raise SystemExit(f"invalid visibility: {visibility}")

        self.ensure_registries()
        instant = normalize_instant(created_at) if created_at else now_utc()
        new_task_id, task_dir = self.unique_task_identity(title, instant, task_id)
        task_dir.mkdir(parents=True)
        self.create_level_dirs(task_dir, process_level)
        self.copy_base_templates(task_dir)

        output_path = user_visible_output_path or None
        self.write_task_json(
            task_dir,
            new_task_id,
            title,
            "active",
            process_level,
            owner_scope,
            visibility,
            instant,
            output_path,
        )
        replace_in_file(
            task_dir / "brief.md",
            {
                "Short summary of the current effective state.": "Task created; no work completed yet.",
                "What has been completed or learned?": "Nothing yet.",
                "What should happen next?": next_action,
            },
        )
        replace_in_file(
            task_dir / "todo.md",
            {
                "Define next step": next_action,
                "Clear next action": "Next action is clear.",
            },
        )
        if (task_dir / "task.md").exists():
            replace_in_file(
                task_dir / "task.md",
                {
                    "# Task": f"# {title}",
                    "What are we trying to accomplish?": goal,
                    "Why is this worth doing?": why,
                    "What should exist when this task is done?": expected,
                },
            )

        rel_path = task_dir.relative_to(self.root).as_posix()
        self.append_registry(
            TASK_REGISTRY.as_posix(),
            ["task_id"],
            {
                "task_id": new_task_id,
                "title": title,
                "status": "active",
                "process_level": process_level,
                "owner_scope": owner_scope,
                "visibility": visibility,
                "priority": priority,
                "created_at": instant,
                "updated_at": instant,
                "user_visible_output_path": output_path or "",
                "source_path": rel_path,
                "brief_path": f"{rel_path}/brief.md",
                "handoff_path": f"{rel_path}/handoff.md",
                "next_action": next_action,
            },
        )
        return CreatedTask(new_task_id, process_level, rel_path)

    def complete_task(
        self,
        task_id: str,
        report_path: str,
        report_content_file: str,
        next_action: str = "",
        process_level: str = "",
        checkpoint: bool = False,
    ) -> None:
        source = Path(report_content_file)
        if not source.exists() or not source.is_file():
            raise SystemExit(f"report content file does not exist: {report_content_file}")
        content = source.read_text(encoding="utf-8")
        report = self.repo_path(report_path)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(content, encoding="utf-8")

        artifact_id = f"{task_id}-report"
        self.add_artifact(
            artifact_id=artifact_id,
            task_id=task_id,
            type="report",
            path=report_path,
            audience="user",
            status="active",
            compute_metadata=True,
        )
        self.sync_task_state(
            task_id=task_id,
            status="closed",
            next_action=next_action,
            user_visible_output_path=report_path,
            brief_current_state="Task is closed.",
            brief_latest_result=f"Report completed: {report_path}.",
            handoff_status="Task is closed.",
            handoff_latest_result=f"Report completed: {report_path}.",
            index_outputs=[report_path],
        )
        if checkpoint:
            self.add_checkpoint(
                task_id=task_id,
                checkpoint_id=f"{task_id}-complete",
                current_status="Task completed.",
                next_action=next_action,
                required_context_paths=report_path,
            )

    def require_task_dir(self, task_id: str) -> Path:
        _, rows = read_registry(self.root / TASK_REGISTRY)
        for row in rows:
            if row.get("task_id") != task_id:
                continue
            source = (row.get("source_path") or "").strip()
            if source:
                path = self.root / source
                if path.exists():
                    return path
        for prefix in ("tasks", "active", "closed"):
            path = self.root / WORK_ROOT / prefix / task_id
            if path.exists():
                return path
        raise SystemExit(f"task not found: {task_id}")

    def write_markdown_record(self, path: Path, title: str, fields: dict[str, str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown_sections(title, fields), encoding="utf-8")

    def update_task_json(
        self,
        task_dir: Path,
        status: str | None,
        updated_at: str,
        user_visible_output_path: str | None,
    ) -> None:
        path = task_dir / "task.json"
        if not path.exists():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        if status is not None:
            payload["status"] = status
        payload["updated_at"] = updated_at
        if user_visible_output_path is not None:
            payload["user_visible_output_path"] = user_visible_output_path or None
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def sync_task_state(
        self,
        task_id: str,
        status: str | None = None,
        updated_at: str | None = None,
        next_action: str | None = None,
        user_visible_output_path: str | None = None,
        brief_current_state: str | None = None,
        brief_latest_result: str | None = None,
        handoff_status: str | None = None,
        handoff_latest_result: str | None = None,
        index_outputs: list[str] | None = None,
        mind_paths: list[str] | None = None,
        continue_summary: str | None = None,
    ) -> None:
        if status is not None and status not in TASK_STATUSES:
            raise SystemExit(f"invalid task status: {status}")
        task_dir = self.require_task_dir(task_id)
        instant = normalize_instant(updated_at) if updated_at else now_utc()

        registry_updates: dict[str, str] = {"updated_at": instant}
        if status is not None:
            registry_updates["status"] = status
        if next_action is not None:
            registry_updates["next_action"] = next_action
        if user_visible_output_path is not None:
            registry_updates["user_visible_output_path"] = user_visible_output_path
        row = self.update_registry_row(TASK_REGISTRY.as_posix(), "task_id", task_id, registry_updates)
        self.update_task_json(task_dir, status, instant, user_visible_output_path)

        current_state = brief_current_state
        latest_result = brief_latest_result
        if current_state is not None or latest_result is not None or next_action is not None:
            self.write_markdown_record(
                task_dir / "brief.md",
                "Brief",
                {
                    "Current State": current_state or f"Task is {row.get('status') or status or 'active'}.",
                    "Latest Result": latest_result or "No result recorded yet.",
                    "Next Step": next_action or row.get("next_action", ""),
                    "Context Policy": "This brief is the preferred task startup context. Keep it short.",
                },
            )

        if handoff_status is not None or handoff_latest_result is not None or next_action is not None:
            self.write_markdown_record(
                task_dir / "handoff.md",
                "Handoff",
                {
                    "Status": handoff_status or current_state or f"Task is {row.get('status') or status or 'active'}.",
                    "Latest Result": handoff_latest_result or latest_result or "",
                    "Decisions": "",
                    "Next Actions": next_action or row.get("next_action", ""),
                },
            )

        append_unique_lines(task_dir / "index.md", "## Outputs", index_outputs or [])
        append_unique_lines(task_dir / "index.md", "## Related Mind Entries", mind_paths or [])

        _ = continue_summary

    def summarize_session(self, task_ids: list[str], summary: str, next_action: str) -> None:
        rows = [self.task_row(task_id) for task_id in task_ids]
        task_lines = "\n".join(f"- {row['title']} ({row['task_id']})" for row in rows)
        continue_text = markdown_sections(
            "Continue",
            {
                "What Was Happening": task_lines,
                "What Matters Now": summary,
                "Next Step": next_action,
            },
        )
        continue_path = self.root / "space/work/continue.md"
        continue_path.parent.mkdir(parents=True, exist_ok=True)
        continue_path.write_text(continue_text, encoding="utf-8")

        context_dir = self.root / ".workroot/runtime/context"
        context_dir.mkdir(parents=True, exist_ok=True)
        (context_dir / "handoff.md").write_text(
            markdown_sections(
                "Handoff",
                {
                    "Current Work": task_lines,
                    "Status": summary,
                    "Next Actions": next_action,
                },
            ),
            encoding="utf-8",
        )
        (context_dir / "current.md").write_text(
            markdown_sections(
                "Current",
                {
                    "Tasks": task_lines,
                    "Summary": summary,
                    "Next Step": next_action,
                },
            ),
            encoding="utf-8",
        )

    def select_session_rows_from_registry(self, recent: int = 5) -> list[dict[str, str]]:
        _, rows = read_registry(self.root / TASK_REGISTRY)
        active = [row for row in rows if row.get("status") in {"active", "paused", "blocked"}]
        closed = [row for row in rows if row.get("status") in {"closed", "released"}]
        closed.sort(key=lambda row: row.get("updated_at", ""), reverse=True)
        return active + closed[:recent]

    def select_session_task_ids_from_registry(self, recent: int = 5) -> list[str]:
        return [row["task_id"] for row in self.select_session_rows_from_registry(recent) if row.get("task_id")]

    def rebuild_continue(self, recent: int = 5) -> None:
        selected = self.select_session_rows_from_registry(recent)
        task_ids = [row["task_id"] for row in selected if row.get("task_id")]
        if not task_ids:
            self.summarize_session([], "No active or recent tasks found.", "Start a task when ready.")
            return
        active_count = len([row for row in selected if row.get("status") in {"active", "paused", "blocked"}])
        recent_count = len(selected) - active_count
        self.summarize_session(
            task_ids,
            f"Continuation rebuilt from the task registry: {active_count} active/paused/blocked task(s) and {recent_count} recent closed/released task(s).",
            "Review the listed tasks and choose the next action.",
        )

    def batch_touched_paths(self, operations: list[object]) -> list[Path]:
        paths = [
            self.root / ".workroot/runtime/index",
            self.root / ".workroot/runtime/work/tasks",
            self.root / ".workroot/runtime/context",
            self.root / "space/work",
            self.root / "space/mind",
        ]
        for operation in operations:
            if not isinstance(operation, dict):
                continue
            op = operation.get("op")
            if op == "artifact.add" and isinstance(operation.get("path"), str):
                paths.append(self.repo_path(str(operation["path"])))
            elif op == "mind.add":
                rel = operation.get("path") or operation.get("source_path")
                if isinstance(rel, str) and rel:
                    paths.append(self.repo_path(rel))
            elif op == "invalidation.add" and isinstance(operation.get("path"), str) and operation.get("path"):
                paths.append(self.repo_path(str(operation["path"])))

        deduped: list[Path] = []
        for path in paths:
            if any(existing == path or existing in path.parents for existing in deduped):
                continue
            deduped = [existing for existing in deduped if not (path == existing or path in existing.parents)]
            deduped.append(path)
        return deduped

    def apply_batch(self, file_path: str) -> None:
        payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
        operations = payload.get("operations")
        if not isinstance(operations, list):
            raise SystemExit("batch file must contain an operations list")

        with file_lock(self.lock_path()):
            self._lock_depth += 1
            transaction_id = f"tx-{now_utc().replace(':', '').replace('-', '')}-{uuid.uuid4().hex[:8]}"
            transaction_dir = self.root / ".workroot/runtime/transactions"
            backup_dir = transaction_dir / transaction_id
            journal = transaction_dir / f"{transaction_id}.json"
            snapshots: list[tuple[Path, Path, bool]] = []
            backup_dir.mkdir(parents=True, exist_ok=True)
            for path in self.batch_touched_paths(operations):
                backup = backup_dir / path.relative_to(self.root)
                existed = path.exists()
                snapshots.append((path, backup, existed))
                if existed:
                    copy_tree_or_file(path, backup)
            journal.write_text(
                json.dumps(
                    {
                        "transaction_id": transaction_id,
                        "status": "started",
                        "created_at": now_utc(),
                        "source_file": file_path,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            try:
                for operation in operations:
                    self.apply_batch_operation(operation)
            except BaseException as exc:
                for path, backup, existed in reversed(snapshots):
                    if existed:
                        restore_tree_or_file(backup, path)
                    else:
                        remove_tree_or_file(path)
                journal.write_text(
                    json.dumps(
                        {
                            "transaction_id": transaction_id,
                            "status": "rolled_back",
                            "created_at": now_utc(),
                            "source_file": file_path,
                            "error": str(exc),
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                raise
            else:
                journal.write_text(
                    json.dumps(
                        {
                            "transaction_id": transaction_id,
                            "status": "committed",
                            "created_at": now_utc(),
                            "source_file": file_path,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
            finally:
                self._lock_depth -= 1

    def apply_batch_operation(self, operation: dict[str, object]) -> None:
        if not isinstance(operation, dict):
            raise SystemExit("batch operation must be an object")
        op = operation.get("op")
        if op == "task.create":
            self.create_task(
                title=str(operation["title"]),
                task_id=operation.get("task_id") if isinstance(operation.get("task_id"), str) else None,
                process_level=optional_str(operation.get("process_level"), "L0"),
                goal=optional_str(operation.get("goal"), "What are we trying to accomplish?"),
                why=optional_str(operation.get("why"), "Why is this worth doing?"),
                expected=optional_str(operation.get("expected"), "What should exist when this task is done?"),
                next_action=optional_str(operation.get("next_action"), "Define next step"),
                owner_scope=optional_str(operation.get("owner_scope"), "personal"),
                visibility=optional_str(operation.get("visibility"), "internal"),
                priority=optional_str(operation.get("priority")),
                created_at=operation.get("created_at") if isinstance(operation.get("created_at"), str) else None,
                user_visible_output_path=operation.get("user_visible_output_path") if isinstance(operation.get("user_visible_output_path"), str) else None,
            )
        elif op == "run.add":
            self.add_run(
                task_id=str(operation["task_id"]),
                run_id=str(operation["run_id"]),
                title=str(operation["title"]),
                status=optional_str(operation.get("status"), "active"),
                validity=optional_str(operation.get("validity")),
                validity_reason=optional_str(operation.get("validity_reason")),
                superseded_by=optional_str(operation.get("superseded_by")),
                started_at=operation.get("started_at") if isinstance(operation.get("started_at"), str) else None,
                completed_at=optional_str(operation.get("completed_at")),
                output_dir=optional_str(operation.get("output_dir")),
                primary_artifact=optional_str(operation.get("primary_artifact")),
                validation=optional_str(operation.get("validation")),
                conclusion_preview=optional_str(operation.get("conclusion_preview")),
            )
        elif op == "task.update":
            self.sync_task_state(
                task_id=str(operation["task_id"]),
                status=operation.get("status") if isinstance(operation.get("status"), str) else None,
                updated_at=operation.get("updated_at") if isinstance(operation.get("updated_at"), str) else None,
                next_action=operation.get("next_action") if isinstance(operation.get("next_action"), str) else None,
                user_visible_output_path=operation.get("user_visible_output_path") if isinstance(operation.get("user_visible_output_path"), str) else None,
                brief_current_state=operation.get("brief_current_state") if isinstance(operation.get("brief_current_state"), str) else None,
                brief_latest_result=operation.get("brief_latest_result") if isinstance(operation.get("brief_latest_result"), str) else None,
                handoff_status=operation.get("handoff_status") if isinstance(operation.get("handoff_status"), str) else None,
                handoff_latest_result=operation.get("handoff_latest_result") if isinstance(operation.get("handoff_latest_result"), str) else None,
                index_outputs=operation.get("index_outputs") if isinstance(operation.get("index_outputs"), list) else None,
                mind_paths=operation.get("mind_paths") if isinstance(operation.get("mind_paths"), list) else None,
                continue_summary=operation.get("continue_summary") if isinstance(operation.get("continue_summary"), str) else None,
            )
        elif op == "artifact.add":
            content = ""
            if isinstance(operation.get("content_file"), str):
                content = Path(str(operation["content_file"])).read_text(encoding="utf-8")
            self.add_artifact(
                    artifact_id=str(operation["artifact_id"]),
                    task_id=str(operation["task_id"]),
                    run_id=optional_str(operation.get("run_id")),
                    action_id=optional_str(operation.get("action_id")),
                    type=optional_str(operation.get("type")),
                    path=str(operation["path"]),
                    audience=optional_str(operation.get("audience"), "internal"),
                    status=optional_str(operation.get("status"), "active"),
                    size=optional_str(operation.get("size")),
                    checksum=optional_str(operation.get("checksum")),
                    created_at=operation.get("created_at") if isinstance(operation.get("created_at"), str) else None,
                    create_missing=bool(operation.get("content_file") or operation.get("content")),
                    content=content or optional_str(operation.get("content")),
                    compute_metadata=bool(operation.get("compute_metadata")),
                )
        elif op == "action.add":
            self.add_action(
                task_id=str(operation["task_id"]),
                action_id=str(operation["action_id"]),
                run_id=optional_str(operation.get("run_id")),
                type=optional_str(operation.get("type")),
                status=optional_str(operation.get("status"), "active"),
                summary=optional_str(operation.get("summary")),
                tool=optional_str(operation.get("tool")),
                input_ref=optional_str(operation.get("input_ref")),
                output_ref=optional_str(operation.get("output_ref")),
                approval_ref=optional_str(operation.get("approval_ref")),
                risk_level=optional_str(operation.get("risk_level")),
                created_at=operation.get("created_at") if isinstance(operation.get("created_at"), str) else None,
            )
        elif op == "checkpoint.add":
            self.add_checkpoint(
                task_id=str(operation["task_id"]),
                checkpoint_id=str(operation["checkpoint_id"]),
                current_status=str(operation["current_status"]),
                last_valid_run_id=optional_str(operation.get("last_valid_run_id")),
                next_action=optional_str(operation.get("next_action")),
                required_context_paths=optional_path_list(operation.get("required_context_paths")),
                created_at=operation.get("created_at") if isinstance(operation.get("created_at"), str) else None,
            )
        elif op == "retrieval_card.add":
            self.add_retrieval_card(
                task_id=str(operation["task_id"]),
                card_id=str(operation["card_id"]),
                freshness=optional_str(operation.get("freshness"), "hot"),
                source_paths=optional_path_list(operation.get("source_paths")),
                created_at=operation.get("created_at") if isinstance(operation.get("created_at"), str) else None,
            )
        elif op == "invalidation.add":
            self.add_invalidation(
                task_id=str(operation["task_id"]),
                invalidation_id=str(operation["invalidation_id"]),
                run_id=optional_str(operation.get("run_id")),
                artifact_id=optional_str(operation.get("artifact_id")),
                invalidated_claim=optional_str(operation.get("invalidated_claim")),
                reason=optional_str(operation.get("reason")),
                replacement_ref=optional_str(operation.get("replacement_ref")),
                path=optional_str(operation.get("path")),
                created_at=operation.get("created_at") if isinstance(operation.get("created_at"), str) else None,
            )
        elif op == "mind.add":
            from_paths = operation.get("from_paths")
            if from_paths is None and isinstance(operation.get("from_path"), str):
                from_paths = [operation["from_path"]]
            if from_paths is None:
                from_paths = []
            if not isinstance(from_paths, list):
                raise SystemExit("mind.add from_paths must be a list")
            from_task_ids = operation.get("from_task_ids")
            if from_task_ids is None and isinstance(operation.get("from_task_id"), str):
                from_task_ids = [operation["from_task_id"]]
            if from_task_ids is None:
                from_task_ids = []
            if not isinstance(from_task_ids, list):
                raise SystemExit("mind.add from_task_ids must be a list")
            set_task_output = operation.get("set_task_output")
            if set_task_output is None:
                set_task_output = False
            if not isinstance(set_task_output, bool):
                raise SystemExit("mind.add set_task_output must be a boolean")
            self.add_mind(
                mind_id=str(operation["mind_id"]),
                title=str(operation["title"]),
                type=str(operation["type"]),
                status=optional_str(operation.get("status"), "active"),
                temperature=optional_str(operation.get("temperature"), "warm"),
                privacy_level=optional_str(operation.get("privacy_level"), "internal"),
                release_level=optional_str(operation.get("release_level"), "active"),
                retrieval_rule=optional_str(operation.get("retrieval_rule")),
                summary=optional_str(operation.get("summary")),
                path=optional_str(operation.get("path")),
                from_paths=[str(value) for value in from_paths],
                from_task_ids=[str(value) for value in from_task_ids],
                set_task_output=set_task_output,
                source_path=optional_str(operation.get("source_path")),
                related_task_id=optional_str(operation.get("related_task_id")),
                replaces_mind_id=optional_str(operation.get("replaces_mind_id")),
                created_at=operation.get("created_at") if isinstance(operation.get("created_at"), str) else None,
            )
        elif op == "session.summarize":
            task_ids = operation["task_ids"]
            if not isinstance(task_ids, list):
                raise SystemExit("session.summarize task_ids must be a list")
            self.summarize_session(
                [str(task_id) for task_id in task_ids],
                str(operation["summary"]),
                str(operation["next_action"]),
            )
        else:
            raise SystemExit(f"unsupported batch operation: {op}")

    def touch_task(self, task_id: str, instant: str) -> None:
        task_dir = self.require_task_dir(task_id)
        self.update_registry_row(TASK_REGISTRY.as_posix(), "task_id", task_id, {"updated_at": instant})
        self.update_task_json(task_dir, None, instant, None)

    def update_run(
        self,
        run_id: str,
        status: str | None = None,
        validity: str | None = None,
        validity_reason: str | None = None,
        superseded_by: str | None = None,
        completed_at: str | None = None,
        output_dir: str | None = None,
        primary_artifact: str | None = None,
        validation: str | None = None,
        conclusion_preview: str | None = None,
        updated_at: str | None = None,
    ) -> ProcessRecord:
        row = self.registry_row(".workroot/runtime/index/run_registry.csv", "run_id", run_id)
        completed = normalize_instant(completed_at) if completed_at else None
        instant = normalize_instant(updated_at) if updated_at else completed or now_utc()
        updates = {"updated_at": instant}
        for key, value in {
            "status": status,
            "validity": validity,
            "validity_reason": validity_reason,
            "superseded_by": superseded_by,
            "completed_at": completed,
            "output_dir": output_dir,
            "primary_artifact": primary_artifact,
            "validation": validation,
            "conclusion_preview": conclusion_preview,
        }.items():
            if value is not None:
                updates[key] = value
        row = self.update_registry_row(".workroot/runtime/index/run_registry.csv", "run_id", run_id, updates)
        task_dir = self.require_task_dir(row["task_id"])
        path = task_dir / "runs" / f"{run_id}.md"
        rel = path.relative_to(self.root).as_posix()
        self.write_markdown_record(
            path,
            row.get("title") or run_id,
            {
                "Run ID": run_id,
                "Task ID": row.get("task_id", ""),
                "Status": row.get("status", ""),
                "Validation": row.get("validation", ""),
                "Conclusion": row.get("conclusion_preview", ""),
            },
        )
        return ProcessRecord(run_id, rel, run_id=run_id)

    def registry_row(self, rel: str, id_field: str, id_value: str) -> dict[str, str]:
        _, rows = read_registry(self.root / rel)
        for row in rows:
            if row.get(id_field) == id_value:
                return row
        raise SystemExit(f"registry row not found: {id_field}={id_value}")

    def add_run(
        self,
        task_id: str,
        run_id: str,
        title: str,
        status: str = "active",
        validity: str = "",
        validity_reason: str = "",
        superseded_by: str = "",
        started_at: str | None = None,
        completed_at: str = "",
        output_dir: str = "",
        primary_artifact: str = "",
        validation: str = "",
        conclusion_preview: str = "",
    ) -> ProcessRecord:
        task_dir = self.require_task_dir(task_id)
        instant = normalize_instant(started_at) if started_at else now_utc()
        completed = normalize_instant(completed_at) if completed_at else ""
        path = task_dir / "runs" / f"{run_id}.md"
        rel = path.relative_to(self.root).as_posix()
        self.write_markdown_record(
            path,
            title,
            {
                "Run ID": run_id,
                "Task ID": task_id,
                "Status": status,
                "Validation": validation,
                "Conclusion": conclusion_preview,
            },
        )
        self.append_registry(
            ".workroot/runtime/index/run_registry.csv",
            ["run_id"],
            {
                "run_id": run_id,
                "task_id": task_id,
                "title": title,
                "status": status,
                "validity": validity,
                "validity_reason": validity_reason,
                "superseded_by": superseded_by,
                "started_at": instant,
                "completed_at": completed,
                "output_dir": output_dir,
                "primary_artifact": primary_artifact,
                "validation": validation,
                "conclusion_preview": conclusion_preview,
                "updated_at": completed or instant,
            },
        )
        self.sync_task_state(
            task_id=task_id,
            updated_at=completed or instant,
            brief_latest_result=conclusion_preview or f"Run recorded: {title}.",
            handoff_latest_result=conclusion_preview,
        )
        return ProcessRecord(run_id, rel, run_id=run_id)

    def add_action(
        self,
        task_id: str,
        action_id: str,
        run_id: str = "",
        type: str = "",
        status: str = "active",
        summary: str = "",
        tool: str = "",
        input_ref: str = "",
        output_ref: str = "",
        approval_ref: str = "",
        risk_level: str = "",
        created_at: str | None = None,
    ) -> ProcessRecord:
        task_dir = self.require_task_dir(task_id)
        instant = normalize_instant(created_at) if created_at else now_utc()
        path = task_dir / "actions" / f"{action_id}.md"
        rel = path.relative_to(self.root).as_posix()
        self.write_markdown_record(
            path,
            action_id,
            {
                "Task ID": task_id,
                "Run ID": run_id,
                "Type": type,
                "Status": status,
                "Summary": summary,
                "Tool": tool,
            },
        )
        self.append_registry(
            ".workroot/runtime/index/action_registry.csv",
            ["action_id"],
            {
                "action_id": action_id,
                "task_id": task_id,
                "run_id": run_id,
                "type": type,
                "status": status,
                "summary": summary,
                "tool": tool,
                "input_ref": input_ref,
                "output_ref": output_ref,
                "approval_ref": approval_ref,
                "risk_level": risk_level,
                "created_at": instant,
                "updated_at": instant,
            },
        )
        self.sync_task_state(
            task_id=task_id,
            updated_at=instant,
            brief_latest_result=summary or f"Action recorded: {action_id}.",
            handoff_latest_result=summary,
        )
        return ProcessRecord(action_id, rel, action_id=action_id)

    def add_artifact(
        self,
        artifact_id: str,
        task_id: str,
        run_id: str = "",
        action_id: str = "",
        type: str = "",
        path: str = "",
        audience: str = "internal",
        status: str = "active",
        size: str = "",
        checksum: str = "",
        created_at: str | None = None,
        create_missing: bool = False,
        content: str = "",
        compute_metadata: bool = False,
    ) -> ProcessRecord:
        self.require_task_dir(task_id)
        instant = normalize_instant(created_at) if created_at else now_utc()
        artifact_path = self.repo_path(path)
        if create_missing and not artifact_path.exists():
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(content, encoding="utf-8")
        if compute_metadata:
            if not artifact_path.exists() or not artifact_path.is_file():
                raise SystemExit(f"artifact path does not exist as a file: {path}")
            data = artifact_path.read_bytes()
            size = str(len(data))
            checksum = "sha256:" + hashlib.sha256(data).hexdigest()
        self.append_registry(
            ".workroot/runtime/index/artifact_registry.csv",
            ["artifact_id"],
            {
                "artifact_id": artifact_id,
                "task_id": task_id,
                "run_id": run_id,
                "action_id": action_id,
                "type": type,
                "path": path,
                "audience": audience,
                "status": status,
                "size": size,
                "checksum": checksum,
                "created_at": instant,
                "updated_at": instant,
            },
        )
        self.sync_task_state(
            task_id=task_id,
            updated_at=instant,
            user_visible_output_path=path,
            brief_latest_result=f"Artifact recorded: {path}.",
            handoff_latest_result=f"Artifact recorded: {path}.",
            index_outputs=[path],
            continue_summary=f"An output was saved at {path}.",
        )
        return ProcessRecord(artifact_id, path, artifact_id=artifact_id)

    def add_retrieval_card(
        self,
        task_id: str,
        card_id: str,
        freshness: str = "hot",
        source_paths: str = "",
        created_at: str | None = None,
    ) -> ProcessRecord:
        task_dir = self.require_task_dir(task_id)
        instant = normalize_instant(created_at) if created_at else now_utc()
        path = task_dir / "retrieval_cards" / f"{card_id}.md"
        rel = path.relative_to(self.root).as_posix()
        self.write_markdown_record(
            path,
            card_id,
            {
                "Task ID": task_id,
                "Freshness": freshness,
                "Source Paths": source_paths,
            },
        )
        self.append_registry(
            ".workroot/runtime/index/retrieval_card_registry.csv",
            ["card_id"],
            {
                "card_id": card_id,
                "task_id": task_id,
                "path": rel,
                "freshness": freshness,
                "source_paths": source_paths,
                "created_at": instant,
                "updated_at": instant,
            },
        )
        self.sync_task_state(
            task_id=task_id,
            updated_at=instant,
            brief_latest_result=f"Retrieval card recorded: {card_id}.",
            handoff_latest_result=f"Retrieval card recorded: {card_id}.",
        )
        return ProcessRecord(card_id, rel, card_id=card_id)

    def add_checkpoint(
        self,
        task_id: str,
        checkpoint_id: str,
        current_status: str,
        last_valid_run_id: str = "",
        next_action: str = "",
        required_context_paths: str = "",
        created_at: str | None = None,
    ) -> ProcessRecord:
        task_dir = self.require_task_dir(task_id)
        instant = normalize_instant(created_at) if created_at else now_utc()
        path = task_dir / "checkpoints" / f"{checkpoint_id}.md"
        rel = path.relative_to(self.root).as_posix()
        self.write_markdown_record(
            path,
            checkpoint_id,
            {
                "Task ID": task_id,
                "Current Status": current_status,
                "Last Valid Run ID": last_valid_run_id,
                "Next Action": next_action,
                "Required Context Paths": required_context_paths,
            },
        )
        self.append_registry(
            ".workroot/runtime/index/checkpoint_registry.csv",
            ["checkpoint_id"],
            {
                "checkpoint_id": checkpoint_id,
                "task_id": task_id,
                "path": rel,
                "created_at": instant,
                "current_status": current_status,
                "last_valid_run_id": last_valid_run_id,
                "next_action": next_action,
                "required_context_paths": required_context_paths,
            },
        )
        self.sync_task_state(
            task_id=task_id,
            updated_at=instant,
            next_action=next_action or None,
            brief_current_state=current_status,
            handoff_status=current_status,
        )
        return ProcessRecord(checkpoint_id, rel, checkpoint_id=checkpoint_id)

    def add_invalidation(
        self,
        task_id: str,
        invalidation_id: str,
        run_id: str = "",
        artifact_id: str = "",
        invalidated_claim: str = "",
        reason: str = "",
        replacement_ref: str = "",
        path: str = "",
        created_at: str | None = None,
    ) -> ProcessRecord:
        task_dir = self.require_task_dir(task_id)
        instant = normalize_instant(created_at) if created_at else now_utc()
        rel = path or (task_dir / "invalidations" / f"{invalidation_id}.md").relative_to(self.root).as_posix()
        record_path = self.root / rel
        self.write_markdown_record(
            record_path,
            invalidation_id,
            {
                "Task ID": task_id,
                "Run ID": run_id,
                "Artifact ID": artifact_id,
                "Invalidated Claim": invalidated_claim,
                "Reason": reason,
                "Replacement Ref": replacement_ref,
            },
        )
        self.append_registry(
            ".workroot/runtime/index/invalidation_registry.csv",
            ["invalidation_id"],
            {
                "invalidation_id": invalidation_id,
                "task_id": task_id,
                "run_id": run_id,
                "artifact_id": artifact_id,
                "invalidated_claim": invalidated_claim,
                "reason": reason,
                "replacement_ref": replacement_ref,
                "path": rel,
                "created_at": instant,
                "updated_at": instant,
            },
        )
        self.sync_task_state(
            task_id=task_id,
            updated_at=instant,
            brief_latest_result=f"Invalidation recorded: {invalidated_claim or invalidation_id}.",
            handoff_latest_result=f"Invalidation recorded: {invalidated_claim or invalidation_id}.",
        )
        return ProcessRecord(invalidation_id, rel, invalidation_id=invalidation_id)

    def add_mind(
        self,
        mind_id: str,
        title: str,
        type: str,
        status: str = "active",
        temperature: str = "warm",
        privacy_level: str = "internal",
        release_level: str = "active",
        retrieval_rule: str = "",
        summary: str = "",
        path: str = "",
        from_paths: list[str] | None = None,
        from_task_ids: list[str] | None = None,
        set_task_output: bool = False,
        source_path: str = "",
        related_task_id: str = "",
        replaces_mind_id: str = "",
        created_at: str | None = None,
    ) -> ProcessRecord:
        if type not in MIND_TYPES:
            raise SystemExit(f"invalid mind type: {type}")
        if related_task_id:
            self.require_task_dir(related_task_id)
        instant = normalize_instant(created_at) if created_at else now_utc()
        rel = path or source_path or f"space/mind/{MIND_DIRS[type]}/{mind_id}.md"
        path = self.repo_path(rel)
        if path.exists():
            raise SystemExit(f"mind file already exists: {rel}")
        template_path = self.root / "space/mind/_templates" / f"{type}.md"
        if template_path.exists():
            text = template_path.read_text(encoding="utf-8")
            text = text.replace(f"# {template_path.stem.title()}", f"# {title}", 1)
        else:
            text = markdown_sections(title, {"Summary": summary})
        if summary:
            text = markdown_sections(
                title,
                {
                    "Summary": summary,
                    "Source": f"- `{related_task_id}`" if related_task_id else "",
                    "Lifecycle": f"- status: {status}\n- temperature: {temperature}",
                },
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

        self.append_registry(
            ".workroot/runtime/index/mind_registry.csv",
            ["mind_id"],
            {
                "mind_id": mind_id,
                "title": title,
                "type": type,
                "status": status,
                "temperature": temperature,
                "privacy_level": privacy_level,
                "release_level": release_level,
                "retrieval_rule": retrieval_rule,
                "created_at": instant,
                "updated_at": instant,
                "source_path": rel,
                "related_task_id": related_task_id,
                "replaces_mind_id": replaces_mind_id,
            },
        )
        for from_path in from_paths or []:
            self.append_registry(
                ".workroot/runtime/index/link_registry.csv",
                ["link_id"],
                {
                    "link_id": f"link-{mind_id}-from-file-{slugify(from_path)}",
                    "source_type": "file",
                    "source_id": from_path,
                    "target_type": "mind",
                    "target_id": mind_id,
                    "relation": "source_for",
                    "created_at": instant,
                    "updated_at": instant,
                },
            )
        for from_task_id in from_task_ids or []:
            self.append_registry(
                ".workroot/runtime/index/link_registry.csv",
                ["link_id"],
                {
                    "link_id": f"link-{mind_id}-from-task-{slugify(from_task_id)}",
                    "source_type": "task",
                    "source_id": from_task_id,
                    "target_type": "mind",
                    "target_id": mind_id,
                    "relation": "source_for",
                    "created_at": instant,
                    "updated_at": instant,
                },
            )
        if related_task_id:
            output_path = rel if set_task_output else None
            self.sync_task_state(
                task_id=related_task_id,
                updated_at=instant,
                user_visible_output_path=output_path,
                brief_latest_result=f"Mind entry promoted: {title}.",
                handoff_latest_result=f"Mind entry promoted: {title}.",
                mind_paths=[rel],
                continue_summary=f"A reusable entry was saved: {title}.",
            )
        return ProcessRecord(mind_id, rel, mind_id=mind_id)
