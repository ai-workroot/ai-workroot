"""Context Card recall hint provider.

ContextRecallHint is the active package name for the Context Card recall
anchor. It stores recall metadata only; source content remains in the target
Asset, Task, WorkAction, Handoff, or other canonical object.

Release governance is intentionally not implemented here. Context Control must
coordinate Release Control before writing recall hints into ordinary context.
"""

from __future__ import annotations

import sqlite3

from ai_workroot.capabilities.retrieval.model import ContextRecallHint
from ai_workroot.capabilities.retrieval.providers.sqlite_fts import compile_safe_fts_query, text_term_score


def upsert_context_recall_hint(conn: sqlite3.Connection, hint: ContextRecallHint) -> None:
    conn.execute(
        """
        INSERT INTO context_recall_hints (
          hint_id, workroot_id, target_type, target_id, scope_type, scope_id,
          kind, title, summary, priority, recall_rule, lifecycle_status,
          origin, source_ref, createdAt, updatedAt
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(hint_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          target_type=excluded.target_type,
          target_id=excluded.target_id,
          scope_type=excluded.scope_type,
          scope_id=excluded.scope_id,
          kind=excluded.kind,
          title=excluded.title,
          summary=excluded.summary,
          priority=excluded.priority,
          recall_rule=excluded.recall_rule,
          lifecycle_status=excluded.lifecycle_status,
          origin=excluded.origin,
          source_ref=excluded.source_ref,
          updatedAt=excluded.updatedAt
        """,
        (
            hint.hint_id,
            hint.workroot_id,
            hint.target_type,
            hint.target_id,
            hint.scope_type,
            hint.scope_id,
            hint.kind,
            hint.title,
            hint.summary,
            hint.priority,
            hint.recall_rule,
            hint.lifecycle_status,
            hint.origin,
            hint.source_ref,
            hint.created_at,
            hint.updated_at,
        ),
    )
    conn.execute("DELETE FROM context_recall_hints_fts WHERE hint_id = ?", (hint.hint_id,))
    conn.execute(
        "INSERT INTO context_recall_hints_fts (hint_id, title, summary) VALUES (?, ?, ?)",
        (hint.hint_id, hint.title, hint.summary),
    )


def query_context_recall_hints(
    conn: sqlite3.Connection,
    workroot_id: str,
    *,
    query: str = "",
    scope: str = "",
    limit: int = 50,
) -> list[ContextRecallHint]:
    params: list[object] = [workroot_id]
    where = [
        "h.workroot_id = ?",
        "COALESCE(h.lifecycle_status, 'active') = 'active'",
    ]
    parsed_scope = _parse_scope(scope)
    if parsed_scope[0] == "task":
        where.append(
            """
            (
              COALESCE(h.scope_type, '') IN ('', 'workroot')
              OR (h.scope_type = 'task' AND h.scope_id = ?)
            )
            """
        )
        params.append(parsed_scope[1])
    row_limit = max(limit * 20, 100) if query.strip() else limit
    params.append(row_limit)
    rows = conn.execute(
        f"""
        SELECT h.*
        FROM context_recall_hints h
        WHERE {" AND ".join(where)}
        ORDER BY
          CASE COALESCE(h.priority, 'normal')
            WHEN 'critical' THEN 0
            WHEN 'high' THEN 1
            WHEN 'normal' THEN 2
            WHEN 'low' THEN 3
            ELSE 4
          END,
          h.hint_id ASC
        LIMIT ?
        """,
        params,
    ).fetchall()
    if not query.strip():
        return [_hint_from_row(row) for row in rows[:limit]]
    hint_ids = _hint_fts_ids(conn, query)
    scored_rows: list[tuple[float, sqlite3.Row | tuple[object, ...]]] = []
    for row in rows:
        score = _hint_query_score(row, query, hint_ids)
        if score <= 0 and str(row[_column(row, "recall_rule", 10)] or "") != "always":
            continue
        scored_rows.append((score, row))
    scored_rows.sort(key=lambda item: (-item[0], _hint_sort_key(item[1])))
    return [_hint_from_row(row) for _score, row in scored_rows[:limit]]


def _hint_fts_ids(conn: sqlite3.Connection, query: str) -> set[str]:
    compiled_query = compile_safe_fts_query(query)
    if not compiled_query:
        return set()
    try:
        rows = conn.execute(
            "SELECT hint_id FROM context_recall_hints_fts WHERE context_recall_hints_fts MATCH ?",
            (compiled_query,),
        ).fetchall()
    except sqlite3.OperationalError:
        return set()
    return {str(row[0]) for row in rows}


def _hint_query_score(
    row: sqlite3.Row | tuple[object, ...],
    query: str,
    hint_ids: set[str],
) -> float:
    score = 0.0
    if str(row[_column(row, "hint_id", 0)]) in hint_ids:
        score += 1.0
    term_score = text_term_score(
        f"{row[_column(row, 'title', 7)] or ''} {row[_column(row, 'summary', 8)] or ''}",
        query,
    )
    if term_score > 0:
        score += min(0.8, term_score * 0.2)
    return score


def _hint_sort_key(row: sqlite3.Row | tuple[object, ...]) -> tuple[int, str]:
    priority = str(row[_column(row, "priority", 9)] or "normal")
    priority_order = {
        "critical": 0,
        "high": 1,
        "normal": 2,
        "low": 3,
    }.get(priority, 4)
    return priority_order, str(row[_column(row, "hint_id", 0)])


def _parse_scope(scope: str) -> tuple[str, str]:
    value = str(scope or "").strip()
    scope_type, separator, scope_id = value.partition(":")
    if separator != ":" or not scope_type or not scope_id:
        return "", ""
    return scope_type, scope_id


def _hint_from_row(row: sqlite3.Row | tuple[object, ...]) -> ContextRecallHint:
    return ContextRecallHint(
        hint_id=str(row[_column(row, "hint_id", 0)]),
        workroot_id=str(row[_column(row, "workroot_id", 1)]),
        target_type=str(row[_column(row, "target_type", 2)]),
        target_id=str(row[_column(row, "target_id", 3)]),
        scope_type=str(row[_column(row, "scope_type", 4)] or ""),
        scope_id=str(row[_column(row, "scope_id", 5)] or ""),
        kind=str(row[_column(row, "kind", 6)] or "context-card"),
        title=str(row[_column(row, "title", 7)] or ""),
        summary=str(row[_column(row, "summary", 8)] or ""),
        priority=str(row[_column(row, "priority", 9)] or "normal"),
        recall_rule=str(row[_column(row, "recall_rule", 10)] or "task-related"),
        lifecycle_status=str(row[_column(row, "lifecycle_status", 11)] or "active"),
        origin=str(row[_column(row, "origin", 12)] or "manual"),
        source_ref=str(row[_column(row, "source_ref", 13)] or ""),
        created_at=str(row[_column(row, "createdAt", 14)] or ""),
        updated_at=str(row[_column(row, "updatedAt", 15)] or ""),
    )


def _column(row: sqlite3.Row | tuple[object, ...], name: str, index: int) -> str | int:
    if isinstance(row, sqlite3.Row):
        return name
    return index
