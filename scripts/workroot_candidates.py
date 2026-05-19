#!/usr/bin/env python3
"""Materialized Context Candidate repository for AI Workroot."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3


ACTIVE_STATUS = "active"
AUTO_EXCLUDED_POLICIES = {"never-auto"}


@dataclass(frozen=True)
class ContextCandidate:
    candidate_id: str
    workroot_id: str
    source_type: str
    source_id: str
    title: str = ""
    summary: str = ""
    domains: str = ""
    related_tasks: str = ""
    related_assets: str = ""
    importance: str = "normal"
    confidence: float = 0.0
    status: str = ACTIVE_STATUS
    context_policy: str = "task-related"
    safety_policy: str = ""
    token_estimate: int = 0
    updated_at: str = ""
    last_used_at: str = ""


def candidate_from_row(row: sqlite3.Row) -> ContextCandidate:
    return ContextCandidate(
        candidate_id=row["candidate_id"],
        workroot_id=row["workroot_id"],
        source_type=row["source_type"],
        source_id=row["source_id"],
        title=row["title"] or "",
        summary=row["summary"] or "",
        domains=row["domains"] or "",
        related_tasks=row["related_tasks"] or "",
        related_assets=row["related_assets"] or "",
        importance=row["importance"] or "normal",
        confidence=float(row["confidence"] or 0.0),
        status=row["status"] or ACTIVE_STATUS,
        context_policy=row["context_policy"] or "task-related",
        safety_policy=row["safety_policy"] or "",
        token_estimate=int(row["token_estimate"] or 0),
        updated_at=row["updated_at"] or "",
        last_used_at=row["last_used_at"] or "",
    )


def upsert_context_candidate(conn: sqlite3.Connection, candidate: ContextCandidate) -> None:
    conn.execute(
        """
        INSERT INTO context_candidates (
          candidate_id, workroot_id, source_type, source_id, title, summary,
          domains, related_tasks, related_assets, importance, confidence,
          status, context_policy, safety_policy, token_estimate, updated_at, last_used_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(candidate_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          source_type=excluded.source_type,
          source_id=excluded.source_id,
          title=excluded.title,
          summary=excluded.summary,
          domains=excluded.domains,
          related_tasks=excluded.related_tasks,
          related_assets=excluded.related_assets,
          importance=excluded.importance,
          confidence=excluded.confidence,
          status=excluded.status,
          context_policy=excluded.context_policy,
          safety_policy=excluded.safety_policy,
          token_estimate=excluded.token_estimate,
          updated_at=excluded.updated_at
        """,
        (
            candidate.candidate_id,
            candidate.workroot_id,
            candidate.source_type,
            candidate.source_id,
            candidate.title,
            candidate.summary,
            candidate.domains,
            candidate.related_tasks,
            candidate.related_assets,
            candidate.importance,
            candidate.confidence,
            candidate.status,
            candidate.context_policy,
            candidate.safety_policy,
            candidate.token_estimate,
            candidate.updated_at,
            candidate.last_used_at,
        ),
    )
    conn.execute("DELETE FROM context_candidates_fts WHERE candidate_id = ?", (candidate.candidate_id,))
    conn.execute(
        "INSERT INTO context_candidates_fts (candidate_id, title, summary) VALUES (?, ?, ?)",
        (candidate.candidate_id, candidate.title, candidate.summary),
    )
    conn.commit()


def mark_candidate_status(conn: sqlite3.Connection, candidate_id: str, status: str, now: str) -> None:
    conn.execute(
        "UPDATE context_candidates SET status = ?, updated_at = ? WHERE candidate_id = ?",
        (status, now, candidate_id),
    )
    conn.commit()


def query_context_candidates(
    conn: sqlite3.Connection,
    workroot_id: str,
    include_never_auto: bool = False,
    limit: int | None = None,
) -> list[ContextCandidate]:
    conn.row_factory = sqlite3.Row
    params: list[object] = [workroot_id, ACTIVE_STATUS]
    policy_filter = ""
    if not include_never_auto:
        policy_filter = "AND context_policy NOT IN ({})".format(",".join("?" for _ in AUTO_EXCLUDED_POLICIES))
        params.extend(sorted(AUTO_EXCLUDED_POLICIES))
    limit_sql = ""
    if limit is not None:
        limit_sql = "LIMIT ?"
        params.append(limit)
    rows = conn.execute(
        f"""
        SELECT * FROM context_candidates
        WHERE workroot_id = ? AND status = ?
        {policy_filter}
        ORDER BY
          CASE importance
            WHEN 'critical' THEN 0
            WHEN 'high' THEN 1
            WHEN 'normal' THEN 2
            WHEN 'low' THEN 3
            ELSE 4
          END,
          updated_at DESC,
          candidate_id ASC
        {limit_sql}
        """,
        params,
    ).fetchall()
    return [candidate_from_row(row) for row in rows]


def mark_candidates_used(conn: sqlite3.Connection, candidate_ids: list[str], now: str) -> None:
    if not candidate_ids:
        return
    conn.executemany(
        "UPDATE context_candidates SET last_used_at = ? WHERE candidate_id = ?",
        [(now, candidate_id) for candidate_id in candidate_ids],
    )
    conn.commit()
