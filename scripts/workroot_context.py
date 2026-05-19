#!/usr/bin/env python3
"""Local Context Guide builder for AI Workroot."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
import time

try:
    from workroot_candidates import ContextCandidate, mark_candidates_used
    from workroot_indexing import search_fts
    from workroot_sqlite import open_sqlite
    from workroot_state import read_jsonl
except ModuleNotFoundError:  # pragma: no cover - package import path for tests.
    from scripts.workroot_candidates import ContextCandidate, mark_candidates_used
    from scripts.workroot_indexing import search_fts
    from scripts.workroot_sqlite import open_sqlite
    from scripts.workroot_state import read_jsonl


@dataclass(frozen=True)
class ContextRequest:
    home: Path
    agent: str
    cwd: Path
    query: str = ""
    debug: bool = False
    now: str = ""
    target_token_budget: int = 0
    hard_token_budget: int = 0
    mode: str = ""
    deep: bool = False
    max_latency_ms: int = 0


@dataclass(frozen=True)
class ContextPackage:
    markdown: str
    state_directory: Path
    trace: dict[str, object]


DEFAULT_CONTEXT_GUIDE_CONFIG: dict[str, object] = {
    "defaultMode": "standard",
    "latency": {
        "targetMs": 1000,
        "standardSoftLimitMs": 2000,
        "qualitySoftLimitMs": 3000,
    },
    "agentBudgets": {
        "codex": {
            "targetTokens": 4000,
            "hardTokenLimit": 6000,
        },
        "claude": {
            "targetTokens": 5000,
            "hardTokenLimit": 8000,
        },
        "default": {
            "targetTokens": 4000,
            "hardTokenLimit": 6000,
        },
    },
    "modes": {
        "fast": {
            "targetTokens": 2500,
            "hardTokenLimit": 4000,
            "maxLatencyMs": 1000,
        },
        "standard": {
            "targetTokens": 4000,
            "hardTokenLimit": 6000,
            "targetLatencyMs": 1000,
            "softLatencyMs": 2000,
        },
        "quality": {
            "targetTokens": 8000,
            "hardTokenLimit": 12000,
            "softLatencyMs": 3000,
        },
        "deep": {
            "requiresExplicitRequest": True,
            "targetTokens": 12000,
            "hardTokenLimit": 20000,
        },
    },
    "hotPath": {
        "allowRemoteLlm": False,
        "allowRemoteEmbedding": False,
        "allowVectorSearch": False,
        "allowFullDirectoryScan": False,
        "allowIndexRebuild": False,
        "allowMaintenanceJob": False,
    },
}


@dataclass(frozen=True)
class ContextBudget:
    mode: str
    requested_mode: str
    target_tokens: int
    hard_token_limit: int
    max_latency_ms: int
    source: str
    config_fallbacks: tuple[str, ...] = ()


def default_context_guide_config() -> dict[str, object]:
    return json.loads(json.dumps(DEFAULT_CONTEXT_GUIDE_CONFIG))


def resolve_workroot(home: Path, cwd: Path) -> tuple[dict[str, object], Path]:
    cwd = cwd.resolve()
    matches = []
    for record in read_jsonl(home / "registry/workroots.jsonl"):
        user_directory = Path(str(record.get("userDirectory", ""))).resolve()
        try:
            inside = cwd == user_directory or cwd.relative_to(user_directory) is not None
        except ValueError:
            inside = False
        if inside:
            matches.append(record)
    if not matches:
        raise SystemExit(f"no Workroot registered for cwd: {cwd}")
    record = max(matches, key=lambda row: len(str(row.get("userDirectory", ""))))
    state_directory = Path(str(record.get("stateDirectory", ""))).resolve()
    metadata = json.loads((state_directory / "workroot.json").read_text(encoding="utf-8"))
    return metadata, state_directory


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_context_guide_config(state_directory: Path) -> tuple[dict[str, object], list[str]]:
    path = state_directory / "state/runtime-hints.json"
    if not path.exists():
        return default_context_guide_config(), ["runtime-hints-missing"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default_context_guide_config(), ["runtime-hints-malformed"]
    context = payload.get("contextGuide")
    if not isinstance(context, dict):
        return default_context_guide_config(), ["runtime-hints-missing-contextGuide"]
    merged = default_context_guide_config()
    for key, value in context.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = dict(merged[key])  # type: ignore[index]
            nested.update(value)
            merged[key] = nested
        else:
            merged[key] = value
    return merged, []


def positive_int(value: object, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a positive integer") from exc
    if parsed <= 0:
        raise ValueError(f"{field_name} must be positive")
    return parsed


def resolve_context_budget(config: dict[str, object], request: ContextRequest) -> ContextBudget:
    agent_budgets = config.get("agentBudgets", {})
    fallbacks: list[str] = []
    if request.target_token_budget < 0:
        raise ValueError("target token budget must be positive")
    if request.hard_token_budget < 0:
        raise ValueError("hard token limit must be positive")
    if request.max_latency_ms < 0:
        raise ValueError("max latency must be positive")
    if not isinstance(agent_budgets, dict):
        agent_budgets = DEFAULT_CONTEXT_GUIDE_CONFIG["agentBudgets"]  # type: ignore[assignment]
        fallbacks.append("runtime-hints-invalid-agentBudgets")
    budget_payload = agent_budgets.get(request.agent) or agent_budgets.get("default") or {}
    if not isinstance(budget_payload, dict):
        budget_payload = {}
        fallbacks.append(f"runtime-hints-invalid-agent-budget:{request.agent}")
    requested_mode = "deep" if request.deep else (request.mode or str(config.get("defaultMode") or "standard"))
    modes = config.get("modes", {})
    if not isinstance(modes, dict):
        modes = DEFAULT_CONTEXT_GUIDE_CONFIG["modes"]  # type: ignore[assignment]
        fallbacks.append("runtime-hints-invalid-modes")
    if requested_mode not in modes:
        raise ValueError(f"unsupported context mode: {requested_mode}")
    mode_payload = modes.get(requested_mode, {})
    if not isinstance(mode_payload, dict):
        mode_payload = {}
        fallbacks.append(f"runtime-hints-invalid-mode:{requested_mode}")
    if requested_mode == "standard":
        default_target = budget_payload.get("targetTokens") or mode_payload.get("targetTokens") or 4000
        default_hard = budget_payload.get("hardTokenLimit") or mode_payload.get("hardTokenLimit") or 6000
    else:
        default_target = mode_payload.get("targetTokens") or budget_payload.get("targetTokens") or 4000
        default_hard = mode_payload.get("hardTokenLimit") or budget_payload.get("hardTokenLimit") or 6000
    try:
        target_tokens = positive_int(request.target_token_budget or default_target, "target token budget")
        hard_token_limit = positive_int(request.hard_token_budget or default_hard, "hard token limit")
    except ValueError:
        target_tokens = positive_int(DEFAULT_CONTEXT_GUIDE_CONFIG["agentBudgets"]["default"]["targetTokens"], "target token budget")  # type: ignore[index]
        hard_token_limit = positive_int(DEFAULT_CONTEXT_GUIDE_CONFIG["agentBudgets"]["default"]["hardTokenLimit"], "hard token limit")  # type: ignore[index]
        fallbacks.append("runtime-hints-invalid-budget")
    if target_tokens > hard_token_limit:
        raise ValueError(f"target token budget {target_tokens} exceeds hard token limit {hard_token_limit}")
    try:
        max_latency_ms = positive_int(
            request.max_latency_ms
            or mode_payload.get("softLatencyMs")
            or mode_payload.get("maxLatencyMs")
            or mode_payload.get("targetLatencyMs")
            or 1000,
            "max latency",
        )
    except ValueError:
        max_latency_ms = 1000
        fallbacks.append("runtime-hints-invalid-latency")
    return ContextBudget(
        mode=requested_mode,
        requested_mode=requested_mode,
        target_tokens=target_tokens,
        hard_token_limit=hard_token_limit,
        max_latency_ms=max_latency_ms,
        source=f"agent:{request.agent}" if request.agent in agent_budgets else "agent:default",
        config_fallbacks=tuple(fallbacks),
    )


def mode_budget(config: dict[str, object], mode: str) -> tuple[int, int, int]:
    modes = config.get("modes", {})
    if not isinstance(modes, dict):
        modes = DEFAULT_CONTEXT_GUIDE_CONFIG["modes"]  # type: ignore[assignment]
    payload = modes.get(mode, {})
    if not isinstance(payload, dict):
        payload = {}
    target = positive_int(payload.get("targetTokens") or DEFAULT_CONTEXT_GUIDE_CONFIG["modes"][mode]["targetTokens"], "target token budget")  # type: ignore[index]
    hard = positive_int(payload.get("hardTokenLimit") or DEFAULT_CONTEXT_GUIDE_CONFIG["modes"][mode]["hardTokenLimit"], "hard token limit")  # type: ignore[index]
    latency = positive_int(
        payload.get("softLatencyMs")
        or payload.get("maxLatencyMs")
        or payload.get("targetLatencyMs")
        or DEFAULT_CONTEXT_GUIDE_CONFIG["latency"]["qualitySoftLimitMs"],  # type: ignore[index]
        "max latency",
    )
    return target, hard, latency


def candidate_score(candidate: ContextCandidate) -> float:
    importance = {
        "critical": 1.0,
        "high": 0.9,
        "normal": 0.7,
        "low": 0.4,
    }.get(candidate.importance, 0.6)
    policy = {
        "always": 0.2,
        "task-related": 0.1,
        "summary-first": 0.05,
        "on-demand": 0.0,
    }.get(candidate.context_policy, 0.0)
    return round(importance + policy + min(candidate.confidence, 1.0) * 0.1, 3)


def select_candidates(
    candidates: list[ContextCandidate],
    target_token_budget: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]], int]:
    selected: list[dict[str, object]] = []
    dropped: list[dict[str, object]] = []
    estimated_used = 0
    for candidate in candidates:
        if candidate.context_policy == "never-auto":
            dropped.append(
                {
                    "candidateId": candidate.candidate_id,
                    "sourceType": candidate.source_type,
                    "reason": "never-auto",
                    "scoreBeforeDrop": candidate_score(candidate),
                }
            )
            continue
        if candidate.status != "active":
            dropped.append(
                {
                    "candidateId": candidate.candidate_id,
                    "sourceType": candidate.source_type,
                    "reason": candidate.status,
                    "scoreBeforeDrop": candidate_score(candidate),
                }
            )
            continue
        token_estimate = candidate.token_estimate or max(1, len((candidate.title + " " + candidate.summary).split()))
        if estimated_used + token_estimate > target_token_budget:
            dropped.append(
                {
                    "candidateId": candidate.candidate_id,
                    "sourceType": candidate.source_type,
                    "reason": "token-budget",
                    "scoreBeforeDrop": candidate_score(candidate),
                }
            )
            continue
        estimated_used += token_estimate
        selected.append(
            {
                "candidateId": candidate.candidate_id,
                "sourceType": candidate.source_type,
                "title": candidate.title,
                "summary": candidate.summary,
                "score": candidate_score(candidate),
                "reasons": [candidate.context_policy, candidate.importance],
                "tokenEstimate": token_estimate,
            }
        )
    return selected, dropped, estimated_used


def summarize_candidate_quality(candidates: list[ContextCandidate], dropped: list[dict[str, object]]) -> dict[str, object]:
    active = [candidate for candidate in candidates if candidate.status == "active"]
    confidences = [candidate.confidence for candidate in active]
    low_confidence_count = sum(1 for value in confidences if value < 0.5)
    return {
        "totalCount": len(candidates),
        "activeCount": len(active),
        "staleCount": sum(1 for candidate in candidates if candidate.status == "stale"),
        "neverAutoCount": sum(1 for candidate in candidates if candidate.context_policy == "never-auto"),
        "lowConfidenceCount": low_confidence_count,
        "droppedCount": len(dropped),
        "averageConfidence": round(sum(confidences) / len(confidences), 3) if confidences else 0.0,
    }


def compute_confidence(
    current_state: dict[str, object],
    selected: list[dict[str, object]],
    candidate_quality: dict[str, object],
    fts_matches: list[dict[str, object]],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    has_active_task = bool(current_state.get("activeTaskId"))
    if has_active_task:
        reasons.append("active task resolved")
    else:
        reasons.append("active task missing")
    if selected:
        reasons.append("selected context candidates")
    else:
        reasons.append("no selected context candidates")
    if not fts_matches:
        reasons.append("FTS results sparse")
    stale_count = int(candidate_quality.get("staleCount", 0))
    if stale_count:
        reasons.append("some context candidates are stale")
    if selected and has_active_task and fts_matches:
        return "high", reasons
    if selected:
        return "medium", reasons
    return "low", reasons


def should_escalate_to_quality(
    budget: ContextBudget,
    confidence: str,
    current_state: dict[str, object],
    fts_matches: list[dict[str, object]],
) -> bool:
    if budget.mode != "standard":
        return False
    if confidence == "low":
        return True
    if confidence == "medium" and not current_state.get("activeTaskId"):
        return True
    if confidence == "medium" and not fts_matches:
        return True
    return False


def load_all_candidate_rows(conn: sqlite3.Connection, workroot_id: str) -> list[ContextCandidate]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM context_candidates WHERE workroot_id = ? ORDER BY updated_at DESC, candidate_id ASC",
        (workroot_id,),
    ).fetchall()
    candidates = [
        ContextCandidate(
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
            status=row["status"] or "active",
            context_policy=row["context_policy"] or "task-related",
            safety_policy=row["safety_policy"] or "",
            token_estimate=int(row["token_estimate"] or 0),
            updated_at=row["updated_at"] or "",
            last_used_at=row["last_used_at"] or "",
        )
        for row in rows
    ]
    return sorted(candidates, key=candidate_score, reverse=True)


def load_graph_signals(conn: sqlite3.Connection) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT node_id, node_type, title, summary, importance
        FROM graph_nodes
        WHERE status IS NULL OR status = 'active'
        ORDER BY
          CASE importance
            WHEN 'critical' THEN 0
            WHEN 'high' THEN 1
            WHEN 'normal' THEN 2
            WHEN 'low' THEN 3
            ELSE 4
          END,
          node_id ASC
        LIMIT 10
        """
    ).fetchall()
    return [
        {
            "nodeId": row[0],
            "nodeType": row[1],
            "title": row[2] or "",
            "summary": row[3] or "",
            "importance": row[4] or "",
        }
        for row in rows
    ]


