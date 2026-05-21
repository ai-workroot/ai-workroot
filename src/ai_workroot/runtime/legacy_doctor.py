#!/usr/bin/env python3
"""Compatibility managed-state doctor checks for AI Workroot."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ai_workroot.agent.native_entry import BEGIN, END
from ai_workroot.runtime.state import DEFAULT_RUNTIME_HINTS, read_jsonl
from ai_workroot.runtime.paths import CleanModeBoundaryError, assert_clean_mode_boundary, workroot_sqlite_path
from ai_workroot.storage.legacy_sqlite import verify_workroot_sqlite


DEFAULT_CONTEXT_GUIDE_CONFIG = DEFAULT_RUNTIME_HINTS["contextGuide"]


@dataclass(frozen=True)
class DoctorCheck:
    check_id: str
    category: str
    status: str
    severity: str
    message: str
    suggested_action: str

    def to_json(self) -> dict[str, str]:
        return {
            "checkId": self.check_id,
            "category": self.category,
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
            "suggestedAction": self.suggested_action,
        }


@dataclass(frozen=True)
class DoctorResult:
    checks: list[DoctorCheck]

    def has_errors(self) -> bool:
        return any(check.status == "fail" and check.severity == "error" for check in self.checks)

    def to_json(self) -> dict[str, object]:
        return {
            "status": "fail" if self.has_errors() else "pass",
            "checks": [check.to_json() for check in self.checks],
        }


def pass_check(check_id: str, category: str, message: str, suggested_action: str = "No action needed.") -> DoctorCheck:
    return DoctorCheck(check_id, category, "pass", "info", message, suggested_action)


def fail_check(check_id: str, category: str, message: str, suggested_action: str) -> DoctorCheck:
    return DoctorCheck(check_id, category, "fail", "error", message, suggested_action)


def warn_check(check_id: str, category: str, message: str, suggested_action: str) -> DoctorCheck:
    return DoctorCheck(check_id, category, "warn", "warning", message, suggested_action)


def resolve_state_record(home: Path, cwd: Path) -> dict[str, object] | None:
    records = read_jsonl(home / "registry/workroots.jsonl")
    matches = []
    for record in records:
        user_directory = Path(str(record.get("userDirectory", ""))).resolve()
        try:
            inside = cwd == user_directory or cwd.relative_to(user_directory) is not None
        except ValueError:
            inside = False
        if inside:
            matches.append(record)
    if not matches:
        return None
    return max(matches, key=lambda row: len(str(row.get("userDirectory", ""))))


def read_workroot_json(state_directory: Path) -> dict[str, object]:
    return json.loads((state_directory / "workroot.json").read_text(encoding="utf-8"))


def check_resolution(home: Path, cwd: Path, metadata: dict[str, object] | None, state_directory: Path | None) -> DoctorCheck:
    if metadata and state_directory:
        return pass_check(
            "workroot-resolution",
            "resolution",
            f"resolved Workroot state at {state_directory}",
        )
    return fail_check(
        "workroot-resolution",
        "resolution",
        f"no managed Workroot is registered for cwd: {cwd}",
        f"Run workroot init --directory {cwd} or pass --cwd inside a registered Workroot.",
    )


def check_clean_mode(metadata: dict[str, object], state_directory: Path) -> DoctorCheck:
    try:
        user_directory = Path(str(metadata.get("userDirectory", ""))).resolve()
        assert_clean_mode_boundary(user_directory, state_directory.resolve())
    except CleanModeBoundaryError as exc:
        return fail_check(
            "clean-mode-boundary",
            "clean-mode",
            str(exc),
            "Move managed state outside the user-selected directory and rerun bootstrap or migration.",
        )
    return pass_check(
        "clean-mode-boundary",
        "clean-mode",
        "managed state is outside the user-selected directory",
    )


def check_managed_layout(state_directory: Path) -> DoctorCheck:
    missing = [
        rel
        for rel in (
            "workroot.json",
            "state/current.json",
            "context/packages/history",
            "context/debug/history",
            "indexes",
            "handoffs",
        )
        if not (state_directory / rel).exists()
    ]
    if missing:
        return fail_check(
            "managed-layout",
            "managed-state",
            f"missing managed layout paths: {', '.join(missing)}",
            "Rerun bootstrap or the managed state initializer for this Workroot.",
        )
    return pass_check("managed-layout", "managed-state", "managed state layout is present")


def check_migration_records(home: Path) -> DoctorCheck:
    migration_dir = home / "migrations"
    if not migration_dir.exists():
        return warn_check(
            "migration-records",
            "migrations",
            "migration records directory is not present yet",
            "Run migrations before relying on versioned managed state.",
        )
    failures = []
    for path in migration_dir.glob("*.jsonl"):
        for row in read_jsonl(path):
            if row.get("status") == "failed":
                failures.append(f"{path.name}:{row.get('migrationId')}")
    if failures:
        return fail_check(
            "migration-records",
            "migrations",
            f"failed migrations found: {', '.join(failures)}",
            "Inspect migration records and rerun or roll back the failed migration.",
        )
    return pass_check("migration-records", "migrations", "no failed migration records found")


def check_sqlite_schema(state_directory: Path) -> DoctorCheck:
    issues = verify_workroot_sqlite(workroot_sqlite_path(state_directory))
    if issues:
        return fail_check(
            "sqlite-schema",
            "indexes",
            "; ".join(issues),
            "Rebuild the Workroot SQLite index with the current schema.",
        )
    return pass_check("sqlite-schema", "indexes", "SQLite schema contains required tables")


def check_context_directories(state_directory: Path) -> DoctorCheck:
    missing = [
        rel
        for rel in ("context/packages/history", "context/debug/history")
        if not (state_directory / rel).is_dir()
    ]
    if missing:
        return fail_check(
            "context-directories",
            "context",
            f"missing context directories: {', '.join(missing)}",
            "Recreate the managed state layout for this Workroot.",
        )
    return pass_check("context-directories", "context", "context package and debug directories are present")


def check_context_runtime_hints(state_directory: Path) -> DoctorCheck:
    path = state_directory / "state/runtime-hints.json"
    if not path.exists():
        return pass_check(
            "context-runtime-hints",
            "context",
            "runtime hints are absent; Context Guide will use built-in defaults",
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return fail_check(
            "context-runtime-hints",
            "context",
            f"malformed runtime hints: {exc}",
            f"Repair or remove {path}; Context Guide can use built-in defaults when the file is absent.",
        )
    context = payload.get("contextGuide")
    if not isinstance(context, dict):
        return fail_check(
            "context-runtime-hints",
            "context",
            "runtime hints missing contextGuide object",
            f"Repair {path} or remove it to use built-in defaults.",
        )
    required = [
        ("defaultMode", str),
        ("agentBudgets", dict),
        ("modes", dict),
        ("hotPath", dict),
    ]
    for key, expected_type in required:
        if not isinstance(context.get(key), expected_type):
            return fail_check(
                "context-runtime-hints",
                "context",
                f"runtime hints contextGuide.{key} is missing or invalid",
                f"Repair {path} or remove it to use built-in defaults.",
            )
    agent_budgets = context["agentBudgets"]
    for agent in ("codex", "claude", "default"):
        budget = agent_budgets.get(agent)
        if not isinstance(budget, dict):
            return fail_check(
                "context-runtime-hints",
                "context",
                f"runtime hints missing agent budget for {agent}",
                f"Add contextGuide.agentBudgets.{agent} or remove {path} to use built-in defaults.",
            )
        for key in ("targetTokens", "hardTokenLimit"):
            if not isinstance(budget.get(key), int) or int(budget[key]) <= 0:
                return fail_check(
                    "context-runtime-hints",
                    "context",
                    f"runtime hints agentBudgets.{agent}.{key} must be a positive integer",
                    f"Repair contextGuide.agentBudgets.{agent}.{key} in {path}.",
                )
        if int(budget["targetTokens"]) > int(budget["hardTokenLimit"]):
            return fail_check(
                "context-runtime-hints",
                "context",
                f"runtime hints agentBudgets.{agent}.targetTokens exceeds hardTokenLimit",
                f"Repair contextGuide.agentBudgets.{agent} in {path}.",
            )
    modes = context["modes"]
    for mode in ("fast", "standard", "quality", "deep"):
        mode_payload = modes.get(mode)
        if not isinstance(mode_payload, dict):
            return fail_check(
                "context-runtime-hints",
                "context",
                f"runtime hints missing mode {mode}",
                f"Add contextGuide.modes.{mode} or remove {path} to use built-in defaults.",
            )
        for key in ("targetTokens", "hardTokenLimit"):
            if key in mode_payload and (not isinstance(mode_payload.get(key), int) or int(mode_payload[key]) <= 0):
                return fail_check(
                    "context-runtime-hints",
                    "context",
                    f"runtime hints modes.{mode}.{key} must be a positive integer",
                    f"Repair contextGuide.modes.{mode}.{key} in {path}.",
                )
        if (
            isinstance(mode_payload.get("targetTokens"), int)
            and isinstance(mode_payload.get("hardTokenLimit"), int)
            and int(mode_payload["targetTokens"]) > int(mode_payload["hardTokenLimit"])
        ):
            return fail_check(
                "context-runtime-hints",
                "context",
                f"runtime hints modes.{mode}.targetTokens exceeds hardTokenLimit",
                f"Repair contextGuide.modes.{mode} in {path}.",
            )
        for key in ("maxLatencyMs", "targetLatencyMs", "softLatencyMs"):
            if key in mode_payload and (not isinstance(mode_payload.get(key), int) or int(mode_payload[key]) <= 0):
                return fail_check(
                    "context-runtime-hints",
                    "context",
                    f"runtime hints modes.{mode}.{key} must be a positive integer",
                    f"Repair contextGuide.modes.{mode}.{key} in {path}.",
                )
    if context.get("defaultMode") != "standard":
        return warn_check(
            "context-runtime-hints",
            "context",
            f"runtime hints default mode is {context.get('defaultMode')}, not standard",
            "Use Standard Mode as the default unless intentionally configured otherwise.",
        )
    if modes["deep"].get("requiresExplicitRequest") is not True:
        return fail_check(
            "context-runtime-hints",
            "context",
            "Deep Mode must require explicit request",
            "Set contextGuide.modes.deep.requiresExplicitRequest to true.",
        )
    hot_path = context["hotPath"]
    for key in ("allowRemoteLlm", "allowRemoteEmbedding", "allowVectorSearch"):
        if hot_path.get(key) is not False:
            return fail_check(
                "context-runtime-hints",
                "context",
                f"hot-path setting {key} must be false",
                f"Set contextGuide.hotPath.{key} to false.",
            )
    _ = DEFAULT_CONTEXT_GUIDE_CONFIG
    return pass_check("context-runtime-hints", "context", "runtime hints are valid")


def check_native_agent_entry(metadata: dict[str, object]) -> DoctorCheck:
    user_directory = Path(str(metadata.get("userDirectory", ""))).resolve()
    warnings = []
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = user_directory / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if text.count(BEGIN) != text.count(END):
            return fail_check(
                "native-agent-entry",
                "agent-entry",
                f"malformed AI Workroot managed block markers in {name}",
                f"Repair or remove the AI Workroot managed block in {name}.",
            )
        if BEGIN not in text:
            warnings.append(name)
    if warnings:
        return warn_check(
            "native-agent-entry",
            "agent-entry",
            f"Native Agent Entry is not installed in: {', '.join(warnings)}",
            "Install Native Agent Entry only when the user explicitly authorizes it.",
        )
    return pass_check("native-agent-entry", "agent-entry", "Native Agent Entry markers are valid or absent")


def run_doctor(home: Path, cwd: Path, state_directory: Path | None = None) -> DoctorResult:
    home = home.resolve()
    cwd = cwd.resolve()
    metadata: dict[str, object] | None = None
    resolved_state: Path | None = None

    if state_directory is not None:
        resolved_state = state_directory.resolve()
        metadata = read_workroot_json(resolved_state)
    else:
        record = resolve_state_record(home, cwd)
        if record:
            resolved_state = Path(str(record.get("stateDirectory", ""))).resolve()
            metadata = read_workroot_json(resolved_state)

    checks = [check_resolution(home, cwd, metadata, resolved_state)]
    if metadata is None or resolved_state is None:
        return DoctorResult(checks)

    checks.extend(
        [
            check_clean_mode(metadata, resolved_state),
            check_managed_layout(resolved_state),
            check_migration_records(home),
            check_sqlite_schema(resolved_state),
            check_context_directories(resolved_state),
            check_context_runtime_hints(resolved_state),
            check_native_agent_entry(metadata),
        ]
    )
    return DoctorResult(checks)


def render_json(result: DoctorResult) -> str:
    return json.dumps(result.to_json(), ensure_ascii=False, indent=2)


def render_text(result: DoctorResult) -> str:
    lines = [f"AI Workroot doctor: {'FAIL' if result.has_errors() else 'PASS'}"]
    for check in result.checks:
        lines.append(f"{check.status.upper()} {check.check_id}: {check.message}")
        if check.status != "pass":
            lines.append(f"  action: {check.suggested_action}")
    return "\n".join(lines)
