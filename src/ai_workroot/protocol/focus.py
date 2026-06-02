"""Runtime-only sync interaction classification and focus resolution."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Any, Optional

from ai_workroot.protocol.model import SyncRequest


CONTINUATION_EVENTS = ["progress", "handoff", "state", "asset", "decision"]
DURABLE_WORK_KINDS = {
    "inbox",
    "task",
    "investigation",
    "implementation",
    "review",
    "decision",
    "learning",
    "authoring",
    "operations",
}
DURABLE_INTENDED_ACTIONS = {
    "plan",
    "execute",
    "inspect",
    "diagnose",
    "edit",
    "test",
    "review",
    "decide",
    "summarize",
    "preserve",
}
FOCUS_STOPWORDS = {
    "about",
    "current",
    "decide",
    "decision",
    "make",
    "next",
    "should",
    "stable",
    "task",
    "work",
}


@dataclass(frozen=True)
class FocusResolution:
    kind: str
    confidence: str
    summary: str
    why: str
    directive_type: str
    directive_goal: Optional[str]
    directive_next_action: str
    durable_commit_allowed: bool
    allowed_events: list[str]
    required_before_stop: list[str]
    task_id: Optional[str] = None
    run_id: Optional[str] = None
    ask_user_when: tuple[str, ...] = ()


@dataclass(frozen=True)
class FocusCandidate:
    task_id: str
    run_id: Optional[str]
    summary: str
    why: str
    score: int
    role: str = "normal"


def resolve_sync_focus(conn: sqlite3.Connection, *, workroot_id: str, request: SyncRequest) -> FocusResolution:
    query = request.query.strip()
    signal = request.work_signal or {}
    if _is_guarded(signal, request.reason):
        return FocusResolution(
            kind="guarded_action",
            confidence="medium",
            summary=query,
            why="guarded protocol signal detected",
            directive_type="ask_user",
            directive_goal="Confirm the guarded Workroot action before durable persistence.",
            directive_next_action="Continue helping the user, but ask before publishing, deleting, releasing, or preserving sensitive facts.",
            durable_commit_allowed=False,
            allowed_events=[],
            required_before_stop=[],
            ask_user_when=("guarded_action",),
        )

    if request.reason == "startup":
        resolution = _resolve_continuation(conn, workroot_id=workroot_id, request=request)
        if resolution is not None:
            return resolution

    if not _query_requests_quick_answer(query) and _declares_new_task_boundary(query=query, signal={}):
        return FocusResolution(
            kind="new_work",
            confidence="medium",
            summary=query,
            why="durable work boundary detected in user request",
            directive_type="commit_required",
            directive_goal="Persist the user's intent before creating task facts.",
            directive_next_action="Call commit with an intent event if this work should be tracked.",
            durable_commit_allowed=True,
            allowed_events=["intent"],
            required_before_stop=[],
        )

    if _is_quick(query, signal, request.reason):
        return FocusResolution(
            kind="quick",
            confidence="medium",
            summary=query,
            why="quick answer signal with no durable work signal",
            directive_type="answer_without_persistence",
            directive_goal="Answer directly without creating persistent Workroot facts.",
            directive_next_action="Answer the user. If the discussion becomes durable work, call sync again.",
            durable_commit_allowed=False,
            allowed_events=[],
            required_before_stop=[],
        )

    if _is_explicit_new_work(signal, query=query):
        if _looks_like_handoff_request(query=query, signal=signal):
            resolution = _resolve_handoff_continuation(conn, workroot_id=workroot_id, request=request)
            if resolution is not None:
                return resolution
            return _unbound_continuation_resolution(query)
        declares_new_boundary = _declares_new_task_boundary(query=query, signal=signal)
        if _looks_like_asset_request(query=query, signal=signal) and not declares_new_boundary:
            if _looks_like_cross_task_asset_request(query=query):
                return _workroot_capture_resolution(query, allowed_events=["asset"])
            resolution = _resolve_asset_continuation(conn, workroot_id=workroot_id, request=request)
            if resolution is not None:
                return resolution
        if _looks_like_decision_request(query=query, signal=signal) and not declares_new_boundary:
            resolution = _resolve_decision_continuation(conn, workroot_id=workroot_id, request=request)
            if resolution is not None:
                return resolution
        if signal.get("work_kind") in {"inbox", "task"} and not declares_new_boundary:
            existing = _resolve_existing_task_match(
                conn,
                workroot_id=workroot_id,
                request=request,
                role="inbox" if signal.get("work_kind") == "inbox" else "normal",
            )
            if existing is not None:
                return _continuation_resolution(existing, confidence="high")
        return FocusResolution(
            kind="new_work",
            confidence="medium",
            summary=query,
            why="explicit new work boundary detected",
            directive_type="commit_required",
            directive_goal="Persist the user's intent before creating task facts.",
            directive_next_action="Call commit with an intent event if this work should be tracked.",
            durable_commit_allowed=True,
            allowed_events=["intent"],
            required_before_stop=[],
        )

    if _is_continuation(signal, request.reason):
        if _looks_like_asset_request(query=query, signal=signal):
            if _looks_like_cross_task_asset_request(query=query):
                resolution = _workroot_capture_resolution(query, allowed_events=["asset"])
            else:
                resolution = _resolve_asset_continuation(conn, workroot_id=workroot_id, request=request)
        elif _looks_like_decision_request(query=query, signal=signal):
            resolution = _resolve_decision_continuation(conn, workroot_id=workroot_id, request=request)
        else:
            resolution = _resolve_continuation(conn, workroot_id=workroot_id, request=request)
        if resolution is not None:
            return resolution
        return FocusResolution(
            kind="ambiguous",
            confidence="none",
            summary=query,
            why="continuation requested but no reliable accepted focus was found",
            directive_type="continue_without_persistence",
            directive_goal="Continue user-visible work without binding durable Workroot facts yet.",
            directive_next_action="Continue helping. Call sync again with clearer focus before committing durable facts.",
            durable_commit_allowed=False,
            allowed_events=[],
            required_before_stop=[],
        )

    if _has_durable_signal(signal):
        if not _is_explicit_new_work(signal, query=query):
            resolution = _resolve_continuation(conn, workroot_id=workroot_id, request=request)
            if resolution is not None and resolution.kind == "continuation":
                return resolution
            if resolution is not None and resolution.kind == "ambiguous":
                return resolution
        return FocusResolution(
            kind="new_work",
            confidence="medium",
            summary=query,
            why="durable work signal detected",
            directive_type="commit_required",
            directive_goal="Persist the user's intent before creating task facts.",
            directive_next_action="Call commit with an intent event if this work should be tracked.",
            durable_commit_allowed=True,
            allowed_events=["intent"],
            required_before_stop=[],
        )

    return FocusResolution(
        kind="quick",
        confidence="low",
        summary=query,
        why="no durable work signal detected",
        directive_type="answer_without_persistence",
        directive_goal="Answer directly without creating persistent Workroot facts.",
        directive_next_action="Answer the user. If the discussion becomes durable work, call sync again.",
        durable_commit_allowed=False,
        allowed_events=[],
        required_before_stop=[],
    )


def _resolve_continuation(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    request: SyncRequest,
) -> FocusResolution | None:
    known_task_id = _clean(request.known_state.get("task_id"))
    known_run_id = _clean(request.known_state.get("run_id"))
    if known_task_id:
        candidate = _known_state_candidate(conn, workroot_id, known_task_id, known_run_id)
        if candidate is not None:
            return _continuation_resolution(candidate, confidence="high")

    candidates = _focus_candidates(conn, workroot_id, query=request.query, signal=request.work_signal or {})
    if not candidates:
        return None
    inbox_candidate = _preferred_inbox_candidate(
        candidates,
        query=request.query,
        signal=request.work_signal or {},
    )
    if inbox_candidate is not None:
        return _continuation_resolution(inbox_candidate, confidence="high")
    candidates.sort(key=lambda item: (-item.score, item.task_id, item.run_id or ""))
    top = candidates[0]
    if len(candidates) > 1 and top.score - candidates[1].score < 12:
        return FocusResolution(
            kind="ambiguous",
            confidence="low",
            summary=top.summary,
            why="multiple accepted focus candidates are too close",
            directive_type="continue_without_persistence",
            directive_goal="Continue user-visible work without binding durable Workroot facts yet.",
            directive_next_action="Continue helping. Ask or sync with clearer focus before committing durable facts.",
            durable_commit_allowed=False,
            allowed_events=[],
            required_before_stop=[],
        )
    confidence = "high" if top.score >= 50 else "medium"
    return _continuation_resolution(top, confidence=confidence)


def _resolve_asset_continuation(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    request: SyncRequest,
) -> FocusResolution | None:
    resolution = _resolve_continuation(conn, workroot_id=workroot_id, request=request)
    if resolution is None or resolution.kind != "ambiguous":
        return resolution
    candidates = _focus_candidates(conn, workroot_id, query=request.query, signal=request.work_signal or {})
    candidate = _clear_top_candidate(candidates, min_gap=3)
    if candidate is None:
        return _workroot_capture_resolution(request.query, allowed_events=["asset"])
    return _continuation_resolution(candidate, confidence="medium")


def _resolve_decision_continuation(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    request: SyncRequest,
) -> FocusResolution | None:
    resolution = _resolve_continuation(conn, workroot_id=workroot_id, request=request)
    if resolution is None:
        return _workroot_capture_resolution(request.query, allowed_events=["decision"])
    if resolution.kind != "ambiguous":
        return resolution
    candidates = _focus_candidates(conn, workroot_id, query=request.query, signal=request.work_signal or {})
    candidate = _clear_top_candidate(candidates, min_gap=10)
    if candidate is None:
        return _workroot_capture_resolution(request.query, allowed_events=["decision"])
    return _continuation_resolution(candidate, confidence="medium")


def _resolve_handoff_continuation(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    request: SyncRequest,
) -> FocusResolution | None:
    resolution = _resolve_continuation(conn, workroot_id=workroot_id, request=request)
    if resolution is None:
        return None
    if resolution.kind != "ambiguous":
        return resolution
    candidates = _focus_candidates(conn, workroot_id, query=request.query, signal=request.work_signal or {})
    if not candidates:
        return resolution
    return _continuation_resolution(candidates[0], confidence="medium")


def _unbound_continuation_resolution(query: str) -> FocusResolution:
    return FocusResolution(
        kind="ambiguous",
        confidence="none",
        summary=query,
        why="continuation requested but no reliable accepted focus was found",
        directive_type="continue_without_persistence",
        directive_goal="Continue user-visible work without binding durable Workroot facts yet.",
        directive_next_action="Continue helping. Call sync again with clearer focus before committing durable facts.",
        durable_commit_allowed=False,
        allowed_events=[],
        required_before_stop=[],
    )


def _workroot_capture_resolution(query: str, *, allowed_events: list[str]) -> FocusResolution:
    return FocusResolution(
        kind="workroot_capture",
        confidence="low",
        summary=query,
        why="durable fact has no high-confidence task owner",
        directive_type="capture_workroot",
        directive_goal="Capture the durable fact without binding it to a task.",
        directive_next_action="Commit only the asset or decision fact. Sync again with clearer task focus before task progress.",
        durable_commit_allowed=True,
        allowed_events=list(allowed_events),
        required_before_stop=[],
    )


def _resolve_existing_task_match(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    request: SyncRequest,
    role: str = "normal",
) -> FocusCandidate | None:
    query = " ".join(
        part
        for part in (
            request.query,
            str((request.work_signal or {}).get("focus") or ""),
        )
        if part
    )
    query_tokens = {token for token in _semantic_tokens(query.lower()) if len(token) >= 4}
    if not query_tokens:
        return None
    candidates: list[FocusCandidate] = []
    role_clause = (
        "AND COALESCE(t.role, 'task') = 'inbox'" if role == "inbox" else "AND COALESCE(t.role, 'task') != 'inbox'"
    )
    for row in conn.execute(
        f"""
        SELECT t.task_id, r.run_id, COALESCE(s.summary_text, r.output_summary, t.title, ''),
               t.title, COALESCE(r.goal, ''), COALESCE(r.input_summary, '')
        FROM tasks t
        LEFT JOIN task_runs r ON r.workroot_id = t.workroot_id AND r.task_id = t.task_id
        LEFT JOIN task_summaries s ON s.workroot_id = t.workroot_id AND s.task_id = t.task_id AND s.status = 'current'
        WHERE t.workroot_id = ?
          AND COALESCE(t.status, 'active') IN ('active', 'paused', 'blocked')
          {role_clause}
        ORDER BY t.updated_at DESC, t.created_at DESC
        LIMIT 10
        """,
        (workroot_id,),
    ).fetchall():
        title = str(row[3] or "")
        summary = str(row[2] or "")
        goal = str(row[4] or "")
        input_summary = str(row[5] or "")
        haystack_tokens = {
            token for token in _semantic_tokens(f"{title} {summary} {goal} {input_summary}".lower()) if len(token) >= 4
        }
        overlap = query_tokens & haystack_tokens
        score = len(overlap) * 10
        if score < 20:
            continue
        candidates.append(
            FocusCandidate(
                task_id=str(row[0]),
                run_id=_clean(row[1]),
                summary=summary,
                why="existing task semantic match overrides a new-task signal",
                score=score,
                role=role,
            )
        )
    if role == "inbox":
        return _clear_top_candidate(candidates, min_gap=10)

    lowered_query = query.lower()
    for row in conn.execute(
        """
        SELECT t.task_id, r.run_id, COALESCE(s.summary_text, r.output_summary, t.title, ''),
               a.title, a.current_path
        FROM assets a
        JOIN relationship_nodes asset_node
          ON asset_node.workroot_id = a.workroot_id
         AND asset_node.target_type = 'asset'
         AND asset_node.target_id = a.asset_id
        JOIN relationship_edges edge
          ON edge.workroot_id = a.workroot_id
         AND edge.to_node_id = asset_node.node_id
         AND COALESCE(edge.status, 'active') = 'active'
        JOIN relationship_nodes task_node
          ON task_node.workroot_id = a.workroot_id
         AND task_node.node_id = edge.from_node_id
         AND task_node.target_type = 'task'
        JOIN tasks t
          ON t.workroot_id = a.workroot_id
         AND t.task_id = task_node.target_id
        LEFT JOIN task_runs r ON r.workroot_id = t.workroot_id AND r.task_id = t.task_id
        LEFT JOIN task_summaries s ON s.workroot_id = t.workroot_id AND s.task_id = t.task_id AND s.status = 'current'
        WHERE a.workroot_id = ?
          AND COALESCE(t.status, 'active') IN ('active', 'paused', 'blocked')
          AND COALESCE(t.role, 'task') != 'inbox'
        ORDER BY t.updated_at DESC, t.created_at DESC
        LIMIT 10
        """,
        (workroot_id,),
    ).fetchall():
        asset_title = str(row[3] or "")
        asset_path = str(row[4] or "")
        asset_tokens = {token for token in _semantic_tokens(f"{asset_title} {asset_path}".lower()) if len(token) >= 4}
        overlap = query_tokens & asset_tokens
        score = len(overlap) * 10
        if asset_path and asset_path.lower() in lowered_query:
            score += 60
        if score < 20:
            continue
        candidates.append(
            FocusCandidate(
                task_id=str(row[0]),
                run_id=_clean(row[1]),
                summary=str(row[2] or ""),
                why="existing task asset match overrides a new-task signal",
                score=score,
                role="normal",
            )
        )
    return _clear_top_candidate(candidates, min_gap=10)


def _continuation_resolution(candidate: FocusCandidate, *, confidence: str) -> FocusResolution:
    return FocusResolution(
        kind="continuation",
        confidence=confidence,
        summary=candidate.summary,
        why=candidate.why,
        directive_type="continue_task",
        directive_goal="Continue the current Workroot task.",
        directive_next_action="Continue the task and commit progress or handoff when a checkpoint is reached.",
        durable_commit_allowed=True,
        allowed_events=list(CONTINUATION_EVENTS),
        required_before_stop=["handoff"],
        task_id=candidate.task_id,
        run_id=candidate.run_id,
    )


def _known_state_candidate(
    conn: sqlite3.Connection,
    workroot_id: str,
    task_id: str,
    run_id: Optional[str],
) -> FocusCandidate | None:
    if run_id:
        row = conn.execute(
            """
            SELECT t.task_id, r.run_id, COALESCE(s.summary_text, r.output_summary, t.title, '')
            FROM tasks t
            JOIN task_runs r ON r.workroot_id = t.workroot_id AND r.task_id = t.task_id
            LEFT JOIN task_summaries s ON s.workroot_id = t.workroot_id AND s.task_id = t.task_id AND s.status = 'current'
            WHERE t.workroot_id = ? AND t.task_id = ? AND r.run_id = ?
              AND COALESCE(t.status, 'active') IN ('active', 'paused', 'blocked')
            LIMIT 1
            """,
            (workroot_id, task_id, run_id),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT t.task_id, r.run_id, COALESCE(s.summary_text, r.output_summary, t.title, '')
            FROM tasks t
            LEFT JOIN task_runs r ON r.workroot_id = t.workroot_id AND r.task_id = t.task_id
            LEFT JOIN task_summaries s ON s.workroot_id = t.workroot_id AND s.task_id = t.task_id AND s.status = 'current'
            WHERE t.workroot_id = ? AND t.task_id = ?
              AND COALESCE(t.status, 'active') IN ('active', 'paused', 'blocked')
            ORDER BY r.started_at DESC
            LIMIT 1
            """,
            (workroot_id, task_id),
        ).fetchone()
    if row is None:
        return None
    return FocusCandidate(
        task_id=str(row[0]),
        run_id=_clean(row[1]),
        summary=str(row[2] or ""),
        why="known_state matched an accepted task/run",
        score=60,
        role="normal",
    )


