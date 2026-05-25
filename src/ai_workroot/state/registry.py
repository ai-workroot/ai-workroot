"""Runtime registry read flows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_workroot.state.jsonl import read_jsonl
from ai_workroot.state.layout import resolve_ai_workroot_home


def list_workroots(*, ai_workroot_home: Path | str | None = None) -> list[dict[str, str]]:
    home = resolve_ai_workroot_home(ai_workroot_home)
    records: list[dict[str, str]] = []
    for record in read_jsonl(home / "registry/workroots.jsonl"):
        state_directory = str(record.get("state_directory") or "")
        workroot_json = _read_workroot_json(Path(state_directory))
        records.append(
            {
                "workrootId": str(record.get("workroot_id") or ""),
                "name": str(record.get("name") or ""),
                "stateDirectory": state_directory,
                "userDirectory": str(workroot_json.get("user_directory") or ""),
            }
        )
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
    data = path.read_text(encoding="utf-8")
    import json

    parsed = json.loads(data)
    return parsed if isinstance(parsed, dict) else {}
