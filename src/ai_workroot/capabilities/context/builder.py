"""Context Control runtime flow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import re
import sqlite3
import time
from pathlib import Path
import uuid

from ai_workroot.capabilities.context.control import workroot_guidance_text
from ai_workroot.capabilities.context.strategy import (
    DisclosureLevel,
    FocusBoundary,
    LeaseFocusSignal,
    RecallPlan,
    StrategyRequest,
    build_recall_plan,
)
from ai_workroot.capabilities.release.evaluation import evaluate_release_targets
from ai_workroot.capabilities.release.filter import (
    FtsReleaseFilterReport,
    RelationshipReleaseFilterReport,
    ReleaseFilterReport,
    filter_fts_matches_for_release,
    filter_relationship_signals_for_release,
    load_release_filter_report,
)
from ai_workroot.capabilities.release.model import ReleaseTargetRef
from ai_workroot.capabilities.relationships.model import RelationshipSignal
from ai_workroot.capabilities.relationships.operations import relationship_signals_for_source_refs
from ai_workroot.capabilities.retrieval.model import ContextRecallHint
from ai_workroot.capabilities.retrieval.providers.candidate_provider import (
    CandidateMatch,
    query_context_candidates_by_refs,
    query_context_candidates,
    upsert_context_candidate,
)
from ai_workroot.capabilities.retrieval.providers.context_recall_hint_provider import (
    query_context_recall_hints,
)
from ai_workroot.capabilities.retrieval.providers.sqlite_fts import FtsMatch, search_fts, search_fts_by_refs
from ai_workroot.state.environment import (
    ContextControlConfig,
    environment_now,
    load_environment_time_config,
    load_context_control_config,
    utc_now,
)
from ai_workroot.state.jsonl import append_jsonl
from ai_workroot.state.registry import find_workroot_by_cwd
from ai_workroot.state.runtime_views import context_rendered_preview, write_context_runtime_view
from ai_workroot.state.versions import load_state_versions


DEFAULT_TARGET_TOKENS = 1200
DEFAULT_HARD_TOKEN_LIMIT = 2400
TOKEN_USAGE_PLACEHOLDER = "__AI_WORKROOT_TOKEN_USAGE__"
CONTEXT_RUNTIME_RETENTION_LIMIT = 100


@dataclass(frozen=True)
class ContextRequest:
    agent: str
    cwd: Path | str = "."
    query: str = ""
    mode: str = "standard"
    target_tokens: int | None = None
    hard_token_limit: int | None = None
    debug: bool = False
    budget_source: str = "default"
    startup_response: dict[str, object] | None = None
    startup_guidance: str = ""
    work_signal: dict[str, object] | None = None


@dataclass(frozen=True)
class ContinuityContext:
    focus: str = ""
    confidence: str = ""
    why: str = ""
    task_brief: str = ""
    current_state: str = ""
    next_action: str = ""
    active_task_id: str = ""
    active_task_title: str = ""
    active_task_status: str = ""
    active_task_kind: str = ""
    active_task_process_level: str = ""
    checkpoint_id: str = ""
    checkpoint_status: str = ""
    handoff_id: str = ""
    handoff_title: str = ""

    def has_content(self) -> bool:
        return bool(self.active_task_id or self.checkpoint_id or self.handoff_id)

    def trace_payload(self) -> dict[str, str]:
        return {
            "focus": self.focus,
            "activeTaskId": self.active_task_id,
            "checkpointId": self.checkpoint_id,
            "handoffId": self.handoff_id,
        }


@dataclass(frozen=True)
class ModePlan:
    mode: str
    candidate_limit: int
    hint_limit: int
    fts_limit: int
    relationship_limit: int
    behavior: str
    deep_explicitly_requested: bool = False

    def trace_payload(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "candidateLimit": self.candidate_limit,
            "hintLimit": self.hint_limit,
            "ftsLimit": self.fts_limit,
            "relationshipLimit": self.relationship_limit,
            "behavior": self.behavior,
            "deepExplicitlyRequested": self.deep_explicitly_requested,
        }


@dataclass(frozen=True)
class ContextRuntime:
    record: dict[str, str]
    request: ContextRequest
    db_path: Path
    context_config: ContextControlConfig
    mode_plan: ModePlan
    recall_plan: RecallPlan
    started: float


@dataclass(frozen=True)
class LoadedContext:
    continuity: ContinuityContext
    workroot_guidance: str = ""


@dataclass(frozen=True)
class RetrievedContext:
    candidates: list[CandidateMatch]
    fts_matches: list[FtsMatch]
    fts_error: str | None


@dataclass(frozen=True)
class GovernedContext:
    candidates: list[CandidateMatch]
    fts_matches: list[FtsMatch]
    fts_error: str | None
    release_report: ReleaseFilterReport
    fts_release_report: FtsReleaseFilterReport


@dataclass(frozen=True)
class SelectedContext:
    candidates: list[CandidateMatch]
    relationship_signals: list[RelationshipSignal]
    relationship_release_report: RelationshipReleaseFilterReport
    fallback_user_asset_candidates: dict[str, object]
    budget_dropped_candidates: list[CandidateMatch] | None = None


@dataclass(frozen=True)
class RenderedContext:
    text: str
    trim_steps: list[str]


def build_context_package(
    request: ContextRequest,
    *,
    ai_workroot_home: Path | str | None = None,
) -> str:
    runtime = _resolve_context_runtime(request, ai_workroot_home)
    loaded = LoadedContext(
        continuity=ContinuityContext(), workroot_guidance=workroot_guidance_text(agent=request.agent)
    )
    retrieved = RetrievedContext(candidates=[], fts_matches=[], fts_error=None)
    governed = GovernedContext(
        candidates=[],
        fts_matches=[],
        fts_error=None,
        release_report=ReleaseFilterReport(frozenset(), frozenset(), ()),
        fts_release_report=FtsReleaseFilterReport((), (), ()),
    )
    selected = SelectedContext(
        candidates=[],
        relationship_signals=[],
        relationship_release_report=RelationshipReleaseFilterReport((), (), ()),
        fallback_user_asset_candidates={"attempted": False, "reason": "not_needed"},
    )

    if runtime.db_path.is_file():
        with sqlite3.connect(runtime.db_path) as conn:
            loaded = _load_context_state(conn, runtime)
            runtime = _with_recall_plan(conn, runtime, loaded)
            _prepare_recall_hints(conn, runtime)
            retrieved = _retrieve_context(conn, runtime)
            governed = _govern_context(conn, runtime, retrieved)
            selected = _select_context(conn, runtime, governed)

    selected = _apply_fallback_selection(runtime, governed, selected)
    rendered = _render_context(runtime, loaded, governed, selected)
    final = _apply_context_budget(runtime, loaded, governed, selected, rendered)
    _record_context_result(runtime, loaded, governed, selected, final)
    return final.text


# Context assembly pipeline.
def _resolve_context_runtime(request: ContextRequest, ai_workroot_home: Path | str | None) -> ContextRuntime:
    started = time.perf_counter()
    record = find_workroot_by_cwd(request.cwd, ai_workroot_home=ai_workroot_home)
    context_config = load_context_control_config(Path(record["stateDirectory"]).parents[1])
    request = _resolve_context_request_budget(request, context_config)
    return ContextRuntime(
        record=record,
        request=request,
        db_path=Path(record["stateDirectory"]) / "cache/workroot.sqlite",
        context_config=context_config,
        mode_plan=_resolve_mode_plan(request.mode),
        recall_plan=_empty_recall_plan(record["workrootId"]),
        started=started,
    )


def _load_context_state(conn: sqlite3.Connection, runtime: ContextRuntime) -> LoadedContext:
    return _load_startup_context_state(runtime)


def _with_recall_plan(conn: sqlite3.Connection, runtime: ContextRuntime, loaded: LoadedContext) -> ContextRuntime:
    lease_signal = _resolve_lease_focus_signal(
        conn,
        workroot_id=runtime.record["workrootId"],
        continuity=loaded.continuity,
    )
    plan = build_recall_plan(
        StrategyRequest(
            query=runtime.request.query,
            mode=runtime.request.mode,
            focus=FocusBoundary(
                workroot_id=runtime.record["workrootId"],
                task_ref=loaded.continuity.active_task_id,
                run_ref=loaded.continuity.checkpoint_id,
                confidence=loaded.continuity.confidence or "none",
                reason=loaded.continuity.why,
            ),
            target_tokens=runtime.request.target_tokens,
            hard_token_limit=runtime.request.hard_token_limit,
            work_signal=_context_work_signal(runtime.request),
            lease_signal=lease_signal,
        )
    )
    return ContextRuntime(
        record=runtime.record,
        request=runtime.request,
        db_path=runtime.db_path,
        context_config=runtime.context_config,
        mode_plan=runtime.mode_plan,
        recall_plan=plan,
        started=runtime.started,
    )


def _empty_recall_plan(workroot_id: str) -> RecallPlan:
    return build_recall_plan(
        StrategyRequest(
            query="",
            mode="standard",
            focus=FocusBoundary(workroot_id=workroot_id, confidence="none"),
            target_tokens=DEFAULT_TARGET_TOKENS,
            hard_token_limit=DEFAULT_HARD_TOKEN_LIMIT,
        )
    )


def _resolve_lease_focus_signal(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    continuity: ContinuityContext,
) -> LeaseFocusSignal:
    rows = _recent_lease_rows(conn, workroot_id=workroot_id, continuity=continuity)
    if not rows:
        return LeaseFocusSignal()
    if not continuity.active_task_id:
        task_ids = {str(row["task_id"] or "") for row in rows if row["task_id"]}
        if len(task_ids) > 1:
            return LeaseFocusSignal(
                status="multiple_recent",
                freshness="unknown",
                debug_reason="several recent leases have different task focus",
            )
    row = rows[0]
    observed_versions = _json_dict(row["observed_versions_json"])
    current_versions = load_state_versions(conn, workroot_id, list(observed_versions.keys()))
    if current_versions != observed_versions:
        return LeaseFocusSignal(
            status="state_conflict",
            freshness="stale",
            debug_reason="observed state versions differ from current versions",
        )
    if str(row["status"] or "") != "active" or str(row["expires_at"] or "") <= utc_now():
        return LeaseFocusSignal(
            status="expired",
            freshness="stale",
            debug_reason="recent lease is expired",
        )
    if not _lease_has_protocol_event(conn, workroot_id=workroot_id, lease_id=str(row["lease_id"] or "")):
        return LeaseFocusSignal(
            status="interrupted",
            freshness="fresh",
            debug_reason="recent lease has no applied protocol event",
        )
    return LeaseFocusSignal(
        status="fresh_active",
        freshness="fresh",
        debug_reason="recent active lease has applied protocol event",
    )


def _recent_lease_rows(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    continuity: ContinuityContext,
) -> list[dict[str, object]]:
    if continuity.active_task_id:
        rows = conn.execute(
            """
            SELECT lease_id, task_id, run_id, observed_versions_json, status, issued_at, expires_at
            FROM exchange_leases
            WHERE workroot_id = ?
              AND (task_id = ? OR run_id = ?)
            ORDER BY issued_at DESC
            LIMIT 5
            """,
            (workroot_id, continuity.active_task_id, continuity.checkpoint_id),
        ).fetchall()
        if rows:
            return [_lease_row_dict(row) for row in rows]
    rows = conn.execute(
        """
        SELECT lease_id, task_id, run_id, observed_versions_json, status, issued_at, expires_at
        FROM exchange_leases
        WHERE workroot_id = ?
        ORDER BY issued_at DESC
        LIMIT 5
        """,
        (workroot_id,),
    ).fetchall()
    return [_lease_row_dict(row) for row in rows]


def _lease_row_dict(row: tuple[object, ...]) -> dict[str, object]:
    return dict(
        zip(
            ("lease_id", "task_id", "run_id", "observed_versions_json", "status", "issued_at", "expires_at"),
            row,
        )
    )


def _lease_has_protocol_event(conn: sqlite3.Connection, *, workroot_id: str, lease_id: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM protocol_events
        WHERE workroot_id = ?
          AND lease_id = ?
          AND status = 'applied'
        LIMIT 1
        """,
        (workroot_id, lease_id),
    ).fetchone()
    return row is not None


