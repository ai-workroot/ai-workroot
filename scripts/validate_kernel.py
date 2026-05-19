#!/usr/bin/env python3
"""Validate the AI Workroot kernel layout, contracts, and release surface."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import datetime as dt
from pathlib import Path
from typing import Any


CONTRACT_DIR = Path(".workroot/kernel/contracts")
SCHEMA_DIR = Path(".workroot/kernel/schemas")
VERSION_PATH = Path(".workroot/kernel/VERSION")
READ_ORDER_PATH = Path(".workroot/kernel/boot/read-order.json")
CONTEXT_BUDGET_PATH = Path(".workroot/kernel/boot/context-budget.json")
LOADED_CONTEXT_PATH = Path(".workroot/runtime/context/loaded-context.json")
EXTENSION_REGISTRY = Path(".workroot/extensions/capability_registry.csv")

REQUIRED_CONTRACTS = [
    "kernel",
    "layout",
    "agent-startup",
    "context-policy",
    "forgetting-policy",
    "globalization-policy",
    "permission-hints",
    "storage-policy",
    "extension-policy",
    "test-policy",
]

REQUIRED_SCHEMAS = [
    "kernel.schema",
    "layout.schema",
    "agent-startup.schema",
    "context-policy.schema",
    "forgetting-policy.schema",
    "globalization-policy.schema",
    "permission-hints.schema",
    "storage-policy.schema",
    "extension-policy.schema",
    "test-policy.schema",
    "read-order.schema",
    "context-budget.schema",
    "loaded-context.schema",
]

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
    ".workroot/extensions/capability_registry.csv": [
        "capability_id",
        "name",
        "type",
        "status",
        "owner",
        "version",
        "purpose",
        "read_scope",
        "write_scope",
        "required_tools",
        "optional_tools",
        "privacy_level",
        "source_path",
        "created_at",
        "updated_at",
    ],
}

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
OFFSET_INSTANT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")
PRIVATE_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[^'\"\s]+"),
]
GENERATED_SUFFIXES = {
    ".sqlite",
    ".sqlite3",
    ".db",
    ".duckdb",
    ".wal",
}
GENERATED_STATE_PATH_PREFIXES = {
    ".ai-workroot-local/",
    "cache/",
    "context/debug/",
    "global-cache/",
    "logs/",
}
REQUIRED_0529_SPECS = [
    "001-project-structure-and-naming.spec.md",
    "002-clean-mode-installation.spec.md",
    "003-managed-state-layout.spec.md",
    "004-bootstrap-process.spec.md",
    "005-migrations.spec.md",
    "006-doctor-command.spec.md",
    "007-context-guide-builder.spec.md",
    "008-materialized-context-candidates.spec.md",
    "009-fts-indexing-and-retrieval.spec.md",
    "010-debug-trace-and-observability.spec.md",
    "011-cli-user-flows.spec.md",
    "012-native-agent-entry.spec.md",
    "013-sqlite-cache-and-provenance-graph.spec.md",
    "014-release-and-test-gates.spec.md",
    "015-context-guide-modes-budgets-and-confidence.spec.md",
]
TASK_PLACEHOLDER_PATTERNS = {
    "Task created; no work completed yet.",
    "Nothing yet.",
    "Short continuation status.",
    "What should happen next?",
}
TASK_RELATIONSHIP_REGISTRIES = {
    ".workroot/runtime/index/artifact_registry.csv": "task_id",
    ".workroot/runtime/index/decision_registry.csv": "task_id",
    ".workroot/runtime/index/mind_registry.csv": "related_task_id",
}
FUTURE_TIMESTAMP_TOLERANCE = dt.timedelta(minutes=5)
ALLOWED_PUBLIC_ROOTS = {
    ".github",
    ".gitignore",
    ".workroot",
    "AGENTS.md",
    "AUTHOR.md",
    "CHANGELOG.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "DCO.md",
    "LICENSE",
    "NOTICE",
    "PROJECT_BRIEF.md",
    "README.md",
    "ROADMAP.md",
    "START_HERE_FOR_HUMANS.md",
    "TRADEMARKS.md",
    "assets",
    "docs",
    "scripts",
    "space",
    "tests",
}
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
MIND_TEMPERATURES = {
    "hot",
    "warm",
    "cold",
    "archived",
    "released",
    "tombstone",
    "deleted",
}
RELEASE_LEVELS = {
    "active",
    "quiet",
    "archived",
    "tombstone",
    "redacted",
    "deleted",
}
TASK_STATUSES = {"active", "paused", "blocked", "closed", "released"}
PROCESS_LEVELS = {"L0", "L1", "L2"}
ACTION_TYPES = {
    "command",
    "database_query",
    "api_call",
    "file_edit",
    "browser_research",
    "model_generation",
    "test_run",
    "deployment",
    "manual_check",
    "other",
}
ARTIFACT_AUDIENCES = {"internal", "user", "public", "evidence"}


def add_error(errors: list[str], message: str) -> None:
    errors.append(message)


def load_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        add_error(errors, f"missing JSON file: {path.as_posix()}")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        add_error(errors, f"invalid JSON {path.as_posix()}: {exc}")
        return None
    if not isinstance(data, dict):
        add_error(errors, f"{path.as_posix()}: top-level JSON must be an object")
        return None
    return data


def type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def validate_type(path: Path, field: str, value: Any, expected: Any, errors: list[str]) -> None:
    actual = type_name(value)
    allowed = expected if isinstance(expected, list) else [expected]
    if actual not in allowed:
        add_error(errors, f"{path.as_posix()}: {field} type {actual}, expected {allowed}")


def validate_schema_contract(path: Path, data: dict[str, Any], schema: dict[str, Any], errors: list[str]) -> None:
    for field in schema.get("required_fields", []):
        if field not in data:
            add_error(errors, f"{path.as_posix()}: missing required field {field}")

    for field, expected in schema.get("field_types", {}).items():
        if field in data:
            validate_type(path, field, data[field], expected, errors)

    for field, allowed in schema.get("enum_values", {}).items():
        if field in data and data[field] not in allowed:
            add_error(errors, f"{path.as_posix()}: {field}={data[field]!r} not in {allowed}")

    for field in schema.get("semver_fields", []):
        value = data.get(field)
        if value and (not isinstance(value, str) or not SEMVER_RE.match(value)):
            add_error(errors, f"{path.as_posix()}: {field} is not semver: {value}")

    for field in schema.get("timestamp_fields", []):
        value = data.get(field)
        if value is None:
            continue
        if value and (not isinstance(value, str) or not UTC_RE.match(value)):
            add_error(errors, f"{path.as_posix()}: {field} is not UTC ISO-8601: {value}")

    for field in schema.get("path_fields", []):
        if field in data:
            validate_path_value(path, field, data[field], errors)


def validate_path_value(path: Path, field: str, value: Any, errors: list[str]) -> None:
    values = value if isinstance(value, list) else [value]
    for item in values:
        if not isinstance(item, str):
            continue
        if item.startswith("/"):
            add_error(errors, f"{path.as_posix()}: {field} contains absolute path: {item}")
        if "\\" in item:
            add_error(errors, f"{path.as_posix()}: {field} must use forward slashes: {item}")
        if ".." in Path(item).parts:
            add_error(errors, f"{path.as_posix()}: {field} must not contain '..': {item}")


def read_csv_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f).fieldnames or [])


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def registry_row_id(row: dict[str, str]) -> str:
    for key in (
        "task_id",
        "run_id",
        "action_id",
        "artifact_id",
        "decision_id",
        "card_id",
        "checkpoint_id",
        "invalidation_id",
        "mind_id",
        "link_id",
        "capability_id",
    ):
        value = (row.get(key) or "").strip()
        if value:
            return value
    return "<unknown>"


def validate_registry_headers(root: Path, errors: list[str]) -> None:
    for rel, expected in REGISTRY_HEADERS.items():
        path = root / rel
        if not path.exists():
            add_error(errors, f"missing registry: {rel}")
            continue
        actual = read_csv_header(path)
        if actual != expected:
            add_error(errors, f"{rel}: header mismatch. expected {expected}, got {actual}")


def validate_registry_time_values(root: Path, errors: list[str]) -> None:
    time_columns = {
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
    }
    for rel in REGISTRY_HEADERS:
        path = root / rel
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_number, row in enumerate(reader, start=2):
                for column in time_columns & set(row):
                    value = (row.get(column) or "").strip()
                    if not value:
                        continue
                    if not (UTC_RE.match(value) or DATE_RE.match(value)):
                        add_error(errors, f"{rel}:{row_number}: {column} must be UTC ISO-8601 or date-only: {value}")


def validate_registry_future_times(root: Path, errors: list[str]) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    time_columns = {
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
    }
    for rel in REGISTRY_HEADERS:
        path = root / rel
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_number, row in enumerate(reader, start=2):
                for column in time_columns & set(row):
                    value = (row.get(column) or "").strip()
                    if not value or not UTC_RE.match(value):
                        continue
                    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
                    if parsed - now > FUTURE_TIMESTAMP_TOLERANCE:
                        add_error(errors, f"{rel}:{row_number}: {column} is in the future: {value}")


def validate_forgetting_registry(root: Path, errors: list[str]) -> None:
    rel = ".workroot/runtime/index/mind_registry.csv"
    path = root / rel
    if not path.exists():
        return
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_number, row in enumerate(reader, start=2):
            mind_type = (row.get("type") or "").strip()
            temperature = (row.get("temperature") or "").strip()
            release_level = (row.get("release_level") or "").strip()
            retrieval_rule = (row.get("retrieval_rule") or "").strip()
            source_path = (row.get("source_path") or "").strip()
            if mind_type and mind_type not in MIND_TYPES:
                add_error(errors, f"{rel}:{row_number}: invalid mind type: {mind_type}")
            if temperature and temperature not in MIND_TEMPERATURES:
                add_error(errors, f"{rel}:{row_number}: invalid temperature: {temperature}")
            if release_level and release_level not in RELEASE_LEVELS:
                add_error(errors, f"{rel}:{row_number}: invalid release_level: {release_level}")
            is_tombstone_entry = "tombstone" in {mind_type, temperature, release_level}
            if is_tombstone_entry:
                if mind_type != "tombstone":
                    add_error(errors, f"{rel}:{row_number}: tombstone entries must use type=tombstone")
                if temperature != "tombstone":
                    add_error(errors, f"{rel}:{row_number}: tombstone entries must use temperature=tombstone")
                if release_level != "tombstone":
                    add_error(errors, f"{rel}:{row_number}: tombstone entries must use release_level=tombstone")
                if not retrieval_rule:
                    add_error(errors, f"{rel}:{row_number}: tombstone entries require retrieval_rule")
            if temperature in {"released", "deleted"} and retrieval_rule == "":
                add_error(errors, f"{rel}:{row_number}: {temperature} entries require retrieval_rule")
            if release_level and release_level != "active" and retrieval_rule == "":
                add_error(errors, f"{rel}:{row_number}: {release_level} release_level entries require retrieval_rule")
            if (temperature == "deleted" or release_level == "deleted") and source_path:
                add_error(errors, f"{rel}:{row_number}: deleted entries must not keep source_path details")


def validate_registry_paths(root: Path, errors: list[str]) -> None:
    path_columns = {
        "source_path",
        "output_path",
        "handoff_path",
        "brief_path",
        "decision_path",
        "path",
        "output_dir",
        "primary_artifact",
        "input_ref",
        "output_ref",
        "approval_ref",
        "promoted_path",
    }
    multi_path_columns = {"source_paths", "required_context_paths"}
    for rel in REGISTRY_HEADERS:
        path = root / rel
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_number, row in enumerate(reader, start=2):
                row_id = registry_row_id(row)
                for column in path_columns & set(row):
                    value = (row.get(column) or "").strip()
                    validate_registry_path_value(root, rel, row_number, column, value, row_id, errors)
                for column in multi_path_columns & set(row):
                    value = (row.get(column) or "").strip()
                    if not value:
                        continue
                    for item in [part.strip() for part in value.split(";") if part.strip()]:
                        validate_registry_path_value(root, rel, row_number, column, item, row_id, errors)


def validate_registry_path_value(
    root: Path,
    rel: str,
    row_number: int,
    column: str,
    value: str,
    row_id: str,
    errors: list[str],
) -> None:
    if not value:
        return
    if value.startswith(("http://", "https://", "mailto:")):
        return
    if value.startswith("/"):
        add_error(errors, f"{rel}:{row_number}: {column} must be repository-relative for {row_id}: {value}")
        return
    target = root / value
    if not target.exists():
        add_error(errors, f"{rel}:{row_number}: {column} path does not exist for {row_id}: {value}")


def related_task_ids(root: Path) -> set[str]:
    related: set[str] = set()
    for rel, column in TASK_RELATIONSHIP_REGISTRIES.items():
        for row in read_csv_rows(root / rel):
            value = (row.get(column) or "").strip()
            if value:
                related.add(value)
    for row in read_csv_rows(root / ".workroot/runtime/index/link_registry.csv"):
        for type_key, id_key in (("source_type", "source_id"), ("target_type", "target_id")):
            if (row.get(type_key) or "").strip() == "task":
                value = (row.get(id_key) or "").strip()
                if value:
                    related.add(value)
    return related


def validate_work_process_tasks(root: Path, errors: list[str]) -> None:
    rel = ".workroot/runtime/index/task_registry.csv"
    for row_number, row in enumerate(read_csv_rows(root / rel), start=2):
        task_id = (row.get("task_id") or "").strip()
        status = (row.get("status") or "").strip()
        process_level = (row.get("process_level") or "L0").strip()
        source_path = (row.get("source_path") or "").strip()
        if status and status not in TASK_STATUSES:
            add_error(errors, f"{rel}:{row_number}: invalid task status for {task_id}: {status}")
        if process_level not in PROCESS_LEVELS:
            add_error(errors, f"{rel}:{row_number}: invalid process_level for {task_id}: {process_level}")
            continue
        if not source_path:
            continue

        task_dir = root / source_path
        if not task_dir.exists():
            continue

        required = ["task.json", "task.md", "brief.md", "todo.md", "handoff.md", "outputs", "archive"]
        if process_level in {"L1", "L2"}:
            required.extend(["decisions.md", "index.md", "plans", "runs", "retrieval_cards", "checkpoints"])
        if process_level == "L2":
            required.extend(["actions", "recipes", "data", "validation", "invalidations"])
        for name in required:
            if not (task_dir / name).exists():
                add_error(errors, f"task {task_id} missing {process_level} required path: {source_path}/{name}")
        if (task_dir / "artifacts").exists():
            add_error(errors, f"task {task_id} must not use artifacts/ directory; use artifact_registry.csv")

        task_json = task_dir / "task.json"
        if task_json.exists():
            data = load_json(task_json, errors)
            if data:
                if data.get("task_id") != task_id:
                    add_error(errors, f"{task_json.as_posix()}: task_id mismatch with registry")
                if data.get("process_level", "L0") != process_level:
                    add_error(errors, f"{task_json.as_posix()}: process_level mismatch with registry")
                if data.get("status") and data.get("status") != status:
                    add_error(errors, f"{task_json.as_posix()}: status mismatch with registry")


def validate_work_process_references(root: Path, errors: list[str]) -> None:
    task_ids = {row.get("task_id", "") for row in read_csv_rows(root / ".workroot/runtime/index/task_registry.csv")}
    run_ids = {row.get("run_id", "") for row in read_csv_rows(root / ".workroot/runtime/index/run_registry.csv")}
    action_ids = {row.get("action_id", "") for row in read_csv_rows(root / ".workroot/runtime/index/action_registry.csv")}
    artifact_ids = {row.get("artifact_id", "") for row in read_csv_rows(root / ".workroot/runtime/index/artifact_registry.csv")}

    checks = [
        (".workroot/runtime/index/run_registry.csv", "task_id", task_ids),
        (".workroot/runtime/index/action_registry.csv", "task_id", task_ids),
        (".workroot/runtime/index/action_registry.csv", "run_id", run_ids),
        (".workroot/runtime/index/artifact_registry.csv", "task_id", task_ids),
        (".workroot/runtime/index/artifact_registry.csv", "run_id", run_ids),
        (".workroot/runtime/index/artifact_registry.csv", "action_id", action_ids),
        (".workroot/runtime/index/decision_registry.csv", "task_id", task_ids),
        (".workroot/runtime/index/retrieval_card_registry.csv", "task_id", task_ids),
        (".workroot/runtime/index/checkpoint_registry.csv", "task_id", task_ids),
        (".workroot/runtime/index/checkpoint_registry.csv", "last_valid_run_id", run_ids),
        (".workroot/runtime/index/invalidation_registry.csv", "task_id", task_ids),
        (".workroot/runtime/index/invalidation_registry.csv", "run_id", run_ids),
        (".workroot/runtime/index/invalidation_registry.csv", "artifact_id", artifact_ids),
    ]
    for rel, column, allowed in checks:
        for row_number, row in enumerate(read_csv_rows(root / rel), start=2):
            value = (row.get(column) or "").strip()
            if value and value not in allowed:
                add_error(errors, f"{rel}:{row_number}: unknown {column}: {value}")

    for row_number, row in enumerate(read_csv_rows(root / ".workroot/runtime/index/action_registry.csv"), start=2):
        action_type = (row.get("type") or "").strip()
        if action_type and action_type not in ACTION_TYPES:
            add_error(errors, f".workroot/runtime/index/action_registry.csv:{row_number}: invalid action type: {action_type}")

    for row_number, row in enumerate(read_csv_rows(root / ".workroot/runtime/index/artifact_registry.csv"), start=2):
        audience = (row.get("audience") or "").strip()
        if audience and audience not in ARTIFACT_AUDIENCES:
            add_error(errors, f".workroot/runtime/index/artifact_registry.csv:{row_number}: invalid artifact audience: {audience}")


def task_has_placeholders(task_dir: Path) -> list[str]:
    hits: list[str] = []
    for name in ("brief.md", "handoff.md", "todo.md", "index.md"):
        path = task_dir / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in sorted(TASK_PLACEHOLDER_PATTERNS):
            if pattern in text:
                hits.append(f"{name}: {pattern}")
    return hits


def validate_task_state_trust(root: Path, errors: list[str]) -> None:
    task_rows = read_csv_rows(root / ".workroot/runtime/index/task_registry.csv")
    if not task_rows:
        return

    related = related_task_ids(root)
    has_active_task = False
    for row_number, row in enumerate(task_rows, start=2):
        task_id = (row.get("task_id") or "").strip()
        status = (row.get("status") or "").strip()
        source_path = (row.get("source_path") or "").strip()
        output_path = (row.get("user_visible_output_path") or "").strip()
        task_dir = root / source_path if source_path else None
        is_active = status in {"active", "paused", "blocked"}
        has_active_task = has_active_task or is_active
        has_related_output = task_id in related

        if is_active and has_related_output and not output_path:
            add_error(errors, f".workroot/runtime/index/task_registry.csv:{row_number}: task {task_id} has related output or links but empty user_visible_output_path")

        if task_dir is not None and task_dir.exists():
            placeholders = task_has_placeholders(task_dir)
            if has_related_output and placeholders:
                add_error(errors, f"task {task_id} has related output or links but still contains template placeholders: {', '.join(placeholders)}")

    handoff_path = root / ".workroot/runtime/context/handoff.md"
    if has_active_task and handoff_path.exists():
        handoff = handoff_path.read_text(encoding="utf-8").strip()
        if handoff in {"# Handoff\n\nNo handoff yet.\n\nWhen work pauses, the AI agent should record the next useful step here.", "# Handoff\n\nNo handoff yet."} or "No handoff yet." in handoff:
            add_error(errors, ".workroot/runtime/context/handoff.md: active tasks exist but global handoff is still empty")


def validate_contracts(root: Path, errors: list[str]) -> dict[str, dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    schemas: dict[str, dict[str, Any]] = {}

    for schema_id in REQUIRED_SCHEMAS:
        path = root / SCHEMA_DIR / f"{schema_id}.json"
        schema = load_json(path, errors)
        if schema is not None:
            schemas[schema_id] = schema

    for contract_id in REQUIRED_CONTRACTS:
        path = root / CONTRACT_DIR / f"{contract_id}.json"
        data = load_json(path, errors)
        schema = schemas.get(f"{contract_id}.schema")
        if data is not None:
            contracts[contract_id] = data
        if data is not None and schema is not None:
            validate_schema_contract(path, data, schema, errors)

    for path, schema_id in [
        (root / READ_ORDER_PATH, "read-order.schema"),
        (root / CONTEXT_BUDGET_PATH, "context-budget.schema"),
        (root / LOADED_CONTEXT_PATH, "loaded-context.schema"),
    ]:
        data = load_json(path, errors)
        schema = schemas.get(schema_id)
        if data is not None and schema is not None:
            validate_schema_contract(path, data, schema, errors)

    return contracts


def validate_layout(root: Path, contracts: dict[str, dict[str, Any]], release: bool, errors: list[str]) -> None:
    layout = contracts.get("layout", {})
    for rel in layout.get("required_paths", []):
        if not (root / rel).exists():
            add_error(errors, f"required path missing: {rel}")

    if release:
        allowed_roots = set(layout.get("public_seed_root_paths", [])) or ALLOWED_PUBLIC_ROOTS
        for path in root.iterdir():
            if path.name == ".git":
                continue
            if path.name not in allowed_roots:
                add_error(errors, f"path is outside the public seed surface: {path.name}")


def validate_version(root: Path, contracts: dict[str, dict[str, Any]], errors: list[str]) -> None:
    path = root / VERSION_PATH
    if not path.exists():
        add_error(errors, f"missing version file: {VERSION_PATH.as_posix()}")
        return
    value = path.read_text(encoding="utf-8").strip()
    kernel = contracts.get("kernel", {})
    contract_version = kernel.get("kernel_version")
    if contract_version and contract_version != value:
        add_error(errors, f"kernel contract version must match {VERSION_PATH.as_posix()}: {contract_version!r} != {value!r}")


def validate_context_budget(root: Path, errors: list[str]) -> None:
    budget = load_json(root / CONTEXT_BUDGET_PATH, errors)
    read_order = load_json(root / READ_ORDER_PATH, errors)
    if not budget or not read_order:
        return
    default_order = read_order.get("default_read_order", [])
    if len(default_order) > budget.get("max_startup_files", 0):
        add_error(errors, "default read order exceeds max_startup_files")
    total_chars = 0
    for rel in default_order:
        path = root / rel
        if path.exists() and path.is_file():
            total_chars += len(path.read_text(encoding="utf-8"))
    if total_chars > budget.get("max_startup_characters", 0):
        add_error(errors, "default read order exceeds max_startup_characters")


def validate_release_surface(root: Path, errors: list[str]) -> None:
    for path in root.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_file() and path.suffix.lower() in GENERATED_SUFFIXES:
            add_error(errors, f"generated store must not be committed for release: {path.relative_to(root).as_posix()}")
        rel = path.relative_to(root).as_posix()
        if path.is_file() and any(rel.startswith(prefix) for prefix in GENERATED_STATE_PATH_PREFIXES):
            add_error(errors, f"generated managed state path must not be committed for release: {rel}")
        if path.is_file() and rel.startswith(".workroot/runtime/cache/") and path.name != ".gitkeep":
            add_error(errors, f"runtime cache file must not be present for release: {rel}")
        if path.is_file() and rel.startswith(".workroot/runtime/logs/") and path.name != ".gitkeep":
            add_error(errors, f"runtime log file must not be present for release: {rel}")
        if path.name in {".DS_Store"} or ".idea" in path.parts or "__pycache__" in path.parts:
            add_error(errors, f"local metadata must not be committed: {path.relative_to(root).as_posix()}")

    text_exts = {".md", ".json", ".csv", ".py", ".yml", ".yaml", ".txt", ".sql"}
    for path in root.rglob("*"):
        if ".git" in path.parts or not path.is_file() or path.suffix.lower() not in text_exts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            add_error(errors, f"text file must be UTF-8: {path.relative_to(root).as_posix()}: {exc}")
            continue
        for pattern in PRIVATE_PATTERNS:
            if pattern.search(text):
                add_error(errors, f"possible private residue in {path.relative_to(root).as_posix()}")
                break


def validate_0529_specs(root: Path, errors: list[str]) -> None:
    for name in REQUIRED_0529_SPECS:
        path = root / "docs/specs" / name
        if not path.exists():
            add_error(errors, f"missing 0.9.529 spec: docs/specs/{name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", action="store_true", help="Run strict public release validation")
    args = parser.parse_args()

    root = Path.cwd()
    errors: list[str] = []

    contracts = validate_contracts(root, errors)
    validate_version(root, contracts, errors)
    validate_layout(root, contracts, args.release, errors)
    validate_registry_headers(root, errors)
    validate_registry_time_values(root, errors)
    validate_registry_future_times(root, errors)
    validate_registry_paths(root, errors)
    validate_work_process_tasks(root, errors)
    validate_work_process_references(root, errors)
    validate_forgetting_registry(root, errors)
    validate_task_state_trust(root, errors)
    validate_context_budget(root, errors)
    if args.release:
        validate_0529_specs(root, errors)
        validate_release_surface(root, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 4 if args.release else 1

    mode = "release " if args.release else ""
    print(f"AI Workroot {mode}kernel validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
