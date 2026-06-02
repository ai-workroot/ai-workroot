"""Derived per-Workroot runtime read views."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ai_workroot.state.environment import utc_now


CONTEXT_LATEST_PREVIEW_MAX_BYTES = 64 * 1024


def refresh_runtime_views(
    *,
    state_directory: Path,
    sqlite_path: Path,
    workroot_id: str,
) -> None:
    """Write rebuildable semantic read views from canonical SQLite facts."""

    if not sqlite_path.is_file():
        return
    state_directory = Path(state_directory)
    with sqlite3.connect(sqlite_path) as conn:
        conn.row_factory = sqlite3.Row
        current_task = _current_task(conn, workroot_id)
        active_tasks = _active_tasks(conn, workroot_id)
        current_handoff = _current_handoff(conn, workroot_id, current_task)
        _write_json(state_directory / "state/current.json", _state_view(conn, workroot_id, current_task))
        _write_json(state_directory / "tasks/current.json", current_task or {})
        _write_json(state_directory / "tasks/active.json", {"tasks": active_tasks})
        _write_json(state_directory / "handoffs/current.json", current_handoff or {})
        _write_text(state_directory / "handoffs/current.md", _handoff_markdown(current_handoff))
        _write_json(state_directory / "assets/manifest.json", _assets_manifest(conn, workroot_id))
        _write_json(state_directory / "relationships/summary.json", _relationships_summary(conn, workroot_id))
        _write_json(state_directory / "indexes/manifest.json", _indexes_manifest(conn, workroot_id))
        _write_json(state_directory / "diagnostics/protocol-friction.json", _protocol_friction(conn, workroot_id))


def write_context_runtime_view(
    *,
    state_directory: Path,
    rendered: str,
    trace: dict[str, Any],
) -> None:
    state_directory = Path(state_directory)
    latest_preview, preview_metadata = context_rendered_preview(rendered)
    trace_payload = dict(trace)
    trace_payload["latestContextPreview"] = preview_metadata
    _write_text(state_directory / "context/latest.md", latest_preview)
    _write_json(state_directory / "context/latest-trace.json", trace_payload)


def context_rendered_preview(
    rendered: str,
    *,
    max_bytes: int = CONTEXT_LATEST_PREVIEW_MAX_BYTES,
) -> tuple[str, dict[str, Any]]:
    rendered_bytes = len(rendered.encode("utf-8"))
    if rendered_bytes <= max_bytes:
        return rendered, {
            "truncated": False,
            "renderedBytes": rendered_bytes,
            "writtenBytes": rendered_bytes,
            "maxBytes": max_bytes,
        }

    marker = f"\n\n[truncated: rendered context was {rendered_bytes} bytes; preview limit is {max_bytes} bytes]\n"
    marker_bytes = marker.encode("utf-8")
    source_bytes = rendered.encode("utf-8")
    prefix_budget = max(max_bytes - len(marker_bytes), 0)
    preview = source_bytes[:prefix_budget].decode("utf-8", errors="ignore") + marker
    preview_bytes = len(preview.encode("utf-8"))
    if preview_bytes > max_bytes:
        preview = preview.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
        preview_bytes = len(preview.encode("utf-8"))
    return preview, {
        "truncated": True,
        "renderedBytes": rendered_bytes,
        "writtenBytes": preview_bytes,
        "maxBytes": max_bytes,
    }


def _current_task(conn: sqlite3.Connection, workroot_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT t.task_id, t.title, t.status, t.role, t.process_level, t.root_task_id,
               t.parent_task_id, t.updated_at, COALESCE(s.summary_text, '') AS summary,
               COALESCE(h.current_state, '') AS current_state,
               COALESCE(h.next_action, '') AS next_action,
               r.run_id, r.status AS run_status
        FROM tasks t
        LEFT JOIN task_summaries s ON s.workroot_id = t.workroot_id
          AND s.task_id = t.task_id AND s.status = 'current'
        LEFT JOIN handoffs h ON h.workroot_id = t.workroot_id
          AND h.task_id = t.task_id AND h.status = 'current'
        LEFT JOIN task_runs r ON r.workroot_id = t.workroot_id
          AND r.task_id = t.task_id AND r.status IN ('active', 'incomplete')
        WHERE t.workroot_id = ?
          AND COALESCE(t.status, 'active') IN ('active', 'paused', 'blocked')
        ORDER BY t.updated_at DESC, h.created_at DESC, r.started_at DESC
        LIMIT 1
        """,
        (workroot_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "workrootId": workroot_id,
        "taskId": str(row["task_id"]),
        "title": str(row["title"] or ""),
        "status": str(row["status"] or ""),
        "role": str(row["role"] or ""),
        "processLevel": str(row["process_level"] or ""),
        "rootTaskId": str(row["root_task_id"] or ""),
        "parentTaskId": str(row["parent_task_id"] or ""),
        "runId": str(row["run_id"] or ""),
        "runStatus": str(row["run_status"] or ""),
        "summary": str(row["summary"] or ""),
        "currentState": str(row["current_state"] or ""),
        "nextAction": str(row["next_action"] or ""),
        "updatedAt": str(row["updated_at"] or ""),
    }


