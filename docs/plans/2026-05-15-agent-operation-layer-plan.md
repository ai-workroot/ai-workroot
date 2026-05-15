# Agent Operation Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a thin Agent Operation Layer that keeps AI Workroot file-first while making agent startup, CLI use, registry writes, Mind promotion, and continuation updates fast and safe.

**Architecture:** Keep CSV and filesystem records as the source of truth. Add compact kernel startup guidance, one optional user-owned startup guidance file, high-level CLI commands, a registry store with lock and atomic write semantics, and session-level continuation commands.

**Tech Stack:** Python standard library, pytest, CSV/JSON/Markdown files, existing AI Workroot scripts.

---

## File Map

- Create: `.workroot/kernel/boot/agent-fast-start.md`
  - Compact operational startup guide for agents.
- Modify: `.workroot/kernel/boot/read-order.json`
  - Add fast-start, document optional user startup guidance, and remove long user interaction contract from default reads.
- Modify: `AGENTS.md`
  - Mention fast-start and the optional `space/profile/startup.md` extension point.
- Modify: `scripts/workroot_client.py`
  - Integrate registry locking, atomic writes, Mind path/source behavior, and continuation separation.
- Modify: `scripts/workroot_cli.py`
  - Add discovery, recipe, batch, task complete, session summarize, and continue rebuild commands.
- Modify: `scripts/validate_kernel.py`
  - Validate new boot file and keep schema constraints aligned.
- Create or modify: `tests/test_agent_fast_start.py`
  - Verify read order and startup contract.
- Create or modify: `tests/test_workroot_cli_discovery.py`
  - Verify quickstart, schema, recipe, and doctor output.
- Create or modify: `tests/test_registry_store.py`
  - Verify atomic writes and concurrent writes.
- Modify: `tests/test_workroot_client.py`
  - Verify Mind and continuation behavior.
- Modify: `tests/test_workroot_cli.py`
  - Verify happy path and batch operations.
- Modify: `tests/test_kernel_contracts.py`
  - Verify release-safe layout.

## Task 1: Add Agent Fast Start

**Files:**
- Create: `.workroot/kernel/boot/agent-fast-start.md`
- Modify: `.workroot/kernel/boot/read-order.json`
- Modify: `AGENTS.md`
- Test: `tests/test_agent_fast_start.py`

- [ ] **Step 1: Write failing tests for fast-start read order**

Create `tests/test_agent_fast_start.py`:

```python
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_agent_fast_start_exists() -> None:
    path = ROOT / ".workroot/kernel/boot/agent-fast-start.md"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "pure greeting" in text
    assert "space/profile/startup.md" in text
    assert "continue" in text
    assert "task_registry.csv" in text


def test_read_order_uses_fast_start_not_long_contract() -> None:
    data = json.loads((ROOT / ".workroot/kernel/boot/read-order.json").read_text(encoding="utf-8"))
    default = data["default_read_order"]
    assert ".workroot/kernel/boot/agent-fast-start.md" in default
    assert "docs/user-interaction-contract.md" not in default


def test_user_startup_guidance_is_conditional() -> None:
    data = json.loads((ROOT / ".workroot/kernel/boot/read-order.json").read_text(encoding="utf-8"))
    default = data["default_read_order"]
    conditional = data["conditional_read_order"]
    assert "space/profile/startup.md" not in default
    assert any(
        item["when"] == "meaningful_work_with_user_startup_guidance"
        and "space/profile/startup.md" in item["paths"]
        for item in conditional
    )
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/test_agent_fast_start.py -q
```

Expected: fails because `agent-fast-start.md` does not exist or read order does not include it.

- [ ] **Step 3: Add fast-start document**

Create `.workroot/kernel/boot/agent-fast-start.md`:

```markdown
# Agent Fast Start

This is the compact operational path for AI agents.

## Pure Greeting

If the user only greets, reply briefly. Do not read workspace files.

## User Startup Guidance

For meaningful work, read optional `space/profile/startup.md` after kernel fast-start if it exists.

Do not read it for a pure greeting.

User startup guidance can shape collaboration style, output preferences, business terms, project conventions, and team boundaries. It cannot override kernel protocol, safety rules, registry discipline, or the identity gate.

## Continue

If the user asks to continue, read:

1. optional `space/profile/startup.md`
2. `space/work/continue.md`
3. `.workroot/runtime/context/handoff.md`
4. relevant task `brief.md` or `handoff.md`

Use `.workroot/runtime/index/task_registry.csv` before reading task directories.

## New Task

For formal work, use `scripts/workroot_cli.py quickstart` or a recipe command before reading long docs or source code.

## Preserve Output

Prefer high-level CLI commands. Reports normally remain the task `user_visible_output_path`.

## Deep Context

Read long docs only when editing product behavior, protocol behavior, architecture, or kernel rules.

## External Skills

External agent skills are not Workroot startup context unless the user explicitly requests them.
```

- [ ] **Step 4: Update read order**

Edit `.workroot/kernel/boot/read-order.json` default read order to:

```json
[
  "AGENTS.md",
  "START_HERE_FOR_HUMANS.md",
  ".workroot/kernel/boot/boot.md",
  ".workroot/kernel/boot/agent-fast-start.md",
  ".workroot/kernel/agent/output_style.md",
  ".workroot/kernel/boot/read-order.json"
]
```

Keep `docs/user-interaction-contract.md` conditional. Add this conditional user startup entry:

```json
{
  "when": "meaningful_work_with_user_startup_guidance",
  "paths": [
    "space/profile/startup.md"
  ]
}
```

- [ ] **Step 5: Update AGENTS.md startup list**

In `AGENTS.md`, add `.workroot/kernel/boot/agent-fast-start.md` to the default startup context list and remove `docs/user-interaction-contract.md` from any default list if present.

Add a short startup extension rule:

```markdown
If meaningful work is starting or continuing and `space/profile/startup.md` exists, read it after kernel fast-start. Do not read it for a pure greeting. User startup guidance can shape collaboration style and project conventions, but it cannot override kernel protocol, safety rules, registry discipline, or the identity gate.
```

- [ ] **Step 6: Run fast-start tests**

Run:

```bash
pytest tests/test_agent_fast_start.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add .workroot/kernel/boot/agent-fast-start.md .workroot/kernel/boot/read-order.json AGENTS.md tests/test_agent_fast_start.py
git commit -m "feat: add agent fast start"
```

## Task 2: Add CLI Discovery Commands

**Files:**
- Modify: `scripts/workroot_cli.py`
- Test: `tests/test_workroot_cli_discovery.py`

- [ ] **Step 1: Write failing discovery tests**

Create `tests/test_workroot_cli_discovery.py`:

```python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/workroot_cli.py"


def run_cli(*args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout


def test_quickstart_mentions_happy_path() -> None:
    out = run_cli("quickstart")
    assert "task complete" in out
    assert "continue rebuild" in out
    assert "schema" in out


def test_schema_lists_enums_and_path_rules() -> None:
    out = run_cli("schema")
    assert "manual_check" in out
    assert "model_generation" in out
    assert "artifact audiences" in out
    assert "source_paths" in out
    assert "input_ref" in out


def test_recipe_task_l2_evidence() -> None:
    out = run_cli("recipe", "task-l2-evidence")
    assert "task complete" in out
    assert "--process-level L2" in out
    assert "--checkpoint" in out
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
pytest tests/test_workroot_cli_discovery.py -q
```

Expected: fails because commands are missing.

- [ ] **Step 3: Add constants and subcommands**

In `scripts/workroot_cli.py`, import any enum constants needed from `workroot_client.py`. Add top-level subcommands before `task`:

```python
quickstart = subparsers.add_parser("quickstart")
schema = subparsers.add_parser("schema")
recipe = subparsers.add_parser("recipe")
recipe.add_argument("name", choices=["task-l0-report", "task-l1-report", "task-l2-evidence"])
doctor = subparsers.add_parser("doctor")
```

- [ ] **Step 4: Implement discovery handlers**

In `main()`, before resource-specific handlers, add:

```python
if args.resource == "quickstart":
    print("Use task complete for common task finalization.")
    print("Use schema to inspect enum and path rules.")
    print("Use continue rebuild for human-facing continuation.")
    return

if args.resource == "schema":
    print("action types: command, database_query, api_call, file_edit, browser_research, model_generation, test_run, deployment, manual_check, other")
    print("artifact audiences: internal, user, public, evidence")
    print("single path fields: input_ref, output_ref, approval_ref, path, primary_artifact")
    print("multi path fields: source_paths, required_context_paths")
    print("input_ref must be one repository-relative path, URL, or empty.")
    print("Use retrieval-card source_paths for multiple source files.")
    return

if args.resource == "recipe":
    if args.name == "task-l2-evidence":
        print("python3 scripts/workroot_cli.py task complete --process-level L2 --task-id TASK --report-path space/work/reports/report.md --checkpoint")
    elif args.name == "task-l1-report":
        print("python3 scripts/workroot_cli.py task complete --process-level L1 --task-id TASK --report-path space/work/reports/report.md")
    else:
        print("python3 scripts/workroot_cli.py task complete --process-level L0 --task-id TASK --report-path space/work/reports/report.md")
    return

if args.resource == "doctor":
    print("Run: python3 scripts/validate_kernel.py")
    return
```

- [ ] **Step 5: Run discovery tests**

Run:

```bash
pytest tests/test_workroot_cli_discovery.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/workroot_cli.py tests/test_workroot_cli_discovery.py
git commit -m "feat: add CLI discovery commands"
```

## Task 3: Add Registry Locking And Atomic Writes

**Files:**
- Modify: `scripts/workroot_client.py`
- Test: `tests/test_registry_store.py`

- [ ] **Step 1: Write failing concurrency test**

Create `tests/test_registry_store.py`:

```python
from __future__ import annotations

import csv
import multiprocessing as mp
from pathlib import Path

from scripts.workroot_client import WorkrootClient


def create_task(root: str, suffix: int) -> None:
    client = WorkrootClient(root)
    client.create_task(
        title=f"Concurrent Task {suffix}",
        task_id=f"concurrent-task-{suffix}",
        process_level="L0",
        next_action="Review result.",
    )


def test_concurrent_task_creates_do_not_corrupt_registry(tmp_path: Path) -> None:
    root = tmp_path
    template = root / ".workroot/runtime/work/_templates"
    template.mkdir(parents=True)
    for name in ["task.md", "brief.md", "todo.md", "handoff.md", "index.md", "decisions.md", "scratch.md"]:
        (template / name).write_text(f"# {name}\n", encoding="utf-8")

    processes = [mp.Process(target=create_task, args=(str(root), i)) for i in range(8)]
    for process in processes:
        process.start()
    for process in processes:
        process.join()
        assert process.exitcode == 0

    registry = root / ".workroot/runtime/index/task_registry.csv"
    with registry.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert reader.fieldnames == WorkrootClient.REGISTRY_HEADERS[".workroot/runtime/index/task_registry.csv"]
    assert len(rows) == 8
```

If `REGISTRY_HEADERS` is not exposed on the class, import it directly from `scripts.workroot_client`.

- [ ] **Step 2: Run failing concurrency test**

Run:

```bash
pytest tests/test_registry_store.py -q
```

Expected: may fail intermittently or due missing class exposure. Continue by implementing locking.

- [ ] **Step 3: Add lock helper**

In `scripts/workroot_client.py`, add:

```python
import contextlib
import os
import tempfile
import time


@contextlib.contextmanager
def file_lock(path: Path, timeout: float = 10.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            payload = f"pid={os.getpid()}\ncreated_at={datetime.datetime.utcnow().isoformat()}Z\n"
            os.write(fd, payload.encode("utf-8"))
            os.close(fd)
            break
        except FileExistsError:
            if time.monotonic() - start > timeout:
                raise SystemExit(f"timed out waiting for Workroot lock: {path}; inspect the lock file before removing it")
            time.sleep(0.02)
    try:
        yield
    finally:
        path.unlink(missing_ok=True)
```

Do not automatically delete a timed-out lock in v0.9.528. A timed-out lock should be treated as an operational signal because another agent process may still be writing. Stale lock cleanup can be a later explicit maintenance command.

- [ ] **Step 4: Add atomic CSV write helper**

In `scripts/workroot_client.py`, add:

```python
def write_registry_atomic(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", dir=path.parent, delete=False) as f:
        tmp_name = f.name
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp_name, path)
```

- [ ] **Step 5: Use lock in registry append/update**

Wrap `append_registry()` and `update_registry_row()` bodies with:

```python
lock = self.root / ".workroot/runtime/locks/workroot.lock"
with file_lock(lock):
    ...
```

Use `write_registry_atomic()` for full-file writes.

- [ ] **Step 6: Run registry tests**

Run:

```bash
pytest tests/test_registry_store.py -q
```

Expected: pass.

- [ ] **Step 7: Run existing client tests**

Run:

```bash
pytest tests/test_workroot_client.py tests/test_workroot_cli.py -q
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add scripts/workroot_client.py tests/test_registry_store.py
git commit -m "fix: make registry writes atomic"
```

## Task 4: Fix Mind Path And Source Semantics

**Files:**
- Modify: `scripts/workroot_cli.py`
- Modify: `scripts/workroot_client.py`
- Test: `tests/test_workroot_client.py`
- Test: `tests/test_workroot_cli.py`

- [ ] **Step 1: Write failing test for Mind not changing task output**

Add to `tests/test_workroot_client.py`:

```python
def test_add_mind_does_not_replace_task_user_visible_output(tmp_path: Path) -> None:
    setup_templates(tmp_path)
    client = WorkrootClient(tmp_path)
    client.create_task(
        "Mind source test",
        task_id="mind-source-test",
        user_visible_output_path="space/work/reports/source.md",
    )
    client.add_mind(
        mind_id="mind-source-test-knowledge",
        title="Mind Source Test Knowledge",
        type="knowledge",
        summary="Reusable fact.",
        related_task_id="mind-source-test",
    )
    row = client.task_row("mind-source-test")
    assert row["user_visible_output_path"] == "space/work/reports/source.md"
```

Use the repository's existing test helper names if they differ.

- [ ] **Step 2: Write failing CLI test for path/source flags**

Add to `tests/test_workroot_cli.py`:

```python
def test_mind_add_path_and_from_path_do_not_conflict(tmp_path: Path) -> None:
    setup_templates(tmp_path)
    run_cli(tmp_path, "task", "create", "Mind CLI test", "--id", "mind-cli-test", "--user-visible-output-path", "space/work/reports/source.md")
    source = tmp_path / "space/work/reports/source.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("# Source\n", encoding="utf-8")
    run_cli(
        tmp_path,
        "mind",
        "add",
        "--mind-id",
        "mind-cli-test-knowledge",
        "--title",
        "Mind CLI Test Knowledge",
        "--type",
        "knowledge",
        "--path",
        "space/mind/knowledge/custom-mind.md",
        "--from-path",
        "space/work/reports/source.md",
        "--related-task-id",
        "mind-cli-test",
    )
    assert (tmp_path / "space/mind/knowledge/custom-mind.md").exists()
```

- [ ] **Step 3: Run failing Mind tests**

Run:

```bash
pytest tests/test_workroot_client.py tests/test_workroot_cli.py -q
```

Expected: fail because `--path` and `--from-path` do not exist and Mind promotion overwrites task output.

- [ ] **Step 4: Update CLI arguments**