def render_markdown(
    metadata: dict[str, object],
    current_state: dict[str, object],
    selected: list[dict[str, object]],
    fts_matches: list[dict[str, object]],
    graph_signals: list[dict[str, object]],
    request: ContextRequest,
    trace: dict[str, object],
) -> str:
    token_budget = trace.get("tokenBudget", {})
    if not isinstance(token_budget, dict):
        token_budget = {}
    fallback_status = "yes" if trace.get("fallbacks") else "no"
    confidence_reasons = trace.get("confidenceReasons", [])
    if not isinstance(confidence_reasons, list):
        confidence_reasons = []
    lines = [
        "# AI Workroot Context Package",
        "",
        f"Agent: {request.agent}",
        f"Workroot: {metadata.get('workrootId')} - {metadata.get('name')}",
        "",
        "## Context Metadata",
        "",
        f"Mode: {trace.get('contextMode', 'standard')}",
        f"Confidence: {trace.get('confidence', 'medium')}",
        f"Latency: {trace.get('latencyMs', 0)}ms",
        f"Tokens: {token_budget.get('estimatedUsed', 0)} / {token_budget.get('hard', '')}",
        f"Fallback: {fallback_status}",
        "",
        "Reason:",
        *(f"- {reason}" for reason in confidence_reasons),
        "",
        "## Current State",
        "",
        f"- Current focus: {current_state.get('currentFocus', '')}",
        f"- Active task: {current_state.get('activeTaskId', '')}",
        f"- Next action: {current_state.get('nextSuggestedAction', '')}",
        "",
        "## Selected Context",
        "",
    ]
    if selected:
        for item in selected:
            lines.append(f"- {item['title']}: {item['summary']}")
    else:
        lines.append("- No selected candidates.")
    lines.extend(["", "## FTS Matches", ""])
    if fts_matches:
        for match in fts_matches:
            heading = f" ({match['heading']})" if match.get("heading") else ""
            lines.append(f"- {match['relativePath']}{heading}: {match['snippet']}")
    else:
        lines.append("- No FTS matches.")
    lines.extend(["", "## Graph Signals", ""])
    if graph_signals:
        for signal in graph_signals:
            lines.append(f"- {signal['title']}: {signal['summary']}")
    else:
        lines.append("- No graph signals.")
    lines.extend(["", "## Guardrails", "", "- Use local managed state only; do not write managed state into the user directory."])
    return "\n".join(lines) + "\n"


