"""Clean Workroot initialization command."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import secrets

from ai_workroot.capabilities.assets.rules import ensure_default_asset_rules
from ai_workroot.state.environment import WorkrootRegistration, register_workroot, unregister_workroot
from ai_workroot.state.jsonl import read_jsonl
from ai_workroot.state.layout import ensure_workroot_id, resolve_ai_workroot_home, validate_user_directory
from ai_workroot.state.sqlite import initialize_workroot_sqlite


@dataclass(frozen=True)
class InitResult:
    registration: WorkrootRegistration
    warnings: tuple[str, ...] = ()

    def message(self) -> str:
        return f"initialized {self.registration.workroot_id} registered"


def initialize_workroot(
    *,
    name: str,
    directory: Path | str,
    workroot_id: str | None = None,
    ai_workroot_home: Path | str | None = None,
) -> InitResult:
    home = resolve_ai_workroot_home(ai_workroot_home)
    user_directory = validate_user_directory(Path(directory), home, create=True)

    resolved_id = workroot_id or _generate_workroot_id(name)
    ensure_workroot_id(resolved_id)

    warnings = tuple(_nested_workroot_warnings(home, user_directory))
    registration = register_workroot(home, resolved_id, name, user_directory)
    initialize_workroot_sqlite(Path(registration.state_directory) / "cache/workroot.sqlite")
    ensure_default_asset_rules(
        state_directory=Path(registration.state_directory),
        user_directory=Path(registration.user_directory),
        workroot_id=registration.workroot_id,
    )

    return InitResult(registration=registration, warnings=warnings)


def rollback_initialized_workroot(
    result: InitResult,
    *,
    ai_workroot_home: Path | str | None = None,
) -> None:
    home = resolve_ai_workroot_home(ai_workroot_home)
    unregister_workroot(
        home,
        workroot_id=result.registration.workroot_id,
        user_directory=Path(result.registration.user_directory),
    )


def _generate_workroot_id(name: str) -> str:
    return f"wr_{_slug(name)}_{secrets.token_hex(4)}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "workroot"


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