def _focus_candidates(
    conn: sqlite3.Connection,
    workroot_id: str,
    *,
    query: str,
    signal: dict[str, Any],
) -> list[FocusCandidate]:
    candidates: dict[tuple[str, str], FocusCandidate] = {}
    for row in conn.execute(
        """
        SELECT h.task_id, h.run_id, COALESCE(h.next_action, h.current_state, s.summary_text, t.title, ''),
               t.title, t.role, COALESCE(r.goal, ''), COALESCE(r.input_summary, '')
        FROM handoffs h
        JOIN tasks t ON t.workroot_id = h.workroot_id AND t.task_id = h.task_id
        LEFT JOIN task_runs r ON r.workroot_id = h.workroot_id AND r.task_id = h.task_id AND r.run_id = h.run_id
        LEFT JOIN task_summaries s ON s.workroot_id = h.workroot_id AND s.task_id = h.task_id AND s.status = 'current'
        WHERE h.workroot_id = ? AND h.status = 'current'
          AND COALESCE(t.status, 'active') IN ('active', 'paused', 'blocked')
        ORDER BY h.created_at DESC
        LIMIT 5
        """,
        (workroot_id,),
    ).fetchall():
        task_id = str(row[0])
        role = _normalize_role(row[4])
        if any(candidate.task_id == task_id for candidate in candidates.values()):
            continue
        _add_candidate(
            candidates,
            FocusCandidate(
                task_id=task_id,
                run_id=_clean(row[1]),
                summary=str(row[2] or ""),
                why="latest current handoff matched a continue-style request",
                score=50
                + _query_focus_boost(
                    query=query,
                    title=str(row[3] or ""),
                    summary=str(row[2] or ""),
                    role=role,
                    signal=signal,
                    goal=str(row[5] or ""),
                    input_summary=str(row[6] or ""),
                ),
                role=role,
            ),
        )
    for row in conn.execute(
        """
        SELECT t.task_id, r.run_id, COALESCE(s.summary_text, r.output_summary, t.title, ''),
               t.title, t.role, COALESCE(r.goal, ''), COALESCE(r.input_summary, '')
        FROM task_runs r
        JOIN tasks t ON t.workroot_id = r.workroot_id AND t.task_id = r.task_id
        LEFT JOIN task_summaries s ON s.workroot_id = r.workroot_id AND s.task_id = r.task_id AND s.status = 'current'
        WHERE r.workroot_id = ?
          AND r.status IN ('active', 'incomplete')
          AND COALESCE(t.status, 'active') IN ('active', 'paused', 'blocked')
        ORDER BY r.started_at DESC
        LIMIT 5
        """,
        (workroot_id,),
    ).fetchall():
        task_id = str(row[0])
        role = _normalize_role(row[4])
        if any(candidate.task_id == task_id for candidate in candidates.values()):
            continue
        _add_candidate(
            candidates,
            FocusCandidate(
                task_id=task_id,
                run_id=_clean(row[1]),
                summary=str(row[2] or ""),
                why="latest active or incomplete run matched a continue-style request",
                score=45
                + _query_focus_boost(
                    query=query,
                    title=str(row[3] or ""),
                    summary=str(row[2] or ""),
                    role=role,
                    signal=signal,
                    goal=str(row[5] or ""),
                    input_summary=str(row[6] or ""),
                ),
                role=role,
            ),
        )
    for row in conn.execute(
        """
        SELECT t.task_id, NULL, COALESCE(s.summary_text, t.title, ''), t.title, t.role
        FROM tasks t
        LEFT JOIN task_summaries s ON s.workroot_id = t.workroot_id AND s.task_id = t.task_id AND s.status = 'current'
        WHERE t.workroot_id = ?
          AND COALESCE(t.status, 'active') IN ('active', 'paused', 'blocked')
        ORDER BY t.updated_at DESC, t.created_at DESC
        LIMIT 5
        """,
        (workroot_id,),
    ).fetchall():
        task_id = str(row[0])
        role = _normalize_role(row[4])
        if any(candidate.task_id == task_id for candidate in candidates.values()):
            continue
        _add_candidate(
            candidates,
            FocusCandidate(
                task_id=task_id,
                run_id=_clean(row[1]),
                summary=str(row[2] or ""),
                why="latest active task matched startup or continuation request",
                score=35
                + _query_focus_boost(
                    query=query,
                    title=str(row[3] or ""),
                    summary=str(row[2] or ""),
                    role=role,
                    signal=signal,
                ),
                role=role,
            ),
        )
    return list(candidates.values())


