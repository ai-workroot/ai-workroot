# Scripts-to-Source Migration Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the 0.9.530 migration so active Clean Workroot product logic lives in `src/ai_workroot/`, while `scripts/` is limited to wrappers, developer tooling, release validation, and legacy compatibility.

**Architecture:** Migrate by capability, not by mechanically moving files. Package modules become authoritative only after package-first tests exist; legacy scripts remain until replacement behavior is mapped, tested, and isolated.

**Tech Stack:** Python standard library, SQLite, unittest, package entry point `python -m ai_workroot`, shell/PowerShell wrappers.

---

## File Responsibility Map

- `src/ai_workroot/cli/`: primary Clean Workroot CLI and legacy namespace boundary.
- `src/ai_workroot/runtime/`: application workflows for init, bootstrap, Work, Asset, Release, Relationship, Indexing, Context, Doctor, and migrations.
- `src/ai_workroot/core/`: domain invariants and value objects.
- `src/ai_workroot/storage/`: SQLite schema/migrations, repositories, JSONL registry, locks, filesystem helpers.
- `src/ai_workroot/indexing/`: FTS, chunks, candidates, relationship projections, global indexes, invalidation.
- `src/ai_workroot/agent/`: Native Agent Entry and agent startup helpers.
- `scripts/`: shell/PowerShell wrappers, developer checkbot tools, and explicitly legacy Python adapters only.
- `tests/unit/`: core and small provider behavior.
- `tests/integration/`: package storage/runtime/indexing flows.
- `tests/smoke/`: CLI, wrapper, bootstrap-dev, install, and Clean Mode smokes.
- `tests/negative/`: release/redaction leakage and Public Seed active-root prevention.
- `tests/legacy/`: preserved Public Seed compatibility tests.

## Phase 0: Baseline Validation

**Files:**
- Read: `docs/dev/0.9.530/scripts-to-src-migration-architecture.md`
- Read: `docs/dev/0.9.530/scripts-to-src-migration-detailed-design.md`
- Read: `docs/specs/023-active-package-cli-and-legacy-isolation.spec.md`
- Read: `docs/specs/030-test-suite-and-public-seed-quarantine.spec.md`

- [ ] **Step 1: Confirm branch and clean status**

Run:

```bash
git branch --show-current
git status --short --ignored
git rev-parse HEAD
```

Expected:

```text
feat/0.9.530-clean-workroot-domain-reset
```

Only expected ignored local files may appear.

