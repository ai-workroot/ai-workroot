#!/usr/bin/env python3
"""Developer bootstrap preflight and local state setup for AI Workroot."""

from __future__ import annotations

from pathlib import Path

try:
    from workroot_agent_entry import apply_managed_block, claude_block, codex_block
    from workroot_client import now_utc, slugify
    from workroot_paths import resolve_ai_workroot_home, workroot_sqlite_path
    from workroot_sqlite import initialize_workroot_sqlite
    from workroot_state import InitializedWorkroot, initialize_workroot_state, read_jsonl
except ModuleNotFoundError:  # pragma: no cover - package import path for tests.
    from scripts.workroot_agent_entry import apply_managed_block, claude_block, codex_block
    from scripts.workroot_client import now_utc, slugify
    from scripts.workroot_paths import resolve_ai_workroot_home, workroot_sqlite_path
    from scripts.workroot_sqlite import initialize_workroot_sqlite
    from scripts.workroot_state import InitializedWorkroot, initialize_workroot_state, read_jsonl


BOOTSTRAP_LOCAL_DIR = ".ai-workroot-local"


def is_ai_workroot_repo(path: Path) -> bool:
    return (
        (path / "PROJECT_BRIEF.md").exists()
        and (path / "AGENTS.md").exists()
        and (path / "scripts/workroot_cli.py").exists()
        and (path / ".workroot/kernel/VERSION").exists()
    )


def ensure_gitignore_entry(repo: Path, entry: str) -> None:
    gitignore = repo / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if entry in existing.splitlines():
        return
    suffix = "" if existing.endswith("\n") or not existing else "\n"
    gitignore.write_text(existing + suffix + entry + "\n", encoding="utf-8")


def existing_bootstrap_workroot(home: Path, workroot_id: str, repo: Path) -> InitializedWorkroot | None:
    for record in read_jsonl(home / "registry/workroots.jsonl"):
        if record.get("workrootId") != workroot_id:
            continue
        registered_dir = Path(str(record.get("userDirectory", ""))).resolve()
        if registered_dir != repo:
            raise ValueError(
                f"bootstrap-dev Workroot ID {workroot_id} already exists for a different directory: {registered_dir}"
            )
        return InitializedWorkroot(
            workroot_id=workroot_id,
            name=str(record.get("name") or "AI Workroot Project"),
            user_directory=registered_dir,
            state_directory=Path(str(record.get("stateDirectory", ""))).resolve(),
        )
    return None


def ensure_bootstrap_side_effects(repo: Path, state_directory: Path) -> None:
    initialize_workroot_sqlite(workroot_sqlite_path(state_directory))
    local_dir = repo / BOOTSTRAP_LOCAL_DIR
    for rel in ("drafts", "reviews", "patches", "context-packages"):
        (local_dir / rel).mkdir(parents=True, exist_ok=True)
    ensure_gitignore_entry(repo, f"{BOOTSTRAP_LOCAL_DIR}/")
    apply_managed_block(repo / "AGENTS.md", codex_block())
    apply_managed_block(repo / "CLAUDE.md", claude_block())


def bootstrap_dev(repo: Path, dry_run: bool = False, now: str | None = None) -> str:
    repo = repo.resolve()
    if not is_ai_workroot_repo(repo):
        raise SystemExit("bootstrap-dev must run from the AI Workroot repository")
    if dry_run:
        return "bootstrap-dev preflight ok"

    timestamp = now or now_utc()
    workroot_id = f"wr_{slugify(repo.name).replace('-', '_')}"
    home = resolve_ai_workroot_home()
    existing = existing_bootstrap_workroot(home, workroot_id, repo)
    if existing is not None:
        ensure_bootstrap_side_effects(repo, existing.state_directory)
        return f"bootstrap-dev reused {workroot_id}"
    initialized = initialize_workroot_state(home, workroot_id, "AI Workroot Project", repo, now=timestamp)
    ensure_bootstrap_side_effects(repo, initialized.state_directory)
    return f"bootstrap-dev initialized {workroot_id}"
