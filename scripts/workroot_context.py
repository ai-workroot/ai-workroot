#!/usr/bin/env python3
"""Local Context Guide builder for AI Workroot."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
from pathlib import Path
import sqlite3
import time

try:
    from workroot_candidates import ContextCandidate, candidate_from_row, mark_candidates_used
    from workroot_indexing import search_fts
    from workroot_paths import workroot_sqlite_path
    from workroot_sqlite import open_sqlite
    from workroot_state import read_jsonl
except ModuleNotFoundError:  # pragma: no cover - package import path for tests.
    from scripts.workroot_candidates import ContextCandidate, candidate_from_row, mark_candidates_used
    from scripts.workroot_indexing import search_fts
    from scripts.workroot_paths import workroot_sqlite_path
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
BLOCKED_SAFETY_POLICIES = {"never-auto", "needs-confirmation", "sensitive"}
MAX_INITIAL_CANDIDATES = 200
SAFE_CANDIDATE_SQL = "(safety_policy IS NULL OR safety_policy = '' OR safety_policy NOT IN ('never-auto', 'needs-confirmation', 'sensitive'))"


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
    merged = deep_merge_dict(default_context_guide_config(), context)
    return merged, []


def deep_merge_dict(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    merged = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = deep_merge_dict(existing, value)
        else:
            merged[key] = value
    return merged


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


def candidate_score(candidate: ContextCandidate, boost: float = 0.0) -> float:
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
    return round(importance + policy + min(candidate.confidence, 1.0) * 0.1 + boost, 3)


def select_candidates(
    candidates: list[ContextCandidate],
    target_token_budget: int,
    score_boosts: dict[str, float] | None = None,
    reason_boosts: dict[str, list[str]] | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]], int]:
    selected: list[dict[str, object]] = []
    dropped: list[dict[str, object]] = []
    estimated_used = 0
    score_boosts = score_boosts or {}
    reason_boosts = reason_boosts or {}
    for candidate in candidates:
        score = candidate_score(candidate, score_boosts.get(candidate.candidate_id, 0.0))
        if candidate.safety_policy in BLOCKED_SAFETY_POLICIES:
            dropped.append(
                {
                    "candidateId": candidate.candidate_id,
                    "sourceType": candidate.source_type,
                    "reason": f"safety-{candidate.safety_policy}",
                    "scoreBeforeDrop": score,
                }
            )
            continue
        if candidate.context_policy == "never-auto":
            dropped.append(
                {
                    "candidateId": candidate.candidate_id,
                    "sourceType": candidate.source_type,
                    "reason": "never-auto",
                    "scoreBeforeDrop": score,
                }
            )
            continue
        if candidate.status != "active":
            dropped.append(
                {
                    "candidateId": candidate.candidate_id,
                    "sourceType": candidate.source_type,
                    "reason": candidate.status,
                    "scoreBeforeDrop": score,
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
                    "scoreBeforeDrop": score,
                }
            )
            continue
        estimated_used += token_estimate
        reasons = [candidate.context_policy, candidate.importance, *reason_boosts.get(candidate.candidate_id, [])]
        selected.append(
            {
                "candidateId": candidate.candidate_id,
                "sourceType": candidate.source_type,
                "sourceId": candidate.source_id,
                "title": candidate.title,
                "summary": candidate.summary,
                "score": score,
                "reasons": reasons,
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


def query_candidate_fts(
    conn: sqlite3.Connection,
    workroot_id: str,
    query: str,
    fts_fallbacks: list[dict[str, object]] | None = None,
) -> set[str]:
    if not query.strip():
        return set()
    queries = [query, f'"{query}"']
    if " " in query or "-" in query:
        terms = [part for part in query.replace("-", " ").split() if part]
        if terms:
            queries.append(" OR ".join(terms))
    rows = []
    for candidate_query in queries:
        try:
            rows = conn.execute(
                """
                SELECT context_candidates_fts.candidate_id
                FROM context_candidates_fts
                JOIN context_candidates c ON c.candidate_id = context_candidates_fts.candidate_id
                WHERE context_candidates_fts MATCH ?
                  AND c.workroot_id = ?
                LIMIT 25
                """,
                (candidate_query, workroot_id),
            ).fetchall()
        except sqlite3.OperationalError as exc:
            if fts_fallbacks is not None:
                fts_fallbacks.append(
                    {
                        "channel": "context-candidates-fts",
                        "query": candidate_query,
                        "error": str(exc),
                    }
                )
            continue
        if rows:
            break
    return {str(row[0]) for row in rows}


def split_reference_ids(value: str) -> set[str]:
    refs: set[str] = set()
    for part in value.replace(";", ",").split(","):
        ref = part.strip()
        if ref:
            refs.add(ref)
    return refs


def sql_placeholders(values: set[str] | list[str]) -> str:
    return ",".join("?" for _ in values)


def fetch_candidates_by_sql(
    conn: sqlite3.Connection,
    sql: str,
    params: list[object],
) -> list[ContextCandidate]:
    conn.row_factory = sqlite3.Row
    return [candidate_from_row(row) for row in conn.execute(sql, params).fetchall()]


def fetch_candidates_by_ids(
    conn: sqlite3.Connection,
    workroot_id: str,
    candidate_ids: set[str],
) -> list[ContextCandidate]:
    if not candidate_ids:
        return []
    ordered_ids = sorted(candidate_ids)
    return fetch_candidates_by_sql(
        conn,
        f"""
        SELECT *
        FROM context_candidates
        WHERE workroot_id = ?
          AND candidate_id IN ({sql_placeholders(ordered_ids)})
          AND {SAFE_CANDIDATE_SQL}
        ORDER BY candidate_id ASC
        """,
        [workroot_id, *ordered_ids],
    )


def build_candidate_pool(
    conn: sqlite3.Connection,
    workroot_id: str,
    current_state: dict[str, object],
    candidate_fts_matches: set[str],
    fts_candidate_ids: set[str],
    graph_candidate_ids: set[str],
    max_initial_candidates: int = MAX_INITIAL_CANDIDATES,
) -> tuple[list[ContextCandidate], dict[str, object]]:
    total_available = int(
        conn.execute("SELECT COUNT(*) FROM context_candidates WHERE workroot_id = ?", (workroot_id,)).fetchone()[0]
    )
    pool: dict[str, ContextCandidate] = {}
    source_counts: dict[str, int] = {}

    def add_candidates(source: str, rows: list[ContextCandidate]) -> None:
        source_counts[source] = len(rows)
        for candidate in rows:
            pool.setdefault(candidate.candidate_id, candidate)

    explicit_ids = candidate_fts_matches | fts_candidate_ids | graph_candidate_ids
    add_candidates("explicit-matches", fetch_candidates_by_ids(conn, workroot_id, explicit_ids))

    active_task = str(current_state.get("activeTaskId") or "")
    if active_task:
        active_task_rows = fetch_candidates_by_sql(
            conn,
            f"""
            SELECT *
            FROM context_candidates
            WHERE workroot_id = ?
              AND status = 'active'
              AND {SAFE_CANDIDATE_SQL}
              AND (source_id = ? OR related_tasks LIKE ?)
            ORDER BY updated_at DESC, candidate_id ASC
            LIMIT ?
            """,
            [workroot_id, active_task, f"%{active_task}%", max_initial_candidates],
        )
        add_candidates("active-task", active_task_rows)
    else:
        source_counts["active-task"] = 0

    always = fetch_candidates_by_sql(
        conn,
        f"""
        SELECT *
        FROM context_candidates
        WHERE workroot_id = ?
          AND status = 'active'
          AND context_policy = 'always'
          AND {SAFE_CANDIDATE_SQL}
        ORDER BY updated_at DESC, candidate_id ASC
        LIMIT ?
        """,
        [workroot_id, max_initial_candidates],
    )
    add_candidates("always", always)

    recent = fetch_candidates_by_sql(
        conn,
        f"""
        SELECT *
        FROM context_candidates
        WHERE workroot_id = ?
          AND status = 'active'
          AND context_policy != 'never-auto'
          AND {SAFE_CANDIDATE_SQL}
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
        LIMIT ?
        """,
        [workroot_id, max_initial_candidates],
    )
    add_candidates("recent-high-importance", recent)

    if len(pool) > max_initial_candidates:
        priority_ids = set(explicit_ids)
        if active_task:
            for candidate in pool.values():
                if candidate.source_id == active_task or active_task in split_reference_ids(candidate.related_tasks):
                    priority_ids.add(candidate.candidate_id)

        def pool_sort_key(candidate: ContextCandidate) -> tuple[int, float, str]:
            if candidate.candidate_id in priority_ids:
                priority = 0
            elif candidate.context_policy == "always":
                priority = 1
            else:
                priority = 2
            return (priority, -candidate_score(candidate), candidate.candidate_id)

        pool = {
            candidate.candidate_id: candidate
            for candidate in sorted(pool.values(), key=pool_sort_key)[:max_initial_candidates]
        }

    return list(pool.values()), {
        "strategy": "bounded-sql-pool",
        "size": len(pool),
        "maxInitialCandidates": max_initial_candidates,
        "totalAvailable": total_available,
        "sources": source_counts,
    }


def load_diagnostic_drops(conn: sqlite3.Connection, workroot_id: str, existing_drop_ids: set[str], limit: int = 50) -> list[dict[str, object]]:
    rows = fetch_candidates_by_sql(
        conn,
        """
        SELECT *
        FROM context_candidates
        WHERE workroot_id = ?
          AND (
            status != 'active'
            OR context_policy = 'never-auto'
            OR safety_policy IN ('never-auto', 'needs-confirmation', 'sensitive')
          )
        ORDER BY updated_at DESC, candidate_id ASC
        LIMIT ?
        """,
        [workroot_id, limit],
    )
    diagnostic_drops: list[dict[str, object]] = []
    for candidate in rows:
        if candidate.candidate_id in existing_drop_ids:
            continue
        score = candidate_score(candidate)
        if candidate.safety_policy in BLOCKED_SAFETY_POLICIES:
            reason = f"safety-{candidate.safety_policy}"
        elif candidate.context_policy == "never-auto":
            reason = "never-auto"
        else:
            reason = candidate.status
        diagnostic_drops.append(
            {
                "candidateId": candidate.candidate_id,
                "sourceType": candidate.source_type,
                "reason": reason,
                "scoreBeforeDrop": score,
            }
        )
    return diagnostic_drops


def load_candidate_quality_counts(conn: sqlite3.Connection, workroot_id: str) -> dict[str, int]:
    row = conn.execute(
        """
        SELECT
          COUNT(*) AS total_count,
          SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active_count,
          SUM(CASE WHEN status = 'stale' THEN 1 ELSE 0 END) AS stale_count,
          SUM(CASE WHEN context_policy = 'never-auto' THEN 1 ELSE 0 END) AS never_auto_count
        FROM context_candidates
        WHERE workroot_id = ?
        """,
        (workroot_id,),
    ).fetchone()
    return {
        "totalCount": int(row[0] or 0),
        "activeCount": int(row[1] or 0),
        "staleCount": int(row[2] or 0),
        "neverAutoCount": int(row[3] or 0),
    }


def merge_candidate_quality_counts(candidate_quality: dict[str, object], counts: dict[str, int]) -> dict[str, object]:
    candidate_quality.update(counts)
    return candidate_quality


def candidate_ids_from_fts_paths(conn: sqlite3.Connection, workroot_id: str, fts_matches: list[dict[str, object]]) -> set[str]:
    paths = [str(match.get("relativePath", "")) for match in fts_matches if match.get("relativePath")]
    if not paths:
        return set()
    placeholders = ",".join("?" for _ in paths)
    rows = conn.execute(
        f"""
        SELECT candidate_id
        FROM context_candidates
        WHERE workroot_id = ?
          AND source_id IN ({placeholders})
        """,
        [workroot_id, *paths],
    ).fetchall()
    return {str(row[0]) for row in rows}


RELATED_GRAPH_RELATIONS = {
    "belongs_to_task",
    "documented_in",
    "supersedes",
    "supports",
    "belongs_to_domain",
}


def query_terms_for_graph(query: str) -> set[str]:
    return {part.casefold() for part in query.replace("-", " ").split() if len(part) >= 3}


def load_graph_candidate_matches(
    conn: sqlite3.Connection,
    workroot_id: str,
    current_state: dict[str, object],
    query: str,
    seed_candidate_ids: set[str],
) -> set[str]:
    seed_ids = set(seed_candidate_ids)
    active_task = current_state.get("activeTaskId")
    if active_task:
        seed_ids.add(str(active_task))
    seed_candidate_rows = fetch_candidates_by_ids(conn, workroot_id, seed_candidate_ids)
    for candidate in seed_candidate_rows:
        seed_ids.add(candidate.candidate_id)
        seed_ids.add(candidate.source_id)
        seed_ids.update(split_reference_ids(candidate.related_tasks))
        seed_ids.update(split_reference_ids(candidate.related_assets))
    matched: set[str] = set()
    if seed_ids:
        seed_placeholders = ",".join("?" for _ in seed_ids)
        rel_placeholders = ",".join("?" for _ in RELATED_GRAPH_RELATIONS)
        rows = conn.execute(
            f"""
            SELECT e.from_node_id, e.to_node_id
            FROM graph_edges e
            WHERE (e.status IS NULL OR e.status = 'active')
              AND e.relation IN ({rel_placeholders})
              AND (e.from_node_id IN ({seed_placeholders}) OR e.to_node_id IN ({seed_placeholders}))
            """,
            [*RELATED_GRAPH_RELATIONS, *seed_ids, *seed_ids],
        ).fetchall()
        adjacent_node_ids: set[str] = set()
        for from_node_id, to_node_id in rows:
            for node_id in (str(from_node_id), str(to_node_id)):
                adjacent_node_ids.add(node_id)
        if adjacent_node_ids:
            ordered_node_ids = sorted(adjacent_node_ids)
            candidate_rows = conn.execute(
                f"""
                SELECT candidate_id
                FROM context_candidates
                WHERE workroot_id = ?
                  AND (candidate_id IN ({sql_placeholders(ordered_node_ids)}) OR source_id IN ({sql_placeholders(ordered_node_ids)}))
                """,
                [workroot_id, *ordered_node_ids, *ordered_node_ids],
            ).fetchall()
            matched.update(str(row[0]) for row in candidate_rows)
    return matched


def load_graph_signals(
    conn: sqlite3.Connection,
    selected: list[dict[str, object]],
    current_state: dict[str, object],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    seed_ids: set[str] = set()
    for item in selected:
        if item.get("candidateId"):
            seed_ids.add(str(item["candidateId"]))
        if item.get("sourceId"):
            seed_ids.add(str(item["sourceId"]))
    active_task = current_state.get("activeTaskId")
    if active_task:
        seed_ids.add(str(active_task))
    if not seed_ids:
        return [], []
    edge_rows: list[sqlite3.Row] = []
    seed_explanations: list[dict[str, object]] = []
    if seed_ids:
        placeholders = ",".join("?" for _ in seed_ids)
        seed_node_rows = conn.execute(
            f"""
            SELECT node_id, node_type, title, summary, importance
            FROM graph_nodes
            WHERE (status IS NULL OR status = 'active')
              AND node_id IN ({placeholders})
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
            """,
            [*seed_ids],
        ).fetchall()
        seed_explanations = [
            {
                "nodeId": str(row[0]),
                "nodeType": row[1] or "",
                "title": row[2] or "",
                "summary": row[3] or "",
                "importance": row[4] or "",
                "reason": "selected-candidate-or-active-task-seed",
            }
            for row in seed_node_rows
        ]
        rel_placeholders = ",".join("?" for _ in RELATED_GRAPH_RELATIONS)
        edge_rows = conn.execute(
            f"""
            SELECT
              e.edge_id,
              e.relation,
              e.from_node_id,
              e.to_node_id,
              n.node_id,
              n.node_type,
              n.title,
              n.summary,
              n.importance
            FROM graph_edges e
            JOIN graph_nodes n
              ON n.node_id = CASE
                WHEN e.from_node_id IN ({placeholders}) THEN e.to_node_id
                ELSE e.from_node_id
              END
            WHERE (e.status IS NULL OR e.status = 'active')
              AND (n.status IS NULL OR n.status = 'active')
              AND e.relation IN ({rel_placeholders})
              AND (e.from_node_id IN ({placeholders}) OR e.to_node_id IN ({placeholders}))
            ORDER BY
              CASE n.importance
                WHEN 'critical' THEN 0
                WHEN 'high' THEN 1
                WHEN 'normal' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
              END,
              n.node_id ASC
            LIMIT 10
            """,
            [*seed_ids, *RELATED_GRAPH_RELATIONS, *seed_ids, *seed_ids],
        ).fetchall()
    seen: set[str] = set()
    signals: list[dict[str, object]] = []
    for row in edge_rows:
        node_id = str(row[4])
        if node_id in seen:
            continue
        title = row[6] or ""
        summary = row[7] or ""
        seen.add(node_id)
        signals.append(
            {
                "nodeId": node_id,
                "nodeType": row[5],
                "title": title,
                "summary": summary,
                "importance": row[8] or "",
                "relation": row[1] or "",
            }
        )
        if len(signals) >= 10:
            break
    return signals, seed_explanations


def estimate_context_package_tokens(markdown: str) -> int:
    if not markdown:
        return 0
    cjk_chars = sum(1 for char in markdown if "\u4e00" <= char <= "\u9fff")
    word_tokens = len(re.findall(r"[A-Za-z0-9]+(?:[_-][A-Za-z0-9]+)*", markdown))
    symbol_tokens = len(re.findall(r"[^\w\s\u4e00-\u9fff]", markdown, re.UNICODE))
    long_runs = re.findall(r"[^\s]{24,}", markdown)
    long_run_extra = sum(max(0, math.ceil(len(run) / 8) - 1) for run in long_runs)
    line_tokens = max(0, markdown.count("\n") // 3)
    estimated = word_tokens + cjk_chars + math.ceil(symbol_tokens / 3) + long_run_extra + line_tokens
    return max(1, estimated)


def render_minimal_markdown(
    metadata: dict[str, object],
    current_state: dict[str, object],
    request: ContextRequest,
    trace: dict[str, object],
) -> str:
    token_budget = trace.get("tokenBudget", {})
    if not isinstance(token_budget, dict):
        token_budget = {}
    return "\n".join(
        [
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
            "Fallback: yes",
            "",
            "## Current State",
            "",
            f"- Active task: {current_state.get('activeTaskId', '')}",
        ]
    ) + "\n"


def enforce_rendered_token_limit(
    metadata: dict[str, object],
    current_state: dict[str, object],
    selected: list[dict[str, object]],
    fts_matches: list[dict[str, object]],
    graph_signals: list[dict[str, object]],
    request: ContextRequest,
    trace: dict[str, object],
) -> tuple[str, list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], int, dict[str, object]]:
    token_budget = trace.get("tokenBudget", {})
    hard_limit = int(token_budget.get("hard", 0)) if isinstance(token_budget, dict) else 0
    trim: dict[str, object] = {
        "applied": False,
        "reason": "",
        "removedGraphSignals": 0,
        "removedFtsMatches": 0,
        "removedCandidates": [],
        "steps": [],
        "finalFallback": False,
    }
    markdown = render_markdown(metadata, current_state, selected, fts_matches, graph_signals, request, trace)
    estimated = estimate_context_package_tokens(markdown)
    if hard_limit <= 0 or estimated <= hard_limit:
        return markdown, selected, fts_matches, graph_signals, estimated, trim

    trim["applied"] = True
    trim["reason"] = "hard-token-limit"
    removed_candidates: list[str] = []

    while graph_signals and estimated > hard_limit:
        graph_signals = graph_signals[:-1]
        trim["removedGraphSignals"] = int(trim["removedGraphSignals"]) + 1
        trim["steps"].append("remove-graph-signal")  # type: ignore[union-attr]
        markdown = render_markdown(metadata, current_state, selected, fts_matches, graph_signals, request, trace)
        estimated = estimate_context_package_tokens(markdown)

    while fts_matches and estimated > hard_limit:
        fts_matches = fts_matches[:-1]
        trim["removedFtsMatches"] = int(trim["removedFtsMatches"]) + 1
        trim["steps"].append("remove-fts-match")  # type: ignore[union-attr]
        markdown = render_markdown(metadata, current_state, selected, fts_matches, graph_signals, request, trace)
        estimated = estimate_context_package_tokens(markdown)

    while selected and estimated > hard_limit:
        removable_indexes = [
            index
            for index, item in enumerate(selected)
            if "always" not in item.get("reasons", [])
        ]
        if not removable_indexes:
            removable_indexes = list(range(len(selected)))
        remove_index = min(removable_indexes, key=lambda index: float(selected[index].get("score", 0.0)))
        removed = selected.pop(remove_index)
        removed_candidates.append(str(removed.get("candidateId")))
        trim["steps"].append("remove-candidate")  # type: ignore[union-attr]
        markdown = render_markdown(metadata, current_state, selected, fts_matches, graph_signals, request, trace)
        estimated = estimate_context_package_tokens(markdown)

    trim["removedCandidates"] = removed_candidates
    if estimated > hard_limit:
        selected = []
        fts_matches = []
        graph_signals = []
        markdown = render_minimal_markdown(metadata, current_state, request, trace)
        estimated = estimate_context_package_tokens(markdown)
        if estimated > hard_limit:
            markdown = "#\n"
            estimated = estimate_context_package_tokens(markdown)
        trim["finalFallback"] = True
        trim["steps"].append("final-fallback")  # type: ignore[union-attr]
    return markdown, selected, fts_matches, graph_signals, estimated, trim


def build_score_inputs(
    candidate_fts_matches: set[str],
    fts_candidate_ids: set[str],
    graph_candidate_ids: set[str],
) -> tuple[dict[str, float], dict[str, list[str]]]:
    boosts: dict[str, float] = {}
    reasons: dict[str, list[str]] = {}
    for candidate_id in candidate_fts_matches:
        boosts[candidate_id] = boosts.get(candidate_id, 0.0) + 0.2
        reasons.setdefault(candidate_id, []).append("candidate-fts-match")
    for candidate_id in fts_candidate_ids:
        boosts[candidate_id] = boosts.get(candidate_id, 0.0) + 0.15
        reasons.setdefault(candidate_id, []).append("file-fts-match")
    for candidate_id in graph_candidate_ids:
        boosts[candidate_id] = boosts.get(candidate_id, 0.0) + 0.55
        reasons.setdefault(candidate_id, []).append("graph-one-hop-match")
    return boosts, reasons


def sort_candidates(candidates: list[ContextCandidate], score_boosts: dict[str, float]) -> list[ContextCandidate]:
    return sorted(candidates, key=lambda candidate: candidate_score(candidate, score_boosts.get(candidate.candidate_id, 0.0)), reverse=True)


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


def write_context_package(state_directory: Path, markdown: str, trace: dict[str, object], retention: int = 50) -> None:
    package_dir = state_directory / "context/packages"
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "latest.md").write_text(markdown, encoding="utf-8")
    history_dir = package_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    trace_id = str(trace.get("traceId", "trace"))
    agent = str(trace.get("agent", "agent"))
    mode = str(trace.get("contextMode", "standard"))
    history_path = history_dir / f"{trace_id}-{agent}-{mode}.md"
    history_path.write_text(markdown, encoding="utf-8")
    history = sorted(history_dir.glob("*.md"), key=lambda path: path.stat().st_mtime)
    for path in history[:-retention]:
        path.unlink()


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
    db_path = workroot_sqlite_path(state_directory)

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
        "ftsFallbacks": [],
        "graphSignals": [],
        "graphSeedExplanations": [],
        "candidateQueryMatches": [],
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
        workroot_id = str(metadata.get("workrootId"))
        trace["challengers"].append({"name": "current-state", "status": "pass", "count": 1 if current_state else 0})
        query = request.query or str(current_state.get("currentFocus", ""))
        span = time.perf_counter()
        fts_fallbacks: list[dict[str, object]] = []
        try:
            fts_matches = search_fts(conn, workroot_id, query, limit=5) if query.strip() else []
        except sqlite3.OperationalError as exc:
            fts_matches = []
            fts_fallbacks.append({"channel": "indexed-chunks-fts", "query": query, "error": str(exc)})
        timing["fts"] = int((time.perf_counter() - span) * 1000)
        trace["ftsFallbacks"] = fts_fallbacks
        trace["challengers"].append(
            {
                "name": "fts",
                "status": "fallback" if fts_fallbacks else "pass",
                "count": len(fts_matches),
                "query": query,
            }
        )
        span = time.perf_counter()
        candidate_fts_matches = query_candidate_fts(conn, workroot_id, query, fts_fallbacks)
        fts_candidate_ids = candidate_ids_from_fts_paths(conn, workroot_id, fts_matches)
        graph_candidate_ids = load_graph_candidate_matches(
            conn,
            workroot_id,
            current_state,
            query,
            candidate_fts_matches | fts_candidate_ids,
        )
        score_boosts, reason_boosts = build_score_inputs(candidate_fts_matches, fts_candidate_ids, graph_candidate_ids)
        candidate_quality_counts = load_candidate_quality_counts(conn, workroot_id)
        candidates, candidate_pool = build_candidate_pool(
            conn,
            workroot_id,
            current_state,
            candidate_fts_matches,
            fts_candidate_ids,
            graph_candidate_ids,
        )
        candidates = sort_candidates(candidates, score_boosts)
        timing["queryCandidates"] = int((time.perf_counter() - span) * 1000)
        trace["candidatePool"] = candidate_pool
        trace["challengers"].append({"name": "materialized-candidates", "status": "pass", "count": len(candidates)})
        trace["candidateQueryMatches"] = sorted(candidate_fts_matches | fts_candidate_ids | graph_candidate_ids)
        selected, dropped, estimated_used = select_candidates(
            candidates,
            budget.target_tokens,
            score_boosts=score_boosts,
            reason_boosts=reason_boosts,
        )
        dropped.extend(
            load_diagnostic_drops(
                conn,
                workroot_id,
                {str(item.get("candidateId")) for item in dropped},
            )
        )
        timing["scoring"] = int((time.perf_counter() - span) * 1000)
        span = time.perf_counter()
        graph_signals, graph_seed_explanations = load_graph_signals(conn, selected, current_state)
        timing["graphExpansion"] = int((time.perf_counter() - span) * 1000)
        trace["challengers"].append({"name": "graph", "status": "pass", "count": len(graph_signals)})
        trace["graphSeedExplanations"] = graph_seed_explanations

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
    candidate_quality = merge_candidate_quality_counts(candidate_quality, candidate_quality_counts)
    if "candidatePool" in trace and isinstance(trace["candidatePool"], dict):
        candidate_quality["totalAvailable"] = trace["candidatePool"].get("totalAvailable", len(candidates))
    confidence, confidence_reasons = compute_confidence(current_state, selected, candidate_quality, fts_matches)
    trace["candidateQuality"] = candidate_quality
    trace["confidence"] = confidence
    trace["confidenceReasons"] = confidence_reasons
    if should_escalate_to_quality(budget, confidence, current_state, fts_matches):
        pre_escalation_confidence = confidence
        quality_target, quality_hard, quality_latency = mode_budget(config, "quality")
        if request.target_token_budget:
            quality_target = request.target_token_budget
        if request.hard_token_budget:
            quality_hard = request.hard_token_budget
        selected, dropped, estimated_used = select_candidates(
            candidates,
            quality_target,
            score_boosts=score_boosts,
            reason_boosts=reason_boosts,
        )
        with open_sqlite(db_path) as conn:
            dropped.extend(
                load_diagnostic_drops(
                    conn,
                    str(metadata.get("workrootId")),
                    {str(item.get("candidateId")) for item in dropped},
                )
            )
        candidate_quality = summarize_candidate_quality(candidates, dropped)
        candidate_quality = merge_candidate_quality_counts(candidate_quality, candidate_quality_counts)
        if "candidatePool" in trace and isinstance(trace["candidatePool"], dict):
            candidate_quality["totalAvailable"] = trace["candidatePool"].get("totalAvailable", len(candidates))
        confidence, confidence_reasons = compute_confidence(current_state, selected, candidate_quality, fts_matches)
        trace["selectedCandidates"] = selected
        trace["droppedCandidates"] = dropped
        trace["candidateQuality"] = candidate_quality
        trace["confidence"] = confidence
        trace["confidenceReasons"] = confidence_reasons
        trace["contextMode"] = "quality"
        trace["qualityBehavior"] = "quality-budget-expansion"
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
    full_token_estimate = estimate_context_package_tokens(markdown)
    token_budget = trace.get("tokenBudget", {})
    if isinstance(token_budget, dict):
        token_budget["candidateTokens"] = estimated_used
        token_budget["estimatedUsed"] = full_token_estimate
        trace["tokenBudget"] = token_budget
    markdown, selected, fts_matches, graph_signals, full_token_estimate, budget_trim = enforce_rendered_token_limit(
        metadata,
        current_state,
        selected,
        fts_matches,
        graph_signals,
        request,
        trace,
    )
    trace["selectedCandidates"] = selected
    trace["ftsMatches"] = fts_matches
    trace["graphSignals"] = graph_signals
    trace["budgetTrim"] = budget_trim
    token_budget = trace.get("tokenBudget", {})
    if isinstance(token_budget, dict):
        token_budget["estimatedUsed"] = full_token_estimate
        trace["tokenBudget"] = token_budget
    if selected:
        with open_sqlite(db_path) as conn:
            mark_candidates_used(conn, str(metadata.get("workrootId")), [str(item["candidateId"]) for item in selected], now=now)
    write_context_package(state_directory, markdown, trace)

    if request.debug:
        write_debug_trace(state_directory / "context/debug", trace)

    return ContextPackage(markdown=markdown, state_directory=state_directory, trace=trace)
