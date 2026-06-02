"""Live Codex + Workroot protocol end-to-end harness."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
from typing import Any

from ai_workroot.protocol.lease import now_utc
from ai_workroot.state.layout import workroot_sqlite_path
from ai_workroot.state.registry import list_workroots
from tests.e2e.harness import REPO_ROOT, env_for, run_cli, validate_user_directory, write_user_files
from tests.e2e.live_agent import REMOTE_LLM_OPT_IN_ENV, build_live_agent_environment
from tests.e2e.personas import Persona
from tests.e2e.safety import OWNED_SENTINEL, ensure_not_real_repo_cwd_for_live_e2e, prepare_run_root, validate_run_root


WORKROOT_ID = "wr_live_protocol"
USER_DIR_SLUG = "live-protocol"
REMOTE_ENV = "AI_WORKROOT_E2E_CODEX_REMOTE"
REMOTE_AUTH_ENV = "AI_WORKROOT_E2E_CODEX_REMOTE_AUTH_TOKEN_ENV"
GUIDED_TASK_ID = "task-live-protocol-guided"
GUIDED_RUN_ID = "run-evt-live-guided-intent"
GUIDED_PROGRESS_SUMMARY = "Live guided progress captured. Review the live protocol transcript next."
GUIDED_HANDOFF_NEXT_ACTION = "Review the live protocol transcript before expanding coverage."
CASE_RESULT_PATH_KEYS = ("stdout", "stderr", "lastMessage", "commandLog", "dbSummary")

LIVE_PROTOCOL_PERSONA = Persona(
    slug=USER_DIR_SLUG,
    name="Live Protocol",
    workroot_id=WORKROOT_ID,
    native_agent_entry=True,
    user_files={"notes.md": "# Live Protocol Notes\n\nSandbox input only.\n"},
)


@dataclass(frozen=True)
class LiveProtocolCaseResult:
    name: str
    user_directory: Path
    transcript_dir: Path
    stdout_path: Path
    stderr_path: Path
    last_message_path: Path
    command_log_path: Path
    db_summary_path: Path
    returncode: int
    classification: str = ""

    @property
    def passed(self) -> bool:
        return self.returncode == 0 and self.last_message_path.is_file()

    def failure_report(self) -> str:
        parts = [
            f"case={self.name}",
            f"returncode={self.returncode}",
            f"prompt={self.transcript_dir / 'prompt.txt'}",
            f"stdout={self.stdout_path}",
            f"stderr={self.stderr_path}",
            f"lastMessage={self.last_message_path}",
            f"commandLog={self.command_log_path}",
            f"dbSummary={self.db_summary_path}",
        ]
        if self.stderr_path.is_file():
            stderr = self.stderr_path.read_text(encoding="utf-8")
            if stderr.strip():
                parts.append(f"stderrTail={stderr[-2000:]}")
        return "\n".join(parts)


@dataclass(frozen=True)
class LiveProtocolResult:
    run_root: Path
    ai_workroot_home: Path
    summary_path: Path
    case_results: tuple[LiveProtocolCaseResult, ...]

    @property
    def returncode(self) -> int:
        return 0 if all(result.passed for result in self.case_results) else 1


@dataclass(frozen=True)
class _LiveProtocolContext:
    run_root: Path
    ai_workroot_home: Path
    user_directory: Path
    env: dict[str, str]
    codex: str


def create_workroot_command_wrapper(*, run_root: Path, command_log_path: Path) -> Path:
    bin_dir = run_root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    (bin_dir / OWNED_SENTINEL).touch()
    command_log_path.parent.mkdir(parents=True, exist_ok=True)
    wrapper = bin_dir / "workroot"
    wrapper.write_text(
        """#!/usr/bin/env python3
from __future__ import annotations
from datetime import datetime, timezone
import json
import os
import subprocess
import sys

started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
log_path = os.environ.get("WORKROOT_COMMAND_LOG")
command = [sys.executable, "-m", "ai_workroot", *sys.argv[1:]]
completed = subprocess.run(command, text=True, capture_output=True, check=False)
ended = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
if log_path:
    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "argv": sys.argv[1:],
            "cwd": os.getcwd(),
            "returncode": completed.returncode,
            "startedAt": started,
            "endedAt": ended,
        }, ensure_ascii=False, sort_keys=True) + "\\n")
