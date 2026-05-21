# Clean Native Context Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build AI Workroot 0.9.529's Clean Native Context Foundation: Clean Mode, managed state outside user directories, bootstrap, migrations, doctor, SQLite, local FTS, materialized context candidates, Context Guide, debug traces, Native Agent Entry, and release gates.

**Architecture:** Keep the public seed file-first protocol intact while adding a product-grade managed-state layer under AI Workroot home. Treat user-selected directories as user asset spaces, keep Workroot managed state outside those directories, and use SQLite as a local acceleration layer for graph, FTS, and materialized context candidates. Context Guide reads local explainable indexes and never requires remote calls or vector retrieval for P0.

**Tech Stack:** Python standard library, `unittest`, SQLite, Markdown/JSON/JSONL/CSV files, existing `scripts/workroot_cli.py` and validation scripts.

---

## Preflight Findings

- Branch created: `feat/0.9.529-clean-native-context-foundation`.
- Target repo: `/Users/zeer/a_ypvip/ai_project/ai-workroot`.
- `main` and `origin/main` were aligned before branching at `958c55c`.
- Working tree was clean before adding specs and this plan.
- Baseline `python3 -m unittest discover -s tests` ran 89 tests with 2 failures caused by local `.idea/` metadata being present in the working directory.
- Baseline `python3 scripts/validate_kernel.py --release` failed for the same `.idea/` local metadata.
- Do not delete `.idea/` without explicit user approval; use a clean clone/worktree or approved cleanup before claiming release validation passes.

## File Map

- Create: `docs/specs/001-project-structure-and-naming.spec.md`
- Create: `docs/specs/002-clean-mode-installation.spec.md`
- Create: `docs/specs/003-managed-state-layout.spec.md`
- Create: `docs/specs/004-bootstrap-process.spec.md`
- Create: `docs/specs/005-migrations.spec.md`
- Create: `docs/specs/006-doctor-command.spec.md`
- Create: `docs/specs/007-context-guide-builder.spec.md`
- Create: `docs/specs/008-materialized-context-candidates.spec.md`
- Create: `docs/specs/009-fts-indexing-and-retrieval.spec.md`
- Create: `docs/specs/010-debug-trace-and-observability.spec.md`
- Create: `docs/specs/011-cli-user-flows.spec.md`
- Create: `docs/specs/012-native-agent-entry.spec.md`
- Create: `docs/specs/013-sqlite-cache-and-provenance-graph.spec.md`
- Create: `docs/specs/014-release-and-test-gates.spec.md`
- Create: `scripts/workroot_paths.py`
  - Resolve `AI_WORKROOT_HOME`, OS defaults, Workroot state paths, and Clean Mode path boundaries.
- Create: `scripts/workroot_state.py`
  - Initialize global config, registry files, directory bindings, per-Workroot `workroot.json`, and state directories.
- Create: `scripts/workroot_migrations.py`
  - Ordered idempotent migrations, migration records, locks, and migration gate.
- Create: `scripts/workroot_sqlite.py`
  - SQLite open/init helpers, WAL mode, graph/candidate/FTS schema verification.
- Create: `scripts/workroot_agent_entry.py`
  - Managed-block generation and validation for optional `AGENTS.md` and `CLAUDE.md`.
- Create: `scripts/workroot_doctor.py`
  - Structured doctor checks and text/JSON output.
- Create: `scripts/workroot_context.py`
  - Context Guide request model, challengers, scoring, budgeting, package rendering, and debug trace writing.
- Create: `scripts/workroot_indexing.py`
  - Local text file indexing, chunking, FTS refresh, and FTS search.
- Create: `scripts/workroot_candidates.py`
  - Materialized Context Candidate model, repository, lifecycle, refresh, and query APIs.
- Create: `scripts/workroot_bootstrap.py`
  - Developer bootstrap preflight and state initialization flow.
- Modify: `scripts/workroot_cli.py`
  - Add P0 product CLI: `init`, `list`, `status`, `context`, `doctor --format json`, `bootstrap-dev`.
