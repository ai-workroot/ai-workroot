"""Live Codex client end-to-end harness."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess

from tests.e2e.harness import REPO_ROOT, env_for, run_cli, write_user_files
from tests.e2e.personas import PERSONAS, Persona
from tests.e2e.safety import ensure_not_real_repo_cwd_for_live_e2e, prepare_run_root


REMOTE_LLM_OPT_IN_ENV = "AI_WORKROOT_E2E_ALLOW_REMOTE_LLM"
CODEX_HOME_FILE_ALLOWLIST = ("auth.json", "config.toml", "AGENTS.md")
READ_ONLY_CONTEXT_SMOKE_COMMAND = "python3 -m ai_workroot context --agent codex --cwd . --query 'Clean Mode' --debug"
LIVE_AGENT_PROMPT = (
    "Live-agent read-only context smoke. Do not modify files. First run exactly this auxiliary command from cwd .: "
    f"{READ_ONLY_CONTEXT_SMOKE_COMMAND}. Do not inspect README.md directly. "
    "Then reply with exactly two short lines: "
    "LIVE_AGENT_E2E_OK, then one sentence describing the visible Context Package metadata from that command output."
)


@dataclass(frozen=True)
class LiveAgentPersonaResult:
    persona_slug: str
    user_directory: Path
    transcript_dir: Path
    stdout_path: Path
    stderr_path: Path
    last_message_path: Path
    returncode: int

    @property
    def passed(self) -> bool:
        return self.returncode == 0 and self.last_message_path.is_file()


@dataclass(frozen=True)
class LiveAgentResult:
    run_root: Path
    ai_workroot_home: Path
    summary_path: Path
    persona_results: tuple[LiveAgentPersonaResult, ...]

    @property
    def returncode(self) -> int:
        return 0 if self.passed else 1

    @property
    def passed(self) -> bool:
        return bool(self.persona_results) and all(result.passed for result in self.persona_results)


def expected_live_agent_persona_slugs() -> tuple[str, ...]:
    return tuple(persona.slug for persona in PERSONAS)


def run_codex_live_agent(*, run_root: Path, sandbox_base: Path | None = None) -> LiveAgentResult:
    if os.environ.get(REMOTE_LLM_OPT_IN_ENV) != "1":
        raise RuntimeError(f"live-agent E2E requires {REMOTE_LLM_OPT_IN_ENV}=1")
    run_root = prepare_run_root(run_root, sandbox_base=sandbox_base)
    ai_workroot_home = run_root / "ai-workroot-home"
    env = env_for(ai_workroot_home)
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("codex CLI is not available")

    persona_results = tuple(
        _run_codex_live_agent_for_persona(
            persona,
            run_root=run_root,
            ai_workroot_home=ai_workroot_home,
            env=env,
            codex=codex,
        )
        for persona in PERSONAS
    )
    summary_path = run_root / "reports" / "live-agent-summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(
            {
                "returncode": 0 if all(result.passed for result in persona_results) else 1,
                "aiWorkrootHome": str(ai_workroot_home),
                "personaResults": [
                    {
                        "personaSlug": result.persona_slug,
                        "cwd": str(result.user_directory),
                        "returncode": result.returncode,
                        "stdout": str(result.stdout_path),
                        "stderr": str(result.stderr_path),
                        "lastMessage": str(result.last_message_path),
                    }
                    for result in persona_results
                ],
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
        summary_path=summary_path,
        persona_results=persona_results,
    )


def _run_codex_live_agent_for_persona(
    persona: Persona,
    *,
    run_root: Path,
    ai_workroot_home: Path,
    env: dict[str, str],
    codex: str,
) -> LiveAgentPersonaResult:
    user_directory = run_root / "user-dirs" / persona.slug
    write_user_files(user_directory, persona.user_files)
    init = run_cli(
        (
            "init",
            "--name",
            persona.name,
            "--directory",
            str(user_directory),
            "--id",
            persona.workroot_id,
            "--native-agent-entry" if persona.native_agent_entry else "--no-native-agent-entry",
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

    transcript_dir = run_root / "transcripts" / "live-agent" / persona.slug
    transcript_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = transcript_dir / "prompt.txt"
    stdout_path = transcript_dir / "codex-stdout.txt"
    stderr_path = transcript_dir / "codex-stderr.txt"
    last_message_path = transcript_dir / "codex-last-message.txt"
    prompt = LIVE_AGENT_PROMPT
    prompt_path.write_text(prompt + "\n", encoding="utf-8")

    live_env = build_live_agent_environment(env, run_root=run_root)

    command = (
        codex,
        "exec",
        "--cd",
        str(user_directory),
        "--add-dir",
        str(ai_workroot_home),
        "--skip-git-repo-check",
        "--ephemeral",
        "--ignore-rules",
        "--sandbox",
        "workspace-write",
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
    return LiveAgentPersonaResult(
        persona_slug=persona.slug,
        user_directory=user_directory,
        transcript_dir=transcript_dir,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        last_message_path=last_message_path,
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
