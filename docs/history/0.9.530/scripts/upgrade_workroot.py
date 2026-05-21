#!/usr/bin/env python3
"""Upgrade an existing AI Workroot instance from a newer seed.

This migrates kernel/protocol/tooling files while preserving user-owned
workspace content. It also upgrades legacy task status directories into the
stable Work Process Layer task path.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import tempfile
from pathlib import Path


TASK_REGISTRY = Path(".workroot/runtime/index/task_registry.csv")
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

SYNC_PATHS = [
    ".github",
    "AGENTS.md",
    "CLAUDE.md",
    "START_HERE_FOR_HUMANS.md",
    "PROJECT_BRIEF.md",
    "README.md",
    ".workroot/kernel",
    ".workroot/extensions",
    ".workroot/runtime/work/README.md",
    ".workroot/runtime/work/_templates",
    ".workroot/runtime/data/README.md",
    ".workroot/runtime/data/graph/README.md",
    ".workroot/runtime/data/indexes/README.md",
    ".workroot/runtime/data/indexes/schema.sql",
    ".workroot/runtime/data/vector/README.md",
    "scripts",
    "tests",
    "docs",
    "assets",
]

PRESERVE_PATHS = [
    "FOUNDER_SPACE.md",
    "AUTHOR.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "DCO.md",
    "LICENSE",
    "NOTICE",
    "ROADMAP.md",
    "TRADEMARKS.md",
    "space",
    ".workroot/runtime/context",
    ".workroot/runtime/index",
    ".workroot/runtime/work/tasks",
    ".workroot/runtime/work/active",
    ".workroot/runtime/work/closed",
    ".workroot/runtime/data",
    ".workroot/runtime/cache",
    ".workroot/runtime/logs",
]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", dir=path.parent, delete=False) as handle:
        tmp_name = handle.name
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})
    os.replace(tmp_name, path)


def copy_path(source_root: Path, target_root: Path, rel: str, *, replace_dir: bool = False) -> bool:
    src = source_root / rel
    dst = target_root / rel
    if not src.exists():
        return False
    if replace_dir and dst.is_dir():
        shutil.rmtree(dst)
    elif dst.exists() and (not src.is_dir() or not dst.is_dir()):
        dst.unlink()
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    else:
        shutil.copy2(src, dst)
    return True


def backup_paths(target_root: Path, backup_root: Path) -> list[str]:
    copied: list[str] = []
    for rel in sorted(set(SYNC_PATHS + PRESERVE_PATHS)):
        src = target_root / rel
        if not src.exists():
            continue
        dst = backup_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(src, dst)
        copied.append(rel)
    return copied


def sync_seed_files(source_root: Path, target_root: Path) -> list[str]:
    copied: list[str] = []
    for rel in SYNC_PATHS:
        replace_dir = rel in {
            ".workroot/kernel",
            ".workroot/extensions",
            ".workroot/runtime/work/_templates",
        }
        if copy_path(source_root, target_root, rel, replace_dir=replace_dir):
            copied.append(rel)
    return copied


def ensure_gitkeep(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    gitkeep = path / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")


def normalize_registry(root: Path, rel: str) -> None:
    headers = REGISTRY_HEADERS[rel]
    path = root / rel
    old_headers, rows = read_csv(path)
    if not path.exists():
        write_csv(path, headers, [])
        return
    if old_headers == headers:
        return
    normalized: list[dict[str, str]] = []
    for row in rows:
        next_row = {header: "" for header in headers}
        for header in headers:
            next_row[header] = row.get(header, "")
        if rel == TASK_REGISTRY.as_posix():
            source_path = next_row.get("source_path", "")
            next_row["process_level"] = next_row.get("process_level") or "L0"
            next_row["brief_path"] = next_row.get("brief_path") or (f"{source_path}/brief.md" if source_path else "")
            next_row["handoff_path"] = next_row.get("handoff_path") or (f"{source_path}/handoff.md" if source_path else "")
            next_row["next_action"] = next_row.get("next_action") or "Ask the AI to continue this task."
        if rel == ".workroot/runtime/index/artifact_registry.csv":
            next_row["artifact_id"] = row.get("artifact_id", "")
            next_row["task_id"] = row.get("related_task_id", "")
            next_row["type"] = row.get("type", "")
            next_row["path"] = row.get("output_path") or row.get("source_path", "")
            next_row["audience"] = "user" if row.get("output_path") else "internal"
            next_row["status"] = row.get("status", "")
            next_row["created_at"] = row.get("created_at", "")
            next_row["updated_at"] = row.get("updated_at", "")
        if rel == ".workroot/runtime/index/decision_registry.csv":
            next_row["decision_id"] = row.get("decision_id", "")
            next_row["task_id"] = row.get("related_task_id", "")
            next_row["path"] = row.get("decision_path", "")
            next_row["title"] = row.get("title", "")
            next_row["status"] = row.get("status", "")
            next_row["created_at"] = row.get("created_at", "")
            next_row["updated_at"] = row.get("updated_at", "")
        normalized.append(next_row)
    write_csv(path, headers, normalized)


def ensure_registries(root: Path) -> list[str]:
    touched: list[str] = []
    for rel in REGISTRY_HEADERS:
        before = (root / rel).read_text(encoding="utf-8") if (root / rel).exists() else None
        normalize_registry(root, rel)
        after = (root / rel).read_text(encoding="utf-8") if (root / rel).exists() else None
        if before != after:
            touched.append(rel)
    return touched


def update_task_json(task_dir: Path, row: dict[str, str]) -> None:
    path = task_dir / "task.json"
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                payload = {}
        except json.JSONDecodeError:
            payload = {}
    else:
        payload = {}
    for key in ("task_id", "title", "status", "process_level", "created_at", "updated_at", "owner_scope", "visibility", "user_visible_output_path"):
        value = row.get(key, "")
        if key == "process_level" and not value:
            value = "L0"
        if value:
            payload[key] = value
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_task_shape(task_dir: Path, process_level: str) -> None:
    for name in ("outputs", "archive"):
        (task_dir / name).mkdir(parents=True, exist_ok=True)
    if process_level in {"L1", "L2"}:
        for name in ("plans", "runs", "retrieval_cards", "checkpoints"):
            (task_dir / name).mkdir(parents=True, exist_ok=True)
    if process_level == "L2":
        for name in ("actions", "recipes", "data", "validation", "invalidations"):
            (task_dir / name).mkdir(parents=True, exist_ok=True)


def migrate_task_paths(root: Path) -> list[str]:
    headers, rows = read_csv(root / TASK_REGISTRY)
    if not rows:
        ensure_gitkeep(root / ".workroot/runtime/work/tasks")
        return []
    if headers != REGISTRY_HEADERS[TASK_REGISTRY.as_posix()]:
        normalize_registry(root, TASK_REGISTRY.as_posix())
        headers, rows = read_csv(root / TASK_REGISTRY)

    moved: list[str] = []
    tasks_root = root / ".workroot/runtime/work/tasks"
    tasks_root.mkdir(parents=True, exist_ok=True)
    for row in rows:
        task_id = row.get("task_id", "")
        if not task_id:
            continue
        source_path = row.get("source_path", "")
        old_dir = root / source_path if source_path else Path()
        new_rel = f".workroot/runtime/work/tasks/{task_id}"
        new_dir = root / new_rel
        if source_path.startswith(".workroot/runtime/work/tasks/"):
            new_dir.mkdir(parents=True, exist_ok=True)
        elif old_dir.exists() and old_dir.is_dir():
            if new_dir.exists():
                shutil.copytree(old_dir, new_dir, dirs_exist_ok=True)
                shutil.rmtree(old_dir)
            else:
                new_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old_dir), str(new_dir))
            moved.append(f"{source_path} -> {new_rel}")
        else:
            new_dir.mkdir(parents=True, exist_ok=True)
        process_level = row.get("process_level") or "L0"
        row["process_level"] = process_level
        row["source_path"] = new_rel
        row["brief_path"] = f"{new_rel}/brief.md"
        row["handoff_path"] = f"{new_rel}/handoff.md"
        row["next_action"] = row.get("next_action") or "Ask the AI to continue this task."
        ensure_task_shape(new_dir, process_level)
        update_task_json(new_dir, row)

    write_csv(root / TASK_REGISTRY, REGISTRY_HEADERS[TASK_REGISTRY.as_posix()], rows)
    ensure_gitkeep(tasks_root)
    for legacy in (root / ".workroot/runtime/work/active", root / ".workroot/runtime/work/closed"):
        if not legacy.exists():
            continue
        remaining = [item for item in legacy.iterdir() if item.name != ".gitkeep"]
        if not remaining:
            shutil.rmtree(legacy)
    return moved


def upgrade(source_root: Path, target_root: Path, backup_dir: Path | None) -> dict[str, object]:
    if not (source_root / ".workroot/kernel/VERSION").exists():
        raise SystemExit(f"source is not an AI Workroot seed: {source_root}")
    if not (target_root / ".workroot/kernel/VERSION").exists():
        raise SystemExit(f"target is not an AI Workroot instance: {target_root}")
    backup_path = backup_dir or target_root / ".workroot/runtime/local" / "upgrade-backups" / (source_root / ".workroot/kernel/VERSION").read_text(encoding="utf-8").strip()
    if backup_path.exists():
        shutil.rmtree(backup_path)
    backed_up = backup_paths(target_root, backup_path)
    copied = sync_seed_files(source_root, target_root)
    registries = ensure_registries(target_root)
    moved = migrate_task_paths(target_root)
    return {
        "source": str(source_root),
        "target": str(target_root),
        "backup": str(backup_path),
        "backed_up": backed_up,
        "synced": copied,
        "registries": registries,
        "moved_tasks": moved,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Path to the newer AI Workroot seed.")
    parser.add_argument("--target", default=".", help="Path to the Workroot instance to upgrade.")
    parser.add_argument("--backup-dir", help="Optional backup directory.")
    parser.add_argument("--report", help="Optional JSON report path.")
    args = parser.parse_args()

    report = upgrade(
        source_root=Path(args.source).resolve(),
        target_root=Path(args.target).resolve(),
        backup_dir=Path(args.backup_dir).resolve() if args.backup_dir else None,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