sys.stdout.write(completed.stdout)
sys.stderr.write(completed.stderr)
raise SystemExit(completed.returncode)
""",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    return wrapper


def classify_workroot_commands(records: list[dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    for record in records:
        argv = [str(part) for part in record.get("argv") or []]
        if not argv:
            continue
        if argv[0] == "context":
            labels.append("context")
        elif len(argv) >= 2 and argv[0] == "agent" and argv[1] in {"sync", "commit"}:
            labels.append(f"agent {argv[1]}")
        else:
            labels.append(argv[0])
    return labels


def classify_protocol_discovery(commands: list[str], *, returncode: int) -> str:
    if returncode != 0:
        return "failed"
    if "agent sync" in commands and "agent commit" in commands:
        return "discovered_full_protocol"
    if "agent sync" in commands:
        return "discovered_sync"
    if "context" in commands:
        return "context_only"
    if not commands:
        return "no_workroot_call"
    return "failed"


def build_codex_command(
    *,
    codex: str,
    user_directory: Path,
    ai_workroot_home: Path,
    last_message_path: Path,
    prompt: str,
    remote: str = "",
    remote_auth_token_env: str = "",
    extra_writable_dirs: tuple[Path, ...] = (),
) -> tuple[str, ...]:
    prefix: list[str] = [codex]
    if remote:
        prefix.extend(["--remote", remote])
    if remote_auth_token_env:
        prefix.extend(["--remote-auth-token-env", remote_auth_token_env])
    command = [
        *prefix,
        "exec",
        "--cd",
        str(user_directory),
        "--add-dir",
        str(ai_workroot_home),
    ]
    for directory in extra_writable_dirs:
        command.extend(["--add-dir", str(directory)])
    command.extend(
        [
            "--skip-git-repo-check",
            "--ephemeral",
            "--ignore-rules",
            "--sandbox",
            "workspace-write",
            "--output-last-message",
            str(last_message_path),
            prompt,
        ]
    )
    return tuple(command)


def summarize_workroot_database(*, ai_home: Path, workroot_id: str) -> dict[str, Any]:
    records = list_workroots(ai_workroot_home=ai_home)
    record = next(item for item in records if item["workrootId"] == workroot_id)
    sqlite_path = workroot_sqlite_path(Path(record["stateDirectory"]))
    with sqlite3.connect(sqlite_path) as conn:
        return {
            "sqlitePath": str(sqlite_path),
            "tasks": _count(conn, "tasks"),
            "taskRuns": _count(conn, "task_runs"),
            "taskSummariesCurrent": _count_where(conn, "task_summaries", "status = 'current'"),
            "handoffsCurrent": _count_where(conn, "handoffs", "status = 'current' AND task_id IS NOT NULL"),
            "taskItems": _count(conn, "task_items"),
            "protocolEvents": [
                {"eventId": row[0], "kind": row[1], "status": row[2]}
                for row in conn.execute(
                    """
                    SELECT event_id, kind, status
                    FROM protocol_events
                    ORDER BY received_at, event_id
                    """
                ).fetchall()
            ],
            "protocolBatches": [
                {"batchId": row[0], "idempotencyKey": row[1], "status": row[2], "responseJson": row[3]}
                for row in conn.execute(
                    """
                    SELECT batch_id, idempotency_key, status, response_json
                    FROM protocol_commit_batches
                    ORDER BY received_at, batch_id
                    """
                ).fetchall()
            ],
            "latestTask": _latest_task(conn),
        }


def run_guided_minimal_loop(*, run_root: Path, sandbox_base: Path) -> LiveProtocolCaseResult:
    context = _prepare_live_protocol_workspace(run_root=run_root, sandbox_base=sandbox_base, reset=True)
    return _run_codex_case(
        case_name="guided-minimal-loop",
        context=context,
        prompt=_guided_minimal_loop_prompt(
            transcript_dir=context.run_root / "transcripts" / "live-protocol" / "guided-minimal-loop"
        ),
    )


def run_continuation_from_handoff(*, run_root: Path, sandbox_base: Path) -> LiveProtocolCaseResult:
    context = _prepare_live_protocol_workspace(run_root=run_root, sandbox_base=sandbox_base, reset=False)
    return _run_codex_case(
        case_name="continuation-from-handoff",
        context=context,
        prompt=_continuation_prompt(),
    )


def run_degraded_commit_case(*, run_root: Path, sandbox_base: Path) -> LiveProtocolCaseResult:
    context = _prepare_live_protocol_workspace(run_root=run_root, sandbox_base=sandbox_base, reset=True)
    transcript_dir = context.run_root / "transcripts" / "live-protocol" / "degraded-commit"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    expired = _prepare_expired_lease_progress_request(context=context, transcript_dir=transcript_dir)
    return _run_codex_case(
        case_name="degraded-commit",
        context=context,
        prompt=_degraded_prompt(request_path=expired["request_path"]),
    )


def run_discovery_diagnostic(*, run_root: Path, sandbox_base: Path) -> LiveProtocolCaseResult:
    context = _prepare_live_protocol_workspace(run_root=run_root, sandbox_base=sandbox_base, reset=True)
    result = _run_codex_case(
        case_name="discovery-diagnostic",
        context=context,
        prompt=_discovery_prompt(),
    )
    records = _read_command_log(result.command_log_path)
    commands = classify_workroot_commands(records)
    classification = classify_protocol_discovery(commands, returncode=result.returncode)
    summary = _summary_for_result(result, context=context)
    summary["classification"] = classification
    result.db_summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    classified = LiveProtocolCaseResult(
        name=result.name,
        user_directory=result.user_directory,
        transcript_dir=result.transcript_dir,
        stdout_path=result.stdout_path,
        stderr_path=result.stderr_path,
        last_message_path=result.last_message_path,
        command_log_path=result.command_log_path,
        db_summary_path=result.db_summary_path,
        returncode=result.returncode,
        classification=classification,
    )
    write_live_protocol_summary(context.run_root, case_results=(classified,))
    return classified


def run_codex_live_protocol(*, run_root: Path, sandbox_base: Path | None = None) -> LiveProtocolResult:
    if sandbox_base is None:
        sandbox_base = run_root.parent
    guided = run_guided_minimal_loop(run_root=run_root, sandbox_base=sandbox_base)
    continuation = run_continuation_from_handoff(run_root=run_root, sandbox_base=sandbox_base)
    degraded = run_degraded_commit_case(run_root=run_root, sandbox_base=sandbox_base)
    discovery = run_discovery_diagnostic(run_root=run_root, sandbox_base=sandbox_base)
    summary_path = write_live_protocol_summary(
        run_root,
        case_results=(guided, continuation, degraded, discovery),
    )
    return LiveProtocolResult(
        run_root=run_root,
        ai_workroot_home=run_root / "ai-workroot-home",
        summary_path=summary_path,
        case_results=(guided, continuation, degraded, discovery),
    )


def _prepare_live_protocol_workspace(
    *,
    run_root: Path,
    sandbox_base: Path,
    reset: bool,
) -> _LiveProtocolContext:
    if os.environ.get(REMOTE_LLM_OPT_IN_ENV) != "1":
        raise RuntimeError(f"live-protocol E2E requires {REMOTE_LLM_OPT_IN_ENV}=1")
    if reset:
        run_root = prepare_run_root(run_root, sandbox_base=sandbox_base)
    else:
        run_root = validate_run_root(run_root, sandbox_base=sandbox_base)
    ai_home = run_root / "ai-workroot-home"
    env = env_for(ai_home)
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("codex CLI is not available")
    user_directory = run_root / "user-dirs" / USER_DIR_SLUG
    if reset:
        write_user_files(user_directory, LIVE_PROTOCOL_PERSONA.user_files)
        init = run_cli(
            (
                "init",
                "--name",
                LIVE_PROTOCOL_PERSONA.name,
                "--directory",
                str(user_directory),
                "--id",
                WORKROOT_ID,
                "--native-agent-entry",
            ),
            env=env,
            cwd=REPO_ROOT,
        )
        if init.returncode != 0:
            raise RuntimeError(init.stderr or init.stdout)
    if not user_directory.is_dir():
        raise RuntimeError(f"missing live protocol user directory: {user_directory}")
    failures = validate_user_directory(LIVE_PROTOCOL_PERSONA, user_directory, ai_home)
    if failures:
        raise RuntimeError("; ".join(failures))
    ensure_not_real_repo_cwd_for_live_e2e(user_directory)
    return _LiveProtocolContext(
        run_root=run_root,
        ai_workroot_home=ai_home,
        user_directory=user_directory,
        env=env,
        codex=codex,
    )


def _run_codex_case(*, case_name: str, context: _LiveProtocolContext, prompt: str) -> LiveProtocolCaseResult:
    transcript_dir = context.run_root / "transcripts" / "live-protocol" / case_name
    transcript_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = transcript_dir / "prompt.txt"
    stdout_path = transcript_dir / "codex-stdout.txt"
    stderr_path = transcript_dir / "codex-stderr.txt"
    last_message_path = transcript_dir / "codex-last-message.txt"
    command_log_path = transcript_dir / "workroot-command-log.jsonl"
    db_summary_path = transcript_dir / "db-summary.json"
    prompt_path.write_text(prompt + "\n", encoding="utf-8")
    wrapper = create_workroot_command_wrapper(run_root=context.run_root, command_log_path=command_log_path)
    live_env = build_live_agent_environment(context.env, run_root=context.run_root)
    live_env.update(
        {
            "PATH": f"{wrapper.parent}:{os.environ.get('PATH', '')}",
            "WORKROOT_COMMAND_LOG": str(command_log_path),
        }
    )
    command = build_codex_command(
        codex=context.codex,
        user_directory=context.user_directory,
        ai_workroot_home=context.ai_workroot_home,
        last_message_path=last_message_path,
        prompt=prompt,
        remote=os.environ.get(REMOTE_ENV, ""),
        remote_auth_token_env=os.environ.get(REMOTE_AUTH_ENV, ""),
        extra_writable_dirs=(transcript_dir, wrapper.parent),
    )
    completed = subprocess.run(
        command,
        cwd=context.user_directory,
        env=live_env,
        text=True,
        capture_output=True,
        check=False,
        timeout=360,
    )
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    result = LiveProtocolCaseResult(
        name=case_name,
        user_directory=context.user_directory,
        transcript_dir=transcript_dir,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        last_message_path=last_message_path,
        command_log_path=command_log_path,
        db_summary_path=db_summary_path,
        returncode=completed.returncode,
    )
    db_summary_path.write_text(
        json.dumps(_summary_for_result(result, context=context), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_live_protocol_summary(context.run_root, case_results=(result,))
    return result


def _summary_for_result(result: LiveProtocolCaseResult, *, context: _LiveProtocolContext) -> dict[str, Any]:
    summary = summarize_workroot_database(ai_home=context.ai_workroot_home, workroot_id=WORKROOT_ID)
    summary["case"] = result.name
    summary["commands"] = classify_workroot_commands(_read_command_log(result.command_log_path))
    summary["userDirectoryRuntimeArtifacts"] = _runtime_artifacts_in_user_directory(context.user_directory)
    return summary


def write_live_protocol_summary(
    run_root: Path,
    *,
    case_results: tuple[LiveProtocolCaseResult | dict[str, Any], ...],
) -> Path:
    summary_path = run_root / "reports" / "live-protocol-summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    merged: dict[str, dict[str, Any]] = {}
    for result in _existing_live_protocol_case_results(run_root, summary_path=summary_path):
        merged[str(result["name"])] = result
    for result in case_results:
        item = _case_result_summary(result)
        merged[str(item["name"])] = item
    merged_results = list(merged.values())
    summary_path.write_text(
        json.dumps(
            {
                "returncode": 0 if all(int(item.get("returncode") or 0) == 0 for item in merged_results) else 1,
                "caseResults": merged_results,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return summary_path


def _existing_live_protocol_case_results(run_root: Path, *, summary_path: Path) -> list[dict[str, Any]]:
    candidates = sorted((run_root / "reports" / "quarantine").glob("**/live-protocol-summary.json"))
    if summary_path.is_file():
        candidates.append(summary_path)
    results: list[dict[str, Any]] = []
    for candidate in candidates:
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        relocated_root = _quarantine_root_for_summary(run_root, candidate)
        for item in payload.get("caseResults") or []:
            if isinstance(item, dict) and item.get("name"):
                results.append(_case_result_summary(item, run_root=run_root, relocated_root=relocated_root))
    return results


def _case_result_summary(
    result: LiveProtocolCaseResult | dict[str, Any],
    *,
    run_root: Path | None = None,
    relocated_root: Path | None = None,
) -> dict[str, Any]:
    if isinstance(result, LiveProtocolCaseResult):
        return {
            "name": result.name,
            "returncode": result.returncode,
            "classification": result.classification,
            "stdout": str(result.stdout_path),
            "stderr": str(result.stderr_path),
            "lastMessage": str(result.last_message_path),
            "commandLog": str(result.command_log_path),
            "dbSummary": str(result.db_summary_path),
        }
    summary = {
        "name": str(result.get("name") or ""),
        "returncode": int(result.get("returncode") or 0),
        "classification": str(result.get("classification") or ""),
        "stdout": str(result.get("stdout") or ""),
        "stderr": str(result.get("stderr") or ""),
        "lastMessage": str(result.get("lastMessage") or ""),
        "commandLog": str(result.get("commandLog") or ""),
        "dbSummary": str(result.get("dbSummary") or ""),
    }
    if run_root is not None:
        for key in CASE_RESULT_PATH_KEYS:
            summary[key] = _remap_quarantined_path(summary[key], run_root=run_root, relocated_root=relocated_root)
    return summary


def _quarantine_root_for_summary(run_root: Path, summary_path: Path) -> Path | None:
    quarantine_root = run_root / "reports" / "quarantine"
    try:
        relative = summary_path.relative_to(quarantine_root)
    except ValueError:
        return None
    if not relative.parts:
        return None
    return quarantine_root / relative.parts[0]


def _remap_quarantined_path(value: str, *, run_root: Path, relocated_root: Path | None) -> str:
    if not value:
        return value
    path = Path(value)
    try:
        relative = path.relative_to(run_root)
    except ValueError:
        return value
    if relocated_root is not None:
        relocated = relocated_root / relative
        if relocated.exists():
            return str(relocated)
    quarantine_root = run_root / "reports" / "quarantine"
    for child in sorted(quarantine_root.iterdir()) if quarantine_root.is_dir() else ():
        candidate = child / relative
        if candidate.exists():
            return str(candidate)
    return value


def _prepare_expired_lease_progress_request(
    *,
    context: _LiveProtocolContext,
    transcript_dir: Path,
) -> dict[str, Path]:
    sync = run_cli(
        (
            "agent",
            "sync",
            "--agent",
            "codex",
            "--cwd",
            str(context.user_directory),
            "--reason",
            "before_work",
            "--query",
            "Prepare degraded live protocol task.",
        ),
        env=context.env,
        cwd=REPO_ROOT,
    )
    if sync.returncode != 0:
        raise RuntimeError(sync.stderr or sync.stdout)
    sync_response = json.loads(sync.stdout)
    intent_path = transcript_dir / "degraded-intent.json"
    intent_path.write_text(
        json.dumps(
            _commit_request(
                request_id="req-live-degraded-intent",
                lease_id=sync_response["workroot_contract"]["commit_contract"]["lease_id"],
                idempotency_key="idem-live-degraded-intent",
                event_id="evt-live-degraded-intent",
                kind="intent",
                payload={
                    "intent_text": "Prepare degraded live protocol task.",
                    "classification": {"persistence": "normal", "confidence": 0.95, "reason": "live-e2e-setup"},
                    "task_hint": {
                        "title": "Live degraded protocol task",
                        "task_id": "task-live-degraded",
                        "parent_task_id": None,
                    },
                },
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    intent = run_cli(("agent", "commit", "--request", str(intent_path)), env=context.env, cwd=context.user_directory)
    if intent.returncode != 0:
        raise RuntimeError(intent.stderr or intent.stdout)
    intent_response = json.loads(intent.stdout)
    lease_id = intent_response["workroot_contract"]["commit_contract"]["lease_id"]
    sqlite_path = workroot_sqlite_path(
        Path(list_workroots(ai_workroot_home=context.ai_workroot_home)[0]["stateDirectory"])
    )
    with sqlite3.connect(sqlite_path) as conn:
        conn.execute(
            "UPDATE exchange_leases SET expires_at = ? WHERE lease_id = ?",
            ("2026-01-01T00:00:00Z", lease_id),
        )
        conn.commit()
    request_path = transcript_dir / "degraded-progress.json"
    request_path.write_text(
        json.dumps(
            _commit_request(
                request_id="req-live-degraded-progress",
                lease_id=lease_id,
                idempotency_key="idem-live-degraded-progress",
                event_id="evt-live-degraded-progress",
                kind="progress",
                payload={
                    "task_id": intent_response["workroot_contract"]["state_refs"]["task_ref"],
                    "run_id": intent_response["workroot_contract"]["state_refs"]["run_ref"],
                    "summary": "Expired lease live progress was still safe to preserve.",
                    "items_created": [
                        {
                            "item_id": "item-live-degraded-done",
                            "title": "Verify degraded commit remains non-blocking",
                            "status": "done",
                            "result_summary": "Workroot accepted safe progress with a lease warning.",
                        }
                    ],
                },
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"request_path": request_path}


def _guided_minimal_loop_prompt(*, transcript_dir: Path) -> str:
    return f"""Live protocol E2E guided loop.

