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

from ai_workroot.indexing.providers.candidate_provider import CandidateMatch, query_context_candidates
from ai_workroot.indexing.providers.context_recall_hint_provider import materialize_context_recall_hints
from ai_workroot.indexing.providers.release_provider import (
    FtsReleaseFilterReport,
    RelationshipReleaseFilterReport,
    ReleaseFilterReport,
    filter_fts_matches_for_release,
    filter_relationship_signals_for_release,
    load_release_filter_report,
)
from ai_workroot.indexing.providers.relationship_provider import RelationshipSignal, relationship_signals_for_sources
from ai_workroot.indexing.providers.sqlite_fts import FtsMatch, search_fts
from ai_workroot.runtime.environment import (
    ContextControlConfig,
    environment_now,
    load_environment_time_config,
    load_context_control_config,
    utc_now,
)
from ai_workroot.runtime.registry import find_workroot_by_cwd
from ai_workroot.storage.jsonl_registry import append_jsonl


DEFAULT_TARGET_TOKENS = 1200
DEFAULT_HARD_TOKEN_LIMIT = 2400
TOKEN_USAGE_PLACEHOLDER = "__AI_WORKROOT_TOKEN_USAGE__"


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


@dataclass(frozen=True)
class ContinuityContext:
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


def build_context_package(
    request: ContextRequest,
    *,
    ai_workroot_home: Path | str | None = None,
) -> str:
    started = time.perf_counter()
    record = find_workroot_by_cwd(request.cwd, ai_workroot_home=ai_workroot_home)
    context_config = load_context_control_config(Path(record["stateDirectory"]).parents[1])
    request = _resolve_context_request_budget(request, context_config)
    db_path = Path(record["stateDirectory"]) / "cache/workroot.sqlite"
    selected: list[CandidateMatch] = []
    fts_matches: list[FtsMatch] = []
    relationship_signals: list[RelationshipSignal] = []
    release_report = ReleaseFilterReport(frozenset(), frozenset(), ())
    fts_release_report = FtsReleaseFilterReport((), (), ())
    relationship_release_report = RelationshipReleaseFilterReport((), (), ())
    fallback_user_asset_candidates = {"attempted": False, "reason": "not_needed"}
    continuity = ContinuityContext()
    mode_plan = _resolve_mode_plan(request.mode)
    fts_error: str | None = None

    if db_path.is_file():
        with sqlite3.connect(db_path) as conn:
            continuity = _load_continuity_context(conn, record["workrootId"])
            materialize_context_recall_hints(
                conn,
                record["workrootId"],
                query=request.query,
                limit=mode_plan.hint_limit,
            )
            candidates = query_context_candidates(
                conn,
                record["workrootId"],
                query=request.query,
                limit=max(mode_plan.candidate_limit * 3, mode_plan.hint_limit),
            )
            release_report = load_release_filter_report(conn, record["workrootId"], candidates)
            candidates = _apply_release_filters(candidates, release_report)
            fts_matches, fts_error = search_fts(conn, record["workrootId"], request.query, limit=mode_plan.fts_limit)
            fts_release_report = filter_fts_matches_for_release(conn, record["workrootId"], fts_matches)
            fts_matches = list(fts_release_report.matches)
            selected = _select_candidates(candidates, fts_matches, limit=mode_plan.candidate_limit)
            source_ids = {candidate.source_id for candidate in selected}
            relationship_signals = relationship_signals_for_sources(
                conn,
                record["workrootId"],
                source_ids,
                limit=mode_plan.relationship_limit,
            )
            relationship_release_report = filter_relationship_signals_for_release(
                conn, record["workrootId"], relationship_signals
            )
            relationship_signals = list(relationship_release_report.signals)
            selected = _boost_relationship_candidates(selected, relationship_signals)

    if not selected:
        if _protected_drop_occurred(release_report, fts_release_report, relationship_release_report):
            fallback_user_asset_candidates = {
                "attempted": False,
                "reason": "disabled_due_to_release_protected_drop",
            }
        else:
            fallback_user_asset_candidates = {"attempted": True, "reason": "no_selected_candidates"}
            selected = _fallback_user_asset_candidates(Path(record["userDirectory"]))

    rendered = _render_package(
        record=record,
        request=request,
        selected=selected,
        fts_matches=fts_matches,
        relationship_signals=relationship_signals,
        release_report=release_report,
        fts_release_report=fts_release_report,
        relationship_release_report=relationship_release_report,
        fallback_user_asset_candidates=fallback_user_asset_candidates,
        continuity=continuity,
        mode_plan=mode_plan,
        fts_error=fts_error,
        started=started,
        trim_steps=[],
    )
    rendered, trim_steps = _enforce_hard_token_limit(rendered, request.hard_token_limit)
    if trim_steps:
        if request.debug:
            rendered = _render_compact_debug_package(
                record=record,
                request=request,
                selected=selected,
                release_report=release_report,
                fts_release_report=fts_release_report,
                relationship_release_report=relationship_release_report,
                fallback_user_asset_candidates=fallback_user_asset_candidates,
                continuity=continuity,
                mode_plan=mode_plan,
                fts_error=fts_error,
                started=started,
                trim_steps=trim_steps,
            )
            rendered, fallback_steps = _enforce_hard_token_limit(rendered, request.hard_token_limit)
            if fallback_steps and "final-fallback" not in trim_steps:
                trim_steps.extend(fallback_steps)
            if fallback_steps and "## Debug Trace" not in rendered:
                rendered = _minimal_debug_package(record=record, request=request, started=started, trim_steps=trim_steps)
            rendered = _append_trim_marker(rendered, trim_steps)
            rendered, _ = _enforce_hard_token_limit(rendered, request.hard_token_limit)
            rendered = _refresh_rendered_token_usage(rendered, request.hard_token_limit)
            if "## Debug Trace" not in rendered:
                rendered = _minimal_debug_package(record=record, request=request, started=started, trim_steps=trim_steps)
                rendered, _ = _enforce_hard_token_limit(rendered, request.hard_token_limit)
                rendered = _refresh_rendered_token_usage(rendered, request.hard_token_limit)
            if db_path.is_file():
                with sqlite3.connect(db_path) as conn:
                    _persist_context_runtime_state(
                        conn,
                        workroot_id=record["workrootId"],
                        request=request,
                        rendered=rendered,
                        selected=selected,
                        release_report=release_report,
                        fts_release_report=fts_release_report,
                        relationship_release_report=relationship_release_report,
                        fallback_user_asset_candidates=fallback_user_asset_candidates,
                        continuity=continuity,
                        mode_plan=mode_plan,
                        trim_steps=trim_steps,
                    )
            _write_context_diagnostic_log(
                record=record,
                request=request,
                rendered=rendered,
                selected=selected,
                release_report=release_report,
                fts_release_report=fts_release_report,
                relationship_release_report=relationship_release_report,
                fallback_user_asset_candidates=fallback_user_asset_candidates,
                mode_plan=mode_plan,
                trim_steps=trim_steps,
                logging_config=context_config.diagnostic_logging,
            )
            return rendered
        rendered = _render_package(
            record=record,
            request=request,
            selected=selected,
            fts_matches=fts_matches,
            relationship_signals=relationship_signals,
            release_report=release_report,
            fts_release_report=fts_release_report,
            relationship_release_report=relationship_release_report,
            fallback_user_asset_candidates=fallback_user_asset_candidates,
            continuity=continuity,
            mode_plan=mode_plan,
            fts_error=fts_error,
            started=started,
            trim_steps=trim_steps,
        )
        if trim_steps:
            rendered = _append_trim_marker(rendered, trim_steps)
        rendered, fallback_steps = _enforce_hard_token_limit(rendered, request.hard_token_limit)
        if fallback_steps:
            trim_steps.extend(step for step in fallback_steps if step not in trim_steps)
            rendered = _append_trim_marker(rendered, trim_steps)
            rendered, _ = _enforce_hard_token_limit(rendered, request.hard_token_limit)
            rendered = _refresh_rendered_token_usage(rendered, request.hard_token_limit)
    if db_path.is_file():
        with sqlite3.connect(db_path) as conn:
            _persist_context_runtime_state(
                conn,
                workroot_id=record["workrootId"],
                request=request,
                rendered=rendered,
                selected=selected,
                release_report=release_report,
                fts_release_report=fts_release_report,
                relationship_release_report=relationship_release_report,
                fallback_user_asset_candidates=fallback_user_asset_candidates,
                continuity=continuity,
                mode_plan=mode_plan,
                trim_steps=trim_steps,
            )
    _write_context_diagnostic_log(
        record=record,
        request=request,
        rendered=rendered,
        selected=selected,
        release_report=release_report,
        fts_release_report=fts_release_report,
        relationship_release_report=relationship_release_report,
        fallback_user_asset_candidates=fallback_user_asset_candidates,
        mode_plan=mode_plan,
        trim_steps=trim_steps,
        logging_config=context_config.diagnostic_logging,
    )
    return rendered