def _query_focus_boost(
    *,
    query: str,
    title: str,
    summary: str,
    role: str,
    signal: dict[str, Any],
    goal: str = "",
    input_summary: str = "",
) -> int:
    focus_text = f"{query} {signal.get('focus') or ''}".lower()
    focus_tokens = _semantic_tokens(focus_text) - FOCUS_STOPWORDS
    title_tokens = _semantic_tokens(title.lower())
    summary_tokens = _semantic_tokens(summary.lower())
    goal_tokens = _semantic_tokens(goal.lower())
    input_tokens = _semantic_tokens(input_summary.lower())
    qualifier_tokens = _task_qualifier_tokens(focus_text)
    candidate_identity_tokens = title_tokens | goal_tokens | input_tokens
    score = 0
    qualifier_score = 0
    work_kind = str(signal.get("work_kind") or "")
    if role == "inbox":
        if work_kind == "inbox":
            score += 35
        elif "inbox" in focus_tokens:
            score += 25
    if role != "inbox" and work_kind in DURABLE_WORK_KINDS and work_kind != "inbox":
        score += 20
    for token in qualifier_tokens:
        if token in candidate_identity_tokens:
            qualifier_score += 50
    for token in focus_tokens:
        if len(token) < 4:
            continue
        if token in title_tokens:
            score += 24
        elif token in goal_tokens:
            score += 16
        elif token in input_tokens:
            score += 10
        elif token in summary_tokens:
            score += 4
    return min(score, 45) + min(qualifier_score, 100)