def _active_tasks(conn: sqlite3.Connection, workroot_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT task_id, title, status, role, process_level, root_task_id, updated_at
        FROM tasks
        WHERE workroot_id = ?
          AND COALESCE(status, 'active') IN ('active', 'paused', 'blocked')
        ORDER BY updated_at DESC, created_at DESC
        LIMIT 50
        """,
        (workroot_id,),
    ).fetchall()
    return [
        {
            "taskId": str(row["task_id"]),
            "title": str(row["title"] or ""),
            "status": str(row["status"] or ""),
            "role": str(row["role"] or ""),
            "processLevel": str(row["process_level"] or ""),
            "rootTaskId": str(row["root_task_id"] or ""),
            "updatedAt": str(row["updated_at"] or ""),
        }
        for row in rows
    ]


def _current_handoff(
    conn: sqlite3.Connection,
    workroot_id: str,
    current_task: dict[str, Any] | None,
) -> dict[str, Any] | None:
    task_id = current_task.get("taskId") if current_task else None
    if not task_id:
        return None
    row = conn.execute(
        """
        SELECT handoff_id, task_id, run_id, title, current_state, next_action, created_at
        FROM handoffs
        WHERE workroot_id = ? AND task_id = ? AND status = 'current'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (workroot_id, task_id),
    ).fetchone()
    if row is None:
        return None
    return {
        "handoffId": str(row["handoff_id"]),
        "taskId": str(row["task_id"] or ""),
        "runId": str(row["run_id"] or ""),
        "title": str(row["title"] or ""),
        "currentState": str(row["current_state"] or ""),
        "nextAction": str(row["next_action"] or ""),
        "createdAt": str(row["created_at"] or ""),
    }


def _state_view(
    conn: sqlite3.Connection,
    workroot_id: str,
    current_task: dict[str, Any] | None,
) -> dict[str, Any]:
    counts = {
        table: int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE workroot_id = ?", (workroot_id,)).fetchone()[0])
        for table in ("tasks", "task_runs", "handoffs", "assets", "context_candidates")
    }
    return {
        "workrootId": workroot_id,
        "generatedAt": utc_now(),
        "currentTaskId": current_task.get("taskId") if current_task else "",
        "currentRunId": current_task.get("runId") if current_task else "",
        "counts": counts,
    }


def _assets_manifest(conn: sqlite3.Connection, workroot_id: str) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT asset_id, asset_type, title, lifecycle_status, current_path, content_hash, updatedAt
        FROM assets
        WHERE workroot_id = ?
        ORDER BY updatedAt DESC, asset_id
        """,
        (workroot_id,),
    ).fetchall()
    return {
        "workrootId": workroot_id,
        "assets": [
            {
                "assetId": str(row["asset_id"]),
                "assetType": str(row["asset_type"] or ""),
                "title": str(row["title"] or ""),
                "status": str(row["lifecycle_status"] or ""),
                "path": str(row["current_path"] or ""),
                "contentHash": str(row["content_hash"] or ""),
                "updatedAt": str(row["updatedAt"] or ""),
            }
            for row in rows
        ],
    }


def _relationships_summary(conn: sqlite3.Connection, workroot_id: str) -> dict[str, Any]:
    edge_rows = conn.execute(
        """
        SELECT relationship_type, COUNT(*) AS count
        FROM relationship_edges
        WHERE workroot_id = ?
        GROUP BY relationship_type
        ORDER BY relationship_type
        """,
        (workroot_id,),
    ).fetchall()
    return {
        "workrootId": workroot_id,
        "edgeCounts": {str(row["relationship_type"]): int(row["count"]) for row in edge_rows},
    }


def _indexes_manifest(conn: sqlite3.Connection, workroot_id: str) -> dict[str, Any]:
    return {
        "workrootId": workroot_id,
        "indexedFiles": _count(conn, "indexed_files", workroot_id),
        "indexedChunks": _count(conn, "indexed_chunks", workroot_id),
        "contextCandidates": _count(conn, "context_candidates", workroot_id),
        "updatedAt": utc_now(),
    }


def _protocol_friction(conn: sqlite3.Connection, workroot_id: str) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT status, COUNT(*) AS count
        FROM protocol_events
        WHERE workroot_id = ?
        GROUP BY status
        ORDER BY status
        """,
        (workroot_id,),
    ).fetchall()
    return {
        "workrootId": workroot_id,
        "eventStatuses": {str(row["status"]): int(row["count"]) for row in rows},
        "updatedAt": utc_now(),
    }


def _count(conn: sqlite3.Connection, table: str, workroot_id: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE workroot_id = ?", (workroot_id,)).fetchone()[0])


def _handoff_markdown(handoff: dict[str, Any] | None) -> str:
    if not handoff:
        return "# Current Handoff\n\nNo current handoff.\n"
    return (
        "# Current Handoff\n\n"
        f"- Task: {handoff['taskId']}\n"
        f"- Run: {handoff['runId']}\n"
        f"- Current state: {handoff['currentState']}\n"
        f"- Next action: {handoff['nextAction']}\n"
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