def write_context_package(state_directory: Path, markdown: str) -> None:
    package_dir = state_directory / "context/packages"
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "latest.md").write_text(markdown, encoding="utf-8")
    history_dir = package_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)


def write_debug_trace(debug_dir: Path, trace: dict[str, object], retention: int = 50) -> None:
    debug_dir.mkdir(parents=True, exist_ok=True)
    history_dir = debug_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    trace_id = str(trace.get("traceId", "trace"))
    text = json.dumps(trace, ensure_ascii=False, indent=2) + "\n"
    (debug_dir / "latest.json").write_text(text, encoding="utf-8")
    (history_dir / f"{trace_id}.json").write_text(text, encoding="utf-8")
    history = sorted(history_dir.glob("*.json"), key=lambda path: path.stat().st_mtime)
    for path in history[:-retention]:
        path.unlink()


def build_context_package(request: ContextRequest) -> ContextPackage:
    started = time.perf_counter()
    now = request.now or "1970-01-01T00:00:00Z"
    timing: dict[str, int] = {}
    span = time.perf_counter()
    metadata, state_directory = resolve_workroot(request.home.resolve(), request.cwd.resolve())
    timing["resolveWorkroot"] = int((time.perf_counter() - span) * 1000)
    span = time.perf_counter()
    current_state = read_json(state_directory / "state/current.json")
    config, config_fallbacks = load_context_guide_config(state_directory)
    budget = resolve_context_budget(config, request)
    fallbacks = [*config_fallbacks, *budget.config_fallbacks]
    timing["loadState"] = int((time.perf_counter() - span) * 1000)
    db_path = state_directory / "indexes/workroot.sqlite"

    trace: dict[str, object] = {
        "schemaVersion": "0.9.529",
        "traceId": f"trace_{now.replace('-', '').replace(':', '').replace('T', '_').replace('Z', '')}",
        "workrootId": metadata.get("workrootId"),
        "agent": request.agent,
        "cwd": str(request.cwd.resolve()),
        "startedAt": now,
        "requestedMode": budget.requested_mode,
        "contextMode": budget.mode,
        "modeSwitchReason": None,
        "qualitySoftLimitMs": budget.max_latency_ms if budget.mode == "quality" else None,
        "deepExplicitlyRequested": request.deep,
        "confidence": "medium",
        "confidenceReasons": [],
        "resolution": {
            "strategy": "nearest-registered-workroot",
            "workrootId": metadata.get("workrootId"),
            "matchedDirectory": metadata.get("userDirectory"),
            "stateDirectory": str(state_directory),
        },
        "challengers": [],
        "selectedCandidates": [],
        "droppedCandidates": [],
        "ftsMatches": [],
        "graphSignals": [],
        "timing": timing,
        "candidateQuality": {},
        "tokenBudget": {
            "target": budget.target_tokens,
            "hard": budget.hard_token_limit,
            "estimatedUsed": 0,
            "source": budget.source,
        },
        "fallbacks": fallbacks,
    }

    with open_sqlite(db_path) as conn:
        trace["challengers"].append({"name": "current-state", "status": "pass", "count": 1 if current_state else 0})
        span = time.perf_counter()
        candidates = load_all_candidate_rows(conn, str(metadata.get("workrootId")))
        timing["queryCandidates"] = int((time.perf_counter() - span) * 1000)
        span = time.perf_counter()
        selected, dropped, estimated_used = select_candidates(candidates, budget.target_tokens)
        timing["scoring"] = int((time.perf_counter() - span) * 1000)
        trace["challengers"].append({"name": "materialized-candidates", "status": "pass", "count": len(candidates)})
        query = request.query or str(current_state.get("currentFocus", ""))
        span = time.perf_counter()
        fts_matches = search_fts(conn, str(metadata.get("workrootId")), query, limit=5) if query.strip() else []
        timing["fts"] = int((time.perf_counter() - span) * 1000)
        trace["challengers"].append({"name": "fts", "status": "pass", "count": len(fts_matches), "query": query})
        span = time.perf_counter()
        graph_signals = load_graph_signals(conn)
        timing["graphExpansion"] = int((time.perf_counter() - span) * 1000)
        trace["challengers"].append({"name": "graph", "status": "pass", "count": len(graph_signals)})
        if selected:
            mark_candidates_used(conn, [str(item["candidateId"]) for item in selected], now=now)

    latency_ms = int((time.perf_counter() - started) * 1000)
    trace["completedAt"] = now
    trace["latencyMs"] = latency_ms
    trace["selectedCandidates"] = selected
    trace["droppedCandidates"] = dropped
    trace["ftsMatches"] = fts_matches
    trace["graphSignals"] = graph_signals
    trace["tokenBudget"] = {
        "target": budget.target_tokens,
        "hard": budget.hard_token_limit,
        "estimatedUsed": estimated_used,
        "source": budget.source,
    }
    candidate_quality = summarize_candidate_quality(candidates, dropped)
    confidence, confidence_reasons = compute_confidence(current_state, selected, candidate_quality, fts_matches)
    trace["candidateQuality"] = candidate_quality
    trace["confidence"] = confidence
    trace["confidenceReasons"] = confidence_reasons
    if should_escalate_to_quality(budget, confidence, current_state, fts_matches):
        pre_escalation_confidence = confidence
        quality_target, quality_hard, quality_latency = mode_budget(config, "quality")
        selected, dropped, estimated_used = select_candidates(candidates, quality_target)
        candidate_quality = summarize_candidate_quality(candidates, dropped)
        confidence, confidence_reasons = compute_confidence(current_state, selected, candidate_quality, fts_matches)
        trace["selectedCandidates"] = selected
        trace["droppedCandidates"] = dropped
        trace["candidateQuality"] = candidate_quality
        trace["confidence"] = confidence
        trace["confidenceReasons"] = confidence_reasons
        trace["contextMode"] = "quality"
        if not current_state.get("activeTaskId"):
            switch_detail = "missing active task"
        elif not fts_matches:
            switch_detail = "sparse FTS results"
        else:
            switch_detail = "low local confidence"
        trace["modeSwitchReason"] = f"standard candidate set had {pre_escalation_confidence} confidence and {switch_detail}"
        trace["qualitySoftLimitMs"] = quality_latency
        trace["tokenBudget"] = {
            "target": quality_target,
            "hard": quality_hard,
            "estimatedUsed": estimated_used,
            "source": budget.source,
        }
    timing["packageBuild"] = int((time.perf_counter() - started) * 1000)
    trace["timing"] = timing
    markdown = render_markdown(metadata, current_state, selected, fts_matches, graph_signals, request, trace)
    write_context_package(state_directory, markdown)

    if request.debug:
        write_debug_trace(state_directory / "context/debug", trace)

    return ContextPackage(markdown=markdown, state_directory=state_directory, trace=trace)