def _task_qualifier_tokens(value: str) -> set[str]:
    tokens = _semantic_token_sequence(value)
    boundary_terms = {"task", "work", "thread", "stream", "investigation", "review"}
    ignored = FOCUS_STOPWORDS | {
        "continue",
        "durable",
        "existing",
        "important",
        "normal",
        "resume",
        "temporary",
    }
    qualifiers: set[str] = set()
    for index, token in enumerate(tokens):
        if token not in boundary_terms:
            continue
        for candidate in tokens[max(0, index - 3) : index]:
            if len(candidate) >= 4 and candidate not in ignored:
                qualifiers.add(candidate)
    return qualifiers


def _semantic_token_sequence(value: str) -> list[str]:
    separators = ",.;:!?()[]{}<>`'\"/\\|-_\n\t"
    normalized = value
    for separator in separators:
        normalized = normalized.replace(separator, " ")
    tokens: list[str] = []
    for token in normalized.split():
        if not token:
            continue
        tokens.append(token)
        if len(token) > 4 and token.endswith("s") and not token.endswith(("ss", "sis", "us")):
            tokens.append(token[:-1])
    return tokens


def _semantic_tokens(value: str) -> set[str]:
    return set(_semantic_token_sequence(value))


def _add_candidate(candidates: dict[tuple[str, str], FocusCandidate], candidate: FocusCandidate) -> None:
    key = (candidate.task_id, candidate.run_id or "")
    existing = candidates.get(key)
    if existing is None or candidate.score > existing.score:
        candidates[key] = candidate


