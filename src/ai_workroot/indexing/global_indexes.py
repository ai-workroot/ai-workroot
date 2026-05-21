"""Minimal global index maintenance for Workroot navigation."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ai_workroot.storage.jsonl_registry import read_jsonl
from ai_workroot.storage.sqlite import initialize_workroot_sqlite


def refresh_global_workroot_index(ai_workroot_home: Path | str) -> int:
    home = Path(ai_workroot_home).expanduser().resolve()
    records = read_jsonl(home / "registry/workroots.jsonl")
    index_records: list[dict[str, str]] = []
    count = 0
    for record in records:
        workroot_id = str(record.get("workroot_id") or "")
        state_directory = Path(str(record.get("state_directory") or ""))
        title = str(record.get("name") or workroot_id)
        if not workroot_id or not state_directory:
            continue
        db_path = state_directory / "cache/workroot.sqlite"
        initialize_workroot_sqlite(db_path)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO global_index_entries (entry_id, workroot_id, entry_type, title)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(entry_id) DO UPDATE SET
                  workroot_id=excluded.workroot_id,
                  entry_type=excluded.entry_type,
                  title=excluded.title
                """,
                (f"workroot:{workroot_id}", workroot_id, "workroot", title),
            )
            conn.commit()
        index_records.append(
            {
                "entryId": f"workroot:{workroot_id}",
                "workrootId": workroot_id,
                "entryType": "workroot",
                "title": title,
                "stateDirectory": str(state_directory),
            }
        )
        count += 1
    _write_global_workroot_index(home / "global-index/workroots.index.jsonl", index_records)
    return count


def query_global_workroot_index(ai_workroot_home: Path | str, *, query: str = "") -> list[dict[str, str]]:
    return _query_global_index(ai_workroot_home, "workroots.index.jsonl", query=query)


def refresh_global_task_index(ai_workroot_home: Path | str) -> int:
    home = Path(ai_workroot_home).expanduser().resolve()
    records: list[dict[str, str]] = []
    for workroot in _registered_workroots(home):
        with sqlite3.connect(workroot.db_path) as conn:
            rows = conn.execute(
                """
                SELECT task_id, title, status, task_kind, process_level
                FROM tasks
                WHERE workroot_id = ?
                ORDER BY task_id ASC
                """,
                (workroot.workroot_id,),
            ).fetchall()
            for task_id, title, status, task_kind, process_level in rows:
                entry_id = f"task:{workroot.workroot_id}:{task_id}"
                title = str(title or task_id)
                conn.execute(
                    """
                    INSERT INTO global_index_entries (entry_id, workroot_id, entry_type, title)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(entry_id) DO UPDATE SET
                      workroot_id=excluded.workroot_id,
                      entry_type=excluded.entry_type,
                      title=excluded.title
                    """,
                    (entry_id, workroot.workroot_id, "task", title),
                )
                records.append(
                    {
                        "entryId": entry_id,
                        "workrootId": workroot.workroot_id,
                        "entryType": "task",
                        "taskId": str(task_id),
                        "title": title,
                        "status": str(status or ""),
                        "taskKind": str(task_kind or ""),
                        "processLevel": str(process_level or ""),
                    }
                )
            conn.commit()
    _write_global_workroot_index(home / "global-index/tasks.index.jsonl", records)
    return len(records)


def query_global_task_index(ai_workroot_home: Path | str, *, query: str = "") -> list[dict[str, str]]:
    return _query_global_index(ai_workroot_home, "tasks.index.jsonl", query=query)


