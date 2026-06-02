# Live Codex Agent Protocol E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in live E2E suite that validates real Codex Client + remote model + Workroot protocol `context/sync/commit/continue` behavior in a sandbox.

**Architecture:** Keep product runtime untouched. Add a test-only live protocol harness that creates a sandbox Workroot, exposes a `workroot` command wrapper on `PATH`, captures command logs/transcripts, and verifies SQLite facts after live Codex runs. Runner opt-in remains fail-closed.

**Tech Stack:** Python unittest, subprocess, Codex CLI, SQLite, existing `tests.e2e` safety/harness helpers, `python3 -m ai_workroot`.

---

## File Structure

- Modify `tests/e2e/runner.py`: register `live-protocol` and enforce remote LLM opt-in for all live suites.
- Modify `tests/e2e/safety_cases.py`: add runner contract assertions for `live-protocol`.
- Create `tests/e2e/live_protocol.py`: live harness, command wrapper, prompt generation, Codex invocation, command-log parsing, SQLite summaries, and deterministic setup helpers.
- Create `tests/e2e/live_protocol_cases.py`: unittest cases for guided loop, continuation, degraded commit, and discovery diagnostic.
- Keep reports/transcripts under the E2E run root only.

## Task 1: Register the Suite and Fail Closed

**Files:**
- Modify: `tests/e2e/runner.py`
- Modify: `tests/e2e/safety_cases.py`

- [ ] **Step 1: Write failing safety tests**

Add these assertions to `tests/e2e/safety_cases.py`:

```python
def test_e2e_runner_lists_live_protocol_suite_when_explicitly_enabled(self) -> None:
    from tests.e2e.runner import SUITES

    self.assertIn("live-protocol", SUITES)

def test_live_protocol_requires_remote_llm_opt_in(self) -> None:
    import os
    import tempfile

    from tests.e2e.runner import main

    previous_run = os.environ.get("AI_WORKROOT_RUN_E2E")
    previous_remote = os.environ.get("AI_WORKROOT_E2E_ALLOW_REMOTE_LLM")
    try:
        os.environ["AI_WORKROOT_RUN_E2E"] = "1"
        os.environ.pop("AI_WORKROOT_E2E_ALLOW_REMOTE_LLM", None)
        with tempfile.TemporaryDirectory() as tmp:
            sandbox_base = Path(tmp) / "sandboxes"
            run_root = sandbox_base / "run-live-protocol-opt-in"
            rc = main(
                [
                    "--suite",
                    "live-protocol",
                    "--dry-run",
                    "--sandbox-base",
                    str(sandbox_base),
                    "--run-root",
                    str(run_root),
                ]
            )
        self.assertEqual(rc, 2)
    finally:
        if previous_run is None:
            os.environ.pop("AI_WORKROOT_RUN_E2E", None)
        else:
            os.environ["AI_WORKROOT_RUN_E2E"] = previous_run
        if previous_remote is None:
            os.environ.pop("AI_WORKROOT_E2E_ALLOW_REMOTE_LLM", None)
        else:
            os.environ["AI_WORKROOT_E2E_ALLOW_REMOTE_LLM"] = previous_remote
```

- [ ] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.e2e.safety_cases -v
```

Expected: fail because `live-protocol` is not in `SUITES`.

- [ ] **Step 3: Implement runner registration**

Update `tests/e2e/runner.py`:

```python
SUITES = {
    "safety": "tests.e2e.safety_cases",
    "persona-smoke": "tests.e2e.persona_smoke_cases",
    "longrun": "tests.e2e.longrun_cases",
    "live-agent": "tests.e2e.live_agent_cases",
    "live-protocol": "tests.e2e.live_protocol_cases",
}

REMOTE_LLM_SUITES = {"live-agent", "live-protocol"}
```

Replace the live-agent-only opt-in check with:

```python
remote_suites = sorted(set(selected) & REMOTE_LLM_SUITES)
if remote_suites and os.environ.get("AI_WORKROOT_E2E_ALLOW_REMOTE_LLM") != "1":
    joined = ", ".join(remote_suites)
    print(f"{joined} E2E requires AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1.", file=__import__("sys").stderr)
    return 2
```

- [ ] **Step 4: Verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.e2e.safety_cases -v
```

Expected: pass.

## Task 2: Build Test-Only Live Protocol Harness

**Files:**
- Create: `tests/e2e/live_protocol.py`
- Test: `tests/e2e/live_protocol_cases.py`

- [ ] **Step 1: Write failing harness tests**

Create the first version of `tests/e2e/live_protocol_cases.py` with import and non-remote harness tests:

