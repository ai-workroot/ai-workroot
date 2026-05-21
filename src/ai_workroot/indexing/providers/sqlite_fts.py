"""SQLite FTS provider for local text chunks."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class FtsMatch:
    chunk_id: str
    relative_path: str
    body: str
    source_type: str = ""
    source_id: str = ""
    reason: str = "file-fts-match"


def index_file_chunk(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    file_id: str,
    chunk_id: str,
    relative_path: str,
    body: str,
    source_type: str = "asset",
    source_id: str = "",
) -> None:
    _ensure_indexed_file_source_columns(conn)
    resolved_source_id = source_id or relative_path
    conn.execute(
        """
        INSERT INTO indexed_files (file_id, workroot_id, relative_path, source_type, source_id)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(file_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          relative_path=excluded.relative_path,
          source_type=excluded.source_type,
          source_id=excluded.source_id
        """,
        (file_id, workroot_id, relative_path, source_type, resolved_source_id),
    )
    conn.execute(
        """
        INSERT INTO indexed_chunks (chunk_id, file_id, workroot_id, body)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(chunk_id) DO UPDATE SET
          file_id=excluded.file_id,
          workroot_id=excluded.workroot_id,
          body=excluded.body
        """,
        (chunk_id, file_id, workroot_id, body),
    )
    conn.execute("DELETE FROM indexed_chunks_fts WHERE chunk_id = ?", (chunk_id,))
    conn.execute("INSERT INTO indexed_chunks_fts (chunk_id, body) VALUES (?, ?)", (chunk_id, body))
    conn.commit()


def search_fts(conn: sqlite3.Connection, workroot_id: str, query: str, *, limit: int = 10) -> tuple[list[FtsMatch], str | None]:
    if not query.strip():
        return [], None
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT c.chunk_id, f.relative_path, c.body, f.source_type, f.source_id
            FROM indexed_chunks_fts
            JOIN indexed_chunks c ON c.chunk_id = indexed_chunks_fts.chunk_id
            JOIN indexed_files f ON f.file_id = c.file_id
            WHERE indexed_chunks_fts MATCH ?
              AND c.workroot_id = ?
            LIMIT ?
            """,
            (query, workroot_id, limit),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        return [], str(exc)
    return [
        FtsMatch(
            chunk_id=str(row["chunk_id"]),
            relative_path=str(row["relative_path"]),
            body=str(row["body"]),
            source_type=str(row["source_type"] or ""),
            source_id=str(row["source_id"] or ""),
        )
        for row in rows
    ], None


def _ensure_indexed_file_source_columns(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(indexed_files)").fetchall()}
    for name in ("source_type", "source_id"):
        if name not in columns:
            conn.execute(f"ALTER TABLE indexed_files ADD COLUMN {name} TEXT")
    conn.commit()
