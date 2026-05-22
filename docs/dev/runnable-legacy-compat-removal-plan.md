# Runnable Legacy Compatibility Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove runnable legacy Public Seed compatibility from active AI Workroot paths while preserving non-runnable historical source snapshots.

**Architecture:** Active Clean Workroot behavior remains under `src/ai_workroot/`, with CLI, runtime, storage, indexing, doctor, scripts, and tests all free of legacy imports and runnable compatibility entry points. Historical Public Seed code is archived as `.py.txt` under `docs/history/public-seed/code-archive` with a manifest, so reviewers can inspect old code without it being importable or executable.

**Tech Stack:** Python standard library, `unittest`, shell scripts, Git.

---

## File Responsibility Map

- `src/ai_workroot/cli/main.py`: current Clean Workroot CLI only.
- `docs/history/public-seed/code-archive/`: non-runnable archive of removed legacy source.
- `scripts/dev/validate-release.sh`: active release validation, no legacy validators.
- `tests/unit/test_import_boundaries.py`: package import and source boundary checks.
- `tests/contracts/test_repository_root_contract.py`, `tests/contracts/test_current_docs_contract.py`: root/docs/scripts/archive surface checks.
- `tests/smoke/test_clean_cli_workflow.py` and related CLI smoke tests: active package CLI smoke checks.
- `tests/smoke/test_clean_release_validator.py`: release doctor and validate-release smoke checks.
- `tests/integration/*`: active Clean Workroot integration checks.
- Active docs: explain that runnable legacy compatibility is removed.

## Tasks

### Task 1: Document the removal boundary

**Files:**
- Create: `docs/dev/runnable-legacy-compat-removal-architecture.md`
- Create: `docs/specs/041-runnable-legacy-compat-removal.spec.md`
- Create: `docs/dev/runnable-legacy-compat-removal-plan.md`

- [x] **Step 1: Add architecture and Spec docs**

Verification:

```bash
test -f docs/dev/runnable-legacy-compat-removal-architecture.md
test -f docs/specs/041-runnable-legacy-compat-removal.spec.md
test -f docs/dev/runnable-legacy-compat-removal-plan.md
```

Expected: all commands exit 0.

### Task 2: Add failing legacy-removal boundary tests

**Files:**
- Modify: `tests/unit/test_import_boundaries.py`
- Modify: `tests/contracts/test_repository_root_contract.py`, `tests/contracts/test_current_docs_contract.py`
- Modify: `tests/smoke/test_cli_discovery.py`
- Modify: `tests/smoke/test_clean_release_validator.py`

- [x] **Step 1: Replace compatibility-positive tests with removal tests**
- [x] **Step 2: Run focused tests and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_import_boundaries tests.smoke.test_cli_discovery -v
```

Expected before implementation: FAIL because legacy modules and CLI still exist.

### Task 3: Remove active CLI legacy dispatch

**Files:**
- Modify: `src/ai_workroot/cli/main.py`
- Modify: `tests/smoke/test_cli_discovery.py`

- [x] **Step 1: Delete hidden legacy parser and dispatcher**
- [x] **Step 2: Verify CLI boundary**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.smoke.test_cli_discovery -v
```

Expected: PASS.

### Task 4: Archive and remove active legacy package modules

**Files:**
- Create: `docs/history/public-seed/code-archive/MANIFEST.md`
- Create: `docs/history/public-seed/code-archive/**/*.py.txt`
- Delete: `src/ai_workroot/cli/legacy_seed.py`
- Delete: `src/ai_workroot/runtime/legacy_context.py`
- Delete: `src/ai_workroot/runtime/legacy_doctor.py`
- Delete: `src/ai_workroot/runtime/legacy_seed/*`
- Delete: `src/ai_workroot/storage/legacy_sqlite.py`
- Delete: `src/ai_workroot/indexing/legacy_candidates.py`
- Delete: `src/ai_workroot/indexing/legacy_fts.py`

- [x] **Step 1: Archive source snapshots as non-runnable files**
- [x] **Step 2: Delete active legacy package files**
- [x] **Step 3: Verify active package has no legacy files**

Run:

```bash
find src/ai_workroot -path '*legacy*' -o -name '*legacy*'
```

Expected: no output.

### Task 5: Remove runnable legacy scripts and update validation scripts

**Files:**
- Delete: `scripts/compat/*`
- Delete: `scripts/legacy/*`
- Delete or rewrite: `scripts/dev/new_task_smoke.py`
- Modify: `scripts/README.md`
- Modify: `scripts/dev/README.md`
- Modify: `scripts/dev/validate-release.sh`

- [x] **Step 1: Remove runnable compatibility and legacy script directories**
- [x] **Step 2: Update validate-release**
- [x] **Step 3: Verify scripts boundary**

### Task 6: Migrate or retire legacy tests

**Files:**
- Modify/delete default tests that import `legacy_*` or execute `scripts/compat` / `scripts/legacy`.
- Keep active tests for Clean Workroot behavior.

- [x] **Step 1: Find remaining legacy imports and paths**
- [x] **Step 2: Retire implementation-only legacy tests**
- [x] **Step 3: Preserve active behavior coverage**

### Task 7: Update docs and release checklist

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `docs/release-checklist.md`
- Modify: `docs/workroot-system-design.md`
- Modify: `docs/architecture/002-engineering-structure.md`
- Modify: current docs/specs that claim runnable compatibility remains.

- [x] **Step 1: Update current docs wording**
- [x] **Step 2: Verify active docs no longer promise compatibility**

### Task 8: Full validation

**Files:** no planned file changes.

- [x] **Step 1: Compile active Python files**
- [x] **Step 2: Run default test suite**
- [x] **Step 3: Run release doctor and validation**
- [x] **Step 4: Run Clean Workroot smoke**

## Validation Results

Run on 2026-05-22:

```text
python3 -m py_compile $(find src scripts tests -name "*.py")
PASS

PYTHONPATH=src python3 -m unittest discover -s tests -v
Ran 224 tests in 9.199s
OK

PYTHONPATH=src python3 -m unittest discover -s tests/unit -v
Ran 65 tests
OK

PYTHONPATH=src python3 -m unittest discover -s tests/integration -v
Ran 25 tests
OK

PYTHONPATH=src python3 -m unittest discover -s tests/negative -v
Ran 8 tests
OK

PYTHONPATH=src python3 -m unittest discover -s tests/smoke -v
Ran 18 tests
OK

PYTHONPATH=src python3 -m ai_workroot doctor --release
AI Workroot release doctor: PASS

scripts/dev/validate-release.sh
Clean Workroot release validation passed

PYTHONPATH=src python3 -m ai_workroot legacy --help
exit=2, invalid choice: 'legacy'

find src/ai_workroot -path '*legacy*' -o -name '*legacy*'
no output
```
