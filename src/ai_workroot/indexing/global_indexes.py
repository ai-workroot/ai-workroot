"""Minimal global index maintenance for Workroot navigation."""

from __future__ import annotations

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
    home = Path(ai_workroot_home).expanduser().resolve()
    entries: list[dict[str, str]] = []
    for record in read_jsonl(home / "global-index/workroots.index.jsonl"):
        entry = {
            "entryId": str(record.get("entryId") or ""),
            "workrootId": str(record.get("workrootId") or ""),
            "entryType": str(record.get("entryType") or ""),
            "title": str(record.get("title") or ""),
        }
        if query and query.lower() not in f"{entry['workrootId']} {entry['title']}".lower():
            continue
        entries.append(entry)
    return entries


def _write_global_workroot_index(path: Path, records: list[dict[str, str]]) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
