"""SQLite FTS provider for local text chunks."""

from __future__ import annotations

from dataclasses import dataclass
import re
import sqlite3


FALLBACK_SCAN_BATCH_SIZE = 200
FALLBACK_SCAN_MAX_ROWS = 2000


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


def search_fts(
    conn: sqlite3.Connection, workroot_id: str, query: str, *, limit: int = 10
) -> tuple[list[FtsMatch], str | None]:
    if not query.strip():
        return [], None
    if _needs_fallback_scan(query):
        return _fallback_scan(conn, workroot_id, query, limit=limit), None
    compiled_query = _compile_match_query(query)
    if not compiled_query:
        return _fallback_scan(conn, workroot_id, query, limit=limit), None
    try:
        rows = _fetch_rows(
            conn,
            """
            SELECT c.chunk_id, f.relative_path, c.body, f.source_type, f.source_id
            FROM indexed_chunks_fts
            JOIN indexed_chunks c ON c.chunk_id = indexed_chunks_fts.chunk_id
            JOIN indexed_files f ON f.file_id = c.file_id
            WHERE indexed_chunks_fts MATCH ?
              AND c.workroot_id = ?
            LIMIT ?
            """,
            (compiled_query, workroot_id, limit),
        )
    except sqlite3.OperationalError as exc:
        fallback_matches = _fallback_scan(conn, workroot_id, query, limit=limit)
        return (fallback_matches, None) if fallback_matches else ([], str(exc))
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


def search_fts_by_refs(
    conn: sqlite3.Connection, workroot_id: str, refs: tuple[str, ...], *, limit: int = 10
) -> tuple[list[FtsMatch], str | None]:
    if not refs:
        return [], None
    source_refs = _source_refs(conn, workroot_id, refs)
    if not source_refs:
        return [], None
    clauses = " OR ".join("(f.source_type = ? AND f.source_id = ?)" for _ in source_refs)
    params: list[object] = [workroot_id]
    for source_type, source_id in source_refs:
        params.extend([source_type, source_id])
    params.append(limit)
    try:
        rows = _fetch_rows(
            conn,
            f"""
            SELECT c.chunk_id, f.relative_path, c.body, f.source_type, f.source_id
            FROM indexed_chunks c
            JOIN indexed_files f ON f.file_id = c.file_id
            WHERE c.workroot_id = ?
              AND ({clauses})
            LIMIT ?
            """,
            tuple(params),
        )
    except sqlite3.OperationalError as exc:
        return [], str(exc)
    return [
        FtsMatch(
            chunk_id=str(row["chunk_id"]),
            relative_path=str(row["relative_path"]),
            body=str(row["body"]),
            source_type=str(row["source_type"] or ""),
            source_id=str(row["source_id"] or ""),
            reason="ref-scoped-evidence",
        )
        for row in rows
    ], None


def compile_safe_fts_query(query: str) -> str:
    return _compile_match_query(query)


def text_term_score(text: str, query: str) -> int:
    haystack = (text or "").lower()
    return sum(1 for term in fallback_text_terms(query) if term in haystack)


def fallback_text_terms(query: str, *, max_terms: int = 24) -> tuple[str, ...]:
    terms: list[str] = []
    seen: set[str] = set()
    for term in _ascii_terms(query):
        if term not in seen:
            terms.append(term)
            seen.add(term)
    for term in _unicode_ngrams(query):
        if term not in seen:
            terms.append(term)
            seen.add(term)
        if len(terms) >= max_terms:
            break
    return tuple(terms)


def _source_refs(conn: sqlite3.Connection, workroot_id: str, refs: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    values: list[tuple[str, str]] = []
    for ref in refs:
        source_type, separator, source_id = ref.partition(":")
        if separator != ":" or not source_type or not source_id:
            continue
        if source_type == "candidate":
            resolved = _candidate_source_ref(conn, workroot_id, source_id)
            if resolved is not None:
                values.append(resolved)
            continue
        values.append((source_type, source_id))
    return tuple(values)


def _candidate_source_ref(conn: sqlite3.Connection, workroot_id: str, candidate_id: str) -> tuple[str, str] | None:
    row = conn.execute(
        """
        SELECT source_type, source_id
        FROM context_candidates
        WHERE workroot_id = ?
          AND candidate_id = ?
          AND COALESCE(status, 'active') = 'active'
          AND (safety_policy IS NULL OR safety_policy = '' OR safety_policy NOT IN ('never-auto', 'needs-confirmation', 'sensitive'))
        LIMIT 1
        """,
        (workroot_id, candidate_id),
    ).fetchone()
    if row is None:
        return None
    source_type = str(row[0] or "")
    source_id = str(row[1] or "")
    if not source_type or not source_id:
        return None
    return source_type, source_id


def _fetch_rows(conn: sqlite3.Connection, query: str, params: tuple[object, ...]) -> list[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.row_factory = sqlite3.Row
    return cursor.execute(query, params).fetchall()


def _compile_match_query(query: str) -> str:
    terms = _ascii_terms(query)
    if not terms:
        return ""
    return " OR ".join(terms[:8])


def _ascii_terms(query: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"[A-Za-z0-9_]{3,}", query.lower()):
        term = match.group(0)
        if term in seen:
            continue
        terms.append(term)
        seen.add(term)
        if len(terms) >= 12:
            break
    return terms


def _fallback_scan(conn: sqlite3.Connection, workroot_id: str, query: str, *, limit: int) -> list[FtsMatch]:
    terms = fallback_text_terms(query)
    if not terms:
        return []
    scored: list[tuple[int, sqlite3.Row]] = []
    scan_limit = min(max(limit * 200, FALLBACK_SCAN_BATCH_SIZE), FALLBACK_SCAN_MAX_ROWS)
    offset = 0
    while offset < scan_limit:
        rows = _fetch_rows(
            conn,
            """
            SELECT c.chunk_id, f.relative_path, c.body, f.source_type, f.source_id
            FROM indexed_chunks c
            JOIN indexed_files f ON f.file_id = c.file_id
            WHERE c.workroot_id = ?
            ORDER BY c.rowid
            LIMIT ? OFFSET ?
            """,
            (workroot_id, min(FALLBACK_SCAN_BATCH_SIZE, scan_limit - offset), offset),
        )
        if not rows:
            break
        for row in rows:
            haystack = f"{row['relative_path']} {row['body']}".lower()
            score = sum(1 for term in terms if term in haystack)
            if score > 0:
                scored.append((score, row))
        offset += len(rows)
    scored.sort(key=lambda item: (-item[0], str(item[1]["relative_path"]), str(item[1]["chunk_id"])))
    return [
        FtsMatch(
            chunk_id=str(row["chunk_id"]),
            relative_path=str(row["relative_path"]),
            body=str(row["body"]),
            source_type=str(row["source_type"] or ""),
            source_id=str(row["source_id"] or ""),
            reason="file-fallback-scan",
        )
        for _score, row in scored[:limit]
    ]


def _needs_fallback_scan(value: str) -> bool:
    return bool(_unicode_ngrams(value))


def _unicode_ngrams(value: str) -> list[str]:
    runs: list[list[str]] = []
    current: list[str] = []
    for char in value:
        if ord(char) >= 128 and char.isalnum():
            current.append(char.lower())
            continue
        if current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    grams: list[str] = []
    for chars in runs:
        for size in (4, 3, 2):
            if len(chars) < size:
                continue
            for index in range(0, len(chars) - size + 1):
                grams.append("".join(chars[index : index + size]))
                if len(grams) >= 20:
                    return grams
    return grams