def _clear_top_candidate(candidates: list[FocusCandidate], *, min_gap: int) -> FocusCandidate | None:
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item.score, item.task_id, item.run_id or ""))
    top = candidates[0]
    if len(candidates) > 1 and top.score - candidates[1].score < min_gap:
        return None
    return top


def _preferred_inbox_candidate(
    candidates: list[FocusCandidate],
    *,
    query: str,
    signal: dict[str, Any],
) -> FocusCandidate | None:
    if not _requests_inbox_focus(query=query, signal=signal):
        return None
    inbox_candidates = [candidate for candidate in candidates if candidate.role == "inbox"]
    if not inbox_candidates:
        return None
    inbox_candidates.sort(key=lambda item: (-item.score, item.task_id, item.run_id or ""))
    top = inbox_candidates[0]
    return top if top.score >= 35 else None


def _requests_inbox_focus(*, query: str, signal: dict[str, Any]) -> bool:
    if signal.get("work_kind") == "inbox":
        return True
    tokens = _semantic_tokens(f"{query} {signal.get('focus') or ''}".lower())
    return "inbox" in tokens


def _normalize_role(value: object) -> str:
    return "inbox" if str(value or "").strip() == "inbox" else "normal"


def _is_quick(query: str, signal: dict[str, Any], reason: str) -> bool:
    if _query_requests_quick_answer(query):
        return True
    return (
        (signal.get("work_kind") == "quick" or signal.get("intended_action") == "answer")
        and reason not in {"continue", "after_error"}
        and not _has_durable_signal(signal)
    )