```python
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tests.e2e.live_protocol import (
    WORKROOT_ID,
    build_codex_command,
    classify_workroot_commands,
    create_workroot_command_wrapper,
    summarize_workroot_database,
)
from tests.e2e.harness import env_for, run_cli
from tests.e2e.safety import new_default_run_root, prepare_run_root


class LiveProtocolHarnessTest(unittest.TestCase):
    def test_wrapper_logs_command_and_executes_workroot_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox_base = Path(tmp) / "sandboxes"
            run_root = prepare_run_root(new_default_run_root(base=sandbox_base), sandbox_base=sandbox_base)
            ai_home = run_root / "ai-workroot-home"
            env = env_for(ai_home)
            user_dir = run_root / "user-dirs" / "live-protocol"
            user_dir.mkdir(parents=True)
            init = run_cli(
                (
                    "init",
                    "--name",
                    "Live Protocol",
                    "--directory",
                    str(user_dir),
                    "--id",
                    WORKROOT_ID,
                    "--native-agent-entry",
                ),
                env=env,
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            log_path = run_root / "transcripts" / "live-protocol" / "wrapper-log.jsonl"
            wrapper = create_workroot_command_wrapper(run_root=run_root, command_log_path=log_path)
            completed = __import__("subprocess").run(
                (str(wrapper), "status", "--cwd", "."),
                cwd=user_dir,
                env={**env, "WORKROOT_COMMAND_LOG": str(log_path)},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(records[0]["argv"], ["status", "--cwd", "."])
            self.assertEqual(records[0]["returncode"], 0)

    def test_command_classifier_reads_semantic_sequence(self) -> None:
        records = [
            {"argv": ["context", "--agent", "codex", "--cwd", "."]},
            {"argv": ["agent", "sync", "--reason", "before_work"]},
            {"argv": ["agent", "commit", "--request", "intent.json"]},
            {"argv": ["agent", "commit", "--request", "progress.json"]},
            {"argv": ["agent", "sync", "--reason", "continue"]},
        ]
        self.assertEqual(
            classify_workroot_commands(records),
            ["context", "agent sync", "agent commit", "agent commit", "agent sync"],
        )

    def test_codex_remote_option_is_global_when_configured(self) -> None:
        command = build_codex_command(
            codex="/opt/homebrew/bin/codex",
            user_directory=Path("/tmp/user"),
            ai_workroot_home=Path("/tmp/ai-home"),
            last_message_path=Path("/tmp/last.txt"),
            prompt="hello",
            remote="ws://127.0.0.1:4321",
        )
        self.assertEqual(command[:4], ("/opt/homebrew/bin/codex", "--remote", "ws://127.0.0.1:4321", "exec"))

    def test_database_summary_counts_protocol_facts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox_base = Path(tmp) / "sandboxes"
            run_root = prepare_run_root(new_default_run_root(base=sandbox_base), sandbox_base=sandbox_base)
            ai_home = run_root / "ai-workroot-home"
            env = env_for(ai_home)
            user_dir = run_root / "user-dirs" / "live-protocol"
            user_dir.mkdir(parents=True)
            init = run_cli(
                (
                    "init",
                    "--name",
                    "Live Protocol",
                    "--directory",
                    str(user_dir),
                    "--id",
                    WORKROOT_ID,
                    "--native-agent-entry",
                ),
                env=env,
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            summary = summarize_workroot_database(ai_home=ai_home, workroot_id=WORKROOT_ID)
            self.assertEqual(summary["tasks"], 0)
            self.assertEqual(summary["taskRuns"], 0)
            self.assertEqual(summary["protocolEvents"], [])
```

- [ ] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.e2e.live_protocol_cases.LiveProtocolHarnessTest -v
```

Expected: import failure because `tests.e2e.live_protocol` does not exist.

- [ ] **Step 3: Implement minimal harness**

Create `tests/e2e/live_protocol.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from typing import Any

from tests.e2e.harness import REPO_ROOT, env_for, run_cli, validate_user_directory
from tests.e2e.live_agent import REMOTE_LLM_OPT_IN_ENV, build_live_agent_environment
from tests.e2e.personas import Persona
from tests.e2e.safety import ensure_not_real_repo_cwd_for_live_e2e, prepare_run_root

WORKROOT_ID = "wr_live_protocol"
USER_DIR_SLUG = "live-protocol"

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


@dataclass(frozen=True)
class LiveProtocolResult:
    run_root: Path
    ai_workroot_home: Path
    summary_path: Path
    case_results: tuple[LiveProtocolCaseResult, ...]

    @property
    def returncode(self) -> int:
        return 0 if all(result.passed for result in self.case_results) else 1