In `scripts/workroot_cli.py`, change mind add args:

```python
mind_add.add_argument("--path", default="")
mind_add.add_argument("--from-path", action="append", default=[])
mind_add.add_argument("--from-task-id", action="append", default=[])
mind_add.add_argument("--source-path", default="", help="Deprecated alias for --path.")
mind_add.add_argument("--set-task-output", action="store_true")
```

- [ ] **Step 5: Update client add_mind signature**

In `scripts/workroot_client.py`, change `add_mind()` signature:

```python
path: str = "",
from_paths: list[str] | None = None,
from_task_ids: list[str] | None = None,
set_task_output: bool = False,
source_path: str = "",
```

Use:

```python
rel = path or source_path or f"space/mind/{MIND_DIRS[type]}/{mind_id}.md"
```

- [ ] **Step 6: Stop default task output overwrite**

In `add_mind()`, call `sync_task_state()` without `user_visible_output_path=rel` unless `set_task_output` is true.

- [ ] **Step 7: Add source links**

When `from_paths` or `from_task_ids` are provided, append rows to `link_registry.csv`:

```python
source_type=file, source_id=<path>, target_type=mind, target_id=<mind_id>, relation=source_for
source_type=task, source_id=<task_id>, target_type=mind, target_id=<mind_id>, relation=source_for
```

- [ ] **Step 8: Run Mind tests**

Run:

```bash
pytest tests/test_workroot_client.py tests/test_workroot_cli.py -q
```

Expected: pass.

- [ ] **Step 9: Commit**

```bash
git add scripts/workroot_cli.py scripts/workroot_client.py tests/test_workroot_client.py tests/test_workroot_cli.py
git commit -m "fix: clarify Mind path and source semantics"
```

## Task 5: Separate Task Updates From Global Continuation

**Files:**
- Modify: `scripts/workroot_client.py`
- Modify: `scripts/workroot_cli.py`
- Test: `tests/test_workroot_client.py`
- Test: `tests/test_workroot_cli.py`

- [ ] **Step 1: Write failing test that task update does not overwrite continue**

Add to `tests/test_workroot_client.py`:

```python
def test_task_update_does_not_overwrite_global_continue_by_default(tmp_path: Path) -> None:
    setup_templates(tmp_path)
    continue_path = tmp_path / "space/work/continue.md"
    continue_path.parent.mkdir(parents=True, exist_ok=True)
    continue_path.write_text("# Continue\n\nOriginal session summary.\n", encoding="utf-8")
    client = WorkrootClient(tmp_path)
    client.create_task("A", task_id="task-a")
    client.sync_task_state("task-a", brief_latest_result="A result.", continue_summary="A summary.")
    assert continue_path.read_text(encoding="utf-8") == "# Continue\n\nOriginal session summary.\n"
```

- [ ] **Step 2: Write failing test for session summarize**

Add:

```python
def test_session_summarize_writes_multi_task_continue(tmp_path: Path) -> None:
    setup_templates(tmp_path)
    client = WorkrootClient(tmp_path)
    client.create_task("A", task_id="task-a", user_visible_output_path="space/work/reports/a.md")
    client.create_task("B", task_id="task-b", user_visible_output_path="space/work/reports/b.md")
    client.summarize_session(["task-a", "task-b"], "Both tasks matter.", "Review both outputs.")
    text = (tmp_path / "space/work/continue.md").read_text(encoding="utf-8")
    assert "A" in text
    assert "B" in text
    assert "Both tasks matter." in text
```

- [ ] **Step 3: Run failing tests**

Run:

```bash
pytest tests/test_workroot_client.py -q
```

Expected: fail.

- [ ] **Step 4: Remove global writes from `sync_task_state()`**

In `scripts/workroot_client.py`, remove or guard writes to:

- `space/work/continue.md`
- `.workroot/runtime/context/handoff.md`

Default behavior must not write global files.

- [ ] **Step 5: Add `summarize_session()`**

