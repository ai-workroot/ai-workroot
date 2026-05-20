"""SQLite Context Candidate provider."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Any


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
        "updated_at": payload.get("updated_at", ""),
        "last_used_at": payload.get("last_used_at", ""),
        "use_count": int(payload.get("use_count", 0)),
    }
    conn.execute(
        """
        INSERT INTO context_candidates (
          candidate_id, workroot_id, source_type, source_id, title, summary,
          domains, importance, confidence, status, context_policy, safety_policy,
          token_estimate, updated_at, last_used_at, use_count
        )
        VALUES (
          :candidate_id, :workroot_id, :source_type, :source_id, :title, :summary,
          :domains, :importance, :confidence, :status, :context_policy, :safety_policy,
          :token_estimate, :updated_at, :last_used_at, :use_count
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
          updated_at=excluded.updated_at
        """,
        record,
    )
    conn.execute("DELETE FROM context_candidates_fts WHERE candidate_id = ?", (record["candidate_id"],))
    conn.execute(
        "INSERT INTO context_candidates_fts (candidate_id, title, summary, domains) VALUES (?, ?, ?, ?)",
        (record["candidate_id"], record["title"], record["summary"], record["domains"]),
    )
    conn.commit()


def query_context_candidates(conn: sqlite3.Connection, workroot_id: str, *, query: str = "", limit: int = 50) -> list[CandidateMatch]:
    _ensure_candidate_columns(conn)
    conn.row_factory = sqlite3.Row
    safe_rows = conn.execute(
        """
        SELECT *
        FROM context_candidates
        WHERE workroot_id = ?
          AND COALESCE(status, 'active') = 'active'
          AND (safety_policy IS NULL OR safety_policy = '' OR safety_policy NOT IN ('never-auto', 'needs-confirmation', 'sensitive'))
        """,
        (workroot_id,),
    ).fetchall()
    fts_ids = _candidate_fts_ids(conn, query) if query.strip() else set()
    matches: list[CandidateMatch] = []
    for row in safe_rows:
        reasons: list[str] = []
        score = _base_score(row)
        if row["context_policy"] == "always":
            reasons.append("always")
        if row["candidate_id"] in fts_ids:
            reasons.append("candidate-fts-match")
            score += 1.0
        if query and _text_contains(row["title"], query):
            reasons.append("title-query-match")
            score += 0.6
        if query and _text_contains(row["summary"], query):
            reasons.append("summary-query-match")
            score += 0.4
        matches.append(_candidate_from_row(row, score, tuple(reasons or ("recent",))))
    matches.sort(key=lambda candidate: (-candidate.score, candidate.candidate_id))
    return matches[:limit]


def _ensure_candidate_columns(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(context_candidates)").fetchall()}
    expected = {
        "domains": "TEXT",
        "importance": "TEXT",
        "confidence": "REAL",
        "status": "TEXT",
        "context_policy": "TEXT",
        "token_estimate": "INTEGER",
        "updated_at": "TEXT",
        "last_used_at": "TEXT",
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
    try:
        rows = conn.execute(
            "SELECT candidate_id FROM context_candidates_fts WHERE context_candidates_fts MATCH ?",
            (query,),
        ).fetchall()
    except sqlite3.OperationalError:
        return set()
    return {str(row[0]) for row in rows}


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