You are in a sandbox user directory. Use the `workroot` command from PATH. Do not create runtime files in the user directory.
Write request JSON files only under this transcript directory:
{transcript_dir}

Run one shell command that executes the following Python orchestration exactly. It must call Workroot through the `workroot` command, not `python -m ai_workroot` directly.

```bash
python3 - <<'PY'
from pathlib import Path
import json
import subprocess

transcript = Path({str(transcript_dir)!r})
transcript.mkdir(parents=True, exist_ok=True)

def call(argv):
    completed = subprocess.run(["workroot", *argv], text=True, capture_output=True, check=False)
    print("$ workroot " + " ".join(argv))
    print(completed.stdout)
    if completed.stderr:
        print(completed.stderr)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return completed.stdout

call(["context", "--agent", "codex", "--cwd", ".", "--query", "Live protocol guided loop", "--debug"])
sync = json.loads(call([
    "agent", "sync",
    "--agent", "codex",
    "--cwd", ".",
    "--reason", "before_work",
    "--query", "Live protocol guided loop",
    "--work-signal", '{{"phase":"starting","work_kind":"implementation","intended_action":"plan","focus":"live protocol guided loop","concerns":["may_change_user_assets"]}}',
]))

def request(path, request_id, lease_id, idem, event_id, kind, payload):
    data = {{
        "protocol_version": "workroot.v1",
        "request_id": request_id,
        "exchange_lease_id": lease_id,
        "idempotency_key": idem,
        "events": [
            {{
                "event_id": event_id,
                "kind": kind,
                "schema_version": f"{{kind}}.v1",
                "occurred_at": "2026-05-27T00:00:00Z",
                "source": {{"actor_type": "agent", "actor_name": "codex", "session_id": "live-protocol-guided"}},
                "confirmation": {{"status": "agent_observed", "confirmed_by": None}},
                "payload": payload,
                "evidence": [],
            }}
        ],
    }}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    return path

intent_path = request(
    transcript / "intent.json",
    "req-live-guided-intent",
    sync["workroot_contract"]["commit_contract"]["lease_id"],
    "idem-live-guided-intent",
    "evt-live-guided-intent",
    "intent",
    {{
        "intent_text": "Run a live Workroot protocol guided loop.",
        "classification": {{"persistence": "normal", "confidence": 0.95, "reason": "live-e2e"}},
        "task_hint": {{"title": "Live Protocol Guided Loop", "task_id": "{GUIDED_TASK_ID}", "parent_task_id": None}},
    }},
)
intent = json.loads(call(["agent", "commit", "--request", str(intent_path)]))
task_id = intent["workroot_contract"]["state_refs"]["task_ref"]
run_id = intent["workroot_contract"]["state_refs"]["run_ref"]

progress_path = request(
    transcript / "progress.json",
    "req-live-guided-progress",
    intent["workroot_contract"]["commit_contract"]["lease_id"],
    "idem-live-guided-progress",
    "evt-live-guided-progress",
    "progress",
    {{
        "task_id": task_id,
        "run_id": run_id,
        "summary": "{GUIDED_PROGRESS_SUMMARY}",
        "items_created": [
            {{"item_id": "item-live-guided-done", "title": "Execute guided live protocol loop", "status": "done", "result_summary": "Intent and progress were committed."}}
        ],
        "open_questions": [],
        "source_refs": [],
    }},
)
progress = json.loads(call(["agent", "commit", "--request", str(progress_path)]))

continuation = json.loads(call([
    "agent", "commit",
    "--shape", "continuation",
    "--lease", progress["workroot_contract"]["commit_contract"]["lease_id"],
    "--cwd", ".",
    "--state", "Guided live protocol loop committed intent and progress.",
    "--next", "{GUIDED_HANDOFF_NEXT_ACTION}",
]))
continued = json.loads(call([
    "agent", "sync",
    "--agent", "codex",
    "--cwd", ".",
    "--reason", "continue",
    "--query", "Continue live protocol guided loop",
    "--known-state", json.dumps({{"task_id": task_id, "run_id": run_id}}),
    "--work-signal", '{{"phase":"preserving","work_kind":"continuation","intended_action":"preserve","focus":"live protocol guided loop"}}',
]))
(transcript / "guided-result.json").write_text(json.dumps({{"task_id": task_id, "run_id": run_id, "continued": continued}}, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
PY
```