Add method:

```python
def summarize_session(self, task_ids: list[str], summary: str, next_action: str) -> None:
    rows = [self.task_row(task_id) for task_id in task_ids]
    task_lines = "\n".join(f"- {row['title']} ({row['task_id']})" for row in rows)
    continue_text = markdown_sections(
        "Continue",
        {
            "What Was Happening": task_lines,
            "What Matters Now": summary,
            "Next Step": next_action,
        },
    )
    (self.root / "space/work").mkdir(parents=True, exist_ok=True)
    (self.root / "space/work/continue.md").write_text(continue_text, encoding="utf-8")
    (self.root / ".workroot/runtime/context").mkdir(parents=True, exist_ok=True)
    (self.root / ".workroot/runtime/context/handoff.md").write_text(
        markdown_sections(
            "Handoff",
            {
                "Current Work": task_lines,
                "Status": summary,
                "Next Actions": next_action,
            },
        ),
        encoding="utf-8",
    )
```

- [ ] **Step 6: Add CLI `session summarize`**

In `scripts/workroot_cli.py`, add:

```python
session = subparsers.add_parser("session")
session_sub = session.add_subparsers(dest="action", required=True)
session_summarize = session_sub.add_parser("summarize")
session_summarize.add_argument("--task-id", action="append", required=True)
session_summarize.add_argument("--summary", required=True)
session_summarize.add_argument("--next-action", required=True)
```

Handler:

```python
if args.resource == "session" and args.action == "summarize":
    client.summarize_session(args.task_id, args.summary, args.next_action)
    print("space/work/continue.md")
    return
```

- [ ] **Step 7: Run continuation tests**

Run:

```bash
pytest tests/test_workroot_client.py tests/test_workroot_cli.py -q
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add scripts/workroot_client.py scripts/workroot_cli.py tests/test_workroot_client.py tests/test_workroot_cli.py
git commit -m "fix: separate task updates from session continuation"
```

## Task 6: Add Continue Rebuild

**Files:**
- Modify: `scripts/workroot_client.py`
- Modify: `scripts/workroot_cli.py`
- Test: `tests/test_workroot_cli.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_workroot_cli.py`:

```python
def test_continue_rebuild_uses_registry_tasks(tmp_path: Path) -> None:
    setup_templates(tmp_path)
    run_cli(tmp_path, "task", "create", "Active Task", "--id", "active-task", "--next", "Do active task.")
    run_cli(tmp_path, "task", "create", "Closed Task", "--id", "closed-task", "--next", "Review closed task.")
    run_cli(tmp_path, "task", "update", "--task-id", "closed-task", "--status", "closed")
    run_cli(tmp_path, "continue", "rebuild", "--recent", "2")
    text = (tmp_path / "space/work/continue.md").read_text(encoding="utf-8")
    assert "Active Task" in text
    assert "Closed Task" in text
```

- [ ] **Step 2: Run failing test**

Run:

```bash
pytest tests/test_workroot_cli.py -q
```

Expected: fail because continue command is missing.

- [ ] **Step 3: Add client method**

Add `rebuild_continue(recent: int = 5)` to read `task_registry.csv`, select active/paused/blocked plus recent closed/released, and call `summarize_session()`.

- [ ] **Step 4: Add CLI command**

Add:

```python
cont = subparsers.add_parser("continue")
cont_sub = cont.add_subparsers(dest="action", required=True)
cont_rebuild = cont_sub.add_parser("rebuild")
cont_rebuild.add_argument("--recent", type=int, default=5)
```

Handler:

```python
if args.resource == "continue" and args.action == "rebuild":
    client.rebuild_continue(recent=args.recent)
    print("space/work/continue.md")
    return
```

- [ ] **Step 5: Run tests**

Run:

```bash
pytest tests/test_workroot_cli.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/workroot_client.py scripts/workroot_cli.py tests/test_workroot_cli.py
git commit -m "feat: rebuild human continuation from task registry"
```