- Modify: `scripts/validate_kernel.py`
  - Extend validation for new specs, generated-state exclusions, SQLite/cache release-surface checks, and terminology gates.
- Create: `scripts/install.sh`
- Create: `scripts/install.ps1`
- Create: `scripts/bootstrap-dev.sh`
- Create: `scripts/bootstrap-dev.ps1`
- Modify: `.gitignore`
  - Ignore `.ai-workroot-local/` and generated AI Workroot managed-state/cache artifacts when they can appear in the repo.
- Create: targeted tests under `tests/` for each module listed below.
- Modify: `docs/release-checklist.md`
  - Add 0.9.529 release gates.

## Task 1: Adopt 0.9.529 Specs In Target Repo

**Files:**
- Create: `docs/specs/001-project-structure-and-naming.spec.md`
- Create: `docs/specs/002-clean-mode-installation.spec.md`
- Create: `docs/specs/003-managed-state-layout.spec.md`
- Create: `docs/specs/004-bootstrap-process.spec.md`
- Create: `docs/specs/005-migrations.spec.md`
- Create: `docs/specs/006-doctor-command.spec.md`
- Create: `docs/specs/007-context-guide-builder.spec.md`
- Create: `docs/specs/008-materialized-context-candidates.spec.md`
- Create: `docs/specs/009-fts-indexing-and-retrieval.spec.md`
- Create: `docs/specs/010-debug-trace-and-observability.spec.md`
- Create: `docs/specs/011-cli-user-flows.spec.md`
- Create: `docs/specs/012-native-agent-entry.spec.md`
- Create: `docs/specs/013-sqlite-cache-and-provenance-graph.spec.md`
- Create: `docs/specs/014-release-and-test-gates.spec.md`

- [ ] **Step 1: Verify spec files exist**

Run:

```bash
find docs/specs -maxdepth 1 -type f -name '[0-9][0-9][0-9]-*.spec.md' -print | sort
```

Expected: all files `001` through `014` are listed.

- [ ] **Step 2: Verify required spec sections**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
required = [
    "# Spec:", "## Status", "## Priority", "## Background", "## Goals",
    "## Non-goals", "## Scope", "### Included", "### Excluded",
    "## Dependencies", "## Requirements", "### Functional Requirements",
    "### Non-functional Requirements", "## Proposed Design",
    "## Acceptance Criteria", "## Test Plan", "### Unit Tests",
    "### Integration Tests", "### Manual Verification",
    "## Migration / Rollback", "## Observability / Debugging",
    "## Task Breakdown", "## Risks", "## Open Questions",
]
failed = False
for path in sorted(Path("docs/specs").glob("[0-9][0-9][0-9]-*.spec.md")):
    text = path.read_text(encoding="utf-8")
    missing = [item for item in required if item not in text]
    if missing:
        failed = True
        print(f"{path}: missing {missing}")
if failed:
    raise SystemExit(1)
print("spec section check passed")
PY
```

Expected: `spec section check passed`.

- [ ] **Step 3: Commit specs**

Run after review:

```bash
git add docs/specs/001-project-structure-and-naming.spec.md \
  docs/specs/002-clean-mode-installation.spec.md \
  docs/specs/003-managed-state-layout.spec.md \
  docs/specs/004-bootstrap-process.spec.md \
  docs/specs/005-migrations.spec.md \
  docs/specs/006-doctor-command.spec.md \
  docs/specs/007-context-guide-builder.spec.md \
  docs/specs/008-materialized-context-candidates.spec.md \
  docs/specs/009-fts-indexing-and-retrieval.spec.md \
  docs/specs/010-debug-trace-and-observability.spec.md \
  docs/specs/011-cli-user-flows.spec.md \
  docs/specs/012-native-agent-entry.spec.md \
  docs/specs/013-sqlite-cache-and-provenance-graph.spec.md \
  docs/specs/014-release-and-test-gates.spec.md
