"""Context Control runtime flow."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3
import time
from pathlib import Path

from ai_workroot.indexing.providers.candidate_provider import CandidateMatch, query_context_candidates
from ai_workroot.indexing.providers.release_provider import ReleaseFilterReport, load_release_filter_report
from ai_workroot.indexing.providers.relationship_provider import RelationshipSignal, relationship_signals_for_sources
from ai_workroot.indexing.providers.sqlite_fts import FtsMatch, search_fts
from ai_workroot.runtime.registry import find_workroot_by_cwd


DEFAULT_TARGET_TOKENS = 1200
DEFAULT_HARD_TOKEN_LIMIT = 2400


@dataclass(frozen=True)
class ContextRequest:
    agent: str
    cwd: Path | str = "."
    query: str = ""
    mode: str = "standard"
    target_tokens: int = DEFAULT_TARGET_TOKENS
    hard_token_limit: int = DEFAULT_HARD_TOKEN_LIMIT
    debug: bool = False


def build_context_package(
    request: ContextRequest,
    *,
    ai_workroot_home: Path | str | None = None,
) -> str:
    started = time.perf_counter()
    record = find_workroot_by_cwd(request.cwd, ai_workroot_home=ai_workroot_home)
    db_path = Path(record["stateDirectory"]) / "cache/workroot.sqlite"
    selected: list[CandidateMatch] = []
    fts_matches: list[FtsMatch] = []
    relationship_signals: list[RelationshipSignal] = []
    release_report = ReleaseFilterReport(frozenset(), frozenset(), ())
    fts_error: str | None = None

    if db_path.is_file():
        with sqlite3.connect(db_path) as conn:
            candidates = query_context_candidates(conn, record["workrootId"], query=request.query, limit=50)
            release_report = load_release_filter_report(conn, record["workrootId"], candidates)
            candidates = _apply_release_filters(candidates, release_report)
            fts_matches, fts_error = search_fts(conn, record["workrootId"], request.query, limit=5)
            selected = _select_candidates(candidates, fts_matches)
            source_ids = {candidate.source_id for candidate in selected}
            relationship_signals = relationship_signals_for_sources(conn, record["workrootId"], source_ids, limit=10)
            selected = _boost_relationship_candidates(selected, relationship_signals)

    if not selected:
        selected = _fallback_user_asset_candidates(Path(record["userDirectory"]))

    rendered = _render_package(
        record=record,
        request=request,
        selected=selected,
        fts_matches=fts_matches,
        relationship_signals=relationship_signals,
        release_report=release_report,
        fts_error=fts_error,
        started=started,
        trim_steps=[],
    )
    rendered, trim_steps = _enforce_hard_token_limit(rendered, request.hard_token_limit)
    if trim_steps:
        rendered = _render_package(
            record=record,
            request=request,
            selected=selected,
            fts_matches=fts_matches,
            relationship_signals=relationship_signals,
            release_report=release_report,
            fts_error=fts_error,
            started=started,
            trim_steps=trim_steps,
        )
        rendered, fallback_steps = _enforce_hard_token_limit(rendered, request.hard_token_limit)
        trim_steps.extend(step for step in fallback_steps if step not in trim_steps)
        if fallback_steps:
            rendered = _append_trim_marker(rendered, trim_steps)
    return rendered


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


def _select_candidates(candidates: list[CandidateMatch], fts_matches: list[FtsMatch]) -> list[CandidateMatch]:
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
    return selected[:8]


def _apply_release_filters(candidates: list[CandidateMatch], release_report: ReleaseFilterReport) -> list[CandidateMatch]:
    filtered: list[CandidateMatch] = []
    for candidate in candidates:
        if candidate.source_id in release_report.protected_source_ids:
            continue
        if candidate.source_id in release_report.tombstone_source_ids:
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


def _render_package(
    *,
    record: dict[str, str],
    request: ContextRequest,
    selected: list[CandidateMatch],
    fts_matches: list[FtsMatch],
    relationship_signals: list[RelationshipSignal],
    release_report: ReleaseFilterReport,
    fts_error: str | None,
    started: float,
    trim_steps: list[str],
) -> str:
    body_for_tokens = "\n".join(candidate.summary for candidate in selected) + "\n" + request.query
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
    lines.extend(["", "## Selected Context"])
    if selected:
        for candidate in selected:
            reason_text = ", ".join(candidate.reasons)
            lines.append(f"- {candidate.title} [{reason_text}]")
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
            ]
        )
        if fts_error:
            lines.append(f"ftsFallback: {fts_error}")
        if trim_steps:
            lines.append(f"trimSteps: {', '.join(trim_steps)}")
        if release_report.dropped or release_report.tombstone_source_ids:
            dropped = ", ".join(f"{candidate_id}:{reason}" for candidate_id, reason in release_report.dropped) or "none"
            annotations = ", ".join(sorted(release_report.tombstone_source_ids)) or "none"
            lines.append(f"releaseFilters: dropped={dropped} annotated={annotations}")
    return "\n".join(lines) + "\n"


def _enforce_hard_token_limit(rendered: str, hard_token_limit: int) -> tuple[str, list[str]]:
    if estimate_tokens(rendered) <= hard_token_limit:
        return rendered, []
    char_limit = max(120, hard_token_limit * 4)
    trimmed = rendered[:char_limit].rstrip() + "\n"
    if estimate_tokens(trimmed) <= hard_token_limit:
        return trimmed, ["final-fallback"]
    return rendered[: max(80, hard_token_limit * 3)].rstrip() + "\n", ["final-fallback"]


def _append_trim_marker(rendered: str, trim_steps: list[str]) -> str:
    marker = "\ntrimSteps: " + ", ".join(trim_steps) + "\n"
    if "trimSteps:" in rendered:
        return rendered
    return rendered.rstrip() + marker