After the command completes, reply with exactly two short lines:
LIVE_PROTOCOL_GUIDED_OK
{GUIDED_PROGRESS_SUMMARY}
"""


def _continuation_prompt() -> str:
    return f"""Live protocol continuation E2E.

Use `workroot` from PATH. Do not create files in the user directory.
Call Workroot to continue this known task:
task_id={GUIDED_TASK_ID}
run_id={GUIDED_RUN_ID}

Run:
workroot agent sync --agent codex --cwd . --reason continue --query "Continue live protocol guided loop" --known-state '{{"task_id":"{GUIDED_TASK_ID}","run_id":"{GUIDED_RUN_ID}"}}' --work-signal '{{"phase":"orienting","work_kind":"continuation","intended_action":"inspect","focus":"live protocol guided loop"}}'

Read the returned task context. Then reply with exactly two short lines:
LIVE_PROTOCOL_CONTINUE_OK
{GUIDED_HANDOFF_NEXT_ACTION}
"""


def _degraded_prompt(*, request_path: Path) -> str:
    return f"""Live protocol degraded commit E2E.

Use `workroot` from PATH. Do not create files in the user directory.
Commit the prepared request:
workroot agent commit --request {request_path}

The lease is intentionally expired. Continue the user-visible work if Workroot returns a warning.
Reply with exactly two short lines:
LIVE_PROTOCOL_DEGRADED_OK
Workroot returned a non-blocking degraded/partial commit response.
"""


def _discovery_prompt() -> str:
    return """Live protocol discovery diagnostic.