git commit -m "docs: add 0.9.529 implementation specs"
```

Expected: one docs-only commit.

## Task 2: Resolve AI Workroot Home And Clean Mode Boundaries

**Files:**
- Create: `scripts/workroot_paths.py`
- Create: `tests/test_workroot_paths.py`

- [ ] **Step 1: Write failing path resolver tests**

Create `tests/test_workroot_paths.py`:

```python
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.workroot_paths import (
    CleanModeBoundaryError,
    assert_clean_mode_boundary,
    resolve_ai_workroot_home,
    workroot_state_dir,
)


class WorkrootPathsTest(unittest.TestCase):
    def test_env_override_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"AI_WORKROOT_HOME": tmp}):
                self.assertEqual(resolve_ai_workroot_home(), Path(tmp).resolve())

    def test_macos_linux_default(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("platform.system", return_value="Darwin"):
                home = resolve_ai_workroot_home(home=Path("/Users/example"))
        self.assertEqual(home, Path("/Users/example/.ai-workroot"))

    def test_windows_default(self) -> None:
        with mock.patch.dict(os.environ, {"LOCALAPPDATA": r"C:\Users\Example\AppData\Local"}, clear=True):
            with mock.patch("platform.system", return_value="Windows"):
                home = resolve_ai_workroot_home()
        self.assertEqual(home, Path(r"C:\Users\Example\AppData\Local\AIWorkroot"))

    def test_state_dir_uses_workroots_namespace(self) -> None:
        base = Path("/tmp/ai-workroot-home")
        self.assertEqual(workroot_state_dir(base, "wr_demo"), base / "workroots" / "wr_demo")

    def test_clean_mode_rejects_state_inside_user_directory(self) -> None:
        with self.assertRaises(CleanModeBoundaryError):
            assert_clean_mode_boundary(Path("/tmp/project"), Path("/tmp/project/.ai-workroot/workroots/wr_demo"))

    def test_clean_mode_allows_state_outside_user_directory(self) -> None:
        assert_clean_mode_boundary(Path("/tmp/project"), Path("/tmp/.ai-workroot/workroots/wr_demo"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python3 -m unittest tests.test_workroot_paths -v
```

Expected: fails because `scripts.workroot_paths` does not exist.

- [ ] **Step 3: Implement path resolver**

Create `scripts/workroot_paths.py`:

```python
from __future__ import annotations

import os
import platform
from pathlib import Path


class CleanModeBoundaryError(ValueError):
    pass


def resolve_ai_workroot_home(home: Path | None = None) -> Path:
    override = os.environ.get("AI_WORKROOT_HOME")
    if override:
        return Path(override).expanduser().resolve()
    if platform.system() == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "AIWorkroot"
        return Path.home() / "AppData" / "Local" / "AIWorkroot"
    base = home or Path.home()
    return base / ".ai-workroot"


def workroot_state_dir(ai_workroot_home: Path, workroot_id: str) -> Path:
    return ai_workroot_home / "workroots" / workroot_id


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def assert_clean_mode_boundary(user_directory: Path, state_directory: Path) -> None:
    if is_relative_to(state_directory, user_directory):
        raise CleanModeBoundaryError(
            f"Clean Mode violation: managed state would be written inside the user directory: {state_directory}"
        )
```

- [ ] **Step 4: Run path tests**

Run:

```bash
python3 -m unittest tests.test_workroot_paths -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/workroot_paths.py tests/test_workroot_paths.py
git commit -m "feat: add Workroot managed state path resolver"
```

## Task 3: Initialize Managed State And Registries

**Files:**
- Create: `scripts/workroot_state.py`
- Create: `tests/test_workroot_state.py`

- [ ] **Step 1: Write failing managed-state tests**

Create `tests/test_workroot_state.py`:

```python
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.workroot_state import initialize_ai_workroot_home, initialize_workroot_state, read_jsonl


class WorkrootStateTest(unittest.TestCase):
    def test_initialize_home_creates_global_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            initialize_ai_workroot_home(home, now="2026-05-19T00:00:00Z")
            self.assertTrue((home / "config.json").exists())
            self.assertTrue((home / "registry/workroots.jsonl").exists())
            self.assertTrue((home / "registry/directory-bindings.jsonl").exists())
            self.assertTrue((home / "global-index").is_dir())
            self.assertTrue((home / "global-cache").is_dir())

    def test_initialize_workroot_state_keeps_state_outside_user_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            result = initialize_workroot_state(
                home,
                workroot_id="wr_demo",
                name="Demo",
                user_directory=user_dir,
                now="2026-05-19T00:00:00Z",
            )
            self.assertEqual(result.workroot_id, "wr_demo")
            self.assertTrue((home / "workroots/wr_demo/workroot.json").exists())
            self.assertFalse((user_dir / ".workroot").exists())
            self.assertFalse((user_dir / ".ai-workroot").exists())
            records = read_jsonl(home / "registry/workroots.jsonl")
            self.assertEqual(records[0]["workrootId"], "wr_demo")

    def test_workroot_json_contains_clean_mode_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialize_workroot_state(home, "wr_demo", "Demo", user_dir, now="2026-05-19T00:00:00Z")
            payload = json.loads((home / "workroots/wr_demo/workroot.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["mode"], "clean")
            self.assertEqual(payload["workrootId"], "wr_demo")
            self.assertEqual(payload["userDirectory"], str(user_dir.resolve()))
            self.assertEqual(payload["stateDirectory"], str((home / "workroots/wr_demo").resolve()))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python3 -m unittest tests.test_workroot_state -v
```

Expected: fails because `scripts.workroot_state` does not exist.

- [ ] **Step 3: Implement managed-state initializer**

Create `scripts/workroot_state.py` with:

- `InitializedWorkroot` dataclass.
- `initialize_ai_workroot_home(home, now)`.
- `initialize_workroot_state(home, workroot_id, name, user_directory, now)`.
- JSONL append helper that avoids duplicate `workrootId`.
- Directory creation for `agent`, `state`, `tasks`, `handoffs`, `assets`, `knowledge`, `graph`, `indexes`, `context`, `maintenance`, `concurrency`, `logs`, and `cache`.

Use `scripts.workroot_paths.assert_clean_mode_boundary` before creating per-Workroot state.

- [ ] **Step 4: Run managed-state tests**

Run:

```bash
python3 -m unittest tests.test_workroot_state -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/workroot_state.py tests/test_workroot_state.py
git commit -m "feat: initialize managed Workroot state"
```

## Task 4: Add SQLite Schema, Graph, Candidates, And FTS Tables

**Files:**
- Create: `scripts/workroot_sqlite.py`
- Create: `tests/test_workroot_sqlite.py`

- [ ] **Step 1: Write failing SQLite tests**

Create `tests/test_workroot_sqlite.py`:

```python
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.workroot_sqlite import initialize_workroot_sqlite, required_tables, verify_workroot_sqlite


class WorkrootSqliteTest(unittest.TestCase):
    def test_initialize_creates_required_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workroot.sqlite"
            initialize_workroot_sqlite(db_path)
            with sqlite3.connect(db_path) as conn:
                tables = {
                    row[0]
                    for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')")
                }
            for table in required_tables():
                self.assertIn(table, tables)

    def test_wal_mode_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workroot.sqlite"
            initialize_workroot_sqlite(db_path)
            with sqlite3.connect(db_path) as conn:
                mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            self.assertEqual(mode.lower(), "wal")

    def test_verify_reports_missing_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "empty.sqlite"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            sqlite3.connect(db_path).close()
            issues = verify_workroot_sqlite(db_path)
            self.assertTrue(any("graph_nodes" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python3 -m unittest tests.test_workroot_sqlite -v
```

Expected: fails because `scripts.workroot_sqlite` does not exist.

- [ ] **Step 3: Implement SQLite initializer**

Create `scripts/workroot_sqlite.py` with:

- `open_sqlite(path)`.
- `initialize_workroot_sqlite(path)`.
- `required_tables()`.
- `verify_workroot_sqlite(path)`.
- SQL for `graph_nodes`, `graph_edges`, `graph_edge_evidence`, `context_candidates`, `context_candidates_fts`, `indexed_files`, `indexed_chunks`, and `indexed_chunks_fts`.

- [ ] **Step 4: Run SQLite tests**

Run:

```bash
python3 -m unittest tests.test_workroot_sqlite -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/workroot_sqlite.py tests/test_workroot_sqlite.py
git commit -m "feat: add SQLite graph and retrieval schema"
```

## Task 5: Add Migrations

**Files:**
- Create: `scripts/workroot_migrations.py`
- Create: `tests/test_workroot_migrations.py`

- [ ] **Step 1: Write failing migration tests**

Create `tests/test_workroot_migrations.py`:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.workroot_migrations import Migration, MigrationRunner, read_migration_records


class WorkrootMigrationsTest(unittest.TestCase):
    def test_migrations_apply_once_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            applied: list[str] = []
            migrations = [
                Migration("0002_second", "global", lambda _: applied.append("0002_second")),
                Migration("0001_first", "global", lambda _: applied.append("0001_first")),
            ]
            runner = MigrationRunner(root, migrations)
            runner.apply("global")
            runner.apply("global")
            self.assertEqual(applied, ["0001_first", "0002_second"])
            records = read_migration_records(root / "migrations/global.jsonl")
            self.assertEqual([row["migrationId"] for row in records], ["0001_first", "0002_second"])

    def test_failed_migration_records_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def fail(_: Path) -> None:
                raise RuntimeError("boom")
            runner = MigrationRunner(root, [Migration("0001_fail", "global", fail)])
            with self.assertRaises(SystemExit):
                runner.apply("global")
            records = read_migration_records(root / "migrations/global.jsonl")
            self.assertEqual(records[0]["status"], "failed")
            self.assertIn("boom", records[0]["error"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python3 -m unittest tests.test_workroot_migrations -v
```

Expected: fails because migrations module does not exist.

- [ ] **Step 3: Implement migration runner**

Create `scripts/workroot_migrations.py` with:

- `Migration` dataclass.
- `MigrationRunner`.
- JSONL migration records.
- Stable ID sorting.
- Idempotency by applied migration ID.
- Failure recording.
- Lock file under `migrations/locks/`.

- [ ] **Step 4: Run migration tests**

Run:

```bash
python3 -m unittest tests.test_workroot_migrations -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/workroot_migrations.py tests/test_workroot_migrations.py
git commit -m "feat: add Workroot migration runner"
```

## Task 6: Add Native Agent Entry Managed Blocks

**Files:**
- Create: `scripts/workroot_agent_entry.py`
- Create: `tests/test_workroot_agent_entry.py`

- [ ] **Step 1: Write failing Native Agent Entry tests**

Create `tests/test_workroot_agent_entry.py`:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.workroot_agent_entry import (
    NativeAgentEntryError,
    apply_managed_block,
    codex_block,
    validate_entry_content,
)


class WorkrootAgentEntryTest(unittest.TestCase):
    def test_codex_block_uses_relative_context_command(self) -> None:
        block = codex_block()
        self.assertIn("workroot context --agent codex --cwd .", block)
        self.assertNotIn(str(Path.home()), block)
        self.assertNotIn(".ai-workroot/workroots", block)

    def test_apply_block_preserves_user_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AGENTS.md"
            path.write_text("# Existing\n\nKeep me.\n", encoding="utf-8")
            apply_managed_block(path, codex_block())
            text = path.read_text(encoding="utf-8")
            self.assertIn("Keep me.", text)
            self.assertIn("<!-- AI_WORKROOT_BEGIN -->", text)
            self.assertIn("<!-- AI_WORKROOT_END -->", text)

    def test_validate_rejects_absolute_state_path(self) -> None:
        with self.assertRaises(NativeAgentEntryError):
            validate_entry_content("state at /Users/example/.ai-workroot/workroots/wr_demo")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python3 -m unittest tests.test_workroot_agent_entry -v
```

Expected: fails because module does not exist.

- [ ] **Step 3: Implement Native Agent Entry module**

Create `scripts/workroot_agent_entry.py` with:

- `BEGIN = "<!-- AI_WORKROOT_BEGIN -->"`.
- `END = "<!-- AI_WORKROOT_END -->"`.
- `codex_block()`.
- `claude_block()`.
- `validate_entry_content(text)`.
- `apply_managed_block(path, block)`.
- malformed marker detection.

- [ ] **Step 4: Run Native Agent Entry tests**

Run:

```bash
python3 -m unittest tests.test_workroot_agent_entry -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/workroot_agent_entry.py tests/test_workroot_agent_entry.py
git commit -m "feat: add Native Agent Entry managed blocks"
```

## Task 7: Add Init, List, Status, And Bootstrap-Dev CLI

**Files:**
- Create: `scripts/workroot_bootstrap.py`
- Modify: `scripts/workroot_cli.py`
- Create: `tests/test_workroot_init_cli.py`
- Create: `tests/test_workroot_bootstrap_dev.py`
- Create: `scripts/bootstrap-dev.sh`
- Create: `scripts/bootstrap-dev.ps1`

- [ ] **Step 1: Write failing init CLI tests**

Create `tests/test_workroot_init_cli.py` with subprocess tests that:

- use `AI_WORKROOT_HOME` in a temp directory;
- run `python3 scripts/workroot_cli.py init --name Demo --directory <tmp/project> --no-native-agent-entry`;
- assert `<AI_WORKROOT_HOME>/workroots/wr_demo/workroot.json` exists;
- assert user directory does not contain `.workroot`, `.ai-workroot`, `context`, `runtime`, `cache`, or `continue.md`;
- run `list` and `status`.

- [ ] **Step 2: Write failing bootstrap-dev tests**

Create `tests/test_workroot_bootstrap_dev.py` with subprocess tests that:

- copy the repo to a temp directory;
- run `bootstrap-dev --dry-run` in a non-repo directory and expect non-zero;
- run `bootstrap-dev --dry-run` in the copied repo and expect preflight success;
- verify `.ai-workroot-local/` is only created without `--dry-run`.

- [ ] **Step 3: Implement CLI commands**

Modify `scripts/workroot_cli.py`:

- add `init`, `list`, `status`, `context`, `doctor --format`, and `bootstrap-dev` parsers;
- keep existing v0.9.528 task commands unchanged;
- wire init/list/status to `workroot_state`;
- wire bootstrap-dev preflight to `workroot_bootstrap`.

- [ ] **Step 4: Add bootstrap scripts**

Create `scripts/bootstrap-dev.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
python3 "$(dirname "$0")/workroot_cli.py" bootstrap-dev "$@"
```

Create `scripts/bootstrap-dev.ps1`:

```powershell
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$ScriptDir/workroot_cli.py" bootstrap-dev @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

- [ ] **Step 5: Run CLI tests**

Run:

```bash
python3 -m unittest tests.test_workroot_init_cli tests.test_workroot_bootstrap_dev -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/workroot_cli.py scripts/workroot_bootstrap.py scripts/bootstrap-dev.sh scripts/bootstrap-dev.ps1 tests/test_workroot_init_cli.py tests/test_workroot_bootstrap_dev.py
git commit -m "feat: add Clean Mode init and bootstrap-dev CLI"
```

## Task 8: Add Doctor Command

**Files:**
- Create: `scripts/workroot_doctor.py`
- Modify: `scripts/workroot_cli.py`
- Create: `tests/test_workroot_doctor_0529.py`

- [ ] **Step 1: Write failing doctor tests**

Create `tests/test_workroot_doctor_0529.py` with tests for:

- healthy Clean Mode state;
- state inside user directory failing;
- missing SQLite table failing;
- JSON output containing check IDs, categories, status, severity, and suggested action.

- [ ] **Step 2: Implement doctor module**

Create `scripts/workroot_doctor.py` with:

- `DoctorCheck` dataclass;
- `DoctorResult` dataclass;
- checks for resolution, Clean Mode boundary, managed layout, migration records, SQLite schema, context directories, and Native Agent Entry markers;
- text and JSON renderers.

- [ ] **Step 3: Wire CLI**

Modify `scripts/workroot_cli.py`:

- preserve legacy `doctor` behavior for current seed when no managed Workroot is resolved only if needed;
- support `workroot doctor --format json`;
- return non-zero when error-severity checks fail.

- [ ] **Step 4: Run doctor tests**

Run:

```bash
python3 -m unittest tests.test_workroot_doctor_0529 -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/workroot_doctor.py scripts/workroot_cli.py tests/test_workroot_doctor_0529.py
git commit -m "feat: add managed state doctor checks"
```

## Task 9: Add Materialized Context Candidates And FTS

**Files:**
- Create: `scripts/workroot_candidates.py`
- Create: `scripts/workroot_indexing.py`
- Create: `tests/test_workroot_candidates.py`
- Create: `tests/test_workroot_indexing.py`

- [ ] **Step 1: Write failing candidate tests**

Create tests that cover:

- upsert candidate;
- lifecycle transitions to `stale`, `superseded`, and `gravestone`;
- query active candidates only;
- update `last_used_at`.

- [ ] **Step 2: Write failing indexing tests**

Create tests that cover:

- Markdown heading chunking;
- plain text chunking;
- binary skip;
- SQLite FTS search returning path, heading, snippet, score, and reason.

- [ ] **Step 3: Implement candidates**

Create `scripts/workroot_candidates.py` with:

- `ContextCandidate` dataclass;
- `upsert_context_candidate`;
- `mark_candidate_status`;
- `query_context_candidates`;
- `mark_candidates_used`.

- [ ] **Step 4: Implement indexing**

Create `scripts/workroot_indexing.py` with:

- text suffix detection;
- binary detection;
- heading-aware chunking;
- incremental file metadata;
- FTS insert/update;
- `search_fts`.

- [ ] **Step 5: Run candidate and indexing tests**

Run:

```bash
python3 -m unittest tests.test_workroot_candidates tests.test_workroot_indexing -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/workroot_candidates.py scripts/workroot_indexing.py tests/test_workroot_candidates.py tests/test_workroot_indexing.py
git commit -m "feat: add local context candidates and FTS retrieval"
```

## Task 10: Add Context Guide And Debug Traces

**Files:**
- Create: `scripts/workroot_context.py`
- Modify: `scripts/workroot_cli.py`
- Create: `tests/test_workroot_context.py`
- Create: `tests/test_workroot_debug_trace.py`

- [ ] **Step 1: Write failing context tests**

Create tests that:

- initialize a fixture Workroot;
- insert current state, candidates, FTS chunks, and graph rows;
- run `build_context_package`;
- assert Markdown sections exist;
- assert selected candidates respect lifecycle and `never-auto`;
- assert no user directory files are created.

- [ ] **Step 2: Write failing debug trace tests**

Create tests that:

- run context generation with debug enabled;
- assert `context/debug/latest.json` exists under managed state;
- assert trace includes Workroot resolution, challengers, selected candidates, dropped candidates, FTS matches, token budget, and latency fields;
- assert history retention prunes beyond 50 records.

- [ ] **Step 3: Implement context module**

Create `scripts/workroot_context.py` with:

- request dataclass;
- package renderer;
- candidate, FTS, graph, safety, and time challengers;
- deterministic scoring;
- token budget trimming;
- debug trace builder and writer.

- [ ] **Step 4: Wire CLI**

Modify `scripts/workroot_cli.py`:

- `workroot context --agent codex --cwd .`;
- `workroot context --agent claude --cwd .`;
- `--debug`;
- output Markdown Context Package to stdout.

- [ ] **Step 5: Run context tests**

Run:

```bash
python3 -m unittest tests.test_workroot_context tests.test_workroot_debug_trace -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/workroot_context.py scripts/workroot_cli.py tests/test_workroot_context.py tests/test_workroot_debug_trace.py
git commit -m "feat: add local Context Guide and debug traces"
```

## Task 11: Add Install Scripts And Release Gates

**Files:**
- Create: `scripts/install.sh`
- Create: `scripts/install.ps1`
- Modify: `scripts/validate_kernel.py`
- Modify: `docs/release-checklist.md`
- Modify: `.gitignore`
- Create: `tests/test_0529_release_gates.py`

- [ ] **Step 1: Write failing release gate tests**

Create `tests/test_0529_release_gates.py` with tests that:

- assert install scripts exist;
- assert bootstrap scripts exist;
- assert `.ai-workroot-local/` is ignored;
- assert new numbered specs exist;
- assert generated suffixes and cache paths are rejected by release validation;
- assert no P0 code path requires vector or remote embeddings.

- [ ] **Step 2: Add install scripts**

Create `scripts/install.sh` and `scripts/install.ps1` with user-level install behavior and first Workroot prompt. Keep actual binary/package installation minimal for P0 if packaging is not ready.

- [ ] **Step 3: Extend validation**

Modify `scripts/validate_kernel.py`:

- include generated AI Workroot home/cache exclusions;
- include `.ai-workroot-local/` checks;
- add numbered spec presence checks;
- add terminology gate scoped to new release docs.

- [ ] **Step 4: Update release checklist**

Add 0.9.529 gates:

- Clean Mode default no user-directory state;
- Native Agent Entry authorization;
- managed state outside user directory;
- SQLite tables;
- Context Guide no remote calls;
- debug trace;
- no vector dependency;
- bootstrap-dev no auto commit/tag;
- release surface clean.

- [ ] **Step 5: Run release gate tests**

Run:

```bash
python3 -m unittest tests.test_0529_release_gates -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/install.sh scripts/install.ps1 scripts/validate_kernel.py docs/release-checklist.md .gitignore tests/test_0529_release_gates.py
git commit -m "test: add 0.9.529 release gates"
```

## Task 12: Full Verification And Review

**Files:**
- No new implementation files unless earlier test failures reveal a required fix.

- [ ] **Step 1: Verify working tree does not include unapproved local metadata**

Run:

```bash
git status --short
find . -maxdepth 2 -name '.idea' -print
```

Expected: no tracked `.idea/`; local `.idea/` is absent or verification is run from a clean clone/worktree.

- [ ] **Step 2: Run full tests**

Run:

```bash
python3 -m unittest discover -s tests
```

Expected: all tests pass.

- [ ] **Step 3: Run release validation**

Run:

```bash
python3 scripts/validate_kernel.py --release
```

Expected: exit 0.

- [ ] **Step 4: Run smoke CLI checks**

Run:

```bash
python3 scripts/workroot_cli.py quickstart
python3 scripts/workroot_cli.py manifest --format json
python3 scripts/workroot_cli.py schema --format json
```

Expected: all commands exit 0 and print valid operational guidance.

- [ ] **Step 5: Review diff**

Run:

```bash
git diff --stat main...HEAD
git diff --name-only main...HEAD
```

Expected: changes are limited to 0.9.529 docs, scripts, tests, install/bootstrap scripts, and release checklist.

- [ ] **Step 6: Final review commit if needed**

If any verification-only doc or test fix is needed:

```bash
git add <paths>
git commit -m "chore: finalize 0.9.529 verification"
```

Expected: branch is ready for review. Do not tag, bump version, push, or merge without explicit approval.

## Self-Review

- Spec coverage: Tasks 1-12 map to Specs 001-014. Native Agent Entry and SQLite/provenance graph have independent tasks because they are implementation boundaries.
- Scope control: P0 implements local-first Clean Mode, managed state, bootstrap, migrations, doctor, SQLite, FTS, candidates, context, debug traces, CLI, install scripts, and release gates. It excludes vector retrieval, remote embeddings, daemon, hooks, MCP, cloud sync, team collaboration, and automatic Git actions.
- Placeholder scan: each task has target files and concrete verification commands.
- Baseline caveat: current local `.idea/` metadata blocks release validation in this checkout. Before claiming release readiness, run verification from a clean checkout/worktree or get approval to remove local `.idea/`.
