"""Level 3/4 long-running multi-persona E2E harness."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3

from ai_workroot.capabilities.release.model import ReleaseTargetRef
from ai_workroot.capabilities.retrieval.providers.context_recall_hint_provider import (
    ContextRecallHint,
    upsert_context_recall_hint,
)
from ai_workroot.capabilities.retrieval.providers.sqlite_fts import index_file_chunk
from ai_workroot.capabilities.assets.operations import create_internal_asset
from ai_workroot.capabilities.handoff.operations import create_handoff
from ai_workroot.capabilities.relationships.operations import create_relationship_edge, create_relationship_node
from ai_workroot.capabilities.release.operations import (
    create_deletion_record,
    create_redaction,
    create_release_record,
    create_tombstone,
)
from ai_workroot.capabilities.work.operations import (
    create_checkpoint,
    create_task,
    record_agent_run,
    record_invalidation,
    record_work_action,
)

from tests.e2e.harness import CommandResult, REPO_ROOT, env_for, run_cli, validate_user_directory, write_user_files
from tests.e2e.personas import PERSONAS, Persona
from tests.e2e.safety import new_default_run_root, prepare_run_root, require_e2e_opt_in
from tests.e2e.scenarios import TaskScenario, scenarios_for_persona


@dataclass(frozen=True)
class PersonaLongrunResult:
    persona_slug: str
    task_count: int
    user_directory: Path
    state_directory: Path
    sqlite_path: Path
    context_checks: int
    hard_trim_checks: int
    max_token_usage: int
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failures


@dataclass(frozen=True)
class LongrunResult:
    level: int
    run_root: Path
    ai_workroot_home: Path
    summary_path: Path
    failures_path: Path
    context_audit_path: Path
    longrun_matrix_path: Path
    commands_path: Path
    client_report: str
    persona_results: tuple[PersonaLongrunResult, ...]

    @property
    def task_count(self) -> int:
        return sum(result.task_count for result in self.persona_results)

    @property
    def passed(self) -> bool:
        return all(result.passed for result in self.persona_results) and _read_failures(self.failures_path) == []


def run_longrun(
    *,
    run_root: Path,
    sandbox_base: Path | None = None,
    level: int = 3,
    tasks_per_persona: int | None = None,
) -> LongrunResult:
    if level not in {3, 4}:
        raise ValueError("level must be 3 or 4")
    run_root = prepare_run_root(run_root, sandbox_base=sandbox_base)
    resolved_tasks_per_persona = tasks_per_persona or (6 if level == 3 else 8)
    if resolved_tasks_per_persona <= 0:
        raise ValueError("tasks_per_persona must be positive")

    ai_workroot_home = run_root / "ai-workroot-home"
    reports_dir = run_root / "reports"
    transcripts_dir = run_root / "transcripts"
    user_dirs = run_root / "user-dirs"
    for directory in (reports_dir, transcripts_dir, user_dirs):
        directory.mkdir(parents=True, exist_ok=True)

    env = env_for(ai_workroot_home)
    commands: list[CommandResult] = []
    persona_results: list[PersonaLongrunResult] = []
    audits: list[dict[str, object]] = []
    for persona in PERSONAS:
        result, persona_audits = _run_persona_longrun(
            persona=persona,
            scenarios=scenarios_for_persona(persona.slug, resolved_tasks_per_persona),
            user_directory=user_dirs / persona.slug,
            env=env,
            commands=commands,
            transcripts_dir=transcripts_dir,
            level=level,
        )
        persona_results.append(result)
        audits.extend(persona_audits)

    list_result = run_cli(("list", "--format", "json"), env=env, cwd=REPO_ROOT)
    commands.append(list_result)
    global_failures: list[dict[str, object]] = []
    if list_result.returncode != 0:
        global_failures.append({"scope": "global", "failure": "workroot list failed", "command": list_result.as_dict()})
    else:
        listed = json.loads(list_result.stdout)
        if len(listed) != len(PERSONAS):
            global_failures.append(
                {"scope": "global", "failure": f"expected {len(PERSONAS)} Workroots, got {len(listed)}"}
            )

    failures = [
        {"scope": result.persona_slug, "failure": failure} for result in persona_results for failure in result.failures
    ]
    failures.extend(global_failures)
    audit_summary = _summarize_context_audit(level, tuple(persona_results), audits)
    matrix = _build_matrix(tuple(persona_results), audits)
    summary_path = reports_dir / "summary.md"
    failures_path = reports_dir / "failures.json"
    context_audit_path = reports_dir / "context-audit.json"
    longrun_matrix_path = reports_dir / "longrun-matrix.json"
    commands_path = reports_dir / "commands.json"
    summary = _render_summary(level, run_root, ai_workroot_home, tuple(persona_results), audit_summary, failures)
    summary_path.write_text(summary, encoding="utf-8")
    failures_path.write_text(json.dumps(failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    context_audit_path.write_text(
        json.dumps(audit_summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    longrun_matrix_path.write_text(
        json.dumps(matrix, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    commands_path.write_text(
        json.dumps([command.as_dict() for command in commands], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    client_report = _render_client_report(level, tuple(persona_results), audit_summary, failures, summary_path)
    return LongrunResult(
        level=level,
        run_root=run_root,
        ai_workroot_home=ai_workroot_home,
        summary_path=summary_path,
        failures_path=failures_path,
        context_audit_path=context_audit_path,
        longrun_matrix_path=longrun_matrix_path,
        commands_path=commands_path,
        client_report=client_report,
        persona_results=tuple(persona_results),
    )


def _run_persona_longrun(
    *,
    persona: Persona,
    scenarios: tuple[TaskScenario, ...],
    user_directory: Path,
    env: dict[str, str],
    commands: list[CommandResult],
    transcripts_dir: Path,
    level: int,
) -> tuple[PersonaLongrunResult, list[dict[str, object]]]:
    failures: list[str] = []
    user_directory.mkdir(parents=True, exist_ok=True)
    write_user_files(user_directory, persona.user_files)
    init = run_cli(
        (
            "init",
            "--name",
            persona.name,
            "--directory",
            str(user_directory),
            "--id",
            persona.workroot_id,
            "--native-agent-entry" if persona.native_agent_entry else "--no-native-agent-entry",
        ),
        env=env,
        cwd=REPO_ROOT,
    )
    commands.append(init)
    if init.returncode != 0:
        failures.append(f"init failed: {init.stderr or init.stdout}")
    state_directory = Path(env["AI_WORKROOT_HOME"]) / "workroots" / persona.workroot_id
    sqlite_path = state_directory / "cache/workroot.sqlite"
    if sqlite_path.is_file():
        _seed_longrun_sqlite(persona, scenarios, sqlite_path, level=level)
        _write_longrun_managed_surface(persona, scenarios, state_directory)
    else:
        failures.append(f"missing SQLite after init: {sqlite_path}")
    failures.extend(validate_user_directory(persona, user_directory, Path(env["AI_WORKROOT_HOME"])))

    status = run_cli(("status", "--cwd", str(user_directory)), env=env, cwd=REPO_ROOT)
    doctor = run_cli(("doctor", "--cwd", str(user_directory)), env=env, cwd=REPO_ROOT)
    commands.extend([status, doctor])
    for label, result in (("status", status), ("doctor", doctor)):
        if result.returncode != 0:
            failures.append(f"{label} failed: {result.stderr or result.stdout}")

    audits: list[dict[str, object]] = []
    context_commands: list[CommandResult] = []
    for scenario in _context_probe_scenarios(scenarios):
        hard_limit = "180" if scenario.force_hard_trim else "900"
        target_tokens = "120" if scenario.force_hard_trim else "600"
        context = run_cli(
            ("context", "--agent", "codex", "--cwd", str(user_directory), "--query", scenario.query),
            env=env,
            cwd=REPO_ROOT,
        )
        debug = run_cli(
            (
                "context",
                "--agent",
                "codex",
                "--cwd",
                str(user_directory),
                "--query",
                scenario.query,
                "--debug",
                "--target-tokens",
                target_tokens,
                "--hard-token-limit",
                hard_limit,
            ),
            env=env,
            cwd=REPO_ROOT,
        )
        commands.extend([context, debug])
        context_commands.extend([context, debug])
        failures.extend(_validate_context_probe(persona, scenario, context, debug, hard_limit=int(hard_limit)))
        audits.append(_audit_context_probe(persona, scenario, context, debug, hard_limit=int(hard_limit)))
    if sqlite_path.is_file():
        failures.extend(_validate_longrun_sqlite(persona, sqlite_path, task_count=len(scenarios)))
    _write_transcript(transcripts_dir, persona, status, doctor, *context_commands)
    return (
        PersonaLongrunResult(
            persona_slug=persona.slug,
            task_count=len(scenarios),
            user_directory=user_directory,
            state_directory=state_directory,
            sqlite_path=sqlite_path,
            context_checks=len(audits),
            hard_trim_checks=sum(1 for audit in audits if audit["hardTrim"]),
            max_token_usage=max((int(audit["tokenUsage"]) for audit in audits), default=0),
            failures=tuple(failures),
        ),
        audits,
    )


def _seed_longrun_sqlite(
    persona: Persona, scenarios: tuple[TaskScenario, ...], sqlite_path: Path, *, level: int
) -> None:
    with sqlite3.connect(sqlite_path) as conn:
        previous_asset_id = ""
        for index, scenario in enumerate(scenarios, start=1):
            suffix = f"{persona.slug.replace('persona-', '').replace('-', '_')}_{index:02d}"
            task_id = f"task_{suffix}"
            asset_id = f"asset_{suffix}"
            create_task(
                conn,
                workroot_id=persona.workroot_id,
                task_id=task_id,
                title=f"{scenario.title}: {persona.name}",
                task_kind=scenario.kind,
                process_level="L2" if level >= 4 or index % 3 == 0 else "L1",
            )
            record_agent_run(
                conn,
                workroot_id=persona.workroot_id,
                run_id=f"run_{suffix}",
                task_id=task_id,
                status="completed",
                validity="valid",
            )
            record_work_action(
                conn,
                workroot_id=persona.workroot_id,
                action_id=f"action_{suffix}",
                task_id=task_id,
                action_type=scenario.kind,
                risk_level="high" if scenario.protection in {"deleted", "redacted"} else "normal",
            )
            create_checkpoint(
                conn,
                workroot_id=persona.workroot_id,
                checkpoint_id=f"checkpoint_{suffix}",
                task_id=task_id,
                current_status=f"{scenario.title} complete. Next query: {scenario.query}.",
            )
            create_handoff(
                conn,
                workroot_id=persona.workroot_id,
                handoff_id=f"handoff_{suffix}",
                title=f"Continue {scenario.title}",
            )
            if index % 4 == 0:
                record_invalidation(
                    conn,
                    workroot_id=persona.workroot_id,
                    invalidation_id=f"invalidation_{suffix}",
                    invalidated_claim=f"Old assumption for {scenario.title}",
                    reason="E2E longrun synthetic invalidation.",
                )
            create_internal_asset(
                conn,
                workroot_id=persona.workroot_id,
                asset_id=asset_id,
                asset_type="result",
                title=f"{scenario.title}: {persona.name}",
                summary=scenario.summary,
                updated_at=f"2026-05-21T00:{index:02d}:00Z",
            )
            upsert_context_recall_hint(
                conn,
                ContextRecallHint(
                    hint_id=f"hint_{suffix}",
                    workroot_id=persona.workroot_id,
                    target_type="asset",
                    target_id=asset_id,
                    title=f"{scenario.title}: {persona.name}",
                    summary=scenario.summary,
                    scope_type="task",
                    scope_id=task_id,
                    priority="critical" if scenario.scenario_id in {"weak-query", "large-context"} else "high",
                    recall_rule="task-related",
                    origin="e2e-longrun",
                    source_ref=f"asset:{asset_id}",
                    created_at=f"2026-05-21T00:{index:02d}:00Z",
                    updated_at=f"2026-05-21T00:{index:02d}:00Z",
                ),
            )
            index_file_chunk(
                conn,
                workroot_id=persona.workroot_id,
                file_id=f"file_{suffix}",
                chunk_id=f"chunk_{suffix}",
                relative_path=f"longrun/{index:02d}-{scenario.scenario_id}.md",
                body=f"{scenario.body}\n{scenario.summary}\nQuery marker: {scenario.query}",
                source_type="asset",
                source_id=asset_id,
            )
            create_relationship_node(
                conn, node_id=asset_id, workroot_id=persona.workroot_id, node_type="asset", title=scenario.title
            )
            create_relationship_node(
                conn, node_id=task_id, workroot_id=persona.workroot_id, node_type="task", title=scenario.title
            )
            create_relationship_edge(
                conn,
                edge_id=f"edge_{suffix}",
                workroot_id=persona.workroot_id,
                from_node_id=asset_id,
                to_node_id=task_id,
                relationship_type="supports",
                created_by="e2e-longrun",
                confidence=0.9,
            )
            if previous_asset_id:
                create_relationship_edge(
                    conn,
                    edge_id=f"edge_sequence_{suffix}",
                    workroot_id=persona.workroot_id,
                    from_node_id=asset_id,
                    to_node_id=previous_asset_id,
                    relationship_type="supersedes" if scenario.scenario_id == "tombstone" else "related_to",
                    created_by="e2e-longrun",
                    confidence=0.7,
                )
            previous_asset_id = asset_id
            if scenario.protection != "none":
                _seed_protected_target(conn, persona, scenario, suffix)
                _seed_safe_release_companion(conn, persona, scenario, suffix, task_id)


def _seed_protected_target(conn: sqlite3.Connection, persona: Persona, scenario: TaskScenario, suffix: str) -> None:
    protected_asset_id = f"asset_protected_{suffix}"
    protected_phrase = f"E2E_LONGRUN_{scenario.protection.upper()}_{suffix.upper()}"
    create_internal_asset(
        conn,
        workroot_id=persona.workroot_id,
        asset_id=protected_asset_id,
        asset_type="note",
        title=f"Protected {scenario.title}",
        summary=protected_phrase,
        updated_at="2026-05-21T01:00:00Z",
    )
    upsert_context_recall_hint(
        conn,
        ContextRecallHint(
            hint_id=f"hint_protected_{suffix}",
            workroot_id=persona.workroot_id,
            target_type="asset",
            target_id=protected_asset_id,
            title=f"Protected {scenario.title}",
            summary=protected_phrase,
            priority="critical",
            recall_rule="always",
            origin="e2e-longrun",
            source_ref=f"asset:{protected_asset_id}",
        ),
    )
    target = ReleaseTargetRef(target_type="asset", target_id=protected_asset_id, workroot_id=persona.workroot_id)
    create_release_record(
        conn,
        release_id=f"release_{suffix}",
        workroot_id=persona.workroot_id,
        target=target,
        release_level=scenario.protection,
        recall_rule="ordinary-context-excluded" if scenario.protection in {"redacted", "deleted"} else "symbolic-only",
    )
    if scenario.protection == "deleted":
        create_deletion_record(
            conn,
            deletion_id=f"delete_{suffix}",
            workroot_id=persona.workroot_id,
            target=target,
            minimum_audit_note="E2E longrun deleted synthetic detail.",
        )
    elif scenario.protection == "redacted":
        create_redaction(
            conn,
            redaction_id=f"redact_{suffix}",
            workroot_id=persona.workroot_id,
            target=target,
            redacted_fields=("summary",),
            redaction_reason="E2E longrun synthetic privacy protection.",
        )
    elif scenario.protection == "tombstone":
        create_tombstone(
            conn,
            tombstone_id=f"tombstone_{suffix}",
            workroot_id=persona.workroot_id,
            target=target,
            title=f"Tombstone {scenario.title}",
            symbolic_note="E2E longrun tombstone annotation should be traceable.",
        )


def _seed_safe_release_companion(
    conn: sqlite3.Connection, persona: Persona, scenario: TaskScenario, suffix: str, task_id: str
) -> None:
    companion_asset_id = f"asset_safe_release_{suffix}"
    create_internal_asset(
        conn,
        workroot_id=persona.workroot_id,
        asset_id=companion_asset_id,
        asset_type="result",
        title=f"{scenario.title}: safe context",
        summary=f"Safe companion context for {scenario.title}. Query marker: {scenario.query}.",
        updated_at="2026-05-21T01:30:00Z",
    )
    upsert_context_recall_hint(
        conn,
        ContextRecallHint(
            hint_id=f"hint_safe_release_{suffix}",
            workroot_id=persona.workroot_id,
            target_type="asset",
            target_id=companion_asset_id,
            title=scenario.title,
            summary=f"Safe release-control summary for {scenario.title}; query marker: {scenario.query}; protected details stay filtered.",
            scope_type="task",
            scope_id=task_id,
            priority="high",
            recall_rule="task-related",
            origin="e2e-longrun",
            source_ref=f"asset:{companion_asset_id}",
        ),
    )
    index_file_chunk(
        conn,
        workroot_id=persona.workroot_id,
        file_id=f"file_safe_release_{suffix}",
        chunk_id=f"chunk_safe_release_{suffix}",
        relative_path=f"longrun/safe-{scenario.scenario_id}.md",
        body=f"{scenario.title} {scenario.query} safe release control companion.",
        source_type="asset",
        source_id=companion_asset_id,
    )


def _context_probe_scenarios(scenarios: tuple[TaskScenario, ...]) -> tuple[TaskScenario, ...]:
    probes: list[TaskScenario] = list(scenarios[:2])
    probes.extend(scenario for scenario in scenarios if scenario.protection != "none")
    probes.extend(scenario for scenario in scenarios if scenario.force_hard_trim)
    weak = next((scenario for scenario in scenarios if scenario.scenario_id == "weak-query"), None)
    if weak:
        probes.append(weak)
    deduped: list[TaskScenario] = []
    seen: set[str] = set()
    for scenario in probes:
        if scenario.scenario_id in seen:
            continue
        seen.add(scenario.scenario_id)
        deduped.append(scenario)
    return tuple(deduped)


def _validate_context_probe(
    persona: Persona,
    scenario: TaskScenario,
    context: CommandResult,
    debug: CommandResult,
    *,
    hard_limit: int,
) -> list[str]:
    failures: list[str] = []
    if context.returncode != 0:
        failures.append(f"context failed for {scenario.scenario_id}: {context.stderr or context.stdout}")
    if debug.returncode != 0:
        failures.append(f"context debug failed for {scenario.scenario_id}: {debug.stderr or debug.stdout}")
    combined = context.stdout + "\n" + debug.stdout
    if "# AI Workroot Context Package" not in context.stdout:
        failures.append(f"context heading missing for {scenario.scenario_id}")
    if _parse_token_usage(context.stdout) <= 0:
        failures.append(f"context token usage is zero for {scenario.scenario_id}")
    if scenario.title not in combined:
        failures.append(f"selected context missing scenario title for {scenario.scenario_id}: {scenario.title}")
    for expected in ("## Debug Trace", "candidateSources:", "filters:", "scoring:", "timing:", "tokenUsage:"):
        if expected not in debug.stdout:
            failures.append(f"debug trace missing {expected} for {scenario.scenario_id}")
    if scenario.force_hard_trim and "trimSteps:" not in debug.stdout:
        failures.append(f"hard trim marker missing for {scenario.scenario_id}")
    if scenario.force_hard_trim and _parse_token_usage(debug.stdout) > hard_limit:
        failures.append(f"debug token usage exceeds hard limit for {scenario.scenario_id}: {hard_limit}")
    if scenario.protection in {"redacted", "deleted"} and (
        "E2E_LONGRUN_REDACTED" in context.stdout or "E2E_LONGRUN_DELETED" in context.stdout
    ):
        failures.append(f"protected longrun marker leaked for {scenario.scenario_id}")
    if (
        persona.protected_phrase
        and persona.protection in {"redacted", "deleted"}
        and persona.protected_phrase in context.stdout
    ):
        failures.append(f"persona protected phrase leaked for {scenario.scenario_id}")
    return failures


def _audit_context_probe(
    persona: Persona, scenario: TaskScenario, context: CommandResult, debug: CommandResult, *, hard_limit: int
) -> dict[str, object]:
    token_usage = _parse_token_usage(context.stdout)
    debug_token_usage = _parse_token_usage(debug.stdout)
    return {
        "persona": persona.slug,
        "scenario": scenario.scenario_id,
        "query": scenario.query,
        "tokenUsage": token_usage,
        "debugTokenUsage": debug_token_usage,
        "hardTokenLimit": hard_limit,
        "debugTokenWithinHardLimit": debug_token_usage <= hard_limit,
        "selectedCount": context.stdout.count("\n- "),
        "hasDebugTrace": "## Debug Trace" in debug.stdout,
        "hasCandidateSources": "candidateSources:" in debug.stdout,
        "hasScoring": "scoring:" in debug.stdout,
        "hasTiming": "timing:" in debug.stdout,
        "hasTokenUsageDebug": "tokenUsage:" in debug.stdout,
        "hardTrim": "trimSteps:" in debug.stdout,
        "protectedLeak": "E2E_LONGRUN_REDACTED" in context.stdout or "E2E_LONGRUN_DELETED" in context.stdout,
        "contextChars": len(context.stdout),
        "debugChars": len(debug.stdout),
    }


def _parse_token_usage(output: str) -> int:
    for line in output.splitlines():
        if line.startswith("TokenUsage:"):
            head = line.split(":", 1)[1].strip().split("/", 1)[0].strip()
            try:
                return int(head)
            except ValueError:
                return 0
    return 0


def _validate_longrun_sqlite(persona: Persona, sqlite_path: Path, *, task_count: int) -> list[str]:
    minimums = {
        "tasks": task_count,
        "agent_runs": task_count,
        "work_actions": task_count,
        "work_checkpoints": task_count,
        "handoffs": task_count,
        "assets": task_count,
        "context_recall_hints": task_count,
        "indexed_chunks": task_count,
        "relationship_edges": task_count,
        "context_packages": 1,
        "context_traces": 1,
    }
    failures: list[str] = []
    with sqlite3.connect(sqlite_path) as conn:
        for table, minimum in minimums.items():
            count = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE workroot_id = ?", (persona.workroot_id,)
            ).fetchone()[0]
            if count < minimum:
                failures.append(f"{table} has {count} rows, expected at least {minimum}")
    return failures


def _write_longrun_managed_surface(
    persona: Persona, scenarios: tuple[TaskScenario, ...], state_directory: Path
) -> None:
    files = {
        "state/longrun-current.json": {
            "workrootId": persona.workroot_id,
            "taskCount": len(scenarios),
            "lastScenario": scenarios[-1].scenario_id if scenarios else "",
        },
        "tasks/longrun-summary.json": [
            {
                "scenarioId": scenario.scenario_id,
                "title": scenario.title,
                "query": scenario.query,
                "kind": scenario.kind,
                "protection": scenario.protection,
            }
            for scenario in scenarios
        ],
        "context/traces/longrun-audit-placeholder.json": {
            "workrootId": persona.workroot_id,
            "taskCount": len(scenarios),
        },
    }
    for rel, payload in files.items():
        path = state_directory / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_transcript(transcripts_dir: Path, persona: Persona, *results: CommandResult) -> None:
    path = transcripts_dir / f"{persona.slug}.md"
    sections = [f"# Longrun Transcript: {persona.name}", ""]
    for result in results:
        sections.extend(
            [
                "## Command",
                "",
                "```bash",
                " ".join(result.command),
                "```",
                "",
                f"Exit: {result.returncode}",
                "",
                "### stdout",
                "",
                "```text",
                result.stdout.rstrip(),
                "```",
                "",
                "### stderr",
                "",
                "```text",
                result.stderr.rstrip(),
                "```",
                "",
            ]
        )
    path.write_text("\n".join(sections), encoding="utf-8")


def _summarize_context_audit(
    level: int, persona_results: tuple[PersonaLongrunResult, ...], audits: list[dict[str, object]]
) -> dict[str, object]:
    token_values = [int(audit["tokenUsage"]) for audit in audits]
    return {
        "level": level,
        "personaCount": len(persona_results),
        "taskCount": sum(result.task_count for result in persona_results),
        "contextChecks": len(audits),
        "selectedContextChecks": sum(1 for audit in audits if int(audit["selectedCount"]) > 0),
        "debugTraceChecks": sum(1 for audit in audits if audit["hasDebugTrace"]),
        "hardTrimChecks": sum(1 for audit in audits if audit["hardTrim"]),
        "zeroTokenUsageCount": sum(1 for value in token_values if value <= 0),
        "protectedLeakCount": sum(1 for audit in audits if audit["protectedLeak"]),
        "debugTokenOverHardLimitCount": sum(1 for audit in audits if not audit["debugTokenWithinHardLimit"]),
        "maxTokenUsage": max(token_values, default=0),
        "audits": audits,
    }


def _build_matrix(
    persona_results: tuple[PersonaLongrunResult, ...], audits: list[dict[str, object]]
) -> dict[str, object]:
    return {
        "personas": [
            {
                "persona": result.persona_slug,
                "taskCount": result.task_count,
                "contextChecks": result.context_checks,
                "hardTrimChecks": result.hard_trim_checks,
                "passed": result.passed,
            }
            for result in persona_results
        ],
        "scenarioCoverage": sorted({str(audit["scenario"]) for audit in audits}),
    }


def _render_summary(
    level: int,
    run_root: Path,
    ai_workroot_home: Path,
    persona_results: tuple[PersonaLongrunResult, ...],
    audit_summary: dict[str, object],
    failures: list[dict[str, object]],
) -> str:
    lines = [
        f"# AI Workroot Level {level} Longrun Report",
        "",
        f"Overall: {'PASS' if not failures else 'FAIL'}",
        f"RunRoot: {run_root}",
        f"AI_WORKROOT_HOME: {ai_workroot_home}",
        f"PersonaCount: {len(persona_results)}",
        f"TaskCount: {audit_summary['taskCount']}",
        f"ContextChecks: {audit_summary['contextChecks']}",
        f"SelectedContextChecks: {audit_summary['selectedContextChecks']}",
        f"DebugTraceChecks: {audit_summary['debugTraceChecks']}",
        f"HardTrimChecks: {audit_summary['hardTrimChecks']}",
        f"ZeroTokenUsageCount: {audit_summary['zeroTokenUsageCount']}",
        f"ProtectedLeakCount: {audit_summary['protectedLeakCount']}",
        f"DebugTokenOverHardLimitCount: {audit_summary['debugTokenOverHardLimitCount']}",
        f"MaxTokenUsage: {audit_summary['maxTokenUsage']}",
        "",
        "## Personas",
    ]
    for result in persona_results:
        lines.extend(
            [
                f"### {result.persona_slug}",
                f"- Tasks: {result.task_count}",
                f"- Context checks: {result.context_checks}",
                f"- Hard trim checks: {result.hard_trim_checks}",
                f"- Max token usage: {result.max_token_usage}",
                f"- Status: {'PASS' if result.passed else 'FAIL'}",
                "",
            ]
        )
    if failures:
        lines.extend(["## Failures", *[f"- {failure['scope']}: {failure['failure']}" for failure in failures], ""])
    return "\n".join(lines)


def _render_client_report(
    level: int,
    persona_results: tuple[PersonaLongrunResult, ...],
    audit_summary: dict[str, object],
    failures: list[dict[str, object]],
    summary_path: Path,
) -> str:
    return (
        "\n".join(
            [
                f"AI Workroot Level {level} Longrun: {'PASS' if not failures else 'FAIL'}",
                f"Personas: {len(persona_results)}",
                f"Tasks: {audit_summary['taskCount']}",
                f"Context checks: {audit_summary['contextChecks']}",
                f"Debug traces: {audit_summary['debugTraceChecks']}",
                f"Hard trims: {audit_summary['hardTrimChecks']}",
                f"Zero token usages: {audit_summary['zeroTokenUsageCount']}",
                f"Protected leaks: {audit_summary['protectedLeakCount']}",
                f"Max token usage: {audit_summary['maxTokenUsage']}",
                f"Summary: {summary_path}",
            ]
        )
        + "\n"
    )


def _read_failures(path: Path) -> list[dict[str, object]]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []


def main() -> int:
    if not require_e2e_opt_in():
        return 2
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root")
    parser.add_argument("--level", type=int, choices=(3, 4), default=3)
    parser.add_argument("--tasks-per-persona", type=int)
    args = parser.parse_args()
    result = run_longrun(
        run_root=Path(args.run_root) if args.run_root else new_default_run_root(),
        level=args.level,
        tasks_per_persona=args.tasks_per_persona,
    )
    print(result.client_report, end="")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