Follow the local Workroot instructions in this sandbox. If Workroot gives you control guidance, follow it when practical. Do not create runtime files in the user directory.

Start by asking Workroot for context for this question:
"Discovery diagnostic: should this small piece of work be preserved?"

Then do the lightest useful next step and reply with one short sentence. Do not mention internal storage paths.
"""


def _commit_request(
    *,
    request_id: str,
    lease_id: str,
    idempotency_key: str,
    event_id: str,
    kind: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "protocol_version": "workroot.v1",
        "request_id": request_id,
        "exchange_lease_id": lease_id,
        "idempotency_key": idempotency_key,
        "events": [
            {
                "event_id": event_id,
                "kind": kind,
                "schema_version": f"{kind}.v1",
                "occurred_at": now_utc(),
                "source": {"actor_type": "agent", "actor_name": "codex", "session_id": "live-protocol"},
                "confirmation": {"status": "agent_observed", "confirmed_by": None},
                "payload": payload,
                "evidence": [],
            }
        ],
    }


def _read_command_log(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _runtime_artifacts_in_user_directory(user_directory: Path) -> list[str]:
    disallowed_names = {
        "longrun",
        "runtime",
        "transcripts",
        "workroot-command-log.jsonl",
        "db-summary.json",
        "codex-stdout.txt",
        "codex-stderr.txt",
        "codex-last-message.txt",
        "intent.json",
        "progress.json",
        "handoff.json",
    }
    artifacts: list[str] = []
    for entry in user_directory.rglob("*"):
        if entry.name in disallowed_names:
            artifacts.append(str(entry.relative_to(user_directory)))
    return sorted(artifacts)


def _count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _count_where(conn: sqlite3.Connection, table: str, where: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0])


def _latest_task(conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT task_id, summary_id, title
        FROM tasks
        ORDER BY updated_at DESC
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        return None
    return {"taskId": row[0], "summaryId": row[1], "title": row[2]}
