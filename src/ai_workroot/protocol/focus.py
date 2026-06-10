"""Runtime-only sync interaction classification and focus resolution."""

from __future__ import annotations

from dataclasses import dataclass
import re
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
STARTABLE_DURABLE_WORK_KINDS = {
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
RELATIVE_FILE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9:/._-])"
    r"(?![A-Za-z][A-Za-z0-9+.-]*://)"
    r"(?:\./)?"
    r"(?:[^\s\"'<>|,\uFF0C;\uFF1B:\uFF1A)\uFF09\]\u3011}]+/)+"
    r"[^\s\"'<>|,\uFF0C;\uFF1B:\uFF1A)\uFF09\]\u3011}]+\.[A-Za-z0-9]{1,12}"
)


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
    candidate_refs: tuple[dict[str, str], ...] = ()
    ask_user_when: tuple[str, ...] = ()
    write_policy: Optional[dict[str, str]] = None


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

    if _looks_like_output_rule_request(query=query, signal=signal):
        return _workroot_capture_resolution(query, allowed_events=["state"])

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
        if signal.get("work_kind") == "inbox":
            if _has_signal_ref_binding(request):
                resolution = _resolve_continuation(conn, workroot_id=workroot_id, request=request)
                if resolution is not None:
                    return resolution
            return FocusResolution(
                kind="new_work",
                confidence="medium",
                summary=query,
                why="explicit temporary inbox boundary detected",
                directive_type="commit_required",
                directive_goal="Persist the user's temporary intent before creating inbox task facts.",
                directive_next_action="Call commit with a temporary intent event if this loose work should be tracked.",
                durable_commit_allowed=True,
                allowed_events=["intent"],
                required_before_stop=[],
                write_policy=_write_policy_for_signal(signal),
            )
        if _has_signal_ref_binding(request):
            resolution = _resolve_continuation(conn, workroot_id=workroot_id, request=request)
            if resolution is not None:
                return resolution
        declares_new_boundary = _declares_new_task_boundary(query=query, signal=signal)
        if _looks_like_asset_request(query=query, signal=signal):
            resolution = _resolve_asset_continuation(conn, workroot_id=workroot_id, request=request)
            if resolution is not None:
                return resolution
        if _looks_like_decision_request(query=query, signal=signal):
            resolution = _resolve_decision_continuation(conn, workroot_id=workroot_id, request=request)
            if resolution is not None:
                return resolution
        if signal.get("work_kind") != "inbox":
            single_normal = _single_active_role_candidate(conn, workroot_id=workroot_id, role="normal")
            if single_normal is not None and not _forces_new_root(signal):
                return _continuation_resolution(single_normal, confidence="medium")
        if signal.get("work_kind") in {"inbox", "task"} and not declares_new_boundary:
            existing = _resolve_existing_task_match(
                conn,
                workroot_id=workroot_id,
                request=request,
                role="inbox" if signal.get("work_kind") == "inbox" else "normal",
            )
            if existing is not None:
                return _continuation_resolution(existing, confidence="high")
            if signal.get("work_kind") == "task":
                single_normal = _single_active_role_candidate(conn, workroot_id=workroot_id, role="normal")
                if single_normal is not None:
                    return _continuation_resolution(single_normal, confidence="medium")
                if _active_role_count(conn, workroot_id=workroot_id, role="normal") > 0:
                    return _unbound_continuation_resolution(query)
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
            write_policy=_write_policy_for_signal(signal),
        )

    if _is_continuation(signal, request.reason):
        if _looks_like_asset_request(query=query, signal=signal):
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
            directive_type="refine_focus",
            directive_goal="Continue user-visible work without binding durable Workroot facts yet.",
            directive_next_action="Continue helping. Call sync again with clearer focus before committing durable facts.",
            durable_commit_allowed=False,
            allowed_events=[],
            required_before_stop=[],
        )

    if _has_durable_signal(signal):
        if _looks_like_asset_request(query=query, signal=signal):
            if "uncertain_task_boundary" in _signal_concerns(signal):
                return _workroot_capture_resolution(query, allowed_events=["asset"])
            resolution = _resolve_asset_continuation(conn, workroot_id=workroot_id, request=request)
            if resolution is not None:
                return resolution
        if _looks_like_decision_request(query=query, signal=signal):
            resolution = _resolve_decision_continuation(conn, workroot_id=workroot_id, request=request)
            if resolution is not None:
                return resolution
        if not _is_explicit_new_work(signal, query=query):
            resolution = _resolve_continuation(conn, workroot_id=workroot_id, request=request)
            if resolution is not None and resolution.kind == "continuation":
                return resolution
            if resolution is not None and resolution.kind == "ambiguous":
                return resolution
        return _unbound_durable_resolution(query)

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

    ref_resolution = _ref_focus_resolution(conn, workroot_id, request.work_signal or {})
    if ref_resolution is not None:
        return ref_resolution

    candidates = _focus_candidates(conn, workroot_id, query=request.query, signal=request.work_signal or {})
    if not candidates:
        return None
    single_role_candidate = _single_requested_role_candidate(candidates, signal=request.work_signal or {})
    if single_role_candidate is not None:
        return _continuation_resolution(single_role_candidate, confidence="medium")
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
        single_normal = _single_normal_default_for_non_inbox_signal(
            conn,
            workroot_id=workroot_id,
            signal=request.work_signal or {},
        )
        if single_normal is not None:
            return _continuation_resolution(single_normal, confidence="medium")
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
            candidate_refs=_candidate_refs(candidates),
        )
    confidence = "high" if top.score >= 50 else "medium"
    return _continuation_resolution(top, confidence=confidence)