## Task 7: Add Task Complete Happy Path

**Files:**
- Modify: `scripts/workroot_cli.py`
- Modify: `scripts/workroot_client.py`
- Test: `tests/test_workroot_cli.py`

- [ ] **Step 1: Write failing test**

Add:

```python
def test_task_complete_creates_report_artifact_and_closes_task(tmp_path: Path) -> None:
    setup_templates(tmp_path)
    report = tmp_path / "report.md"
    report.write_text("# Report\n\nDone.\n", encoding="utf-8")
    run_cli(tmp_path, "task", "create", "Complete Me", "--id", "complete-me")
    run_cli(
        tmp_path,
        "task",
        "complete",
        "--task-id",
        "complete-me",
        "--report-path",
        "space/work/reports/complete-me.md",
        "--report-content-file",
        str(report),
    )
    assert (tmp_path / "space/work/reports/complete-me.md").exists()
    assert "complete-me" in (tmp_path / ".workroot/runtime/index/artifact_registry.csv").read_text(encoding="utf-8")
    assert '"status": "closed"' in (tmp_path / ".workroot/runtime/work/tasks/complete-me/task.json").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run failing test**

Run:

```bash
pytest tests/test_workroot_cli.py -q
```

Expected: fail.

- [ ] **Step 3: Add client method `complete_task()`**

Implement a method that:

- writes report content
- registers artifact with computed metadata
- updates task status to closed
- updates brief/handoff/index/todo
- leaves global continue untouched

- [ ] **Step 4: Add CLI `task complete`**

Add task subparser:

```python
task_complete = task_sub.add_parser("complete")
task_complete.add_argument("--task-id", required=True)
task_complete.add_argument("--report-path", required=True)
task_complete.add_argument("--report-content-file", required=True)
task_complete.add_argument("--next-action", default="")
```

Handler calls `client.complete_task()`.

- [ ] **Step 5: Run task complete tests**

Run:

```bash
pytest tests/test_workroot_cli.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/workroot_client.py scripts/workroot_cli.py tests/test_workroot_cli.py
git commit -m "feat: add task complete happy path"
```

## Task 8: Add Batch Apply

**Files:**
- Modify: `scripts/workroot_cli.py`
- Modify: `scripts/workroot_client.py`
- Test: `tests/test_workroot_cli.py`

- [ ] **Step 1: Write failing batch test**

Add:

```python
def test_batch_apply_creates_common_lightweight_records(tmp_path: Path) -> None:
    setup_templates(tmp_path)
    report = tmp_path / "report.md"
    report.write_text("# Batch Report\n", encoding="utf-8")
    batch = tmp_path / "batch.json"
    batch.write_text(
        json.dumps(
            {
                "operations": [
                    {"op": "task.create", "title": "Batch A", "task_id": "batch-a"},
                    {"op": "task.update", "task_id": "batch-a", "next_action": "Review batch output."},
                    {
                        "op": "artifact.add",
                        "artifact_id": "batch-artifact",
                        "task_id": "batch-a",
                        "path": "space/work/reports/batch-report.md",
                        "content_file": str(report),
                        "audience": "user",
                        "compute_metadata": True,
                    },
                    {
                        "op": "action.add",
                        "action_id": "batch-action",
                        "task_id": "batch-a",
                        "type": "manual_check",
                        "summary": "Reviewed batch output.",
                    },
                    {
                        "op": "checkpoint.add",
                        "checkpoint_id": "batch-checkpoint",
                        "task_id": "batch-a",
                        "current_status": "Batch checkpoint created.",
                    },
                    {
                        "op": "retrieval_card.add",
                        "card_id": "batch-card",
                        "task_id": "batch-a",
                        "source_paths": "space/work/reports/batch-report.md",
                    },
                    {
                        "op": "session.summarize",
                        "task_ids": ["batch-a"],
                        "summary": "Batch operation complete.",
                        "next_action": "Review batch output.",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    run_cli(tmp_path, "batch", "apply", "--file", str(batch))
    assert "batch-a" in (tmp_path / ".workroot/runtime/index/task_registry.csv").read_text(encoding="utf-8")
    assert "batch-artifact" in (tmp_path / ".workroot/runtime/index/artifact_registry.csv").read_text(encoding="utf-8")
    assert "batch-action" in (tmp_path / ".workroot/runtime/index/action_registry.csv").read_text(encoding="utf-8")
    assert "batch-checkpoint" in (tmp_path / ".workroot/runtime/index/checkpoint_registry.csv").read_text(encoding="utf-8")
    assert "batch-card" in (tmp_path / ".workroot/runtime/index/retrieval_card_registry.csv").read_text(encoding="utf-8")
    assert "Batch operation complete." in (tmp_path / "space/work/continue.md").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run failing test**

Run:

```bash
pytest tests/test_workroot_cli.py -q
```

Expected: fail.

- [ ] **Step 3: Add `apply_batch()` lightweight operation support**

Support these operations in v0.9.528 batch implementation:

- `task.create`
- `task.update`
- `artifact.add`
- `action.add`
- `checkpoint.add`
- `retrieval_card.add`
- `session.summarize`

Do not support `mind.add`, `decision.add`, release operations, or forget/tombstone operations in this batch command.

This is not a workflow engine. Do not add branching, retries, scheduling, dependency graphs, or background execution.

Use one lock scope if registry store supports it.

- [ ] **Step 4: Add CLI `batch apply`**

Add:

```python
batch = subparsers.add_parser("batch")
batch_sub = batch.add_subparsers(dest="action", required=True)
batch_apply = batch_sub.add_parser("apply")
batch_apply.add_argument("--file", required=True)
```

- [ ] **Step 5: Run batch test**

Run:

```bash
pytest tests/test_workroot_cli.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/workroot_client.py scripts/workroot_cli.py tests/test_workroot_cli.py
git commit -m "feat: add batch apply command"
```

## Task 9: Full Verification

**Files:**
- No new files expected.

- [ ] **Step 1: Run focused tests**

Run:

```bash
pytest tests/test_agent_fast_start.py tests/test_workroot_cli_discovery.py tests/test_registry_store.py tests/test_workroot_client.py tests/test_workroot_cli.py -q
```

Expected: all pass.

- [ ] **Step 2: Run kernel validation**

Run:

```bash
python3 scripts/validate_kernel.py
```

Expected:

```text
AI Workroot kernel validation passed.
```

- [ ] **Step 3: Run release validation**

Run:

```bash
python3 scripts/validate_kernel.py --release
```

Expected:

```text
AI Workroot release kernel validation passed.
```

- [ ] **Step 4: Run full test suite**

Run:

```bash
pytest -q
```

Expected: all tests pass.

- [ ] **Step 5: Inspect git diff**

Run:

```bash
git diff --stat
git diff --check
```

Expected: no whitespace errors.

- [ ] **Step 6: Commit verification fixes if needed**

If any small verification-only fixes are required:

```bash
git add <files>
git commit -m "test: verify agent operation layer"
```

## Self-Review

Spec coverage:

- Agent fast start: Task 1
- user startup guidance extension point: Task 1
- CLI discovery: Task 2
- registry concurrency: Task 3
- Mind source/path semantics: Task 4
- continuation separation: Tasks 5 and 6
- happy path: Task 7
- batch operations: Task 8
- verification: Task 9

No placeholders remain. Any implementation that needs exact existing helper names must adapt only to current test helper names while preserving the test behaviors defined above.

## Execution Options

Plan complete and saved to `docs/plans/2026-05-15-agent-operation-layer-plan.md`.

Two execution options:

1. Subagent-Driven: dispatch a fresh worker per task, review between tasks, faster iteration.
2. Inline Execution: execute tasks in this session with checkpoints.

Implementation should begin only after the spec and plan are approved.