def _json_dict(value: object) -> dict[str, int]:
    try:
        loaded = json.loads(str(value or "{}"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(loaded, dict):
        return {}
    result: dict[str, int] = {}
    for key, item in loaded.items():
        try:
            result[str(key)] = int(item)
        except (TypeError, ValueError):
            continue
    return result


def _prepare_recall_hints(conn: sqlite3.Connection, runtime: ContextRuntime) -> None:
    if runtime.recall_plan.source_limit("context_recall_hints", default=0) <= 0:
        return
    _materialize_context_recall_hints_for_release(
        conn,
        runtime.record["workrootId"],
        query=runtime.request.query,
        scope=runtime.recall_plan.source_scope("context_recall_hints"),
        limit=runtime.recall_plan.source_limit("context_recall_hints", default=0),
    )


def _retrieve_context(conn: sqlite3.Connection, runtime: ContextRuntime) -> RetrievedContext:
    candidates: list[CandidateMatch] = []
    candidate_limit = runtime.recall_plan.source_limit("context_candidates", default=0)
    if candidate_limit > 0:
        candidates = query_context_candidates(
            conn,
            runtime.record["workrootId"],
            query=runtime.request.query,
            scope=runtime.recall_plan.source_scope("context_candidates"),
            limit=max(candidate_limit * 3, runtime.recall_plan.source_limit("context_recall_hints", default=0)),
        )
    refs = _work_signal_refs(runtime)
    ref_candidate_limit = runtime.recall_plan.source_limit("ref_candidates", default=0)
    if refs and ref_candidate_limit > 0:
        ref_candidates = query_context_candidates_by_refs(
            conn,
            runtime.record["workrootId"],
            refs,
            scope=runtime.recall_plan.source_scope("ref_candidates"),
            limit=ref_candidate_limit,
        )
        candidates = _merge_candidates(ref_candidates, candidates)
    if not runtime.recall_plan.allows(DisclosureLevel.L3):
        return RetrievedContext(candidates=candidates, fts_matches=[], fts_error=None)
    fts_matches: list[FtsMatch] = []
    fts_error: str | None = None
    fts_limit = runtime.recall_plan.source_limit("indexed_chunks", default=0)
    if fts_limit > 0:
        fts_matches, fts_error = search_fts(
            conn,
            runtime.record["workrootId"],
            runtime.request.query,
            limit=fts_limit,
        )
    ref_fts_limit = runtime.recall_plan.source_limit("ref_indexed_chunks", default=0)
    if refs and ref_fts_limit > 0:
        ref_matches, ref_error = search_fts_by_refs(
            conn,
            runtime.record["workrootId"],
            refs,
            limit=ref_fts_limit,
        )
        fts_matches = _merge_fts_matches(ref_matches, fts_matches)
        fts_error = fts_error or ref_error
    fts_candidate_refs = _fts_source_refs(fts_matches)
    if fts_candidate_refs and candidate_limit > 0:
        fts_candidates = query_context_candidates_by_refs(
            conn,
            runtime.record["workrootId"],
            fts_candidate_refs,
            scope=runtime.recall_plan.source_scope("context_candidates"),
            limit=max(candidate_limit, len(fts_candidate_refs)),
        )
        candidates = _merge_candidates(fts_candidates, candidates)
    return RetrievedContext(candidates=candidates, fts_matches=fts_matches, fts_error=fts_error)


def _govern_context(
    conn: sqlite3.Connection,
    runtime: ContextRuntime,
    retrieved: RetrievedContext,
) -> GovernedContext:
    release_report = load_release_filter_report(conn, runtime.record["workrootId"], retrieved.candidates)
    candidates = _apply_release_filters(retrieved.candidates, release_report)
    fts_release_report = filter_fts_matches_for_release(conn, runtime.record["workrootId"], retrieved.fts_matches)
    return GovernedContext(
        candidates=candidates,
        fts_matches=list(fts_release_report.matches),
        fts_error=retrieved.fts_error,
        release_report=release_report,
        fts_release_report=fts_release_report,
    )


def _select_context(
    conn: sqlite3.Connection,
    runtime: ContextRuntime,
    governed: GovernedContext,
) -> SelectedContext:
    candidates, budget_dropped_candidates = _select_candidates(
        governed.candidates,
        governed.fts_matches,
        limit=_candidate_selection_limit(runtime.recall_plan),
    )
    source_refs = {
        (candidate.source_type, candidate.source_id)
        for candidate in candidates
        if candidate.source_type and candidate.source_id
    }
    relationship_limit = runtime.recall_plan.source_limit("relationships", default=0)
    relationship_signals = []
    if relationship_limit > 0:
        relationship_signals = relationship_signals_for_source_refs(
            conn,
            runtime.record["workrootId"],
            source_refs,
            limit=relationship_limit,
        )
    relationship_release_report = filter_relationship_signals_for_release(
        conn,
        runtime.record["workrootId"],
        relationship_signals,
    )
    relationship_signals = list(relationship_release_report.signals)
    candidates = _boost_relationship_candidates(candidates, relationship_signals)
    return SelectedContext(
        candidates=candidates,
        relationship_signals=relationship_signals,
        relationship_release_report=relationship_release_report,
        fallback_user_asset_candidates={"attempted": False, "reason": "not_needed"},
        budget_dropped_candidates=budget_dropped_candidates,
    )


def _apply_fallback_selection(
    runtime: ContextRuntime,
    governed: GovernedContext,
    selected: SelectedContext,
) -> SelectedContext:
    if selected.candidates:
        return selected
    if _protected_drop_occurred(
        governed.release_report,
        governed.fts_release_report,
        selected.relationship_release_report,
    ):
        return SelectedContext(
            candidates=[],
            relationship_signals=selected.relationship_signals,
            relationship_release_report=selected.relationship_release_report,
            fallback_user_asset_candidates={
                "attempted": False,
                "reason": "disabled_due_to_release_protected_drop",
            },
            budget_dropped_candidates=selected.budget_dropped_candidates,
        )
    fallback_limit = runtime.recall_plan.source_limit("fallback_user_assets", default=0)
    if fallback_limit <= 0:
        return SelectedContext(
            candidates=[],
            relationship_signals=selected.relationship_signals,
            relationship_release_report=selected.relationship_release_report,
            fallback_user_asset_candidates={"attempted": False, "reason": "not_in_recall_plan"},
            budget_dropped_candidates=selected.budget_dropped_candidates,
        )
    return SelectedContext(
        candidates=_fallback_user_asset_candidates(Path(runtime.record["userDirectory"]), limit=fallback_limit),
        relationship_signals=selected.relationship_signals,
        relationship_release_report=selected.relationship_release_report,
        fallback_user_asset_candidates={"attempted": True, "reason": "no_selected_candidates"},
        budget_dropped_candidates=selected.budget_dropped_candidates,
    )


def _render_context(
    runtime: ContextRuntime,
    loaded: LoadedContext,
    governed: GovernedContext,
    selected: SelectedContext,
) -> RenderedContext:
    return RenderedContext(
        text=_render_context_text(runtime, loaded, governed, selected, trim_steps=[]),
        trim_steps=[],
    )


def _apply_context_budget(
    runtime: ContextRuntime,
    loaded: LoadedContext,
    governed: GovernedContext,
    selected: SelectedContext,
    rendered: RenderedContext,
) -> RenderedContext:
    text, trim_steps = _enforce_hard_token_limit(rendered.text, runtime.request.hard_token_limit)
    if not trim_steps:
        return RenderedContext(text=text, trim_steps=[])

    if runtime.request.debug:
        text = _render_compact_debug_context_text(runtime, loaded, governed, selected, trim_steps=trim_steps)
        text, fallback_steps = _enforce_hard_token_limit(text, runtime.request.hard_token_limit)
        if fallback_steps and "final-fallback" not in trim_steps:
            trim_steps.extend(fallback_steps)
        if fallback_steps and "## Debug Trace" not in text:
            text = _minimal_debug_package(
                record=runtime.record, request=runtime.request, started=runtime.started, trim_steps=trim_steps
            )
        text = _append_trim_marker(text, trim_steps)
        text, _ = _enforce_hard_token_limit(text, runtime.request.hard_token_limit)
        text = _refresh_rendered_token_usage(text, runtime.request.hard_token_limit)
        if "## Debug Trace" not in text:
            text = _minimal_debug_package(
                record=runtime.record, request=runtime.request, started=runtime.started, trim_steps=trim_steps
            )
            text, _ = _enforce_hard_token_limit(text, runtime.request.hard_token_limit)
            text = _refresh_rendered_token_usage(text, runtime.request.hard_token_limit)
        return RenderedContext(text=text, trim_steps=trim_steps)

    text = _render_context_text(runtime, loaded, governed, selected, trim_steps=trim_steps)
    text = _append_trim_marker(text, trim_steps)
    text, fallback_steps = _enforce_hard_token_limit(text, runtime.request.hard_token_limit)
    if fallback_steps:
        trim_steps.extend(step for step in fallback_steps if step not in trim_steps)
        text = _append_trim_marker(text, trim_steps)
        text, _ = _enforce_hard_token_limit(text, runtime.request.hard_token_limit)
        text = _refresh_rendered_token_usage(text, runtime.request.hard_token_limit)
    return RenderedContext(text=text, trim_steps=trim_steps)


def _record_context_result(
    runtime: ContextRuntime,
    loaded: LoadedContext,
    governed: GovernedContext,
    selected: SelectedContext,
    rendered: RenderedContext,
) -> None:
    if runtime.db_path.is_file():
        with sqlite3.connect(runtime.db_path) as conn:
            _persist_context_runtime_state(
                conn,
                workroot_id=runtime.record["workrootId"],
                request=runtime.request,
                rendered=rendered.text,
                selected=selected.candidates,
                budget_dropped_candidates=selected.budget_dropped_candidates or [],
                release_report=governed.release_report,
                fts_release_report=governed.fts_release_report,
                relationship_release_report=selected.relationship_release_report,
                fallback_user_asset_candidates=selected.fallback_user_asset_candidates,
                continuity=loaded.continuity,
                mode_plan=runtime.mode_plan,
                recall_plan=runtime.recall_plan,
                trim_steps=rendered.trim_steps,
            )
    _write_context_runtime_view_best_effort(
        state_directory=Path(runtime.record["stateDirectory"]),
        rendered=rendered.text,
        trace={
            "workrootId": runtime.record["workrootId"],
            "agent": runtime.request.agent,
            "mode": runtime.request.mode,
            "query": runtime.request.query,
            "selectedCandidateIds": [candidate.candidate_id for candidate in selected.candidates],
            "continuity": loaded.continuity.trace_payload(),
            "modePlan": runtime.mode_plan.trace_payload(),
            "recallPlan": runtime.recall_plan.trace_payload(),
            "evidenceDecision": runtime.recall_plan.evidence_decision.trace_payload(),
            "budgetPlan": _budget_plan_trace(
                request=runtime.request,
                rendered=rendered.text,
                selected=selected.candidates,
                budget_dropped_candidates=selected.budget_dropped_candidates or [],
                fts_release_report=governed.fts_release_report,
                relationship_release_report=selected.relationship_release_report,
            ),
            "retrievalStats": _retrieval_stats_trace(
                selected=selected.candidates,
                budget_dropped_candidates=selected.budget_dropped_candidates or [],
                fts_release_report=governed.fts_release_report,
                relationship_release_report=selected.relationship_release_report,
                release_report=governed.release_report,
            ),
            "trimSteps": rendered.trim_steps,
            "tokenUsage": estimate_tokens(rendered.text),
        },
    )
    _write_context_diagnostic_log(
        record=runtime.record,
        request=runtime.request,
        rendered=rendered.text,
        selected=selected.candidates,
        release_report=governed.release_report,
        fts_release_report=governed.fts_release_report,
        relationship_release_report=selected.relationship_release_report,
        fallback_user_asset_candidates=selected.fallback_user_asset_candidates,
        mode_plan=runtime.mode_plan,
        recall_plan=runtime.recall_plan,
        trim_steps=rendered.trim_steps,
        logging_config=runtime.context_config.diagnostic_logging,
    )


def _render_context_text(
    runtime: ContextRuntime,
    loaded: LoadedContext,
    governed: GovernedContext,
    selected: SelectedContext,
    *,
    trim_steps: list[str],
) -> str:
    return _render_package(
        record=runtime.record,
        request=runtime.request,
        selected=selected.candidates,
        fts_matches=governed.fts_matches,
        relationship_signals=selected.relationship_signals,
        release_report=governed.release_report,
        fts_release_report=governed.fts_release_report,
        relationship_release_report=selected.relationship_release_report,
        fallback_user_asset_candidates=selected.fallback_user_asset_candidates,
        continuity=loaded.continuity,
        mode_plan=runtime.mode_plan,
        recall_plan=runtime.recall_plan,
        fts_error=governed.fts_error,
        started=runtime.started,
        trim_steps=trim_steps,
        workroot_guidance=loaded.workroot_guidance,
    )


def _render_compact_debug_context_text(
    runtime: ContextRuntime,
    loaded: LoadedContext,
    governed: GovernedContext,
    selected: SelectedContext,
    *,
    trim_steps: list[str],
) -> str:
    return _render_compact_debug_package(
        record=runtime.record,
        request=runtime.request,
        selected=selected.candidates,
        release_report=governed.release_report,
        fts_release_report=governed.fts_release_report,
        relationship_release_report=selected.relationship_release_report,
        fallback_user_asset_candidates=selected.fallback_user_asset_candidates,
        continuity=loaded.continuity,
        mode_plan=runtime.mode_plan,
        recall_plan=runtime.recall_plan,
        fts_error=governed.fts_error,
        started=runtime.started,
        trim_steps=trim_steps,
        workroot_guidance=loaded.workroot_guidance,
    )


# Request and budget resolution.
def _resolve_context_request_budget(request: ContextRequest, config: ContextControlConfig) -> ContextRequest:
    target_tokens = request.target_tokens if request.target_tokens is not None else config.default_target_tokens
    hard_token_limit = (
        request.hard_token_limit if request.hard_token_limit is not None else config.default_hard_token_limit
    )
    budget_source = request.budget_source
    if budget_source == "default":
        budget_source = "config" if request.target_tokens is None or request.hard_token_limit is None else "request"
    return ContextRequest(
        agent=request.agent,
        cwd=request.cwd,
        query=request.query,
        mode=request.mode,
        target_tokens=target_tokens,
        hard_token_limit=hard_token_limit,
        debug=request.debug,
        budget_source=budget_source,
        startup_response=request.startup_response,
        startup_guidance=request.startup_guidance,
        work_signal=request.work_signal,
    )


def estimate_tokens(text: str) -> int:
    ascii_count = sum(1 for char in text if ord(char) < 128 and not char.isspace())
    non_ascii_count = sum(1 for char in text if ord(char) >= 128)
    whitespace_words = len(text.split())
    code_punctuation = sum(1 for char in text if char in "{}[]().,:;=+-*/<>_")
    estimates = [
        max(1, whitespace_words),
        max(1, (ascii_count + 3) // 4 + non_ascii_count),
        max(1, code_punctuation + non_ascii_count),
    ]
    return max(estimates)


def rendered_token_usage(rendered: str) -> int:
    for line in rendered.splitlines():
        match = re.match(r"^TokenUsage:\s*(\d+)/\d+\s*$", line)
        if match:
            return int(match.group(1))
    return 0


def _resolve_mode_plan(mode: str) -> ModePlan:
    normalized = (mode or "standard").lower().strip()
    if normalized == "fast":
        return ModePlan(
            "fast", candidate_limit=4, hint_limit=4, fts_limit=2, relationship_limit=0, behavior="fast-local"
        )
    if normalized == "quality":
        return ModePlan(
            "quality",
            candidate_limit=12,
            hint_limit=16,
            fts_limit=10,
            relationship_limit=16,
            behavior="quality-budget-expansion",
        )
    if normalized == "deep":
        return ModePlan(
            "deep",
            candidate_limit=16,
            hint_limit=24,
            fts_limit=12,
            relationship_limit=24,
            behavior="deep-explicit-local",
            deep_explicitly_requested=True,
        )
    return ModePlan(
        "standard", candidate_limit=8, hint_limit=8, fts_limit=5, relationship_limit=10, behavior="standard-local"
    )


# Release-aware recall hint materialization. Retrieval owns the hint/candidate
# read models; Context Control coordinates Release Control before writing
# derived context candidates.
def _materialize_context_recall_hints_for_release(
    conn: sqlite3.Connection,
    workroot_id: str,
    *,
    query: str = "",
    scope: str = "",
    limit: int = 50,
) -> list[str]:
    hints = query_context_recall_hints(conn, workroot_id, query=query, scope=scope, limit=limit)
    if query.strip() and not hints and scope.startswith("task:"):
        hints = query_context_recall_hints(conn, workroot_id, query="", scope=scope, limit=min(limit, 10))
    return [_materialize_context_recall_hint_for_release(conn, hint) for hint in hints]


def _materialize_context_recall_hint_for_release(conn: sqlite3.Connection, hint: ContextRecallHint) -> str:
    candidate_id = f"hint:{hint.hint_id}"
    title, summary = _release_safe_hint_text(conn, hint)
    upsert_context_candidate(
        conn,
        {
            "candidate_id": candidate_id,
            "workroot_id": hint.workroot_id,
            "source_type": "context_recall_hint",
            "source_id": hint.hint_id,
            "title": title,
            "summary": summary,
            "domains": _hint_scope_domain(hint),
            "importance": hint.priority or "normal",
            "confidence": 0.9,
            "status": "active",
            "context_policy": hint.recall_rule or "task-related",
            "safety_policy": "",
            "token_estimate": 0,
            "updatedAt": hint.updated_at,
        },
    )
    return candidate_id


def _hint_scope_domain(hint: ContextRecallHint) -> str:
    if hint.scope_type == "task" and hint.scope_id:
        return f"task:{hint.scope_id}"
    if hint.scope_type == "workroot":
        return "workroot"
    return hint.scope_id


def _release_safe_hint_text(conn: sqlite3.Connection, hint: ContextRecallHint) -> tuple[str, str]:
    evaluation = evaluate_release_targets(
        conn,
        hint.workroot_id,
        (
            ReleaseTargetRef(
                target_type=hint.target_type,
                target_id=hint.target_id,
                workroot_id=hint.workroot_id,
            ),
        ),
    )
    if not evaluation.strictly_protected:
        return hint.title, hint.summary
    placeholder = "[redacted]" if evaluation.level == "redacted" else "[deleted]"
    return placeholder, placeholder


# Candidate selection.
def _select_candidates(
    candidates: list[CandidateMatch],
    fts_matches: list[FtsMatch],
    *,
    limit: int,
) -> tuple[list[CandidateMatch], list[CandidateMatch]]:
    path_terms = {match.relative_path for match in fts_matches}
    selected = list(candidates)
    if path_terms:
        boosted: list[CandidateMatch] = []
        for candidate in selected:
            if candidate.source_id in path_terms or candidate.title in path_terms:
                boosted.append(
                    CandidateMatch(
                        candidate_id=candidate.candidate_id,
                        source_type=candidate.source_type,
                        source_id=candidate.source_id,
                        title=candidate.title,
                        summary=candidate.summary,
                        importance=candidate.importance,
                        context_policy=candidate.context_policy,
                        safety_policy=candidate.safety_policy,
                        score=candidate.score + 0.4,
                        reasons=tuple(dict.fromkeys((*candidate.reasons, "file-fts-match"))),
                    )
                )
            else:
                boosted.append(candidate)
        selected = boosted
    selected.sort(key=lambda candidate: (-candidate.score, candidate.candidate_id))
    return selected[:limit], selected[limit:]


def _merge_candidates(primary: list[CandidateMatch], fallback: list[CandidateMatch]) -> list[CandidateMatch]:
    merged: dict[str, CandidateMatch] = {}
    for candidate in (*primary, *fallback):
        existing = merged.get(candidate.candidate_id)
        if existing is None or candidate.score > existing.score:
            merged[candidate.candidate_id] = candidate
    return list(merged.values())


def _merge_fts_matches(primary: list[FtsMatch], fallback: list[FtsMatch]) -> list[FtsMatch]:
    merged: dict[str, FtsMatch] = {}
    for match in (*primary, *fallback):
        merged.setdefault(match.chunk_id, match)
    return list(merged.values())


def _fts_source_refs(fts_matches: list[FtsMatch]) -> tuple[str, ...]:
    refs: list[str] = []
    seen: set[str] = set()
    for match in fts_matches:
        if not match.source_type or not match.source_id:
            continue
        ref = f"{match.source_type}:{match.source_id}"
        if ref in seen:
            continue
        refs.append(ref)
        seen.add(ref)
    return tuple(refs)


def _apply_release_filters(
    candidates: list[CandidateMatch], release_report: ReleaseFilterReport
) -> list[CandidateMatch]:
    filtered: list[CandidateMatch] = []
    for candidate in candidates:
        if (
            candidate.candidate_id in release_report.protected_candidate_ids
            or candidate.source_id in release_report.protected_source_ids
        ):
            continue
        if (
            candidate.candidate_id in release_report.tombstone_candidate_ids
            or candidate.source_id in release_report.tombstone_source_ids
        ):
            filtered.append(
                CandidateMatch(
                    candidate_id=candidate.candidate_id,
                    source_type=candidate.source_type,
                    source_id=candidate.source_id,
                    title=candidate.title,
                    summary=candidate.summary,
                    importance=candidate.importance,
                    context_policy=candidate.context_policy,
                    safety_policy=candidate.safety_policy,
                    score=candidate.score,
                    reasons=tuple(dict.fromkeys((*candidate.reasons, "tombstone", "annotated-release-state"))),
                )
            )
        else:
            filtered.append(candidate)
    return filtered


def _boost_relationship_candidates(
    candidates: list[CandidateMatch],
    relationship_signals: list[RelationshipSignal],
) -> list[CandidateMatch]:
    related_sources = {
        node_id for signal in relationship_signals for node_id in (signal.from_node_id, signal.to_node_id)
    }
    related_source_refs = {
        (source_ref.source_type, source_ref.source_id)
        for signal in relationship_signals
        for source_ref in signal.matched_source_refs
    }
    boosted: list[CandidateMatch] = []
    for candidate in candidates:
        if (
            candidate.source_id in related_sources
            or (candidate.source_type, candidate.source_id) in related_source_refs
        ):
            boosted.append(
                CandidateMatch(
                    candidate_id=candidate.candidate_id,
                    source_type=candidate.source_type,
                    source_id=candidate.source_id,
                    title=candidate.title,
                    summary=candidate.summary,
                    importance=candidate.importance,
                    context_policy=candidate.context_policy,
                    safety_policy=candidate.safety_policy,
                    score=candidate.score + 0.5,
                    reasons=tuple(dict.fromkeys((*candidate.reasons, "relationship-edge"))),
                )
            )
        else:
            boosted.append(candidate)
    boosted.sort(key=lambda candidate: (-candidate.score, candidate.candidate_id))
    return boosted


def _candidate_selection_limit(recall_plan: RecallPlan) -> int:
    explicit_limits = (
        recall_plan.source_limit("context_candidates", default=0),
        recall_plan.source_limit("ref_candidates", default=0),
    )
    return max(0, *explicit_limits)


def _protected_drop_occurred(
    release_report: ReleaseFilterReport,
    fts_release_report: FtsReleaseFilterReport,
    relationship_release_report: RelationshipReleaseFilterReport,
) -> bool:
    return bool(release_report.dropped or fts_release_report.dropped or relationship_release_report.dropped)


def _fallback_user_asset_candidates(user_directory: Path, *, limit: int) -> list[CandidateMatch]:
    if not user_directory.exists():
        return []
    candidates: list[CandidateMatch] = []
    for path in sorted(user_directory.iterdir()):
        if path.name in {"AGENTS.md", "CLAUDE.md"} or path.name.startswith("."):
            continue
        if path.is_file():
            candidates.append(
                CandidateMatch(
                    candidate_id=f"file:{path.name}",
                    source_type="file",
                    source_id=path.name,
                    title=path.name,
                    summary="User asset discovered in the selected Workroot directory.",
                    importance="normal",
                    context_policy="task-related",
                    safety_policy="",
                    score=0.1,
                    reasons=("user-asset",),
                )
            )
    return candidates[:limit]


def _load_startup_context_state(runtime: ContextRuntime) -> LoadedContext:
    response = runtime.request.startup_response or {}
    guidance = runtime.request.startup_guidance or workroot_guidance_text(agent=runtime.request.agent)
    return LoadedContext(
        continuity=_continuity_from_startup_response(response),
        workroot_guidance=guidance.rstrip() + "\n",
    )


def _startup_work_signal(request: ContextRequest) -> dict[str, object]:
    return {
        "phase": "orienting",
        "work_kind": "",
        "intended_action": "inspect",
        "focus": request.query,
        "concerns": [],
    }


def _context_work_signal(request: ContextRequest) -> dict[str, object]:
    if isinstance(request.work_signal, dict):
        return request.work_signal
    response = request.startup_response or {}
    signal = response.get("request_work_signal")
    return signal if isinstance(signal, dict) else {}


def _work_signal_refs(runtime: ContextRuntime) -> tuple[str, ...]:
    signal = _context_work_signal(runtime.request)
    refs = signal.get("refs")
    if not isinstance(refs, list):
        return ()
    return tuple(str(ref) for ref in refs if str(ref).strip())


def _continuity_from_startup_response(response: dict[str, object]) -> ContinuityContext:
    view = response.get("workroot_view") if isinstance(response.get("workroot_view"), dict) else {}
    contract = response.get("workroot_contract") if isinstance(response.get("workroot_contract"), dict) else {}
    state_refs = contract.get("state_refs") if isinstance(contract.get("state_refs"), dict) else {}
    refs = view.get("refs") if isinstance(view.get("refs"), list) else []
    task_ref_data = _first_ref(refs, "task")
    checkpoint_ref_data = _first_ref(refs, "checkpoint")
    handoff_ref_data = _first_ref(refs, "handoff")
    task_ref = str(state_refs.get("task_ref") or "") if view.get("focus") == "continuation" else ""
    run_ref = str(state_refs.get("run_ref") or "") if task_ref else ""
    return ContinuityContext(
        focus=str(view.get("focus") or ""),
        confidence=str(view.get("confidence") or ""),
        why=str(view.get("why") or ""),
        task_brief=str(view.get("task_brief") or ""),
        current_state=str(view.get("current_state") or ""),
        next_action=str(view.get("next_action") or ""),
        active_task_id=task_ref,
        active_task_title=str(task_ref_data.get("summary") or view.get("task_brief") or ""),
        active_task_status=str(task_ref_data.get("status") or ("active" if task_ref else "")),
        active_task_kind=str(task_ref_data.get("task_kind") or ("task" if task_ref else "")),
        active_task_process_level=str(task_ref_data.get("process_level") or ""),
        checkpoint_id=str(checkpoint_ref_data.get("id") or run_ref),
        checkpoint_status=str(checkpoint_ref_data.get("summary") or view.get("current_state") or ""),
        handoff_id=str(handoff_ref_data.get("id") or ""),
        handoff_title=str(handoff_ref_data.get("summary") or view.get("next_action") or ""),
    )


def _first_ref(refs: list[object], ref_type: str) -> dict[str, object]:
    for ref in refs:
        if isinstance(ref, dict) and ref.get("type") == ref_type:
            return ref
    return {}


# Rendering.
def _render_package(
    *,
    record: dict[str, str],
    request: ContextRequest,
    selected: list[CandidateMatch],
    fts_matches: list[FtsMatch],
    relationship_signals: list[RelationshipSignal],
    release_report: ReleaseFilterReport,
    fts_release_report: FtsReleaseFilterReport,
    relationship_release_report: RelationshipReleaseFilterReport,
    fallback_user_asset_candidates: dict[str, object],
    continuity: ContinuityContext,
    mode_plan: ModePlan,
    recall_plan: RecallPlan,
    fts_error: str | None,
    started: float,
    trim_steps: list[str],
    workroot_guidance: str,
) -> str:
    latency_ms = int((time.perf_counter() - started) * 1000)
    lines = [
        "# AI Workroot Context Package",
        "",
        f"Workroot: {record['name']} ({record['workrootId']})",
        f"Agent: {request.agent}",
        f"Mode: {request.mode}",
        "Confidence: 0.70" if selected else "Confidence: 0.30",
        f"LatencyMs: {latency_ms}",
        f"TokenUsage: {TOKEN_USAGE_PLACEHOLDER}/{request.hard_token_limit}",
    ]
    if request.query:
        lines.append(f"Query: {request.query}")
    lines.extend(["", workroot_guidance.rstrip(), "", "## Stable Guidance"])
    for item in _stable_guidance_lines(request.startup_response):
        lines.append(item)
    lines.extend(["", "## Task Context"])
    if continuity.focus:
        lines.extend(["", "## Workroot View", f"- Focus: {continuity.focus}"])
        if continuity.confidence:
            lines.append(f"- Confidence: {continuity.confidence}")
        if continuity.task_brief:
            lines.append(f"- Task brief: {continuity.task_brief}")
        if continuity.current_state:
            lines.append(f"- Current state: {continuity.current_state}")
        if continuity.next_action:
            lines.append(f"- Next useful action: {continuity.next_action}")
    lines.extend(["", "## Workroot", f"- {record['name']} ({record['workrootId']})"])
    if continuity.active_task_id:
        lines.extend(
            [
                "",
                "## Current Task",
                f"- {continuity.active_task_title}",
            ]
        )
    if continuity.checkpoint_id or continuity.handoff_id:
        lines.extend(["", "## Continuity"])
        if continuity.checkpoint_id:
            lines.append(f"- Checkpoint: {continuity.checkpoint_status}")
        if continuity.handoff_id:
            lines.append(f"- Handoff: {continuity.handoff_title}")
    lines.extend(["", "## Context Map"])
    if selected:
        for candidate in selected:
            reason_text = ", ".join(candidate.reasons)
            ref = _semantic_ref(candidate)
            lines.append(f"- {candidate.title} [{candidate.source_type}; {reason_text}; Ref: {ref}]")
    else:
        lines.append("- No context candidates selected.")
    if selected:
        lines.extend(["", "## Relevant Summaries"])
        for candidate in selected:
            if candidate.summary:
                lines.append(f"- {candidate.title}: {candidate.summary}")
    if fts_matches:
        lines.extend(["", "## Evidence"])
        for match in fts_matches:
            lines.append(f"- {match.relative_path}: {match.reason}; Ref: chunk:{match.chunk_id}")
    if relationship_signals:
        lines.extend(["", "## Relationship Signals"])
        for signal in relationship_signals:
            lines.append(f"- {signal.edge_id}: {signal.from_node_id} {signal.relationship_type} {signal.to_node_id}")
    if request.debug:
        lines.extend(
            [
                "",
                "## Debug Trace",
                f"tokenUsage: estimated={TOKEN_USAGE_PLACEHOLDER} target={request.target_tokens} hard={request.hard_token_limit}",
                f"budgetSource: {request.budget_source}",
                f"timing: totalMs={latency_ms}",
                f"candidateSources: {','.join(source.name for source in recall_plan.sources)}",
                f"filters: safety=default droppedSafetyPolicies={','.join(sorted({'never-auto', 'needs-confirmation', 'sensitive'}))}",
                "scoring: importance + candidate-fts-match + file-fts-match + relationship-edge",
                (
                    f"modePlan: mode={mode_plan.mode} behavior={mode_plan.behavior} "
                    f"candidateLimit={mode_plan.candidate_limit} hintLimit={mode_plan.hint_limit} "
                    f"ftsLimit={mode_plan.fts_limit} relationshipLimit={mode_plan.relationship_limit} "
                    f"deepExplicitlyRequested={str(mode_plan.deep_explicitly_requested).lower()}"
                ),
                "contextStrategy: plan-driven",
                f"contextIntent: {recall_plan.intent}",
                f"semanticSource: {recall_plan.semantic_source}",
                f"recallSources: {','.join(source.name for source in recall_plan.sources)}",
            ]
        )
        if recall_plan.semantic_source == "conservative":
            lines.append("semanticFallback: conservative")
        if continuity.has_content():
            lines.append(
                "continuitySources: "
                f"activeTask={continuity.active_task_id or 'none'} "
                f"checkpoint={continuity.checkpoint_id or 'none'} "
                f"handoff={continuity.handoff_id or 'none'}"
            )
        lease_debug = _render_lease_signal(recall_plan)
        if lease_debug:
            lines.append(lease_debug)
        if fts_error:
            lines.append(f"ftsFallback: {fts_error}")
        if trim_steps:
            lines.append(f"trimSteps: {', '.join(trim_steps)}")
        if release_report.dropped or release_report.tombstone_source_ids:
            dropped = ", ".join(f"{candidate_id}:{reason}" for candidate_id, reason in release_report.dropped) or "none"
            annotations = ", ".join(sorted(release_report.tombstone_source_ids)) or "none"
            lines.append(f"releaseFilters: dropped={dropped} annotated={annotations}")
        if fts_release_report.dropped or fts_release_report.tombstones:
            dropped = ", ".join(f"{chunk_id}:{reason}" for chunk_id, reason in fts_release_report.dropped) or "none"
            tombstones = (
                ", ".join(f"{chunk_id}:{reason}" for chunk_id, reason in fts_release_report.tombstones) or "none"
            )
            lines.append(f"ftsReleaseFilters: dropped={dropped} annotated={tombstones}")
        if relationship_release_report.dropped or relationship_release_report.tombstones:
            dropped = (
                ", ".join(f"{edge_id}:{reason}" for edge_id, reason in relationship_release_report.dropped) or "none"
            )
            tombstones = (
                ", ".join(f"{edge_id}:{reason}" for edge_id, reason in relationship_release_report.tombstones) or "none"
            )
            lines.append(f"relationshipReleaseFilters: dropped={dropped} annotated={tombstones}")
        lines.append(
            "fallbackUserAssetCandidates: "
            f"attempted={str(bool(fallback_user_asset_candidates.get('attempted'))).lower()} "
            f"reason={fallback_user_asset_candidates.get('reason')}"
        )
    return _finalize_rendered_token_usage("\n".join(lines) + "\n")


def _render_compact_debug_package(
    *,
    record: dict[str, str],
    request: ContextRequest,
    selected: list[CandidateMatch],
    release_report: ReleaseFilterReport,
    fts_release_report: FtsReleaseFilterReport,
    relationship_release_report: RelationshipReleaseFilterReport,
    fallback_user_asset_candidates: dict[str, object],
    continuity: ContinuityContext,
    mode_plan: ModePlan,
    recall_plan: RecallPlan,
    fts_error: str | None,
    started: float,
    trim_steps: list[str],
    workroot_guidance: str,
) -> str:
    latency_ms = int((time.perf_counter() - started) * 1000)
    selected_titles = "; ".join(candidate.title for candidate in selected[:3]) or "none"
    lines = [
        "# AI Workroot Context Package",
        "",
        f"Workroot: {record['name']} ({record['workrootId']})",
        f"Agent: {request.agent}",
        f"Mode: {request.mode}",
        "Confidence: 0.70" if selected else "Confidence: 0.30",
        f"LatencyMs: {latency_ms}",
        f"TokenUsage: {TOKEN_USAGE_PLACEHOLDER}/{request.hard_token_limit}",
    ]
    if request.query:
        lines.append(f"Query: {request.query}")
    lines.extend(["", workroot_guidance.rstrip(), "", "## Stable Guidance"])
    for item in _stable_guidance_lines(request.startup_response):
        lines.append(item)
    lines.extend(["", "## Task Context"])
    if continuity.focus:
        lines.extend(["", "## Workroot View", f"- Focus: {continuity.focus}"])
    if continuity.active_task_id:
        lines.extend(["", "## Current Task", f"- {continuity.active_task_title}"])
    lines.extend(
        [
            "",
            "## Context Map",
            f"- {selected_titles}",
            "",
            "## Debug Trace",
            f"tokenUsage: estimated={TOKEN_USAGE_PLACEHOLDER} target={request.target_tokens} hard={request.hard_token_limit}",
            f"budgetSource: {request.budget_source}",
            f"timing: totalMs={latency_ms}",
            f"candidateSources: {','.join(source.name for source in recall_plan.sources)}",
            f"filters: safety=default droppedSafetyPolicies={','.join(sorted({'never-auto', 'needs-confirmation', 'sensitive'}))}",
            "scoring: importance + candidate-fts-match + file-fts-match + relationship-edge",
            (
                f"modePlan: mode={mode_plan.mode} behavior={mode_plan.behavior} "
                f"candidateLimit={mode_plan.candidate_limit} hintLimit={mode_plan.hint_limit} "
                f"ftsLimit={mode_plan.fts_limit} relationshipLimit={mode_plan.relationship_limit} "
                f"deepExplicitlyRequested={str(mode_plan.deep_explicitly_requested).lower()}"
            ),
            "contextStrategy: plan-driven",
            f"contextIntent: {recall_plan.intent}",
            f"semanticSource: {recall_plan.semantic_source}",
            f"recallSources: {','.join(source.name for source in recall_plan.sources)}",
            f"trimSteps: {', '.join(trim_steps)}",
        ]
    )
    if recall_plan.semantic_source == "conservative":
        lines.append("semanticFallback: conservative")
    if fts_error:
        lines.append(f"ftsFallback: {fts_error}")
    lease_debug = _render_lease_signal(recall_plan)
    if lease_debug:
        lines.append(lease_debug)
    if release_report.dropped or release_report.tombstone_source_ids:
        dropped = ", ".join(f"{candidate_id}:{reason}" for candidate_id, reason in release_report.dropped) or "none"
        annotations = ", ".join(sorted(release_report.tombstone_source_ids)) or "none"
        lines.append(f"releaseFilters: dropped={dropped} annotated={annotations}")
    if fts_release_report.dropped or fts_release_report.tombstones:
        dropped = ", ".join(f"{chunk_id}:{reason}" for chunk_id, reason in fts_release_report.dropped) or "none"
        tombstones = ", ".join(f"{chunk_id}:{reason}" for chunk_id, reason in fts_release_report.tombstones) or "none"
        lines.append(f"ftsReleaseFilters: dropped={dropped} annotated={tombstones}")
    if relationship_release_report.dropped or relationship_release_report.tombstones:
        dropped = ", ".join(f"{edge_id}:{reason}" for edge_id, reason in relationship_release_report.dropped) or "none"
        tombstones = (
            ", ".join(f"{edge_id}:{reason}" for edge_id, reason in relationship_release_report.tombstones) or "none"
        )
        lines.append(f"relationshipReleaseFilters: dropped={dropped} annotated={tombstones}")
    lines.append(
        "fallbackUserAssetCandidates: "
        f"attempted={str(bool(fallback_user_asset_candidates.get('attempted'))).lower()} "
        f"reason={fallback_user_asset_candidates.get('reason')}"
    )
    return _finalize_rendered_token_usage("\n".join(lines) + "\n")


def _minimal_debug_package(
    *,
    record: dict[str, str],
    request: ContextRequest,
    started: float,
    trim_steps: list[str],
) -> str:
    latency_ms = int((time.perf_counter() - started) * 1000)
    lines = [
        "# AI Workroot Context Package",
        f"Workroot: {record['name']} ({record['workrootId']})",
        f"Agent: {request.agent}",
        f"Mode: {request.mode}",
        "Confidence: 0.30",
        f"LatencyMs: {latency_ms}",
        f"TokenUsage: {TOKEN_USAGE_PLACEHOLDER}/{request.hard_token_limit}",
        "## Debug Trace",
        f"trimSteps: {', '.join(trim_steps)}",
        f"tokenUsage: estimated={TOKEN_USAGE_PLACEHOLDER} target={request.target_tokens} hard={request.hard_token_limit}",
        f"budgetSource: {request.budget_source}",
        f"timing: totalMs={latency_ms}",
        "candidateSources: context-candidates,indexed-chunks,relationship-network",
        "filters: safety=default",
        "scoring: compact-debug-hard-trim",
        "contextStrategy: unavailable",
    ]
    return _finalize_rendered_token_usage("\n".join(lines) + "\n")


def _finalize_rendered_token_usage(rendered: str) -> str:
    token_usage = 1
    finalized = rendered
    for _ in range(3):
        finalized = rendered.replace(TOKEN_USAGE_PLACEHOLDER, str(token_usage))
        next_usage = estimate_tokens(finalized)
        if next_usage == token_usage:
            return finalized
        token_usage = next_usage
    return rendered.replace(TOKEN_USAGE_PLACEHOLDER, str(max(token_usage, estimate_tokens(finalized))))


# Hard-token-limit enforcement.
def _enforce_hard_token_limit(rendered: str, hard_token_limit: int) -> tuple[str, list[str]]:
    if estimate_tokens(rendered) <= hard_token_limit:
        return rendered, []
    char_limit = max(120, hard_token_limit * 4)
    trimmed = rendered[:char_limit].rstrip() + "\n"
    if estimate_tokens(trimmed) <= hard_token_limit:
        return trimmed, ["final-fallback"]
    final_limit = min(len(rendered), max(1, hard_token_limit * 3))
    while final_limit > 1:
        trimmed = rendered[:final_limit].rstrip() + "\n"
        if estimate_tokens(trimmed) <= hard_token_limit:
            return trimmed, ["final-fallback"]
        final_limit -= 1
    return rendered[:1].rstrip() + "\n", ["final-fallback"]


def _append_trim_marker(rendered: str, trim_steps: list[str]) -> str:
    marker = "\ntrimSteps: " + ", ".join(trim_steps) + "\n"
    if "trimSteps:" in rendered:
        return rendered
    return rendered.rstrip() + marker


def _refresh_rendered_token_usage(rendered: str, hard_token_limit: int) -> str:
    token_usage = 1
    refreshed = rendered
    for _ in range(3):
        refreshed = re.sub(
            r"^TokenUsage:\s*\d+/\d+\s*$", f"TokenUsage: {token_usage}/{hard_token_limit}", rendered, flags=re.MULTILINE
        )
        refreshed = re.sub(
            r"^tokenUsage:\s*estimated=\d+\s+target=",
            f"tokenUsage: estimated={token_usage} target=",
            refreshed,
            flags=re.MULTILINE,
        )
        next_usage = estimate_tokens(refreshed)
        if next_usage == token_usage:
            return refreshed
        token_usage = next_usage
    final_usage = estimate_tokens(refreshed)
    refreshed = re.sub(
        r"^TokenUsage:\s*\d+/\d+\s*$", f"TokenUsage: {final_usage}/{hard_token_limit}", refreshed, flags=re.MULTILINE
    )
    return re.sub(
        r"^tokenUsage:\s*estimated=\d+\s+target=",
        f"tokenUsage: estimated={final_usage} target=",
        refreshed,
        flags=re.MULTILINE,
    )


def _stable_guidance_lines(startup_response: dict[str, object] | None) -> list[str]:
    output_rules = _output_rules_from_startup_response(startup_response)
    lines = ["- New user-visible outputs default to workroot-output/ unless the user gives another path."]
    declared = [rule for rule in output_rules if rule.get("role") == "declared_output"]
    for rule in declared:
        lines.append(f"- For {rule['asset_kind']} outputs, prefer {rule['path']}/ when it matches the user request.")
    lines.append("- Register generated user-visible files with an asset commit that includes the final relative path.")
    lines.append("- Existing folders are read or written only when the user asks.")
    return lines


def _output_rules_from_startup_response(startup_response: dict[str, object] | None) -> list[dict[str, str]]:
    if not isinstance(startup_response, dict):
        return []
    view = startup_response.get("workroot_view")
    if not isinstance(view, dict):
        return []
    rules = view.get("output_rules")
    if not isinstance(rules, list):
        return []
    compact_rules: list[dict[str, str]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        asset_kind = str(rule.get("asset_kind") or "").strip()
        path = str(rule.get("path") or "").strip()
        role = str(rule.get("role") or "").strip()
        if asset_kind and path and role:
            compact_rules.append({"asset_kind": asset_kind, "path": path, "role": role})
    return compact_rules[:5]


def _semantic_ref(candidate: CandidateMatch) -> str:
    if candidate.source_type and candidate.source_id:
        return f"{candidate.source_type}:{candidate.source_id}"
    return candidate.candidate_id


def _render_lease_signal(recall_plan: RecallPlan) -> str:
    signal = recall_plan.lease_signal
    if not signal.status or signal.status == "missing":
        return ""
    return f"leaseSignal: status={signal.status} freshness={signal.freshness or 'unknown'}"


def _budget_plan_trace(
    *,
    request: ContextRequest,
    rendered: str,
    selected: list[CandidateMatch],
    budget_dropped_candidates: list[CandidateMatch],
    fts_release_report: FtsReleaseFilterReport,
    relationship_release_report: RelationshipReleaseFilterReport,
) -> dict[str, object]:
    token_usage = estimate_tokens(rendered)
    target = max(int(request.target_tokens or DEFAULT_TARGET_TOKENS), 1)
    hard = max(int(request.hard_token_limit or DEFAULT_HARD_TOKEN_LIMIT), 1)
    context_map_used = sum(max(1, _candidate_token_estimate(candidate)) for candidate in selected)
    evidence_used = len(fts_release_report.matches) * 24
    relationships_used = len(relationship_release_report.signals) * 16
    return {
        "targetTokens": target,
        "hardTokenLimit": hard,
        "estimatedAfterBudget": token_usage,
        "pressure": round(token_usage / hard, 4),
        "sections": {
            "core_continuity": {
                "budget": max(80, int(target * 0.25)),
                "status": "protected",
            },
            "context_map": {
                "budget": max(120, int(target * 0.35)),
                "used": context_map_used,
                "status": "reduced" if budget_dropped_candidates else "selected",
            },
            "relationships": {
                "budget": max(40, int(target * 0.15)),
                "used": relationships_used,
                "status": "selected" if relationship_release_report.signals else "empty",
            },
            "evidence": {
                "budget": max(0, int(target * 0.20)),
                "used": evidence_used,
                "status": "selected" if fts_release_report.matches else "empty",
            },
        },
    }


def _candidate_token_estimate(candidate: CandidateMatch) -> int:
    return estimate_tokens(f"{candidate.title} {candidate.summary}")


def _retrieval_stats_trace(
    *,
    selected: list[CandidateMatch],
    budget_dropped_candidates: list[CandidateMatch],
    fts_release_report: FtsReleaseFilterReport,
    relationship_release_report: RelationshipReleaseFilterReport,
    release_report: ReleaseFilterReport,
) -> dict[str, int]:
    return {
        "candidateCount": len(selected) + len(budget_dropped_candidates) + len(release_report.dropped),
        "selectedCount": len(selected),
        "ftsCount": len(fts_release_report.matches),
        "relationshipCount": len(relationship_release_report.signals),
        "droppedByBudget": len(budget_dropped_candidates),
        "droppedByRelease": len(release_report.dropped) + len(fts_release_report.dropped),
    }


# Persistence.
def _persist_context_runtime_state(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    request: ContextRequest,
    rendered: str,
    selected: list[CandidateMatch],
    budget_dropped_candidates: list[CandidateMatch],
    release_report: ReleaseFilterReport,
    fts_release_report: FtsReleaseFilterReport,
    relationship_release_report: RelationshipReleaseFilterReport,
    fallback_user_asset_candidates: dict[str, object],
    continuity: ContinuityContext,
    mode_plan: ModePlan,
    recall_plan: RecallPlan,
    trim_steps: list[str],
) -> None:
    package_id = f"ctxpkg_{uuid.uuid4().hex}"
    trace_id = f"ctxtrace_{uuid.uuid4().hex}"
    created_at = utc_now()
    rendered_preview, rendered_preview_metadata = context_rendered_preview(rendered)
    conn.execute(
        """
        INSERT INTO context_packages (package_id, workroot_id, mode, rendered, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (package_id, workroot_id, request.mode, rendered_preview, created_at),
    )
    debug_payload = {
        "packageId": package_id,
        "mode": request.mode,
        "query": request.query,
        "targetTokens": request.target_tokens,
        "hardTokenLimit": request.hard_token_limit,
        "budgetSource": request.budget_source,
        "selectedCandidateIds": [candidate.candidate_id for candidate in selected],
        "releaseDropped": list(release_report.dropped),
        "ftsReleaseDropped": list(fts_release_report.dropped),
        "relationshipReleaseDropped": list(relationship_release_report.dropped),
        "fallbackUserAssetCandidates": fallback_user_asset_candidates,
        "continuity": continuity.trace_payload(),
        "modePlan": mode_plan.trace_payload(),
        "recallPlan": recall_plan.trace_payload(),
        "evidenceDecision": recall_plan.evidence_decision.trace_payload(),
        "budgetPlan": _budget_plan_trace(
            request=request,
            rendered=rendered,
            selected=selected,
            budget_dropped_candidates=budget_dropped_candidates,
            fts_release_report=fts_release_report,
            relationship_release_report=relationship_release_report,
        ),
        "retrievalStats": _retrieval_stats_trace(
            selected=selected,
            budget_dropped_candidates=budget_dropped_candidates,
            fts_release_report=fts_release_report,
            relationship_release_report=relationship_release_report,
            release_report=release_report,
        ),
        "trimSteps": trim_steps,
        "tokenUsage": estimate_tokens(rendered),
        "renderedPreview": rendered_preview_metadata,
    }
    conn.execute(
        """
        INSERT INTO context_traces (trace_id, workroot_id, package_id, debug_json)
        VALUES (?, ?, ?, ?)
        """,
        (trace_id, workroot_id, package_id, json.dumps(debug_payload, ensure_ascii=False, sort_keys=True)),
    )
    for candidate in selected:
        conn.execute(
            """
            INSERT INTO candidate_selections (selection_id, trace_id, candidate_id, reason)
            VALUES (?, ?, ?, ?)
            """,
            (f"sel_{uuid.uuid4().hex}", trace_id, candidate.candidate_id, "selected"),
        )
        conn.execute(
            """
            UPDATE context_candidates
            SET use_count = COALESCE(use_count, 0) + 1,
                lastUsedAt = ?
            WHERE workroot_id = ? AND candidate_id = ?
            """,
            (utc_now(), workroot_id, candidate.candidate_id),
        )
    for candidate_id, reason in release_report.dropped:
        conn.execute(
            """
            INSERT INTO candidate_selections (selection_id, trace_id, candidate_id, reason)
            VALUES (?, ?, ?, ?)
            """,
            (f"sel_{uuid.uuid4().hex}", trace_id, candidate_id, f"dropped:{reason}"),
        )
    for candidate in budget_dropped_candidates:
        conn.execute(
            """
            INSERT INTO candidate_selections (selection_id, trace_id, candidate_id, reason)
            VALUES (?, ?, ?, ?)
            """,
            (f"sel_{uuid.uuid4().hex}", trace_id, candidate.candidate_id, "dropped:budget"),
        )
    if budget_dropped_candidates:
        conn.execute(
            """
            INSERT INTO budget_trim_decisions (decision_id, trace_id, section, reason)
            VALUES (?, ?, ?, ?)
            """,
            (f"trim_{uuid.uuid4().hex}", trace_id, "candidate-map", "budget-selection"),
        )
    for step in trim_steps:
        conn.execute(
            """
            INSERT INTO budget_trim_decisions (decision_id, trace_id, section, reason)
            VALUES (?, ?, ?, ?)
            """,
            (f"trim_{uuid.uuid4().hex}", trace_id, "rendered-package", step),
        )
    _prune_context_runtime_state(conn, workroot_id=workroot_id, keep_latest=CONTEXT_RUNTIME_RETENTION_LIMIT)
    conn.commit()


def _prune_context_runtime_state(conn: sqlite3.Connection, *, workroot_id: str, keep_latest: int) -> None:
    if keep_latest < 1:
        keep_latest = 1
    old_package_ids = [
        str(row[0])
        for row in conn.execute(
            """
            SELECT package_id
            FROM context_packages
            WHERE workroot_id = ?
            ORDER BY rowid DESC
            LIMIT -1 OFFSET ?
            """,
            (workroot_id, keep_latest),
        ).fetchall()
    ]
    if not old_package_ids:
        return

    old_trace_ids = [
        str(row[0])
        for row in conn.execute(
            f"""
            SELECT trace_id
            FROM context_traces
            WHERE workroot_id = ? AND package_id IN ({_sql_placeholders(old_package_ids)})
            """,
            (workroot_id, *old_package_ids),
        ).fetchall()
    ]
    if old_trace_ids:
        _delete_rows_by_ids(conn, "candidate_selections", "trace_id", old_trace_ids)
        _delete_rows_by_ids(conn, "budget_trim_decisions", "trace_id", old_trace_ids)
        _delete_rows_by_ids(conn, "context_traces", "trace_id", old_trace_ids)
    _delete_rows_by_ids(conn, "context_packages", "package_id", old_package_ids)


def _delete_rows_by_ids(conn: sqlite3.Connection, table: str, column: str, values: list[str]) -> None:
    if not values:
        return
    conn.execute(
        f"DELETE FROM {table} WHERE {column} IN ({_sql_placeholders(values)})",
        tuple(values),
    )


def _sql_placeholders(values: list[str]) -> str:
    return ", ".join("?" for _ in values)


# Diagnostic logging.
def _write_context_diagnostic_log(
    *,
    record: dict[str, str],
    request: ContextRequest,
    rendered: str,
    selected: list[CandidateMatch],
    release_report: ReleaseFilterReport,
    fts_release_report: FtsReleaseFilterReport,
    relationship_release_report: RelationshipReleaseFilterReport,
    fallback_user_asset_candidates: dict[str, object],
    mode_plan: ModePlan,
    recall_plan: RecallPlan,
    trim_steps: list[str],
    logging_config: object,
) -> None:
    if not getattr(logging_config, "enabled", False):
        return
    token_usage = estimate_tokens(rendered)
    home = Path(record["stateDirectory"]).parents[1]
    timestamp_utc = utc_now()
    time_config = load_environment_time_config(home)
    entry: dict[str, object] = {
        "displayTime": environment_now(home, now_utc=timestamp_utc),
        "createdAt": timestamp_utc,
        "timezone": time_config.timezone,
        "workrootId": record["workrootId"],
        "agent": request.agent,
        "mode": request.mode,
        "query": request.query,
        "budget": {
            "source": request.budget_source,
            "targetTokens": request.target_tokens,
            "hardTokenLimit": request.hard_token_limit,
        },
    }
    if getattr(logging_config, "include_token_estimate", True):
        entry["tokenUsage"] = {"estimated": token_usage, "renderedMetadata": rendered_token_usage(rendered)}
    if getattr(logging_config, "include_trace_summary", True):
        entry["trace"] = {
            "confidence": "0.70" if selected else "0.30",
            "modePlan": mode_plan.trace_payload(),
            "recallPlan": recall_plan.trace_payload(),
            "trimSteps": trim_steps,
            "fallbackUserAssetCandidates": fallback_user_asset_candidates,
        }
    if getattr(logging_config, "include_retrieval_summary", True):
        entry["retrieval"] = {
            "selectedCandidateIds": [candidate.candidate_id for candidate in selected],
            "releaseDropped": list(release_report.dropped),
            "ftsReleaseDropped": list(fts_release_report.dropped),
            "relationshipReleaseDropped": list(relationship_release_report.dropped),
        }
    if getattr(logging_config, "include_rendered_package", False):
        entry["renderedPackage"] = rendered
    log_path = Path(record["stateDirectory"]) / "logs/context-requests.jsonl"
    append_jsonl(log_path, entry)
    _prune_context_diagnostic_log(
        log_path,
        retention_days=int(getattr(logging_config, "retention_days", 7)),
        max_entries=int(getattr(logging_config, "max_entries_per_workroot", 200)),
    )


def _write_context_runtime_view_best_effort(
    *,
    state_directory: Path,
    rendered: str,
    trace: dict[str, object],
) -> None:
    try:
        write_context_runtime_view(state_directory=state_directory, rendered=rendered, trace=trace)
    except Exception:
        return


def _prune_context_diagnostic_log(log_path: Path, *, retention_days: int, max_entries: int) -> None:
    if not log_path.is_file():
        return
    lines = [line for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if retention_days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        kept: list[str] = []
        for line in lines:
            try:
                record = json.loads(line)
                timestamp_utc = record.get("createdAt")
                parsed = datetime.strptime(str(timestamp_utc), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            except (json.JSONDecodeError, ValueError):
                kept.append(line)
                continue
            if parsed >= cutoff:
                kept.append(line)
        lines = kept
    if max_entries > 0:
        lines = lines[-max_entries:]
    log_path.write_text(("\n".join(lines) + "\n") if lines else "", encoding="utf-8")