def _resolve_context_request_budget(request: ContextRequest, config: ContextControlConfig) -> ContextRequest:
    target_tokens = request.target_tokens if request.target_tokens is not None else config.default_target_tokens
    hard_token_limit = request.hard_token_limit if request.hard_token_limit is not None else config.default_hard_token_limit
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
        return ModePlan("fast", candidate_limit=4, hint_limit=4, fts_limit=2, relationship_limit=0, behavior="fast-local")
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
    return ModePlan("standard", candidate_limit=8, hint_limit=8, fts_limit=5, relationship_limit=10, behavior="standard-local")


def _select_candidates(
    candidates: list[CandidateMatch],
    fts_matches: list[FtsMatch],
    *,
    limit: int,
) -> list[CandidateMatch]:
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
    return selected[:limit]


def _apply_release_filters(candidates: list[CandidateMatch], release_report: ReleaseFilterReport) -> list[CandidateMatch]:
    filtered: list[CandidateMatch] = []
    for candidate in candidates:
        if candidate.candidate_id in release_report.protected_candidate_ids or candidate.source_id in release_report.protected_source_ids:
            continue
        if candidate.candidate_id in release_report.tombstone_candidate_ids or candidate.source_id in release_report.tombstone_source_ids:
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
        node_id
        for signal in relationship_signals
        for node_id in (signal.from_node_id, signal.to_node_id)
    }
    boosted: list[CandidateMatch] = []
    for candidate in candidates:
        if candidate.source_id in related_sources:
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


