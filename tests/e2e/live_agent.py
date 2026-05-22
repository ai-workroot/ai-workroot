"""Live Codex client end-to-end harness."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess

from tests.e2e.harness import REPO_ROOT, env_for, run_cli
from tests.e2e.personas import PERSONAS
from tests.e2e.safety import ensure_not_real_repo_cwd_for_live_e2e, prepare_run_root


REMOTE_LLM_OPT_IN_ENV = "AI_WORKROOT_E2E_ALLOW_REMOTE_LLM"
CODEX_HOME_FILE_ALLOWLIST = ("auth.json", "config.toml", "AGENTS.md")


@dataclass(frozen=True)
class LiveAgentResult:
    run_root: Path
    ai_workroot_home: Path
    transcript_dir: Path
    stdout_path: Path
    stderr_path: Path
    last_message_path: Path
    summary_path: Path
    returncode: int

    @property
    def passed(self) -> bool:
        return self.returncode == 0 and self.last_message_path.is_file()


def run_codex_live_agent(*, run_root: Path, sandbox_base: Path | None = None) -> LiveAgentResult:
    if os.environ.get(REMOTE_LLM_OPT_IN_ENV) != "1":
        raise RuntimeError(f"live-agent E2E requires {REMOTE_LLM_OPT_IN_ENV}=1")
    run_root = prepare_run_root(run_root, sandbox_base=sandbox_base)
    ai_workroot_home = run_root / "ai-workroot-home"
    user_directory = run_root / "user-dirs" / "persona-software-engineer"
    user_directory.mkdir(parents=True, exist_ok=True)
    for rel, content in PERSONAS[0].user_files.items():
        path = user_directory / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    env = env_for(ai_workroot_home)
    init = run_cli(
        (
            "init",
            "--name",
            PERSONAS[0].name,
            "--directory",
            str(user_directory),
            "--id",
            PERSONAS[0].workroot_id,
            "--no-native-agent-entry",
        ),
        env=env,
        cwd=REPO_ROOT,
    )
    if init.returncode != 0:
        raise RuntimeError(init.stderr or init.stdout)
    context = run_cli(
        ("context", "--agent", "codex", "--cwd", str(user_directory), "--query", "Clean Mode", "--debug"),
        env=env,
        cwd=REPO_ROOT,
    )
    if context.returncode != 0:
        raise RuntimeError(context.stderr or context.stdout)

    ensure_not_real_repo_cwd_for_live_e2e(user_directory)
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("codex CLI is not available")

    transcript_dir = run_root / "transcripts" / "live-agent"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = transcript_dir / "prompt.txt"
    stdout_path = transcript_dir / "codex-stdout.txt"
    stderr_path = transcript_dir / "codex-stderr.txt"
    last_message_path = transcript_dir / "codex-last-message.txt"
    summary_path = run_root / "reports" / "live-agent-summary.json"
    prompt = (
        "Live-agent E2E smoke. Do not modify files. Inspect the local Workroot context for cwd . "
        "and reply with exactly two short lines: LIVE_AGENT_E2E_OK, then one sentence describing "
        "the visible Context Package metadata."
    )
    prompt_path.write_text(prompt + "\n", encoding="utf-8")

    live_env = build_live_agent_environment(env, run_root=run_root)

    command = (
        codex,
        "exec",
        "--cd",
        str(user_directory),
        "--skip-git-repo-check",
        "--ephemeral",
        "--ignore-rules",
        "--sandbox",
        "read-only",
        "--output-last-message",
        str(last_message_path),
        prompt,
    )
    completed = subprocess.run(
        command,
        cwd=user_directory,
        env=live_env,
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
    )
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(
            {
                "command": list(command),
                "cwd": str(user_directory),
                "returncode": completed.returncode,
                "stdout": str(stdout_path),
                "stderr": str(stderr_path),
                "lastMessage": str(last_message_path),
                "aiWorkrootHome": str(ai_workroot_home),
                "usedCodexHome": live_env.get("CODEX_HOME"),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return LiveAgentResult(
        run_root=run_root,
        ai_workroot_home=ai_workroot_home,
        transcript_dir=transcript_dir,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        last_message_path=last_message_path,
        summary_path=summary_path,
        returncode=completed.returncode,
    )


def build_live_agent_environment(base_env: dict[str, str], *, run_root: Path) -> dict[str, str]:
    sandbox_home = run_root / "home"
    sandbox_codex_home = sandbox_home / ".codex"
    sandbox_codex_home.mkdir(parents=True, exist_ok=True)
    _copy_codex_auth_config_to_sandbox(sandbox_codex_home)
    live_env = {
        **os.environ,
        "HOME": base_env["HOME"],
        "AI_WORKROOT_HOME": base_env["AI_WORKROOT_HOME"],
        "PYTHONPATH": base_env["PYTHONPATH"],
        "CODEX_HOME": str(sandbox_codex_home),
    }
    return live_env


def _copy_codex_auth_config_to_sandbox(sandbox_codex_home: Path) -> None:
    source_home = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).expanduser().resolve()
    if not source_home.is_dir() or source_home == sandbox_codex_home.resolve():
        return
    for name in CODEX_HOME_FILE_ALLOWLIST:
        source = source_home / name
        if source.is_file():
            shutil.copy2(source, sandbox_codex_home / name)