def create_workroot_command_wrapper(*, run_root: Path, command_log_path: Path) -> Path:
    bin_dir = run_root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
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


def build_codex_command(
    *,
    codex: str,
    user_directory: Path,
    ai_workroot_home: Path,
    last_message_path: Path,
    prompt: str,
    remote: str = "",
    remote_auth_token_env: str = "",
) -> tuple[str, ...]:
    prefix: list[str] = [codex]
    if remote:
        prefix.extend(["--remote", remote])
    if remote_auth_token_env:
        prefix.extend(["--remote-auth-token-env", remote_auth_token_env])
    return (
        *prefix,
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


def summarize_workroot_database(*, ai_home: Path, workroot_id: str) -> dict[str, Any]:
    registry = json.loads((ai_home / "registry.json").read_text(encoding="utf-8"))
    record = next(item for item in registry["workroots"] if item["workrootId"] == workroot_id)
    sqlite_path = Path(record["stateDirectory"]) / "cache" / "workroot.sqlite"
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
                    "SELECT event_id, kind, status FROM protocol_events ORDER BY received_at, event_id"
                ).fetchall()
            ],
            "protocolBatches": [
                {"idempotencyKey": row[0], "status": row[1], "responseJson": row[2]}
                for row in conn.execute(
                    "SELECT idempotency_key, status, response_json FROM protocol_commit_batches ORDER BY received_at"
                ).fetchall()
            ],
            "latestTask": _latest_task(conn),
        }


def _count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _count_where(conn: sqlite3.Connection, table: str, where: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0])