def _protected_drop_occurred(
    release_report: ReleaseFilterReport,
    fts_release_report: FtsReleaseFilterReport,
    relationship_release_report: RelationshipReleaseFilterReport,
) -> bool:
    return bool(release_report.dropped or fts_release_report.dropped or relationship_release_report.dropped)


def _fallback_user_asset_candidates(user_directory: Path) -> list[CandidateMatch]:
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
    return candidates[:10]


def _load_continuity_context(conn: sqlite3.Connection, workroot_id: str) -> ContinuityContext:
    task = _fetch_one_safely(
        conn,
        """
        SELECT task_id, title, status, task_kind, process_level
        FROM tasks
        WHERE workroot_id = ? AND COALESCE(status, 'active') = 'active'
        ORDER BY rowid DESC
        LIMIT 1
        """,
        (workroot_id,),
    )
    checkpoint = None
    if task:
        checkpoint = _fetch_one_safely(
            conn,
            """
            SELECT checkpoint_id, current_status
            FROM work_checkpoints
            WHERE workroot_id = ? AND task_id = ?
            ORDER BY rowid DESC
            LIMIT 1
            """,
            (workroot_id, str(task[0])),
        )
    handoff = _fetch_one_safely(
        conn,
        """
        SELECT handoff_id, title
        FROM handoffs
        WHERE workroot_id = ?
        ORDER BY rowid DESC
        LIMIT 1
        """,
        (workroot_id,),
    )
    return ContinuityContext(
        active_task_id=str(task[0] or "") if task else "",
        active_task_title=str(task[1] or "") if task else "",
        active_task_status=str(task[2] or "") if task else "",
        active_task_kind=str(task[3] or "") if task else "",
        active_task_process_level=str(task[4] or "") if task else "",
        checkpoint_id=str(checkpoint[0] or "") if checkpoint else "",
        checkpoint_status=str(checkpoint[1] or "") if checkpoint else "",
        handoff_id=str(handoff[0] or "") if handoff else "",
        handoff_title=str(handoff[1] or "") if handoff else "",
    )