def _single_normal_default_for_non_inbox_signal(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    signal: dict[str, Any],
) -> FocusCandidate | None:
    if signal.get("work_kind") == "inbox":
        return None
    return _single_active_role_candidate(conn, workroot_id=workroot_id, role="normal")


def _resolve_asset_continuation(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    request: SyncRequest,
) -> FocusResolution | None:
    resolution = _resolve_continuation(conn, workroot_id=workroot_id, request=request)
    if resolution is None or resolution.kind != "ambiguous":
        if resolution is not None and resolution.kind == "continuation":
            return _require_asset_before_handoff(resolution)
        return resolution
    candidates = _focus_candidates(conn, workroot_id, query=request.query, signal=request.work_signal or {})
    candidate = _clear_top_candidate(candidates, min_gap=3)
    if candidate is None:
        return _workroot_capture_resolution(request.query, allowed_events=["asset"])
    return _require_asset_before_handoff(_continuation_resolution(candidate, confidence="medium"))


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
        return resolution
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
    return resolution


def _unbound_continuation_resolution(query: str) -> FocusResolution:
    return FocusResolution(
        kind="ambiguous",
        confidence="none",
        summary=query,
        why="continuation requested but no reliable accepted focus was found",
        directive_type="refine_focus",
        directive_goal="Continue user-visible work without binding durable Workroot facts yet.",
        directive_next_action="Continue helping. Call sync again with clearer focus before committing durable facts.",
        durable_commit_allowed=False,
        allowed_events=[],
        required_before_stop=[],
    )


def _unbound_durable_resolution(query: str) -> FocusResolution:
    return FocusResolution(
        kind="ambiguous",
        confidence="none",
        summary=query,
        why="durable signal had no explicit new boundary or reliable task owner",
        directive_type="refine_focus",
        directive_goal="Continue user-visible work without creating or binding Workroot task facts yet.",
        directive_next_action=(
            "Continue helping. Call sync with phase=starting and work_kind=task before committing a new task, "
            "or provide refs/known_state before committing task progress."
        ),
        durable_commit_allowed=False,
        allowed_events=[],
        required_before_stop=[],
    )