def _query_requests_quick_answer(query: str) -> bool:
    tokens = _semantic_tokens(query.lower())
    return "quick" in tokens and "answer" in tokens


def _is_continuation(signal: dict[str, Any], reason: str) -> bool:
    if reason in {"continue", "after_error"}:
        return True
    if signal.get("work_kind") == "continuation" or signal.get("phase") == "recovering":
        return True
    return False


def _is_guarded(signal: dict[str, Any], reason: str) -> bool:
    concerns = signal.get("concerns") if isinstance(signal.get("concerns"), list) else []
    return (
        reason == "before_high_risk_action" or signal.get("intended_action") == "publish" or "may_publish" in concerns
    )


def _is_explicit_new_work(signal: dict[str, Any], *, query: str) -> bool:
    if signal.get("phase") == "switching" and signal.get("work_kind") == "inbox":
        return True
    if (
        signal.get("phase") == "switching"
        and signal.get("work_kind") == "task"
        and signal.get("intended_action") in {"plan", "execute"}
        and (_clean(query) or _clean(signal.get("focus")))
    ):
        return True
    return False


def _looks_like_asset_request(*, query: str, signal: dict[str, Any]) -> bool:
    text = f"{query} {signal.get('focus') or ''}".lower()
    tokens = _semantic_tokens(text)
    has_asset_language = bool(tokens & {"asset", "file", "document", "output", "artifact"})
    has_preservation_language = bool(tokens & {"preserve", "save", "record", "index", "track"})
    has_path_language = _contains_user_file_reference(text)
    return has_path_language and (has_asset_language or has_preservation_language)


