"""WorkrootEnvironment runtime flows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from ai_workroot.core.environment import WorkrootEnvironment
from ai_workroot.storage.jsonl_registry import append_jsonl, read_jsonl, write_json
from ai_workroot.storage.locks import file_lock


REGISTRY_FILES = (
    "workroots.jsonl",
    "directory-bindings.jsonl",
    "aliases.jsonl",
    "relationships.jsonl",
)
PER_WORKROOT_DIRS = (
    "charter",
    "state",
    "tasks",
    "handoffs",
    "assets",
    "release",
    "relationships",
    "indexes",
    "context",
    "diagnostics",
    "maintenance",
    "cache",
    "logs",
)
ENVIRONMENT_VERSION = "0.9.530"
DEFAULT_ENVIRONMENT_ID = "env_local_default"


@dataclass(frozen=True)
class WorkrootRegistration:
    workroot_id: str
    name: str
    user_directory: str
    state_directory: str


@dataclass(frozen=True)
class ContextDiagnosticLoggingConfig:
    enabled: bool = False
    include_rendered_package: bool = False
    include_trace_summary: bool = True
    include_retrieval_summary: bool = True
    include_token_estimate: bool = True
    retention_days: int = 7
    max_entries_per_workroot: int = 200


@dataclass(frozen=True)
class ContextControlConfig:
    default_target_tokens: int = 1200
    default_hard_token_limit: int = 2400
    diagnostic_logging: ContextDiagnosticLoggingConfig = ContextDiagnosticLoggingConfig()


def initialize_environment(home: Path) -> WorkrootEnvironment:
    home = home.expanduser().resolve()
    for rel in (
        "registry",
        "preferences/agent-defaults",
        "global-index",
        "global-cache",
        "migrations/history",
        "migrations/locks",
        "concurrency/locks",
        "workroots",
    ):
        (home / rel).mkdir(parents=True, exist_ok=True)

    ensure_environment_config(home)
    merge_json(home / "preferences/operator-preferences.json", {"version": ENVIRONMENT_VERSION})
    merge_json(home / "preferences/policy-defaults.json", {"version": ENVIRONMENT_VERSION})

    for filename in REGISTRY_FILES:
        path = home / "registry" / filename
        path.touch(exist_ok=True)
    (home / "registry/.registry.lock").touch(exist_ok=True)

    return WorkrootEnvironment(home=str(home))


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_environment_config(home: Path, *, now: str | None = None) -> dict[str, Any]:
    home = home.expanduser().resolve()
    config_path = home / "config.json"
    timestamp = now or utc_now()
    existing = _read_json_object(config_path)
    config = {
        **existing,
        "kind": "WorkrootEnvironment",
        "environmentId": str(existing.get("environmentId") or DEFAULT_ENVIRONMENT_ID),
        "version": ENVIRONMENT_VERSION,
        "schemaVersion": ENVIRONMENT_VERSION,
        "layoutVersion": ENVIRONMENT_VERSION,
        "mode": "clean",
        "createdAt": str(existing.get("createdAt") or timestamp),
        "updatedAt": str(existing.get("updatedAt") or timestamp),
        "summary": _merge_summary(existing.get("summary")),
        "maintenance": _merge_maintenance(existing.get("maintenance")),
        "contextControl": _merge_context_control(existing.get("contextControl")),
    }
    for removed in ("paths", "layout", "policies", "agentIntegration", "workroots"):
        config.pop(removed, None)
    write_json(config_path, config)
    return config


def refresh_environment_registry_summary(home: Path, *, now: str | None = None) -> dict[str, Any]:
    home = home.expanduser().resolve()
    timestamp = now or utc_now()
    config = ensure_environment_config(home, now=timestamp)
    workroots = read_jsonl(home / "registry/workroots.jsonl")
    active_count = sum(1 for record in workroots if str(record.get("status") or "active") == "active")
    summary = _merge_summary(config.get("summary"))
    summary.update(
        {
            "registeredWorkrootCount": len(workroots),
            "activeWorkrootCount": active_count,
            "lastRegistryUpdatedAt": timestamp,
        }
    )
    config["summary"] = summary
    config["updatedAt"] = timestamp
    write_json(home / "config.json", config)
    return config


def record_environment_doctor_summary(home: Path, *, status: str, now: str | None = None) -> dict[str, Any]:
    home = home.expanduser().resolve()
    timestamp = now or utc_now()
    config = ensure_environment_config(home, now=timestamp)
    summary = _merge_summary(config.get("summary"))
    summary.update(
        {
            "lastDoctorStatus": status,
            "lastDoctorRunAt": timestamp,
        }
    )
    config["summary"] = summary
    config["updatedAt"] = timestamp
    write_json(home / "config.json", config)
    return config


def merge_json(path: Path, defaults: dict[str, Any]) -> None:
    existing: dict[str, Any] = {}
    if path.is_file():
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict):
            existing = parsed
    merged = {**existing, **defaults}
    write_json(path, merged)


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _merge_summary(value: object) -> dict[str, Any]:
    existing = value if isinstance(value, dict) else {}
    return {
        "registeredWorkrootCount": int(existing.get("registeredWorkrootCount") or 0),
        "activeWorkrootCount": int(existing.get("activeWorkrootCount") or 0),
        "lastRegistryUpdatedAt": existing.get("lastRegistryUpdatedAt"),
        "lastDoctorStatus": existing.get("lastDoctorStatus"),
        "lastDoctorRunAt": existing.get("lastDoctorRunAt"),
        "lastMigrationId": existing.get("lastMigrationId"),
        "lastMigrationAt": existing.get("lastMigrationAt"),
    }


def _merge_maintenance(value: object) -> dict[str, Any]:
    existing = value if isinstance(value, dict) else {}
    return {
        "status": str(existing.get("status") or "idle"),
        "operation": existing.get("operation"),
        "operationId": existing.get("operationId"),
        "startedAt": existing.get("startedAt"),
        "updatedAt": existing.get("updatedAt"),
        "message": existing.get("message"),
        "blocksWrites": bool(existing.get("blocksWrites", True)),
        "blocksContextGeneration": bool(existing.get("blocksContextGeneration", False)),
    }


def _merge_context_control(value: object) -> dict[str, Any]:
    existing = value if isinstance(value, dict) else {}
    diagnostics = existing.get("diagnosticLogging")
    return {
        "defaultTargetTokens": _positive_int(existing.get("defaultTargetTokens"), 1200),
        "defaultHardTokenLimit": _positive_int(existing.get("defaultHardTokenLimit"), 2400),
        "diagnosticLogging": _merge_context_diagnostic_logging(diagnostics),
    }


def _merge_context_diagnostic_logging(value: object) -> dict[str, Any]:
    existing = value if isinstance(value, dict) else {}
    return {
        "enabled": bool(existing.get("enabled", False)),
        "includeRenderedPackage": bool(existing.get("includeRenderedPackage", False)),
        "includeTraceSummary": bool(existing.get("includeTraceSummary", True)),
        "includeRetrievalSummary": bool(existing.get("includeRetrievalSummary", True)),
        "includeTokenEstimate": bool(existing.get("includeTokenEstimate", True)),
        "retentionDays": _positive_int(existing.get("retentionDays"), 7),
        "maxEntriesPerWorkroot": _positive_int(existing.get("maxEntriesPerWorkroot"), 200),
    }


def _positive_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def load_context_control_config(home: Path | str | None) -> ContextControlConfig:
    if home is None:
        return ContextControlConfig()
    config_path = Path(home).expanduser().resolve() / "config.json"
    merged = _merge_context_control(_read_json_object(config_path).get("contextControl"))
    diagnostic = merged["diagnosticLogging"]
    return ContextControlConfig(
        default_target_tokens=int(merged["defaultTargetTokens"]),
        default_hard_token_limit=int(merged["defaultHardTokenLimit"]),
        diagnostic_logging=ContextDiagnosticLoggingConfig(
            enabled=bool(diagnostic["enabled"]),
            include_rendered_package=bool(diagnostic["includeRenderedPackage"]),
            include_trace_summary=bool(diagnostic["includeTraceSummary"]),
            include_retrieval_summary=bool(diagnostic["includeRetrievalSummary"]),
            include_token_estimate=bool(diagnostic["includeTokenEstimate"]),
            retention_days=int(diagnostic["retentionDays"]),
            max_entries_per_workroot=int(diagnostic["maxEntriesPerWorkroot"]),
        ),
    )


def register_workroot(home: Path, workroot_id: str, name: str, user_directory: Path) -> WorkrootRegistration:
    home = home.expanduser().resolve()
    user_directory = user_directory.expanduser().resolve()
    initialize_environment(home)
    lock_path = home / "registry/.registry.lock"

    with file_lock(lock_path):
        registration = register_workroot_unlocked(home, workroot_id, name, user_directory)

    return registration


def register_workroot_unlocked(home: Path, workroot_id: str, name: str, user_directory: Path) -> WorkrootRegistration:
    home = home.expanduser().resolve()
    user_directory = user_directory.expanduser().resolve()
    workroots_path = home / "registry/workroots.jsonl"
    bindings_path = home / "registry/directory-bindings.jsonl"
    workroots = read_jsonl(workroots_path)
    bindings = read_jsonl(bindings_path)

    if any(record.get("workroot_id") == workroot_id for record in workroots):
        raise ValueError(f"Workroot ID already exists: {workroot_id}")
    for record in bindings:
        if record.get("user_directory") == str(user_directory):
            raise ValueError(f"user directory already registered as Workroot {record.get('workroot_id')}: {user_directory}")

    state_directory = home / "workroots" / workroot_id
    for rel in PER_WORKROOT_DIRS:
        (state_directory / rel).mkdir(parents=True, exist_ok=True)

    write_json(
        state_directory / "workroot.json",
        {
            "workroot_id": workroot_id,
            "name": name,
            "user_directory": str(user_directory),
            "state_directory": str(state_directory),
            "version": "0.9.530",
        },
    )
    append_jsonl(
        workroots_path,
        {
            "workroot_id": workroot_id,
            "name": name,
            "state_directory": str(state_directory),
            "version": "0.9.530",
        },
    )
    append_jsonl(
        bindings_path,
        {
            "workroot_id": workroot_id,
            "user_directory": str(user_directory),
        },
    )
    refresh_environment_registry_summary(home)

    return WorkrootRegistration(
        workroot_id=workroot_id,
        name=name,
        user_directory=str(user_directory),
        state_directory=str(state_directory),
    )