- [ ] **Step 2: Run baseline checkbot commands**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile $(find src scripts -name "*.py")
PYTHONPATH=src python3 -m ai_workroot doctor --release
python3 scripts/validate_kernel.py --release
scripts/dev/validate-release.sh
git diff --check origin/main...HEAD
```

Expected: all commands exit 0 before migration begins. If a command fails, stop and fix baseline before moving capability code.

- [ ] **Step 3: Capture script import audit**

Run:

```bash
grep -R "from scripts\\|import scripts\\|scripts\\." -n tests src docs | tee /tmp/ai-workroot-script-import-audit.txt
```

Expected: current legacy import list is known. This is the baseline for reducing active script dependence.

## Phase 1: CLI and Legacy Boundary

**Files:**
- Modify: `src/ai_workroot/cli/main.py`
- Create or modify: `src/ai_workroot/cli/commands/*.py`
- Modify: `scripts/workroot_cli.py`
- Modify tests: `tests/smoke/test_clean_package_cli.py`, `tests/test_workroot_cli.py`, `tests/legacy/`

- [ ] **Step 1: Write package CLI help tests**

Add tests asserting:

```python
def test_package_help_shows_only_primary_clean_commands():
    ...

def test_package_help_does_not_show_legacy_seed_commands():
    ...
```

Expected command:

```bash
PYTHONPATH=src python3 -m unittest tests.smoke.test_clean_package_cli -v
```

Expected first run before implementation: failing test only for missing legacy boundary if not already covered.

- [ ] **Step 2: Implement command module split only if needed**

Keep behavior unchanged. Move parser/action code into `src/ai_workroot/cli/commands/` only when it reduces file size or clarifies legacy boundary.

- [ ] **Step 3: Make script Clean commands delegate**

Change `scripts/workroot_cli.py` so `init`, `list`, `status`, `context`, `doctor`, and `bootstrap-dev` call package CLI/runtime. Keep old seed commands under legacy handling.

- [ ] **Step 4: Run CLI tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.smoke.test_clean_package_cli tests.test_workroot_cli tests.test_workroot_cli_discovery -v
```

Expected: primary package behavior passes; legacy tests are clearly marked.

- [ ] **Step 5: Commit**

```bash
git add src/ai_workroot/cli scripts/workroot_cli.py tests
git commit -m "Isolate Clean CLI and legacy commands"
```

## Phase 2: Storage and Migrations

**Files:**
- Create: `src/ai_workroot/storage/migrations.py`
- Create: `src/ai_workroot/storage/repositories.py`
- Modify: `src/ai_workroot/storage/sqlite.py`
- Modify: `src/ai_workroot/runtime/environment.py`
- Modify: `src/ai_workroot/runtime/bootstrap.py`
- Add tests: `tests/integration/test_environment_storage.py`, `tests/unit/`

- [ ] **Step 1: Write migration runner tests**

Tests must cover ordered migrations, idempotent application, old DB fixture migration, and backup before destructive migration.

- [ ] **Step 2: Implement migration runner**

Implement package migration runner using `schema_migrations` records. Keep standard library only.

- [ ] **Step 3: Consolidate registry locking**

Ensure init and bootstrap-dev registry writes share `src/ai_workroot/storage/locks.py`.

- [ ] **Step 4: Run storage tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.integration.test_environment_storage tests.unit.test_import_boundaries -v
```

Expected: storage, schema, and import-boundary tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/ai_workroot/storage src/ai_workroot/runtime tests
git commit -m "Move storage migrations into package"
```

## Phase 3: Work and Asset Runtime

**Files:**
- Create: `src/ai_workroot/runtime/work.py`
- Create: `src/ai_workroot/runtime/assets.py`
- Create or modify: `src/ai_workroot/storage/repositories.py`
- Modify: `src/ai_workroot/core/work.py`
- Modify: `src/ai_workroot/core/assets.py`
- Move/label tests: `tests/legacy/`, `tests/integration/`

- [ ] **Step 1: Write package Work tests**

Cover task create/update, run add/update, action add, checkpoint add, handoff add, and retrieval card add.

- [ ] **Step 2: Write package Asset tests**

Cover artifact/decision/knowledge/result mapping to Asset subtypes and no default user-directory writes.

- [ ] **Step 3: Write batch rollback tests**

Cover partial failure rollback and `OperationTransaction` outcome records.

- [ ] **Step 4: Implement Work runtime and repositories**

Port behavior from `scripts/workroot_client.py` in small groups. Do not expose new CLI commands until runtime tests pass.

- [ ] **Step 5: Implement Asset runtime and repositories**

Map legacy output concepts to Asset types. Preserve provenance and visibility.

- [ ] **Step 6: Move legacy client tests**

Move script-only behavior tests to `tests/legacy/` or rename clearly.

- [ ] **Step 7: Run Work/Asset tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.integration tests.unit tests.legacy -v
```

Expected: package tests and legacy preservation tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/ai_workroot/runtime src/ai_workroot/storage src/ai_workroot/core tests
git commit -m "Migrate Work and Asset runtime capabilities"
```

## Phase 4: Retrieval, Indexing, and Context Control

**Files:**
- Create or modify: `src/ai_workroot/indexing/fts.py`
- Create or modify: `src/ai_workroot/indexing/candidates.py`
- Create or modify: `src/ai_workroot/indexing/pipeline.py`
- Modify: `src/ai_workroot/indexing/providers/*.py`
- Modify: `src/ai_workroot/runtime/context.py`
- Modify: `src/ai_workroot/core/context.py`
- Move tests from script imports to package imports.

- [ ] **Step 1: Write package indexing tests**

Cover supported-file detection, binary exclusion, chunking, content hash, FTS insert, FTS query, and FTS fallback trace.

- [ ] **Step 2: Write package candidate tests**

Cover source flags, query FTS, safety filtering, candidate use count, and starvation prevention.

- [ ] **Step 3: Write package context tests**

Cover FTS/query/relationship influence, confidence, token budgets, CJK/code token estimates, hard-limit fallback, and debug trace.

- [ ] **Step 4: Migrate indexing helpers**

Move behavior from `scripts/workroot_indexing.py` into package indexing modules.

- [ ] **Step 5: Migrate candidate helpers**

Move behavior from `scripts/workroot_candidates.py` into package candidate modules.

- [ ] **Step 6: Migrate context helpers**

Move only coherent groups from `scripts/workroot_context.py`: budget/config merge, pool building, scoring, rendering, trace, hard limit.

- [ ] **Step 7: Run context/indexing tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.integration.test_indexing_context_control tests.test_workroot_context tests.test_workroot_debug_trace -v
```

Expected: migrated package tests pass; remaining script tests are legacy-labeled or scheduled.

- [ ] **Step 8: Commit**

```bash
git add src/ai_workroot/indexing src/ai_workroot/runtime/context.py src/ai_workroot/core/context.py tests
git commit -m "Complete package Context Control and indexing parity"
```

## Phase 5: Release, Relationship, and Safety

**Files:**
- Modify: `src/ai_workroot/indexing/providers/release_provider.py`
- Modify: `src/ai_workroot/indexing/providers/relationship_provider.py`
- Modify: `src/ai_workroot/runtime/context.py`
- Modify: `src/ai_workroot/core/release.py`
- Modify: `src/ai_workroot/core/relationships.py`
- Add tests: `tests/unit/test_release_target_resolver.py`, `tests/negative/test_release_control_protection.py`

- [ ] **Step 1: Write resolver coverage tests**

Cover `asset`, `task`, `work_action`, `agent_run`, `checkpoint`, `handoff`, `retrieval_card`, `indexed_chunk`, `fts_match`, `relationship_edge`, and nested `context_candidate`.

- [ ] **Step 2: Write safety filtering tests**

Cover `never-auto`, `needs-confirmation`, and sensitive policies at provider and Context Control levels.

- [ ] **Step 3: Write relationship signal tests**

Ensure signals render only when backed by real edges and unrelated high-importance nodes do not appear.

- [ ] **Step 4: Implement missing resolver/safety/relationship behavior**

Keep release filtering centralized; do not bypass protections for unknown source types.

- [ ] **Step 5: Run release/relationship tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_release_target_resolver tests.negative.test_release_control_protection -v
```

Expected: release protection and relationship filtering pass.

- [ ] **Step 6: Commit**

```bash
git add src/ai_workroot/indexing/providers src/ai_workroot/runtime/context.py src/ai_workroot/core tests
git commit -m "Harden release and relationship context filtering"
```

## Phase 6: Doctor, Checkbot, Install, and Wrappers

**Files:**
- Modify: `src/ai_workroot/runtime/doctor.py`
- Modify: `scripts/dev/validate-release.sh`
- Create/modify: `install/unix/install.sh`
- Create/modify: `install/windows/install.ps1`
- Modify: `scripts/install.sh`
- Modify: `scripts/install.ps1`
- Modify: `scripts/bootstrap-dev.sh`
- Modify: `scripts/bootstrap-dev.ps1`
- Add tests: `tests/smoke/`, `tests/negative/`

- [ ] **Step 1: Write release doctor tests**

Cover tracked vs ignored `AGENTS.md`, `CLAUDE.md`, `space/`, `.workroot/`, `.idea/`.

- [ ] **Step 2: Write install/wrapper smoke tests**

Cover shell syntax, temp install dir, idempotency, no sudo/admin default, bootstrap-dev wrapper temp state.

- [ ] **Step 3: Expand release doctor and checkbot**

Make package release doctor primary. Keep historical validator as baseline only while documented.

- [ ] **Step 4: Move/wrap install scripts**

Add `install/` scripts and keep old paths as compatibility wrappers.

- [ ] **Step 5: Run validation**

Run:

```bash
bash -n scripts/install.sh
bash -n scripts/bootstrap-dev.sh
PYTHONPATH=src python3 -m ai_workroot doctor --release
scripts/dev/validate-release.sh
```

Expected: all required checks pass.

- [ ] **Step 6: Commit**

```bash
git add src/ai_workroot/runtime/doctor.py scripts install tests docs
git commit -m "Move validation and wrappers to Clean Workroot package"
```

## Phase 7: Test Suite Split and Public Seed Quarantine

**Files:**
- Modify: `tests/`
- Modify: `docs/history/`
- Modify: `docs/dev/0.9.530/`
- Modify: release validator tests.

- [ ] **Step 1: Write test audit checks**

Audit:

```bash
git ls-files tests
git ls-files | grep -E '(^|/)test_.*\.py$|(^|/).*_test\.py$' || true
grep -R "from scripts\\|import scripts\\|scripts\\." -n tests src docs || true
```

- [ ] **Step 2: Move legacy tests**

Move script-importing tests under `tests/legacy/` or convert them to package imports.

- [ ] **Step 3: Quarantine remaining Public Seed fixtures**

Preserve useful historical material under `docs/history/` or `tests/fixtures/`; do not keep active-root assumptions.

- [ ] **Step 4: Run full suite**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile $(find src scripts -name "*.py")
git diff --check origin/main...HEAD
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add tests docs scripts src
git commit -m "Split tests and quarantine legacy Public Seed behavior"
```

## Phase 8: Final Handoff Without Tag

**Files:**
- Modify: `docs/dev/0.9.530/`
- Read: Git diff and validation output.

- [ ] **Step 1: Run final validation**

Run:

```bash
git fetch origin
git diff --stat origin/main...HEAD
git diff --name-only origin/main...HEAD
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile $(find src scripts -name "*.py")
PYTHONPATH=src python3 -m ai_workroot doctor --release
scripts/dev/validate-release.sh
git diff --check origin/main...HEAD
```

Expected: all required checks pass.

- [ ] **Step 2: Produce review handoff**

Include:

```text
branch
latest commit
base branch
changed files
production code changed
tests changed
docs changed
scripts changed
validation output
known limitations
questions for reviewer
```

- [ ] **Step 3: Push review branch only after user approval**

Run only when instructed:

```bash
git push -u origin feat/0.9.530-clean-workroot-domain-reset
```

Do not merge, tag, or release.
