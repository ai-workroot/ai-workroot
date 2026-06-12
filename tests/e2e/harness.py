"""Shared E2E helpers for invoking the package CLI."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
import time

from ai_workroot.state.environment import ensure_environment_config, write_environment_config
from tests.e2e.personas import Persona


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    cwd: str
    returncode: int
    stdout: str
    stderr: str
    elapsed_ms: int = 0
    timed_out: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "command": list(self.command),
            "cwd": self.cwd,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "elapsed_ms": self.elapsed_ms,
            "timed_out": self.timed_out,
        }


def env_for(ai_workroot_home: Path) -> dict[str, str]:
    ai_workroot_home = ai_workroot_home.expanduser().resolve()
    _enable_e2e_context_diagnostics(ai_workroot_home)
    run_root = ai_workroot_home.parent
    return {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT / "src"),
        "AI_WORKROOT_HOME": str(ai_workroot_home),
        "HOME": str(run_root / "home"),
    }


def _enable_e2e_context_diagnostics(ai_workroot_home: Path) -> None:
    config = ensure_environment_config(ai_workroot_home)
    context_control = config.get("contextControl", {})
    diagnostic_logging = context_control.get("diagnosticLogging", {})
    config["contextControl"] = {
        **context_control,
        "defaultTargetTokens": int(context_control.get("defaultTargetTokens") or 1200),
        "defaultHardTokenLimit": int(context_control.get("defaultHardTokenLimit") or 2400),
        "diagnosticLogging": {
            **diagnostic_logging,
            "enabled": True,
            "includeRenderedPackage": True,
            "includeTraceSummary": True,
            "includeRetrievalSummary": True,
            "includeTokenEstimate": True,
            "retentionDays": int(diagnostic_logging.get("retentionDays") or 7),
            "maxEntriesPerWorkroot": int(diagnostic_logging.get("maxEntriesPerWorkroot") or 500),
        },
    }
    write_environment_config(ai_workroot_home / "config.json", config)


def run_cli(
    args: tuple[str, ...],
    *,
    env: dict[str, str],
    cwd: Path = REPO_ROOT,
    timeout_seconds: float = 60.0,
) -> CommandResult:
    command = (sys.executable, "-m", "ai_workroot", *args)
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return CommandResult(
            command=tuple(command),
            cwd=str(cwd),
            returncode=124,
            stdout=_timeout_text(exc.output),
            stderr=_timeout_text(exc.stderr) or f"command timed out after {timeout_seconds} seconds",
            elapsed_ms=elapsed_ms,
            timed_out=True,
        )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return CommandResult(
        command=tuple(command),
        cwd=str(cwd),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        elapsed_ms=elapsed_ms,
        timed_out=False,
    )


def _timeout_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


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
            if len(text.splitlines()) > 13:
                failures.append(f"{filename} is too long")
            if (
                f'workroot agent sync --agent {agent} --cwd . --query "<current user request>" --format packet'
                not in text
            ):
                failures.append(f"{filename} missing relative sync command")
    else:
        for filename in ("AGENTS.md", "CLAUDE.md"):
            if (user_directory / filename).exists():
                failures.append(f"unexpected Native Agent Entry {filename}")
    return failures