def _looks_like_cross_task_asset_request(*, query: str) -> bool:
    tokens = _semantic_tokens(query.lower())
    if "cross" in tokens and "task" in tokens:
        return True
    if "final" in tokens and bool(tokens & {"summary", "synthesis"}):
        return True
    return False


def _looks_like_handoff_request(*, query: str, signal: dict[str, Any]) -> bool:
    text = f"{query} {signal.get('focus') or ''}".lower()
    tokens = _semantic_tokens(text)
    return bool(tokens & {"handoff", "continuation"})


def _looks_like_decision_request(*, query: str, signal: dict[str, Any]) -> bool:
    if signal.get("work_kind") == "decision" or signal.get("intended_action") == "decide":
        return True
    text = f"{query} {signal.get('focus') or ''}".lower()
    tokens = _semantic_tokens(text)
    return bool(tokens & {"choose", "choice", "decide", "decision", "select"})


def _contains_user_file_reference(text: str) -> bool:
    extensions = (
        ".md",
        ".txt",
        ".csv",
        ".json",
        ".yaml",
        ".yml",
        ".pdf",
        ".docx",
        ".xlsx",
        ".png",
        ".jpg",
        ".jpeg",
        ".svg",
    )
    return any(extension in text for extension in extensions)


def _declares_new_task_boundary(*, query: str, signal: dict[str, Any]) -> bool:
    text = f"{query} {signal.get('focus') or ''}".lower()
    tokens = _semantic_tokens(text)
    if "new" in tokens and ("task" in tokens or "work" in tokens):
        return True
    phrases = (
        "start task",
        "start a task",
        "start durable",
        "open task",
        "open a task",
        "create task",
        "create a task",
        "create new task",
        "create a new task",
        "create work",
        "create a work",
    )
    if any(phrase in text for phrase in phrases):
        return True
    boundary_nouns = {"task", "work", "investigation", "implementation", "review"}
    if tokens & {"start", "open"} and tokens & boundary_nouns:
        return True
    if "create" in tokens and tokens & boundary_nouns:
        if not _contains_user_file_reference(text):
            return True
        return bool(tokens & {"durable", "investigation", "implementation", "review"})
    return False


def _has_durable_signal(signal: dict[str, Any]) -> bool:
    if signal.get("work_kind") in DURABLE_WORK_KINDS:
        return True
    if signal.get("intended_action") in DURABLE_INTENDED_ACTIONS:
        return True
    return False


def _clean(value: object) -> Optional[str]:
    text = str(value or "").strip()
    return text or None
