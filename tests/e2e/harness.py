"""Shared E2E helpers for invoking the package CLI."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys

from tests.e2e.personas import Persona


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    cwd: str
    returncode: int
    stdout: str
    stderr: str

    def as_dict(self) -> dict[str, object]:
        return {
            "command": list(self.command),
            "cwd": self.cwd,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


def env_for(ai_workroot_home: Path) -> dict[str, str]:
    run_root = ai_workroot_home.parent
    return {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT / "src"),
        "AI_WORKROOT_HOME": str(ai_workroot_home),
        "HOME": str(run_root / "home"),
    }


def run_cli(args: tuple[str, ...], *, env: dict[str, str], cwd: Path = REPO_ROOT) -> CommandResult:
    command = (sys.executable, "-m", "ai_workroot", *args)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return CommandResult(
        command=tuple(command),
        cwd=str(cwd),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def write_user_files(user_directory: Path, files: dict[str, str]) -> None:
    user_directory.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        path = user_directory / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def validate_user_directory(persona: Persona, user_directory: Path, ai_workroot_home: Path) -> list[str]:
    failures: list[str] = []
    for entry in user_directory.rglob("*"):
        if ai_workroot_home in entry.resolve().parents:
            failures.append(f"user directory entry points into AI_WORKROOT_HOME: {entry}")
    if persona.native_agent_entry:
        for filename, agent in (("AGENTS.md", "codex"), ("CLAUDE.md", "claude")):
            path = user_directory / filename
            if not path.is_file():
                failures.append(f"missing Native Agent Entry {filename}")
                continue
            text = path.read_text(encoding="utf-8")
            if str(ai_workroot_home) in text:
                failures.append(f"{filename} leaks AI_WORKROOT_HOME")
            if len(text.splitlines()) > 12:
                failures.append(f"{filename} is too long")
            if f"workroot context --agent {agent} --cwd ." not in text:
                failures.append(f"{filename} missing relative context command")
    else:
        for filename in ("AGENTS.md", "CLAUDE.md"):
            if (user_directory / filename).exists():
                failures.append(f"unexpected Native Agent Entry {filename}")
    return failures
