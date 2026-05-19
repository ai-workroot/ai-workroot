#!/usr/bin/env python3
"""Local SQLite FTS indexing and retrieval for AI Workroot."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import sqlite3
from pathlib import Path


TEXT_SUFFIXES = {
    ".c",
    ".cc",
    ".csv",
    ".go",
    ".h",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".rs",
    ".sh",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class TextChunk:
    heading: str
    body: str
    ordinal: int


@dataclass(frozen=True)
class IndexResult:
    relative_path: str
    status: str
    reason: str
    chunk_count: int = 0


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def is_supported_text_path(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def is_binary_file(path: Path) -> bool:
    data = path.read_bytes()[:4096]
    if b"\x00" in data:
        return True
    if not data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def split_bounded_text(text: str, max_chars: int) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs or [text.strip()]:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            for start in range(0, len(paragraph), max_chars):
                chunks.append(paragraph[start : start + max_chars].strip())
            continue
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current.strip())
            current = paragraph
    if current:
        chunks.append(current.strip())
    return [chunk for chunk in chunks if chunk]


def chunk_plain_text(text: str, max_chars: int = 2000) -> list[TextChunk]:
    return [TextChunk("", body, ordinal) for ordinal, body in enumerate(split_bounded_text(text, max_chars))]


def chunk_markdown(text: str, max_chars: int = 2000) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    current_heading = ""
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines
        body = "\n".join(current_lines).strip()
        if body or current_heading:
            for bounded in split_bounded_text(body or current_heading, max_chars):
                chunks.append(TextChunk(current_heading, bounded, len(chunks)))
        current_lines = []

    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            flush()
            current_heading = match.group(2).strip()
            continue
        current_lines.append(line)
    flush()
    return chunks


def chunks_for_path(path: Path, text: str) -> list[TextChunk]:
    if path.suffix.lower() == ".md":
        return chunk_markdown(text)
    return chunk_plain_text(text)


def file_id_for(relative_path: str) -> str:
    return hashlib.sha1(relative_path.encode("utf-8")).hexdigest()


def chunk_id_for(file_id: str, ordinal: int) -> str:
    return f"{file_id}:{ordinal}"


def index_text_file(
    conn: sqlite3.Connection,
    workroot_id: str,
    root_directory: Path,
    path: Path,
    indexed_at: str,
) -> IndexResult:
    relative_path = path.resolve().relative_to(root_directory.resolve()).as_posix()
    if not is_supported_text_path(path):
        return IndexResult(relative_path, "skipped", "unsupported-file-type")
    if is_binary_file(path):
        return IndexResult(relative_path, "skipped", "binary-file")

    data = path.read_bytes()
    text = data.decode("utf-8")
    file_id = file_id_for(relative_path)
    title = path.stem
    chunks = chunks_for_path(path, text)

    conn.execute(
        """
        INSERT INTO indexed_files (
          file_id, workroot_id, relative_path, source_type, title, size_bytes,
          modified_at, content_hash, indexed_at, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(file_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          relative_path=excluded.relative_path,
          source_type=excluded.source_type,
          title=excluded.title,
          size_bytes=excluded.size_bytes,
          modified_at=excluded.modified_at,
          content_hash=excluded.content_hash,
          indexed_at=excluded.indexed_at,
          status=excluded.status
        """,
        (
            file_id,
            workroot_id,
            relative_path,
            "file",
            title,
            len(data),
            str(path.stat().st_mtime),
            content_hash(data),
            indexed_at,
            "indexed",
        ),
    )
    conn.execute("DELETE FROM indexed_chunks WHERE file_id = ?", (file_id,))
    conn.execute("DELETE FROM indexed_chunks_fts WHERE chunk_id LIKE ?", (f"{file_id}:%",))
    for chunk in chunks:
        chunk_id = chunk_id_for(file_id, chunk.ordinal)
        body_hash = hashlib.sha256(chunk.body.encode("utf-8")).hexdigest()
        conn.execute(
            """
            INSERT INTO indexed_chunks (
              chunk_id, file_id, workroot_id, relative_path, heading, ordinal,
              token_estimate, content_hash, indexed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chunk_id,
                file_id,
                workroot_id,
                relative_path,
                chunk.heading,
                chunk.ordinal,
                estimate_tokens(chunk.body),
                body_hash,
                indexed_at,
            ),
        )
        conn.execute(
            "INSERT INTO indexed_chunks_fts (chunk_id, title, heading, body) VALUES (?, ?, ?, ?)",
            (chunk_id, title, chunk.heading, chunk.body),
        )
    conn.commit()
    return IndexResult(relative_path, "indexed", "text-indexed", len(chunks))


def search_fts(conn: sqlite3.Connection, workroot_id: str, query: str, limit: int = 10) -> list[dict[str, object]]:
    if not query.strip():
        return []
    try:
        rows = conn.execute(
            """
            SELECT
              c.relative_path,
              c.heading,
              snippet(indexed_chunks_fts, 3, '[', ']', '...', 12) AS snippet,
              bm25(indexed_chunks_fts) AS score
            FROM indexed_chunks_fts
            JOIN indexed_chunks c ON c.chunk_id = indexed_chunks_fts.chunk_id
            WHERE indexed_chunks_fts MATCH ? AND c.workroot_id = ?
            ORDER BY score ASC
            LIMIT ?
            """,
            (query, workroot_id, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [
        {
            "relativePath": row[0],
            "heading": row[1] or "",
            "snippet": row[2] or "",
            "score": float(row[3]),
            "reason": "fts-match",
        }
        for row in rows
    ]
