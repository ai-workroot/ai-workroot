"""SQLite FTS provider for local text chunks."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class FtsMatch:
    chunk_id: str
    relative_path: str
    body: str
    reason: str = "file-fts-match"


def index_file_chunk(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    file_id: str,
    chunk_id: str,
    relative_path: str,
    body: str,
) -> None:
    conn.execute(
        """
        INSERT INTO indexed_files (file_id, workroot_id, relative_path)
        VALUES (?, ?, ?)
        ON CONFLICT(file_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          relative_path=excluded.relative_path
        """,
        (file_id, workroot_id, relative_path),
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
            SELECT c.chunk_id, f.relative_path, c.body
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
        )
        for row in rows
    ], None
