"""Context Card recall hint provider.

ContextRecallHint is the active package name for the Context Card recall
anchor. It stores recall metadata only; source content remains in the target
Asset, Task, WorkAction, Handoff, or other canonical object.
"""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from ai_workroot.core.release import ReleaseTargetRef
from ai_workroot.indexing.providers.candidate_provider import upsert_context_candidate
from ai_workroot.indexing.providers.release_provider import evaluate_release_targets


@dataclass(frozen=True)
class ContextRecallHint:
    hint_id: str
    workroot_id: str
    target_type: str
    target_id: str
    title: str
    summary: str = ""
    scope_type: str = ""
    scope_id: str = ""
    kind: str = "context-card"
    priority: str = "normal"
    recall_rule: str = "task-related"
    lifecycle_status: str = "active"
    origin: str = "manual"
    source_ref: str = ""
    created_at: str = ""
    updated_at: str = ""


def upsert_context_recall_hint(conn: sqlite3.Connection, hint: ContextRecallHint) -> None:
    conn.execute(
        """
        INSERT INTO context_recall_hints (
          hint_id, workroot_id, target_type, target_id, scope_type, scope_id,
          kind, title, summary, priority, recall_rule, lifecycle_status,
          origin, source_ref, created_at, updated_at
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
          updated_at=excluded.updated_at
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
    conn.commit()


def query_context_recall_hints(
    conn: sqlite3.Connection,
    workroot_id: str,
    *,
    query: str = "",
    limit: int = 50,
) -> list[ContextRecallHint]:
    params: list[object] = [workroot_id]
    where = [
        "h.workroot_id = ?",
        "COALESCE(h.lifecycle_status, 'active') = 'active'",
    ]
    if query.strip():
        hint_ids = _hint_fts_ids(conn, query)
        if not hint_ids:
            return []
        placeholders = ",".join("?" for _ in hint_ids)
        where.append(f"h.hint_id IN ({placeholders})")
        params.extend(sorted(hint_ids))
    params.append(limit)
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
    return [_hint_from_row(row) for row in rows]


def materialize_context_recall_hint(conn: sqlite3.Connection, hint: ContextRecallHint) -> str:
    candidate_id = f"hint:{hint.hint_id}"
    evaluation = evaluate_release_targets(
        conn,
        hint.workroot_id,
        (ReleaseTargetRef(target_type=hint.target_type, target_id=hint.target_id, workroot_id=hint.workroot_id),),
    )
    title = hint.title
    summary = hint.summary
    if evaluation.strictly_protected:
        placeholder = "[redacted]" if evaluation.level == "redacted" else "[deleted]"
        title = placeholder
        summary = placeholder
    upsert_context_candidate(
        conn,
        {
            "candidate_id": candidate_id,
            "workroot_id": hint.workroot_id,
            "source_type": "context_recall_hint",
            "source_id": hint.hint_id,
            "title": title,
            "summary": summary,
            "domains": hint.scope_id,
            "importance": hint.priority or "normal",
            "confidence": 0.9,
            "status": "active",
            "context_policy": hint.recall_rule or "task-related",
            "safety_policy": "",
            "token_estimate": 0,
            "updated_at": hint.updated_at,
        },
    )
    return candidate_id


def materialize_context_recall_hints(
    conn: sqlite3.Connection,
    workroot_id: str,
    *,
    query: str = "",
    limit: int = 50,
) -> list[str]:
    hints = query_context_recall_hints(conn, workroot_id, query=query, limit=limit)
    if query.strip() and not hints:
        hints = query_context_recall_hints(conn, workroot_id, query="", limit=min(limit, 10))
    return [
        materialize_context_recall_hint(conn, hint)
        for hint in hints
    ]


def _hint_fts_ids(conn: sqlite3.Connection, query: str) -> set[str]:
    try:
        rows = conn.execute(
            "SELECT hint_id FROM context_recall_hints_fts WHERE context_recall_hints_fts MATCH ?",
            (query,),
        ).fetchall()
    except sqlite3.OperationalError:
        return set()
    return {str(row[0]) for row in rows}


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
        created_at=str(row[_column(row, "created_at", 14)] or ""),
        updated_at=str(row[_column(row, "updated_at", 15)] or ""),
    )


def _column(row: sqlite3.Row | tuple[object, ...], name: str, index: int) -> str | int:
    if isinstance(row, sqlite3.Row):
        return name
    return index
