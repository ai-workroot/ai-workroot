from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLIC_SEED = ROOT / "docs/history/public-seed"
LOCAL_ARTIFACT_IGNORE_PATTERNS = (
    ".git",
    ".idea",
    ".ai-workroot-local",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "*.pyc",
    "*.egg-info",
    ".DS_Store",
    "__MACOSX",
)


def install_public_seed_fixture(workroot: Path, *, include_agent_entries: bool = True) -> None:
    """Install the historical Public Seed layout into a temporary test repo."""
    for rel in (".workroot", "space"):
        src = PUBLIC_SEED / rel
        dst = workroot / rel
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    if include_agent_entries:
        for name in ("AGENTS.md", "CLAUDE.md"):
            shutil.copy2(PUBLIC_SEED / name, workroot / name)


def copy_repo_with_public_seed(target: Path, *, include_agent_entries: bool = True) -> None:
    """Copy the current repo and add Public Seed files only inside the copy."""
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns(*LOCAL_ARTIFACT_IGNORE_PATTERNS),
    )
    install_public_seed_fixture(target, include_agent_entries=include_agent_entries)
