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
    target_token_budget: int = 4000
    hard_token_budget: int = 6000


@dataclass(frozen=True)
class ContextPackage:
    markdown: str
    state_directory: Path
    trace: dict[str, object]


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
) -> str:
    lines = [
        "# AI Workroot Context Package",
        "",
        f"Agent: {request.agent}",
        f"Workroot: {metadata.get('workrootId')} - {metadata.get('name')}",
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
    metadata, state_directory = resolve_workroot(request.home.resolve(), request.cwd.resolve())
    current_state = read_json(state_directory / "state/current.json")
    db_path = state_directory / "indexes/workroot.sqlite"

    trace: dict[str, object] = {
        "schemaVersion": "0.9.529",
        "traceId": f"trace_{now.replace('-', '').replace(':', '').replace('T', '_').replace('Z', '')}",
        "workrootId": metadata.get("workrootId"),
        "agent": request.agent,
        "cwd": str(request.cwd.resolve()),
        "startedAt": now,
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
        "tokenBudget": {
            "target": request.target_token_budget,
            "hard": request.hard_token_budget,
            "estimatedUsed": 0,
        },
        "fallbacks": [],
    }

    with open_sqlite(db_path) as conn:
        trace["challengers"].append({"name": "current-state", "status": "pass", "count": 1 if current_state else 0})
        candidates = load_all_candidate_rows(conn, str(metadata.get("workrootId")))
        selected, dropped, estimated_used = select_candidates(candidates, request.target_token_budget)
        trace["challengers"].append({"name": "materialized-candidates", "status": "pass", "count": len(candidates)})
        query = request.query or str(current_state.get("currentFocus", ""))
        fts_matches = search_fts(conn, str(metadata.get("workrootId")), query, limit=5) if query.strip() else []
        trace["challengers"].append({"name": "fts", "status": "pass", "count": len(fts_matches), "query": query})
        graph_signals = load_graph_signals(conn)
        trace["challengers"].append({"name": "graph", "status": "pass", "count": len(graph_signals)})
        if selected:
            mark_candidates_used(conn, [str(item["candidateId"]) for item in selected], now=now)

    markdown = render_markdown(metadata, current_state, selected, fts_matches, graph_signals, request)
    write_context_package(state_directory, markdown)

    latency_ms = int((time.perf_counter() - started) * 1000)
    trace["completedAt"] = now
    trace["latencyMs"] = latency_ms
    trace["selectedCandidates"] = selected
    trace["droppedCandidates"] = dropped
    trace["ftsMatches"] = fts_matches
    trace["graphSignals"] = graph_signals
    trace["tokenBudget"] = {
        "target": request.target_token_budget,
        "hard": request.hard_token_budget,
        "estimatedUsed": estimated_used,
    }

    if request.debug:
        write_debug_trace(state_directory / "context/debug", trace)

    return ContextPackage(markdown=markdown, state_directory=state_directory, trace=trace)
