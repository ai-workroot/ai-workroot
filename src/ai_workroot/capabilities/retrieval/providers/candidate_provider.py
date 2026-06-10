"""SQLite Context Candidate provider."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Any

from ai_workroot.capabilities.retrieval.providers.sqlite_fts import compile_safe_fts_query, text_term_score


BLOCKED_SAFETY_POLICIES = {"never-auto", "needs-confirmation", "sensitive"}


@dataclass(frozen=True)
class CandidateMatch:
    candidate_id: str
    source_type: str
    source_id: str
    title: str
    summary: str
    importance: str
    context_policy: str
    safety_policy: str
    score: float
    reasons: tuple[str, ...]


def upsert_context_candidate(conn: sqlite3.Connection, payload: dict[str, Any]) -> None:
    _ensure_candidate_columns(conn)
    record = {
        "candidate_id": payload["candidate_id"],
        "workroot_id": payload["workroot_id"],
        "source_type": payload["source_type"],
        "source_id": payload["source_id"],
        "title": payload.get("title", ""),
        "summary": payload.get("summary", ""),
        "domains": payload.get("domains", ""),
        "importance": payload.get("importance", "normal"),
        "confidence": float(payload.get("confidence", 0.5)),
        "status": payload.get("status", "active"),
        "context_policy": payload.get("context_policy", "task-related"),
        "safety_policy": payload.get("safety_policy", ""),
        "token_estimate": int(payload.get("token_estimate", 0)),
        "updatedAt": payload.get("updatedAt", ""),
        "lastUsedAt": payload.get("lastUsedAt", ""),
        "use_count": int(payload.get("use_count", 0)),
    }
    conn.execute(
        """
        INSERT INTO context_candidates (
          candidate_id, workroot_id, source_type, source_id, title, summary,
          domains, importance, confidence, status, context_policy, safety_policy,
          token_estimate, updatedAt, lastUsedAt, use_count
        )
        VALUES (
          :candidate_id, :workroot_id, :source_type, :source_id, :title, :summary,
          :domains, :importance, :confidence, :status, :context_policy, :safety_policy,
          :token_estimate, :updatedAt, :lastUsedAt, :use_count
        )
        ON CONFLICT(candidate_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          source_type=excluded.source_type,
          source_id=excluded.source_id,
          title=excluded.title,
          summary=excluded.summary,
          domains=excluded.domains,
          importance=excluded.importance,
          confidence=excluded.confidence,
          status=excluded.status,
          context_policy=excluded.context_policy,
          safety_policy=excluded.safety_policy,
          token_estimate=excluded.token_estimate,
          updatedAt=excluded.updatedAt
        """,
        record,
    )
    conn.execute("DELETE FROM context_candidates_fts WHERE candidate_id = ?", (record["candidate_id"],))
    conn.execute(
        "INSERT INTO context_candidates_fts (candidate_id, title, summary, domains) VALUES (?, ?, ?, ?)",
        (record["candidate_id"], record["title"], record["summary"], record["domains"]),
    )
    conn.commit()


def query_context_candidates(
    conn: sqlite3.Connection, workroot_id: str, *, query: str = "", scope: str = "", limit: int = 50
) -> list[CandidateMatch]:
    _ensure_candidate_columns(conn)
    safe_rows = _fetch_rows(
        conn,
        """
        SELECT *
        FROM context_candidates
        WHERE workroot_id = ?
          AND COALESCE(status, 'active') = 'active'
          AND (safety_policy IS NULL OR safety_policy = '' OR safety_policy NOT IN ('never-auto', 'needs-confirmation', 'sensitive'))
        """,
        (workroot_id,),
    )
    fts_ids = _candidate_fts_ids(conn, query) if query.strip() else set()
    parsed_scope = _parse_scope(scope)
    matches: list[CandidateMatch] = []
    for row in safe_rows:
        if not _candidate_visible_in_scope(row, parsed_scope):
            continue
        reasons: list[str] = []
        score = _base_score(row)
        if row["context_policy"] == "always":
            reasons.append("always")
        if row["candidate_id"] in fts_ids:
            reasons.append("candidate-fts-match")
            score += 1.0
        term_score = _candidate_text_term_score(row, query)
        if term_score > 0 and row["candidate_id"] not in fts_ids:
            reasons.append("candidate-term-match")
            score += min(0.8, term_score * 0.2)
        if query and _text_contains(row["title"], query):
            reasons.append("title-query-match")
            score += 0.6
        if query and _text_contains(row["summary"], query):
            reasons.append("summary-query-match")
            score += 0.4
        if _candidate_matches_scope(row, parsed_scope):
            reasons.append("scope-match")
            score += 0.3
        if query.strip() and not reasons:
            continue
        matches.append(_candidate_from_row(row, score, tuple(reasons or ("recent",))))
    matches.sort(key=lambda candidate: (-candidate.score, candidate.candidate_id))
    return matches[:limit]


def query_context_candidates_by_refs(
    conn: sqlite3.Connection, workroot_id: str, refs: tuple[str, ...], *, scope: str = "", limit: int = 20
) -> list[CandidateMatch]:
    _ensure_candidate_columns(conn)
    if not refs:
        return []
    source_refs = _source_refs(refs)
    if not source_refs:
        return []
    clauses = " OR ".join("(source_type = ? AND source_id = ?)" for _ in source_refs)
    params: list[object] = [workroot_id]
    for source_type, source_id in source_refs:
        params.extend([source_type, source_id])
    params.append(limit)
    rows = _fetch_rows(
        conn,
        f"""
        SELECT *
        FROM context_candidates
        WHERE workroot_id = ?
          AND COALESCE(status, 'active') = 'active'
          AND (safety_policy IS NULL OR safety_policy = '' OR safety_policy NOT IN ('never-auto', 'needs-confirmation', 'sensitive'))
          AND ({clauses})
        LIMIT ?
        """,
        tuple(params),
    )
    parsed_scope = _parse_scope(scope)
    return [
        _candidate_from_row(row, _base_score(row) + 1.2, _ref_reasons(row, parsed_scope))
        for row in rows
        if _candidate_visible_in_scope(row, parsed_scope)
    ]


def _fetch_rows(conn: sqlite3.Connection, query: str, params: tuple[object, ...]) -> list[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.row_factory = sqlite3.Row
    return cursor.execute(query, params).fetchall()


def _ensure_candidate_columns(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(context_candidates)").fetchall()}
    expected = {
        "domains": "TEXT",
        "importance": "TEXT",
        "confidence": "REAL",
        "status": "TEXT",
        "context_policy": "TEXT",
        "safety_policy": "TEXT",
        "token_estimate": "INTEGER",
        "updatedAt": "TEXT",
        "lastUsedAt": "TEXT",
        "use_count": "INTEGER DEFAULT 0",
    }
    for name, column_type in expected.items():
        if name not in columns:
            conn.execute(f"ALTER TABLE context_candidates ADD COLUMN {name} {column_type}")
    fts_columns = {row[1] for row in conn.execute("PRAGMA table_info(context_candidates_fts)").fetchall()}
    if not {"candidate_id", "title", "summary", "domains"}.issubset(fts_columns):
        conn.execute("DROP TABLE IF EXISTS context_candidates_fts")
        conn.execute("CREATE VIRTUAL TABLE context_candidates_fts USING fts5(candidate_id, title, summary, domains)")
    conn.commit()


def _candidate_fts_ids(conn: sqlite3.Connection, query: str) -> set[str]:
    compiled_query = compile_safe_fts_query(query)
    if not compiled_query:
        return set()
    try:
        rows = conn.execute(
            "SELECT candidate_id FROM context_candidates_fts WHERE context_candidates_fts MATCH ?",
            (compiled_query,),
        ).fetchall()
    except sqlite3.OperationalError:
        return set()
    return {str(row[0]) for row in rows}


def _candidate_text_term_score(row: sqlite3.Row, query: str) -> int:
    if not query.strip():
        return 0
    return text_term_score(f"{row['title']} {row['summary']} {row['domains']}", query)


def _parse_scope(scope: str) -> tuple[str, str]:
    value = str(scope or "").strip()
    scope_type, separator, scope_id = value.partition(":")
    if separator != ":" or not scope_type or not scope_id:
        return "", ""
    return scope_type, scope_id


def _candidate_visible_in_scope(row: sqlite3.Row, parsed_scope: tuple[str, str]) -> bool:
    scope_type, scope_id = parsed_scope
    if scope_type != "task" or not scope_id:
        return True
    tokens = _domain_tokens(row)
    task_tokens = {token.removeprefix("task:") for token in tokens if token.startswith("task:")}
    legacy_task_tokens = {token for token in tokens if _looks_like_legacy_task_token(token)}
    if task_tokens or legacy_task_tokens:
        return scope_id in task_tokens or scope_id in legacy_task_tokens
    return True


def _candidate_matches_scope(row: sqlite3.Row, parsed_scope: tuple[str, str]) -> bool:
    scope_type, scope_id = parsed_scope
    if scope_type != "task" or not scope_id:
        return False
    tokens = _domain_tokens(row)
    return f"task:{scope_id}" in tokens or scope_id in tokens


def _domain_tokens(row: sqlite3.Row) -> set[str]:
    return {token for token in str(row["domains"] or "").split() if token}


def _looks_like_legacy_task_token(token: str) -> bool:
    return token.startswith("task-") or token.startswith("task_")


def _ref_reasons(row: sqlite3.Row, parsed_scope: tuple[str, str]) -> tuple[str, ...]:
    if _candidate_matches_scope(row, parsed_scope):
        return ("ref-match", "scope-match")
    return ("ref-match",)


def _source_refs(refs: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    values: list[tuple[str, str]] = []
    for ref in refs:
        source_type, separator, source_id = ref.partition(":")
        if separator == ":" and source_type and source_id:
            values.append((source_type, source_id))
    return tuple(values)


def _base_score(row: sqlite3.Row) -> float:
    return {
        "critical": 1.0,
        "high": 0.8,
        "normal": 0.5,
        "low": 0.2,
    }.get(str(row["importance"] or "normal"), 0.4)


def _candidate_from_row(row: sqlite3.Row, score: float, reasons: tuple[str, ...]) -> CandidateMatch:
    return CandidateMatch(
        candidate_id=str(row["candidate_id"]),
        source_type=str(row["source_type"] or ""),
        source_id=str(row["source_id"] or ""),
        title=str(row["title"] or ""),
        summary=str(row["summary"] or ""),
        importance=str(row["importance"] or "normal"),
        context_policy=str(row["context_policy"] or "task-related"),
        safety_policy=str(row["safety_policy"] or ""),
        score=score,
        reasons=reasons,
    )


def _text_contains(text: str, query: str) -> bool:
    return query.lower() in (text or "").lower()