def _latest_task(conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT task_id, summary_id, title FROM tasks ORDER BY updated_at DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    return {"taskId": row[0], "summaryId": row[1], "title": row[2]}
```

- [ ] **Step 4: Verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.e2e.live_protocol_cases.LiveProtocolHarnessTest -v
```

Expected: pass.

## Task 3: Add Guided Live Protocol Loop

**Files:**
- Modify: `tests/e2e/live_protocol.py`
- Modify: `tests/e2e/live_protocol_cases.py`

- [ ] **Step 1: Add failing live test**

Add `LiveProtocolE2ETest.test_codex_guided_protocol_minimal_loop` to `tests/e2e/live_protocol_cases.py`:

```python
class LiveProtocolE2ETest(unittest.TestCase):
    def test_codex_guided_protocol_minimal_loop(self) -> None:
        run_root = os.environ.get("AI_WORKROOT_E2E_RUN_ROOT")
        sandbox_base = os.environ.get("AI_WORKROOT_E2E_SANDBOX_BASE")
        if not run_root or not sandbox_base:
            self.skipTest("live-protocol E2E must run through tests.e2e.runner")
        if os.environ.get("AI_WORKROOT_E2E_ALLOW_REMOTE_LLM") != "1":
            self.skipTest("remote LLM opt-in is required")

        from tests.e2e.live_protocol import run_guided_minimal_loop

        result = run_guided_minimal_loop(run_root=Path(run_root), sandbox_base=Path(sandbox_base))

        self.assertEqual(result.returncode, 0, result.stderr_path.read_text(encoding="utf-8"))
        self.assertIn("LIVE_PROTOCOL_GUIDED_OK", result.last_message_path.read_text(encoding="utf-8"))
        records = [
            json.loads(line)
            for line in result.command_log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        commands = classify_workroot_commands(records)
        for expected in ("context", "agent sync", "agent commit", "agent commit", "agent commit", "agent sync"):
            self.assertIn(expected, commands)
        summary = json.loads(result.db_summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["tasks"], 1)
        self.assertEqual(summary["taskRuns"], 1)
        self.assertEqual(summary["taskSummariesCurrent"], 1)
        self.assertEqual(summary["handoffsCurrent"], 1)
        event_statuses = {(event["kind"], event["status"]) for event in summary["protocolEvents"]}
        self.assertIn(("intent", "applied"), event_statuses)
        self.assertIn(("progress", "applied"), event_statuses)
        self.assertIn(("handoff", "applied"), event_statuses)
```

- [ ] **Step 2: Verify RED without runner skips cleanly**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.e2e.live_protocol_cases.LiveProtocolE2ETest.test_codex_guided_protocol_minimal_loop -v
```

Expected: skipped outside E2E runner.

- [ ] **Step 3: Implement guided loop runner**

Add to `tests/e2e/live_protocol.py`:

```python
def run_guided_minimal_loop(*, run_root: Path, sandbox_base: Path) -> LiveProtocolCaseResult:
    context = _prepare_live_protocol_workspace(run_root=run_root, sandbox_base=sandbox_base)
    return _run_codex_case(
        case_name="guided-minimal-loop",
        context=context,
        prompt=_guided_minimal_loop_prompt(),
    )
```

Implement private helpers:

```python
@dataclass(frozen=True)
class _LiveProtocolContext:
    run_root: Path
    ai_workroot_home: Path
    user_directory: Path
    env: dict[str, str]
    codex: str


def _prepare_live_protocol_workspace(*, run_root: Path, sandbox_base: Path) -> _LiveProtocolContext:
    if os.environ.get(REMOTE_LLM_OPT_IN_ENV) != "1":
        raise RuntimeError(f"live-protocol E2E requires {REMOTE_LLM_OPT_IN_ENV}=1")
    run_root = prepare_run_root(run_root, sandbox_base=sandbox_base)
    ai_home = run_root / "ai-workroot-home"
    env = env_for(ai_home)
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("codex CLI is not available")
    user_directory = run_root / "user-dirs" / USER_DIR_SLUG
    user_directory.mkdir(parents=True, exist_ok=True)
    for rel, content in LIVE_PROTOCOL_PERSONA.user_files.items():
        path = user_directory / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
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
```

Use request JSON files under the transcript directory, never under the user directory. The prompt must instruct Codex to write request files into the transcript directory and call `workroot agent commit --request <that-file>`.

- [ ] **Step 4: Verify live guided loop manually**

Run only when remote calls are intended:

```bash
AI_WORKROOT_RUN_E2E=1 \
AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1 \
PYTHONPATH=src \
python3 -m tests.e2e.runner --suite live-protocol
```

Expected: guided loop passes or fails with transcript paths.

## Task 4: Add Continuation, Degraded, and Discovery Cases

**Files:**
- Modify: `tests/e2e/live_protocol.py`
- Modify: `tests/e2e/live_protocol_cases.py`

- [ ] **Step 1: Add continuation assertion**

Add `run_continuation_from_handoff` and a test that reuses the same run root after `run_guided_minimal_loop`. It must assert:

```python
self.assertEqual(summary["tasks"], 1)
self.assertIn("LIVE_PROTOCOL_CONTINUE_OK", result.last_message_path.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Add degraded assertion**

Add `run_degraded_commit_case` and a test that prepares an expired lease locally, then asks Codex to commit progress using that lease. It must assert:

```python
self.assertIn("LIVE_PROTOCOL_DEGRADED_OK", result.last_message_path.read_text(encoding="utf-8"))
latest_batch = json.loads(summary["protocolBatches"][-1]["responseJson"])
self.assertTrue(latest_batch["agent_may_continue"])
self.assertIn(latest_batch["batch_status"], {"partial", "degraded"})
self.assertIn("lease_expired", latest_batch["warnings"])
```

- [ ] **Step 3: Add discovery diagnostic assertion**

Add `run_discovery_diagnostic` and a non-blocking test. It must write one classification:

```python
self.assertIn(result.classification, {"discovered_full_protocol", "context_only", "no_workroot_call", "failed"})
```

The classification must also be stored in the case `db-summary.json`.

- [ ] **Step 4: Verify live suite**

Run:

```bash
AI_WORKROOT_RUN_E2E=1 \
AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1 \
PYTHONPATH=src \
python3 -m tests.e2e.runner --suite live-protocol
```

Expected: guided, continuation, degraded pass; discovery reports a classification.

## Task 5: Full Verification

**Files:**
- No new files.

- [ ] **Step 1: Run focused E2E unit checks**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.e2e.safety_cases -v
PYTHONPATH=src python3 -m unittest tests.e2e.live_protocol_cases.LiveProtocolHarnessTest -v
```

Expected: pass.

- [ ] **Step 2: Run default test suite**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
```

Expected: pass, with live protocol tests skipped unless runner opt-in is present.

- [ ] **Step 3: Run release validation**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" scripts/dev/validate-release.sh
```

Expected: PASS.

- [ ] **Step 4: Run live protocol only after explicit opt-in**

Run:

```bash
AI_WORKROOT_RUN_E2E=1 \
AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1 \
PYTHONPATH=src \
python3 -m tests.e2e.runner --suite live-protocol
```

Optional WebSocket app-server transport:

```bash
AI_WORKROOT_RUN_E2E=1 \
AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1 \
AI_WORKROOT_E2E_CODEX_REMOTE=ws://127.0.0.1:PORT \
PYTHONPATH=src \
python3 -m tests.e2e.runner --suite live-protocol
```

Expected: writes reports under the sandbox run root and does not create runtime/process files inside the user directory.
