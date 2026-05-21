"""Clean Workroot initialization runtime flow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import secrets

from ai_workroot.agent.native_entry import sync_native_agent_entry
from ai_workroot.runtime.bootstrap import resolve_ai_workroot_home
from ai_workroot.runtime.environment import WorkrootRegistration, register_workroot
from ai_workroot.storage.jsonl_registry import read_jsonl
from ai_workroot.storage.sqlite import initialize_workroot_sqlite


@dataclass(frozen=True)
class InitResult:
    registration: WorkrootRegistration
    native_agent_entry: bool
    warnings: tuple[str, ...] = ()

    def message(self) -> str:
        suffix = " agent-ready" if self.native_agent_entry else " registered"
        return f"initialized {self.registration.workroot_id}{suffix}"


def initialize_workroot(
    *,
    name: str,
    directory: Path | str,
    workroot_id: str | None = None,
    native_agent_entry: bool = False,
    ai_workroot_home: Path | str | None = None,
) -> InitResult:
    home = resolve_ai_workroot_home(ai_workroot_home)
    user_directory = Path(directory).expanduser().resolve()
    _validate_user_directory(user_directory, home)
    user_directory.mkdir(parents=True, exist_ok=True)
    _probe_directory(user_directory)

    resolved_id = workroot_id or _generate_workroot_id(name)
    _check_workroot_id(resolved_id)

    warnings = tuple(_nested_workroot_warnings(home, user_directory))
    registration = register_workroot(home, resolved_id, name, user_directory)
    initialize_workroot_sqlite(Path(registration.state_directory) / "cache/workroot.sqlite")

    if native_agent_entry:
        sync_native_agent_entry(user_directory / "AGENTS.md", "codex")
        sync_native_agent_entry(user_directory / "CLAUDE.md", "claude")

    return InitResult(registration=registration, native_agent_entry=native_agent_entry, warnings=warnings)


def _generate_workroot_id(name: str) -> str:
    return f"wr_{_slug(name)}_{secrets.token_hex(4)}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "workroot"


def _check_workroot_id(workroot_id: str) -> None:
    if not re.fullmatch(r"wr_[a-z0-9_]+", workroot_id):
        raise ValueError(f"invalid Workroot ID: {workroot_id}")
    if "/" in workroot_id or "\\" in workroot_id or ".." in workroot_id:
        raise ValueError(f"invalid Workroot ID: {workroot_id}")


def _validate_user_directory(user_directory: Path, home: Path) -> None:
    if user_directory == home or home in user_directory.parents:
        raise ValueError("user directory must not be AI_WORKROOT_HOME or inside it")
    if user_directory.exists() and not user_directory.is_dir():
        raise ValueError(f"user directory is not a directory: {user_directory}")


def _probe_directory(user_directory: Path) -> None:
    probe = user_directory / f".ai-workroot-write-probe-{secrets.token_hex(4)}"
    try:
        probe.write_text("probe\n", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        raise ValueError(f"user directory is not writable: {user_directory}") from exc


def _nested_workroot_warnings(home: Path, user_directory: Path) -> list[str]:
    warnings: list[str] = []
    resolved = user_directory.resolve()
    for record in read_jsonl(home / "registry/workroots.jsonl"):
        state_directory = Path(str(record.get("state_directory", "")))
        metadata_path = state_directory / "workroot.json"
        if not metadata_path.is_file():
            continue
        try:
            import json

            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        existing_raw = metadata.get("user_directory")
        if not existing_raw:
            continue
        existing = Path(str(existing_raw)).resolve()
        if resolved != existing and (existing in resolved.parents or resolved in existing.parents):
            warnings.append(
                f"warning: nested Workroot directory relationship with {record.get('workroot_id')}: {existing}"
            )
    return warnings
