#!/usr/bin/env python3
"""Rebuild the optional AI Workroot SQLite index from runtime registries."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path


DB_PATH = Path(".workroot/runtime/data/indexes/workroot.sqlite")
SCHEMA_PATH = Path(".workroot/runtime/data/indexes/schema.sql")
INDEX_DIR = Path(".workroot/runtime/index")

TABLES = [
    ("task_registry.csv", "tasks"),
    ("artifact_registry.csv", "artifacts"),
    ("decision_registry.csv", "decisions"),
    ("mind_registry.csv", "mind_entries"),
    ("link_registry.csv", "links"),
]


def load_csv(conn: sqlite3.Connection, csv_path: Path, table: str) -> None:
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not reader.fieldnames:
        return
    table_columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    columns = [column for column in reader.fieldnames if column in table_columns]
    if not columns:
        return
    placeholders = ", ".join(["?"] * len(columns))
    column_sql = ", ".join(columns)
    conn.execute(f"DELETE FROM {table}")
    if rows:
        conn.executemany(
            f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})",
            [[row.get(col, "") or None for col in columns] for row in rows],
        )


def main() -> None:
    root = Path.cwd()
    schema = root / SCHEMA_PATH
    db = root / DB_PATH
    if not schema.exists():
        raise SystemExit(f"schema not found: {SCHEMA_PATH}")

    db.parent.mkdir(parents=True, exist_ok=True)
    if db.exists():
        db.unlink()

    conn = sqlite3.connect(db)
    try:
        conn.executescript(schema.read_text(encoding="utf-8"))
        for csv_name, table in TABLES:
            csv_path = root / INDEX_DIR / csv_name
            if csv_path.exists():
                load_csv(conn, csv_path, table)
        conn.commit()
    finally:
        conn.close()

    print(DB_PATH.as_posix())


if __name__ == "__main__":
    main()