def _fetch_one_safely(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[object, ...],
) -> tuple[object, ...] | None:
    try:
        return conn.execute(sql, params).fetchone()
    except sqlite3.OperationalError:
        return None


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
    fts_error: str | None,
    started: float,
    trim_steps: list[str],
) -> str:
    body_for_tokens = _package_body_for_tokens(
        record=record,
        request=request,
        selected=selected,
        fts_matches=fts_matches,
        relationship_signals=relationship_signals,
        release_report=release_report,
        fts_release_report=fts_release_report,
        relationship_release_report=relationship_release_report,
        fallback_user_asset_candidates=fallback_user_asset_candidates,
        continuity=continuity,
        mode_plan=mode_plan,
        trim_steps=trim_steps,
    )
    token_usage = estimate_tokens(body_for_tokens)
    latency_ms = int((time.perf_counter() - started) * 1000)
    lines = [
        "# AI Workroot Context Package",
        "",
        f"Workroot: {record['name']} ({record['workrootId']})",
        f"Agent: {request.agent}",
        f"Mode: {request.mode}",
        "Confidence: 0.70" if selected else "Confidence: 0.30",
        f"LatencyMs: {latency_ms}",
        f"TokenUsage: {token_usage}/{request.hard_token_limit}",
    ]
    if request.query:
        lines.append(f"Query: {request.query}")
    lines.extend(["", "## Workroot", f"- {record['name']} ({record['workrootId']})"])
    if continuity.active_task_id:
        lines.extend(
            [
                "",
                "## Current Task",
                f"- {continuity.active_task_title} [{continuity.active_task_status}; {continuity.active_task_kind}; {continuity.active_task_process_level}]",
            ]
        )
    if continuity.checkpoint_id or continuity.handoff_id:
        lines.extend(["", "## Continuity"])
        if continuity.checkpoint_id:
            lines.append(f"- Checkpoint: {continuity.checkpoint_status}")
        if continuity.handoff_id:
            lines.append(f"- Handoff: {continuity.handoff_title}")
    lines.extend(["", "## Selected Context"])
    if selected:
        for candidate in selected:
            reason_text = ", ".join(candidate.reasons)
            lines.append(f"- {candidate.title} [{candidate.source_type}; {reason_text}]")
            if candidate.summary:
                lines.append(f"  {candidate.summary}")
    else:
        lines.append("- No context candidates selected.")
    if fts_matches:
        lines.extend(["", "## FTS Matches"])
        for match in fts_matches:
            lines.append(f"- {match.relative_path}: {match.reason}")
    if relationship_signals:
        lines.extend(["", "## Relationship Signals"])
        for signal in relationship_signals:
            lines.append(
                f"- {signal.edge_id}: {signal.from_node_id} {signal.relationship_type} {signal.to_node_id}"
            )
    if request.debug:
        lines.extend(
            [
                "",
                "## Debug Trace",
                "candidateSources: context-candidates, indexed-chunks, relationship-network",
                f"filters: safety=default droppedSafetyPolicies={','.join(sorted({'never-auto', 'needs-confirmation', 'sensitive'}))}",
                "scoring: importance + candidate-fts-match + file-fts-match + relationship-edge",
                f"timing: totalMs={latency_ms}",
                f"tokenUsage: estimated={token_usage} target={request.target_tokens} hard={request.hard_token_limit}",
                f"budgetSource: {request.budget_source}",
                (
                    f"modePlan: mode={mode_plan.mode} behavior={mode_plan.behavior} "
                    f"candidateLimit={mode_plan.candidate_limit} hintLimit={mode_plan.hint_limit} "
                    f"ftsLimit={mode_plan.fts_limit} relationshipLimit={mode_plan.relationship_limit} "
                    f"deepExplicitlyRequested={str(mode_plan.deep_explicitly_requested).lower()}"
                ),
            ]
        )
        if continuity.has_content():
            lines.append(
                "continuitySources: "
                f"activeTask={continuity.active_task_id or 'none'} "
                f"checkpoint={continuity.checkpoint_id or 'none'} "
                f"handoff={continuity.handoff_id or 'none'}"
            )
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
            tombstones = ", ".join(f"{chunk_id}:{reason}" for chunk_id, reason in fts_release_report.tombstones) or "none"
            lines.append(f"ftsReleaseFilters: dropped={dropped} annotated={tombstones}")
        if relationship_release_report.dropped or relationship_release_report.tombstones:
            dropped = ", ".join(f"{edge_id}:{reason}" for edge_id, reason in relationship_release_report.dropped) or "none"
            tombstones = ", ".join(f"{edge_id}:{reason}" for edge_id, reason in relationship_release_report.tombstones) or "none"
            lines.append(f"relationshipReleaseFilters: dropped={dropped} annotated={tombstones}")
        lines.append(
            "fallbackUserAssetCandidates: "
            f"attempted={str(bool(fallback_user_asset_candidates.get('attempted'))).lower()} "
            f"reason={fallback_user_asset_candidates.get('reason')}"
        )
    return "\n".join(lines) + "\n"


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
    fts_error: str | None,
    started: float,
    trim_steps: list[str],
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
    if continuity.active_task_id:
        lines.extend(["", "## Current Task", f"- {continuity.active_task_title}"])
    lines.extend(
        [
            "",
            "## Selected Context",
            f"- {selected_titles}",
            "",
            "## Debug Trace",
            "candidateSources: context-candidates, indexed-chunks, relationship-network",
            f"filters: safety=default droppedSafetyPolicies={','.join(sorted({'never-auto', 'needs-confirmation', 'sensitive'}))}",
            "scoring: importance + candidate-fts-match + file-fts-match + relationship-edge",
            f"timing: totalMs={latency_ms}",
            f"tokenUsage: estimated={TOKEN_USAGE_PLACEHOLDER} target={request.target_tokens} hard={request.hard_token_limit}",
            f"budgetSource: {request.budget_source}",
            (
                f"modePlan: mode={mode_plan.mode} behavior={mode_plan.behavior} "
                f"candidateLimit={mode_plan.candidate_limit} hintLimit={mode_plan.hint_limit} "
                f"ftsLimit={mode_plan.fts_limit} relationshipLimit={mode_plan.relationship_limit} "
                f"deepExplicitlyRequested={str(mode_plan.deep_explicitly_requested).lower()}"
            ),
            f"trimSteps: {', '.join(trim_steps)}",
        ]
    )
    if fts_error:
        lines.append(f"ftsFallback: {fts_error}")
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
        tombstones = ", ".join(f"{edge_id}:{reason}" for edge_id, reason in relationship_release_report.tombstones) or "none"
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
        "candidateSources: context-candidates,indexed-chunks,relationship-network",
        "filters: safety=default",
        "scoring: compact-debug-hard-trim",
        f"timing: totalMs={latency_ms}",
        f"tokenUsage: estimated={TOKEN_USAGE_PLACEHOLDER} target={request.target_tokens} hard={request.hard_token_limit}",
        f"budgetSource: {request.budget_source}",
        f"trimSteps: {', '.join(trim_steps)}",
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
        refreshed = re.sub(r"^TokenUsage:\s*\d+/\d+\s*$", f"TokenUsage: {token_usage}/{hard_token_limit}", rendered, flags=re.MULTILINE)
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
    refreshed = re.sub(r"^TokenUsage:\s*\d+/\d+\s*$", f"TokenUsage: {final_usage}/{hard_token_limit}", refreshed, flags=re.MULTILINE)
    return re.sub(
        r"^tokenUsage:\s*estimated=\d+\s+target=",
        f"tokenUsage: estimated={final_usage} target=",
        refreshed,
        flags=re.MULTILINE,
    )


