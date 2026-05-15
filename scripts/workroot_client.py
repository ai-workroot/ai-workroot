#!/usr/bin/env python3
"""File-first client for AI Workroot task process records."""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
import shutil
import unicodedata
from pathlib import Path


TASK_STATUSES = {"active", "paused", "blocked", "closed", "released"}
PROCESS_LEVELS = {"L0", "L1", "L2"}
OWNER_SCOPES = {"personal", "team", "role", "organization"}
VISIBILITIES = {"internal", "shared", "public", "private"}
TASK_REGISTRY = Path(".workroot/runtime/index/task_registry.csv")
WORK_ROOT = Path(".workroot/runtime/work")
TEMPLATE_DIR = WORK_ROOT / "_templates"
MAX_SLUG_LENGTH = 64

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


def normalize_instant(value: str) -> str:
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"invalid instant; use ISO-8601 with timezone: {value}") from exc
    if parsed.tzinfo is None:
        raise SystemExit(f"invalid instant; timezone is required: {value}")
    return parsed.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def replace_in_file(path: Path, replacements: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


class WorkrootClient:
    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root)

    def registry_path(self, rel: str) -> Path:
        return self.root / rel

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

        with path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writerow(full_row)

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
        lines = [f"# {title}", ""]
        for key, value in fields.items():
            lines.extend([f"## {key}", "", value or "", ""])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

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
    ) -> ProcessRecord:
        self.require_task_dir(task_id)
        instant = normalize_instant(created_at) if created_at else now_utc()
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
        return ProcessRecord(invalidation_id, rel, invalidation_id=invalidation_id)
