"""Runtime registry read flows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_workroot.state.jsonl import read_jsonl
from ai_workroot.state.layout import resolve_ai_workroot_home


def list_workroots(*, ai_workroot_home: Path | str | None = None) -> list[dict[str, str]]:
    home = resolve_ai_workroot_home(ai_workroot_home)
    records: list[dict[str, str]] = []
    bindings_by_id = {
        str(record.get("workroot_id") or ""): str(record.get("user_directory") or "")
        for record in read_jsonl(home / "registry/directory-bindings.jsonl")
    }
    for record in read_jsonl(home / "registry/workroots.jsonl"):
        state_directory = str(record.get("state_directory") or "")
        workroot_json = _read_workroot_json(Path(state_directory))
        workroot_id = str(record.get("workroot_id") or "")
        user_directory = str(workroot_json.get("user_directory") or bindings_by_id.get(workroot_id) or "")
        item = {
            "workrootId": workroot_id,
            "name": str(record.get("name") or ""),
            "stateDirectory": state_directory,
            "userDirectory": user_directory,
        }
        warning = str(workroot_json.get("_metadata_warning") or "")
        if warning:
            item["metadataWarning"] = warning
        records.append(item)
    return records


def find_workroot_by_cwd(cwd: Path | str, *, ai_workroot_home: Path | str | None = None) -> dict[str, str]:
    target = Path(cwd).expanduser().resolve()
    best: dict[str, str] | None = None
    best_len = -1
    for record in list_workroots(ai_workroot_home=ai_workroot_home):
        user_dir = Path(record["userDirectory"]).expanduser().resolve()
        if target == user_dir or user_dir in target.parents:
            path_len = len(user_dir.parts)
            if path_len > best_len:
                best = record
                best_len = path_len
    if best is None:
        raise ValueError(f"no registered Workroot found for cwd: {target}")
    return best


def _read_workroot_json(state_directory: Path) -> dict[str, Any]:
    path = state_directory / "workroot.json"
    if not path.is_file():
        return {}
    try:
        data = path.read_text(encoding="utf-8")
        parsed = json.loads(data)
    except (OSError, json.JSONDecodeError):
        return {"_metadata_warning": f"malformed_workroot_json:{path}"}
    return parsed if isinstance(parsed, dict) else {}