def _ambiguous_focus_resolution(*, summary: str, why: str, candidates: list[FocusCandidate]) -> FocusResolution:
    return FocusResolution(
        kind="ambiguous",
        confidence="low",
        summary=summary,
        why=why,
        directive_type="continue_without_persistence",
        directive_goal="Continue user-visible work without binding durable Workroot facts yet.",
        directive_next_action="Continue helping. Ask or sync with clearer focus before committing durable facts.",
        durable_commit_allowed=False,
        allowed_events=[],
        required_before_stop=[],
        candidate_refs=_candidate_refs(candidates),
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


def _require_asset_before_handoff(resolution: FocusResolution) -> FocusResolution:
    return FocusResolution(
        kind=resolution.kind,
        confidence=resolution.confidence,
        summary=resolution.summary,
        why=resolution.why,
        directive_type=resolution.directive_type,
        directive_goal=resolution.directive_goal,
        directive_next_action=(
            "Create or update the user-visible file, commit it as an asset, then preserve continuation before stopping."
        ),
        durable_commit_allowed=resolution.durable_commit_allowed,
        allowed_events=list(CONTINUATION_EVENTS),
        required_before_stop=["asset", "handoff"],
        task_id=resolution.task_id,
        run_id=resolution.run_id,
        candidate_refs=resolution.candidate_refs,
        ask_user_when=resolution.ask_user_when,
        write_policy=resolution.write_policy,
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
            SELECT t.task_id, r.run_id, COALESCE(s.summary_text, r.output_summary, t.title, ''), t.role
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
            SELECT t.task_id, r.run_id, COALESCE(s.summary_text, r.output_summary, t.title, ''), t.role
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
        role=_normalize_role(row[3]),
    )


def _ref_focus_resolution(
    conn: sqlite3.Connection,
    workroot_id: str,
    signal: dict[str, Any],
) -> FocusResolution | None:
    candidates = _ref_focus_candidates(conn, workroot_id, signal)
    if not candidates:
        return None
    normal_resolution = _normal_ref_resolution_for_non_inbox_signal(
        conn,
        workroot_id,
        candidates,
        signal=signal,
    )
    if normal_resolution is not None:
        return normal_resolution
    if _refs_share_owner(candidates):
        return _continuation_resolution(_merge_ref_candidates(candidates), confidence="high")
    return _ambiguous_focus_resolution(
        summary=candidates[0].summary,
        why="work_signal refs resolved to multiple possible owners",
        candidates=candidates,
    )


def _normal_ref_resolution_for_non_inbox_signal(
    conn: sqlite3.Connection,
    workroot_id: str,
    candidates: list[FocusCandidate],
    *,
    signal: dict[str, Any],
) -> FocusResolution | None:
    if signal.get("work_kind") == "inbox":
        return None
    normal_candidates = [candidate for candidate in candidates if candidate.role != "inbox"]
    if normal_candidates:
        if _refs_share_owner(normal_candidates):
            return _continuation_resolution(_merge_ref_candidates(normal_candidates), confidence="high")
        return _ambiguous_focus_resolution(
            summary=normal_candidates[0].summary,
            why="work_signal refs resolved to multiple possible normal owners",
            candidates=normal_candidates,
        )
    single_normal = _single_active_role_candidate(conn, workroot_id=workroot_id, role="normal")
    if single_normal is None:
        return None
    return _continuation_resolution(single_normal, confidence="medium")


def _ref_focus_candidates(
    conn: sqlite3.Connection,
    workroot_id: str,
    signal: dict[str, Any],
) -> list[FocusCandidate]:
    refs = signal.get("refs")
    if not isinstance(refs, list):
        return []
    candidates: list[FocusCandidate] = []
    seen: set[tuple[str, str]] = set()
    for ref in refs:
        candidate = _candidate_for_ref(conn, workroot_id, str(ref or ""))
        if candidate is not None:
            key = (candidate.task_id, candidate.run_id or "")
            if key in seen:
                continue
            candidates.append(candidate)
            seen.add(key)
    return candidates


def _candidate_for_ref(conn: sqlite3.Connection, workroot_id: str, ref: str) -> FocusCandidate | None:
    prefix, separator, target_id = ref.partition(":")
    if separator != ":" or not target_id:
        return None
    if prefix == "task":
        return _known_state_candidate(conn, workroot_id, target_id, None)
    if prefix == "run":
        return _run_ref_candidate(conn, workroot_id, target_id)
    if prefix in {"asset", "decision"}:
        return _related_target_candidate(conn, workroot_id, target_type=prefix, target_id=target_id)
    if prefix == "chunk":
        return _chunk_ref_candidate(conn, workroot_id, target_id)
    if prefix == "candidate":
        return _context_candidate_ref_candidate(conn, workroot_id, target_id)
    return None


def _refs_share_owner(candidates: list[FocusCandidate]) -> bool:
    task_ids = {candidate.task_id for candidate in candidates}
    if len(task_ids) != 1:
        return False
    run_ids = {candidate.run_id for candidate in candidates if candidate.run_id}
    return len(run_ids) <= 1


def _merge_ref_candidates(candidates: list[FocusCandidate]) -> FocusCandidate:
    first = candidates[0]
    run_ids = [candidate.run_id for candidate in candidates if candidate.run_id]
    return FocusCandidate(
        task_id=first.task_id,
        run_id=run_ids[0] if run_ids else first.run_id,
        summary=first.summary,
        why="work_signal refs resolved to one accepted owner",
        score=max(candidate.score for candidate in candidates),
        role=first.role,
    )


def _run_ref_candidate(conn: sqlite3.Connection, workroot_id: str, run_id: str) -> FocusCandidate | None:
    row = conn.execute(
        """
        SELECT t.task_id, r.run_id, COALESCE(s.summary_text, r.output_summary, t.title, ''), t.role
        FROM task_runs r
        JOIN tasks t ON t.workroot_id = r.workroot_id AND t.task_id = r.task_id
        LEFT JOIN task_summaries s ON s.workroot_id = t.workroot_id AND s.task_id = t.task_id AND s.status = 'current'
        WHERE r.workroot_id = ? AND r.run_id = ?
          AND COALESCE(t.status, 'active') IN ('active', 'paused', 'blocked')
        LIMIT 1
        """,
        (workroot_id, run_id),
    ).fetchone()
    if row is None:
        return None
    return FocusCandidate(
        task_id=str(row[0]),
        run_id=_clean(row[1]),
        summary=str(row[2] or ""),
        why="work_signal ref matched an accepted run",
        score=90,
        role=_normalize_role(row[3]),
    )


def _related_target_candidate(
    conn: sqlite3.Connection,
    workroot_id: str,
    *,
    target_type: str,
    target_id: str,
) -> FocusCandidate | None:
    row = conn.execute(
        """
        SELECT t.task_id, r.run_id, COALESCE(s.summary_text, r.output_summary, t.title, ''), t.role
        FROM relationship_nodes target_node
        JOIN relationship_edges edge
          ON edge.workroot_id = target_node.workroot_id
         AND edge.to_node_id = target_node.node_id
         AND COALESCE(edge.status, 'active') = 'active'
        JOIN relationship_nodes task_node
          ON task_node.workroot_id = target_node.workroot_id
         AND task_node.node_id = edge.from_node_id
         AND task_node.target_type = 'task'
        JOIN tasks t
          ON t.workroot_id = task_node.workroot_id
         AND t.task_id = task_node.target_id
        LEFT JOIN task_runs r
          ON r.workroot_id = t.workroot_id
         AND r.task_id = t.task_id
         AND r.status IN ('active', 'incomplete')
        LEFT JOIN task_summaries s
          ON s.workroot_id = t.workroot_id
         AND s.task_id = t.task_id
         AND s.status = 'current'
        WHERE target_node.workroot_id = ?
          AND target_node.target_type = ?
          AND target_node.target_id = ?
          AND COALESCE(t.status, 'active') IN ('active', 'paused', 'blocked')
        ORDER BY edge.confidence DESC, t.updated_at DESC, r.started_at DESC
        LIMIT 1
        """,
        (workroot_id, target_type, target_id),
    ).fetchone()
    if row is None:
        return None
    return FocusCandidate(
        task_id=str(row[0]),
        run_id=_clean(row[1]),
        summary=str(row[2] or ""),
        why=f"work_signal ref matched a related {target_type} owner",
        score=90,
        role=_normalize_role(row[3]),
    )


def _chunk_ref_candidate(conn: sqlite3.Connection, workroot_id: str, chunk_id: str) -> FocusCandidate | None:
    row = conn.execute(
        """
        SELECT f.source_type, f.source_id
        FROM indexed_chunks c
        JOIN indexed_files f ON f.file_id = c.file_id
        WHERE c.workroot_id = ? AND c.chunk_id = ?
        LIMIT 1
        """,
        (workroot_id, chunk_id),
    ).fetchone()
    if row is None:
        return None
    source_type = str(row[0] or "")
    source_id = str(row[1] or "")
    if source_type in {"asset", "decision"} and source_id:
        return _related_target_candidate(conn, workroot_id, target_type=source_type, target_id=source_id)
    return None


def _context_candidate_ref_candidate(
    conn: sqlite3.Connection,
    workroot_id: str,
    candidate_id: str,
) -> FocusCandidate | None:
    row = conn.execute(
        """
        SELECT source_type, source_id
        FROM context_candidates
        WHERE workroot_id = ? AND candidate_id = ?
        LIMIT 1
        """,
        (workroot_id, candidate_id),
    ).fetchone()
    if row is None:
        return None
    source_type = str(row[0] or "")
    source_id = str(row[1] or "")
    if source_type in {"asset", "decision"} and source_id:
        return _related_target_candidate(conn, workroot_id, target_type=source_type, target_id=source_id)
    if source_type == "task" and source_id:
        return _known_state_candidate(conn, workroot_id, source_id, None)
    return None


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


def _candidate_refs(candidates: list[FocusCandidate], *, limit: int = 3) -> tuple[dict[str, str], ...]:
    ordered = sorted(candidates, key=lambda item: (-item.score, item.role, item.task_id, item.run_id or ""))
    refs: list[dict[str, str]] = []
    for candidate in ordered[:limit]:
        item = {
            "ref": f"task:{candidate.task_id}",
            "task_ref": candidate.task_id,
            "summary": candidate.summary,
            "why": candidate.why,
        }
        if candidate.run_id:
            item["run_ref"] = candidate.run_id
        if candidate.role:
            item["role"] = candidate.role
        refs.append(item)
    return tuple(refs)


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


def _single_requested_role_candidate(
    candidates: list[FocusCandidate], *, signal: dict[str, Any]
) -> FocusCandidate | None:
    role = "inbox" if signal.get("work_kind") == "inbox" else ""
    if not role:
        return None
    role_candidates = [candidate for candidate in candidates if candidate.role == role]
    if len(role_candidates) != 1:
        return None
    return role_candidates[0]


def _single_active_role_candidate(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    role: str,
) -> FocusCandidate | None:
    rows = conn.execute(
        """
        SELECT t.task_id, r.run_id, COALESCE(s.summary_text, r.output_summary, t.title, '')
        FROM tasks t
        LEFT JOIN task_runs r
          ON r.workroot_id = t.workroot_id
         AND r.task_id = t.task_id
         AND r.status IN ('active', 'incomplete')
        LEFT JOIN task_summaries s
          ON s.workroot_id = t.workroot_id
         AND s.task_id = t.task_id
         AND s.status = 'current'
        WHERE t.workroot_id = ?
          AND COALESCE(t.status, 'active') IN ('active', 'paused', 'blocked')
          AND COALESCE(t.role, 'task') = ?
        ORDER BY t.updated_at DESC, t.created_at DESC, r.started_at DESC
        LIMIT 2
        """,
        (workroot_id, role),
    ).fetchall()
    if len(rows) != 1:
        return None
    row = rows[0]
    return FocusCandidate(
        task_id=str(row[0]),
        run_id=_clean(row[1]),
        summary=str(row[2] or ""),
        why=f"single active {role} task matched structured work signal",
        score=55,
        role=role,
    )


def _active_role_count(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    role: str,
) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM tasks
        WHERE workroot_id = ?
          AND COALESCE(status, 'active') IN ('active', 'paused', 'blocked')
          AND COALESCE(role, 'task') = ?
        """,
        (workroot_id, role),
    ).fetchone()
    return int(row[0]) if row else 0


def _requests_inbox_focus(*, query: str, signal: dict[str, Any]) -> bool:
    if signal.get("work_kind") == "inbox":
        return True
    return False


def _has_explicit_focus_binding(request: SyncRequest) -> bool:
    if _clean(request.known_state.get("task_id")) or _clean(request.known_state.get("run_id")):
        return True
    return _has_signal_ref_binding(request)


def _has_signal_ref_binding(request: SyncRequest) -> bool:
    refs = request.work_signal.get("refs") if isinstance(request.work_signal, dict) else None
    return isinstance(refs, list) and any(str(ref or "").strip() for ref in refs)


def _normalize_role(value: object) -> str:
    return "inbox" if str(value or "").strip() == "inbox" else "normal"


def _write_policy_for_signal(signal: dict[str, Any]) -> Optional[dict[str, str]]:
    if signal.get("work_kind") != "inbox":
        return None
    return {
        "expected_start_work_persistence": "temporary",
        "expected_task_role": "inbox",
        "source": "work_signal",
    }


def _forces_new_root(signal: dict[str, Any]) -> bool:
    concerns = _signal_concerns(signal)
    return bool(concerns & {"new_root", "separate_root", "new_task_boundary"})


def _is_quick(query: str, signal: dict[str, Any], reason: str) -> bool:
    return (
        (signal.get("work_kind") == "quick" or signal.get("intended_action") == "answer")
        and reason not in {"continue", "after_error"}
        and not _has_durable_signal(signal)
    )


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
        signal.get("phase") == "starting"
        and signal.get("work_kind") in STARTABLE_DURABLE_WORK_KINDS
        and signal.get("intended_action") in DURABLE_INTENDED_ACTIONS
    ):
        return True
    return False


def _looks_like_asset_request(*, query: str, signal: dict[str, Any]) -> bool:
    if _has_explicit_relative_file_path(query):
        return True
    action = str(signal.get("intended_action") or "")
    if action not in {"edit", "preserve", "summarize"}:
        return False
    if signal.get("work_kind") == "authoring":
        return True
    return _signal_has_ref(signal, {"asset", "candidate", "chunk"})


def _has_explicit_relative_file_path(query: str) -> bool:
    return bool(RELATIVE_FILE_PATH_RE.search(query))


def _looks_like_handoff_request(*, query: str, signal: dict[str, Any]) -> bool:
    return _signal_has_ref(signal, {"handoff"})


def _looks_like_decision_request(*, query: str, signal: dict[str, Any]) -> bool:
    if signal.get("work_kind") == "decision" or signal.get("intended_action") == "decide":
        return True
    return signal.get("intended_action") == "preserve" and _signal_has_ref(signal, {"decision"})


def _looks_like_output_rule_request(*, query: str, signal: dict[str, Any]) -> bool:
    return signal.get("intended_action") == "preserve" and _signal_has_ref(signal, {"output_rule"})


def _declares_new_task_boundary(*, query: str, signal: dict[str, Any]) -> bool:
    return _is_explicit_new_work(signal, query="")


def _has_durable_signal(signal: dict[str, Any]) -> bool:
    if signal.get("work_kind") in DURABLE_WORK_KINDS:
        return True
    if signal.get("intended_action") in DURABLE_INTENDED_ACTIONS:
        return True
    return False


def _signal_has_ref(signal: dict[str, Any], prefixes: set[str]) -> bool:
    refs = signal.get("refs")
    if not isinstance(refs, list):
        return False
    for ref in refs:
        prefix, separator, _target_id = str(ref or "").partition(":")
        if separator == ":" and prefix in prefixes:
            return True
    return False


def _signal_concerns(signal: dict[str, Any]) -> set[str]:
    concerns = signal.get("concerns")
    if not isinstance(concerns, list):
        return set()
    return {str(concern or "") for concern in concerns}


def _clean(value: object) -> Optional[str]:
    text = str(value or "").strip()
    return text or None