def refresh_global_asset_index(ai_workroot_home: Path | str) -> int:
    home = Path(ai_workroot_home).expanduser().resolve()
    records: list[dict[str, str]] = []
    for workroot in _registered_workroots(home):
        with sqlite3.connect(workroot.db_path) as conn:
            rows = conn.execute(
                """
                SELECT asset_id, asset_type, title, lifecycle_status, publication_status
                FROM assets
                WHERE workroot_id = ?
                ORDER BY asset_id ASC
                """,
                (workroot.workroot_id,),
            ).fetchall()
            for asset_id, asset_type, title, lifecycle_status, publication_status in rows:
                entry_id = f"asset:{workroot.workroot_id}:{asset_id}"
                title = str(title or asset_id)
                conn.execute(
                    """
                    INSERT INTO global_index_entries (entry_id, workroot_id, entry_type, title)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(entry_id) DO UPDATE SET
                      workroot_id=excluded.workroot_id,
                      entry_type=excluded.entry_type,
                      title=excluded.title
                    """,
                    (entry_id, workroot.workroot_id, "asset", title),
                )
                records.append(
                    {
                        "entryId": entry_id,
                        "workrootId": workroot.workroot_id,
                        "entryType": "asset",
                        "assetId": str(asset_id),
                        "assetType": str(asset_type or ""),
                        "title": title,
                        "lifecycleStatus": str(lifecycle_status or ""),
                        "publicationStatus": str(publication_status or ""),
                    }
                )
            conn.commit()
    _write_global_workroot_index(home / "global-index/assets.index.jsonl", records)
    return len(records)


def query_global_asset_index(ai_workroot_home: Path | str, *, query: str = "") -> list[dict[str, str]]:
    return _query_global_index(ai_workroot_home, "assets.index.jsonl", query=query)


def refresh_global_time_index(ai_workroot_home: Path | str) -> int:
    home = Path(ai_workroot_home).expanduser().resolve()
    records: list[dict[str, str]] = []
    for workroot in _registered_workroots(home):
        with sqlite3.connect(workroot.db_path) as conn:
            rows = conn.execute(
                """
                SELECT event_id, subject_type, subject_id, event_type, occurred_at
                FROM time_events
                WHERE workroot_id = ?
                ORDER BY occurred_at ASC, event_id ASC
                """,
                (workroot.workroot_id,),
            ).fetchall()
            for event_id, subject_type, subject_id, event_type, occurred_at in rows:
                entry_id = f"time:{workroot.workroot_id}:{event_id}"
                title = f"{event_type} {subject_type} {subject_id}"
                conn.execute(
                    """
                    INSERT INTO global_index_entries (entry_id, workroot_id, entry_type, title)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(entry_id) DO UPDATE SET
                      workroot_id=excluded.workroot_id,
                      entry_type=excluded.entry_type,
                      title=excluded.title
                    """,
                    (entry_id, workroot.workroot_id, "time_event", title),
                )
                records.append(
                    {
                        "entryId": entry_id,
                        "workrootId": workroot.workroot_id,
                        "entryType": "time_event",
                        "eventId": str(event_id),
                        "subjectType": str(subject_type),
                        "subjectId": str(subject_id),
                        "eventType": str(event_type),
                        "occurredAt": str(occurred_at),
                        "title": title,
                    }
                )
            conn.commit()
    _write_global_workroot_index(home / "global-index/time.index.jsonl", records)
    return len(records)


def query_global_time_index(ai_workroot_home: Path | str, *, query: str = "") -> list[dict[str, str]]:
    return _query_global_index(ai_workroot_home, "time.index.jsonl", query=query)


class _RegisteredWorkroot:
    def __init__(self, workroot_id: str, db_path: Path) -> None:
        self.workroot_id = workroot_id
        self.db_path = db_path


def _registered_workroots(home: Path) -> list[_RegisteredWorkroot]:
    workroots: list[_RegisteredWorkroot] = []
    for record in read_jsonl(home / "registry/workroots.jsonl"):
        workroot_id = str(record.get("workroot_id") or "")
        state_directory = Path(str(record.get("state_directory") or ""))
        if not workroot_id or not state_directory:
            continue
        db_path = state_directory / "cache/workroot.sqlite"
        initialize_workroot_sqlite(db_path)
        workroots.append(_RegisteredWorkroot(workroot_id, db_path))
    return workroots


def _query_global_index(ai_workroot_home: Path | str, filename: str, *, query: str = "") -> list[dict[str, str]]:
    home = Path(ai_workroot_home).expanduser().resolve()
    entries: list[dict[str, str]] = []
    needle = query.lower()
    for record in read_jsonl(home / "global-index" / filename):
        entry = {str(key): str(value) for key, value in record.items()}
        if needle and needle not in " ".join(entry.values()).lower():
            continue
        entries.append(entry)
    return entries


def _write_global_workroot_index(path: Path, records: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
