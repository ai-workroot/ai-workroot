"""Level 2 multi-persona Clean Workroot smoke harness."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from tests.e2e.harness import CommandResult, REPO_ROOT, env_for, run_cli, validate_user_directory, write_user_files
from tests.e2e.personas import PERSONAS
from tests.e2e.safety import prepare_run_root


@dataclass(frozen=True)
class PersonaSmokeResult:
    run_root: Path
    ai_workroot_home: Path
    report_path: Path
    commands_path: Path
    failures_path: Path
    failures: tuple[str, ...]
    client_report: str

    @property
    def passed(self) -> bool:
        return not self.failures


def run_persona_smoke(*, run_root: Path, sandbox_base: Path | None = None) -> PersonaSmokeResult:
    run_root = prepare_run_root(run_root, sandbox_base=sandbox_base)
    reports_dir = run_root / "reports"
    user_dirs = run_root / "user-dirs"
    ai_workroot_home = run_root / "ai-workroot-home"
    reports_dir.mkdir(parents=True, exist_ok=True)
    user_dirs.mkdir(parents=True, exist_ok=True)
    env = env_for(ai_workroot_home)
    commands: list[CommandResult] = []
    failures: list[str] = []

    for persona in PERSONAS:
        user_directory = user_dirs / persona.slug
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
        status = run_cli(("status", "--cwd", str(user_directory)), env=env, cwd=REPO_ROOT)
        context = run_cli(("context", "--agent", "codex", "--cwd", str(user_directory), "--query", "Clean Mode"), env=env)
        doctor = run_cli(("doctor", "--cwd", str(user_directory)), env=env)
        commands.extend([init, status, context, doctor])
        for label, result in (("init", init), ("status", status), ("context", context), ("doctor", doctor)):
            if result.returncode != 0:
                failures.append(f"{persona.slug} {label} failed: {result.stderr or result.stdout}")
        if "TokenUsage:" not in context.stdout:
            failures.append(f"{persona.slug} context missing token usage")
        failures.extend(f"{persona.slug} {failure}" for failure in validate_user_directory(persona, user_directory, ai_workroot_home))

    listed = run_cli(("list", "--format", "json"), env=env)
    commands.append(listed)
    if listed.returncode != 0:
        failures.append(f"list failed: {listed.stderr or listed.stdout}")
    else:
        records = json.loads(listed.stdout)
        if len(records) != len(PERSONAS):
            failures.append(f"expected {len(PERSONAS)} Workroots, got {len(records)}")

    report_path = reports_dir / "summary.md"
    failures_path = reports_dir / "failures.json"
    commands_path = reports_dir / "commands.json"
    client_report = _render_client_report(run_root, failures)
    report_path.write_text(client_report, encoding="utf-8")
    failures_path.write_text(json.dumps(failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    commands_path.write_text(json.dumps([command.as_dict() for command in commands], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return PersonaSmokeResult(
        run_root=run_root,
        ai_workroot_home=ai_workroot_home,
        report_path=report_path,
        commands_path=commands_path,
        failures_path=failures_path,
        failures=tuple(failures),
        client_report=client_report,
    )


def _render_client_report(run_root: Path, failures: list[str]) -> str:
    lines = [
        "# AI Workroot Level 2 Persona Smoke Report",
        "",
        f"RunRoot: {run_root}",
        f"Overall: {'PASS' if not failures else 'FAIL'}",
        f"PersonaCount: {len(PERSONAS)}",
        "",
        "## Personas",
    ]
    for persona in PERSONAS:
        lines.append(f"- {persona.slug}: {persona.name}")
    if failures:
        lines.extend(["", "## Failures", *[f"- {failure}" for failure in failures]])
    return "\n".join(lines) + "\n"