def _package_body_for_tokens(
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
    trim_steps: list[str],
) -> str:
    parts = [
        record.get("name", ""),
        record.get("workrootId", ""),
        request.agent,
        request.mode,
        request.query,
        continuity.active_task_title,
        continuity.active_task_status,
        continuity.active_task_kind,
        continuity.active_task_process_level,
        continuity.checkpoint_status,
        continuity.handoff_title,
        mode_plan.mode,
        mode_plan.behavior,
        str(mode_plan.candidate_limit),
        str(mode_plan.hint_limit),
        str(mode_plan.fts_limit),
        str(mode_plan.relationship_limit),
        "\n".join(f"{candidate.title}\n{candidate.summary}\n{','.join(candidate.reasons)}" for candidate in selected),
        "\n".join(f"{match.relative_path}\n{match.body}" for match in fts_matches),
        "\n".join(
            f"{signal.edge_id}\n{signal.from_node_id}\n{signal.relationship_type}\n{signal.to_node_id}"
            for signal in relationship_signals
        ),
        "\n".join(f"{candidate_id}:{reason}" for candidate_id, reason in release_report.dropped),
        "\n".join(f"{chunk_id}:{reason}" for chunk_id, reason in fts_release_report.dropped),
        "\n".join(f"{edge_id}:{reason}" for edge_id, reason in relationship_release_report.dropped),
        "\n".join(trim_steps),
    ]
    return "\n".join(parts)


def _persist_context_runtime_state(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    request: ContextRequest,
    rendered: str,
    selected: list[CandidateMatch],
    release_report: ReleaseFilterReport,
    fts_release_report: FtsReleaseFilterReport,
    relationship_release_report: RelationshipReleaseFilterReport,
    fallback_user_asset_candidates: dict[str, object],
    continuity: ContinuityContext,
    mode_plan: ModePlan,
    trim_steps: list[str],
) -> None:
    package_id = f"ctxpkg_{uuid.uuid4().hex}"
    trace_id = f"ctxtrace_{uuid.uuid4().hex}"
    conn.execute(
        """
        INSERT INTO context_packages (package_id, workroot_id, mode, rendered)
        VALUES (?, ?, ?, ?)
        """,
        (package_id, workroot_id, request.mode, rendered),
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
        "trimSteps": trim_steps,
        "tokenUsage": estimate_tokens(rendered),
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
    for step in trim_steps:
        conn.execute(
            """
            INSERT INTO budget_trim_decisions (decision_id, trace_id, section, reason)
            VALUES (?, ?, ?, ?)
            """,
            (f"trim_{uuid.uuid4().hex}", trace_id, "rendered-package", step),
        )
    conn.commit()


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
