# Compatibility-Preserving Final Script Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish moving remaining script-owned behavior into `src/ai_workroot/` while preserving all old script and legacy CLI compatibility for Part 1.

**Architecture:** Package modules own behavior. Scripts remain callable wrappers or explicitly documented compatibility adapters. Compatibility removal is deferred to a later Part 2 branch/version.

**Tech Stack:** Python standard library, SQLite, unittest, package entry point `python -m ai_workroot`, shell and PowerShell wrappers.

---

## Compatibility Rule

Do not remove old script entry points in this plan. A script may become a wrapper, but the old path must remain callable. Original implementations may be copied into `docs/history/0.9.530/scripts/` for traceability.

## File Responsibility Map

- `src/ai_workroot/runtime/legacy_seed/`: package-owned implementation home for legacy Public Seed compatibility behavior.
- `src/ai_workroot/cli/legacy_seed.py`: package-owned parser/dispatch for legacy CLI compatibility.
- `src/ai_workroot/runtime/release_validation.py`: package-owned release-surface validation where safe.
- `scripts/*.py`: wrappers, dev tools, or compatibility adapters.
- `docs/history/0.9.530/scripts/`: historical snapshots, not active code.
- `tests/legacy/` or clearly named legacy tests: preserved Public Seed behavior.
- `tests/smoke/`: wrapper and Clean CLI smoke tests.
- `tests/unit/` and `tests/integration/`: package-first tests.

## Phase 0: Baseline and Audit

**Files:**
- Read: `docs/dev/0.9.530/final-compatibility-preserving-script-migration-design.md`
- Read: `docs/specs/031-compatibility-preserving-script-migration.spec.md`
- Read: `scripts/workroot_client.py`
- Read: `scripts/workroot_cli.py`

- [ ] **Step 1: Confirm branch and clean status**

Run:

```bash
git branch --show-current
git status --short
git rev-parse HEAD
```

Expected:

```text
feat/0.9.530-clean-workroot-domain-reset
```

`git status --short` should be empty before implementation starts.

- [ ] **Step 2: Run baseline validation**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile $(find src scripts -name "*.py")
PYTHONPATH=src python3 -m ai_workroot doctor --release
python3 scripts/validate_kernel.py --release
scripts/dev/validate-release.sh
git diff --check origin/main...HEAD
```

Expected: every command exits 0. Stop and fix baseline failures before moving code.

- [ ] **Step 3: Capture script import audit**

Run:

```bash
rg -n "from scripts|import scripts|scripts\\." tests src docs > /tmp/ai-workroot-script-import-audit-before.txt || true
```

Expected: audit file captures intentional script dependencies before migration.

## Phase 1: Add Legacy Seed Package Shell

**Files:**
- Create: `src/ai_workroot/runtime/legacy_seed/__init__.py`
- Add test if missing: `tests/unit/test_import_boundaries.py`

- [ ] **Step 1: Add failing package import test**

Add assertions equivalent to:

```python
def test_legacy_seed_package_is_importable():
    import ai_workroot.runtime.legacy_seed as legacy_seed
    self.assertIsNotNone(legacy_seed)
```

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_import_boundaries -v
```

Expected before implementation: fail if the package does not exist.

- [ ] **Step 2: Create package shell**

Create `src/ai_workroot/runtime/legacy_seed/__init__.py` with a short docstring that states the package preserves legacy Public Seed compatibility and is not the active Clean Workroot architecture.

- [ ] **Step 3: Run focused validation**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_import_boundaries -v
python3 -m py_compile $(find src scripts -name "*.py")
```

Expected: pass.

- [ ] **Step 4: Commit**

Run:

```bash
git add src/ai_workroot/runtime/legacy_seed tests/unit/test_import_boundaries.py
git commit -m "Add legacy seed package boundary"
```

## Phase 2: Move Neutral Workroot Client Helpers

**Files:**
- Create: `src/ai_workroot/runtime/legacy_seed/models.py`
- Create: `src/ai_workroot/runtime/legacy_seed/time.py`
- Create: `src/ai_workroot/runtime/legacy_seed/filesystem.py`
- Create: `src/ai_workroot/runtime/legacy_seed/registries.py`
- Modify: `scripts/workroot_client.py`
- Modify: `tests/test_workroot_client.py`
- Modify: `tests/test_registry_store.py`
- Archive: `docs/history/0.9.530/scripts/workroot_client.py` if the snapshot is missing or stale

- [ ] **Step 1: Add package-first helper tests**

Update tests so helper behavior is imported from package modules:

```python
from ai_workroot.runtime.legacy_seed.time import normalize_instant, now_utc, timestamp_slug
from ai_workroot.runtime.legacy_seed.registries import read_registry, write_registry_atomic
from ai_workroot.runtime.legacy_seed.filesystem import copy_tree_or_file, restore_tree_or_file, remove_tree_or_file
```

Run:

```bash
PYTHONPATH=src python3 -m unittest tests/test_registry_store.py tests/test_workroot_client.py -v
```

Expected before implementation: fail on missing modules or imports.

- [ ] **Step 2: Move helpers without behavior changes**

Move these definitions from `scripts/workroot_client.py` into package modules:

```text
CreatedTask
ProcessRecord
now_utc
normalize_instant
timestamp_slug
slugify
read_registry
optional_str
optional_path_list
file_lock
write_registry_atomic
copy_tree_or_file
restore_tree_or_file
remove_tree_or_file
replace_in_file
markdown_sections
append_unique_lines
```

Keep names and behavior identical.

- [ ] **Step 3: Re-export helpers from the script**

Update `scripts/workroot_client.py` so old import paths still expose the same names. The script may import from package modules at the top of the file while `WorkrootClient` remains temporarily in the script.

- [ ] **Step 4: Run focused validation**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests/test_registry_store.py tests/test_workroot_client.py -v
python3 -m py_compile $(find src scripts -name "*.py")
```

Expected: pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/ai_workroot/runtime/legacy_seed scripts/workroot_client.py tests docs/history/0.9.530/scripts/workroot_client.py
git commit -m "Move legacy client helpers into package"
```

## Phase 3: Move WorkrootClient Facade

**Files:**
- Create: `src/ai_workroot/runtime/legacy_seed/client.py`
- Modify: `scripts/workroot_client.py`
- Modify: `tests/test_workroot_client.py`
- Modify: `tests/test_workroot_cli.py`

- [ ] **Step 1: Add package-first WorkrootClient tests**

Update client tests to import:

```python
from ai_workroot.runtime.legacy_seed.client import WorkrootClient
```

Keep a separate wrapper test that loads `scripts/workroot_client.py` and confirms:

```python
self.assertTrue(hasattr(module, "WorkrootClient"))
self.assertTrue(hasattr(module, "normalize_instant"))
self.assertTrue(hasattr(module, "slugify"))
```

Run:

```bash
PYTHONPATH=src python3 -m unittest tests/test_workroot_client.py -v
```

Expected before implementation: package import fails.

- [ ] **Step 2: Move the full facade into the package**

Move `WorkrootClient` and all constants it requires into `ai_workroot.runtime.legacy_seed.client`. Do not redesign behavior during this move.

- [ ] **Step 3: Convert script to compatibility re-export**

Reduce `scripts/workroot_client.py` to a wrapper that re-exports the package public names. Keep the wrapper small and readable.

- [ ] **Step 4: Run focused validation**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests/test_workroot_client.py tests/test_workroot_cli.py -v
python3 -m py_compile $(find src scripts -name "*.py")
```

Expected: pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/ai_workroot/runtime/legacy_seed/client.py scripts/workroot_client.py tests docs/history/0.9.530/scripts/workroot_client.py
git commit -m "Move legacy WorkrootClient into package"
```

## Phase 4: Move Small Helper Scripts

**Files:**
- Create: `src/ai_workroot/runtime/legacy_seed/task_listing.py`
- Create: `src/ai_workroot/runtime/legacy_seed/task_creation.py`
- Create: `src/ai_workroot/runtime/legacy_seed/registry_tools.py`
- Create: `src/ai_workroot/runtime/legacy_seed/sqlite_rebuild.py`
- Create: `src/ai_workroot/runtime/legacy_seed/profile.py`
- Create: `src/ai_workroot/runtime/legacy_seed/setup.py`
- Create: `src/ai_workroot/runtime/legacy_seed/upgrade.py`
- Modify corresponding scripts in `scripts/`
- Modify corresponding tests in `tests/`
- Archive corresponding original scripts in `docs/history/0.9.530/scripts/`

- [ ] **Step 1: Move `list_tasks.py` behavior**

Package module: `ai_workroot.runtime.legacy_seed.task_listing`.

Run:

```bash
PYTHONPATH=src python3 -m unittest tests/test_list_tasks.py -v
python3 scripts/list_tasks.py --limit 1 --format json >/tmp/ai-workroot-list-tasks-smoke.json || true
```

Expected: tests pass. Smoke may report missing legacy registry in a clean repo, but it must execute the wrapper and fail only with the existing expected missing-registry message.

- [ ] **Step 2: Move `new_task.py` behavior**

Package module: `ai_workroot.runtime.legacy_seed.task_creation`.

Run:

```bash
PYTHONPATH=src python3 -m unittest tests/test_new_task.py -v
python3 -m py_compile scripts/new_task.py src/ai_workroot/runtime/legacy_seed/task_creation.py
```

Expected: pass.

- [ ] **Step 3: Move `add_registry_row.py` behavior**

Package module: `ai_workroot.runtime.legacy_seed.registry_tools`.

Run:

```bash
PYTHONPATH=src python3 -m unittest tests/test_add_registry_row.py -v
python3 -m py_compile scripts/add_registry_row.py src/ai_workroot/runtime/legacy_seed/registry_tools.py
```

Expected: pass.

- [ ] **Step 4: Move `rebuild_sqlite.py` behavior**

Package module: `ai_workroot.runtime.legacy_seed.sqlite_rebuild`.

Run:

```bash
PYTHONPATH=src python3 -m py_compile scripts/rebuild_sqlite.py src/ai_workroot/runtime/legacy_seed/sqlite_rebuild.py
PYTHONPATH=src python3 -m unittest discover -s tests -p "*sqlite*.py" -v
```

Expected: pass.

- [ ] **Step 5: Move profile/setup/upgrade helpers**

Package modules:

```text
ai_workroot.runtime.legacy_seed.profile
ai_workroot.runtime.legacy_seed.setup
ai_workroot.runtime.legacy_seed.upgrade
```

Run:

```bash
PYTHONPATH=src python3 -m unittest tests/test_update_usage_direction.py tests/test_setup_workroot.py tests/test_upgrade_workroot.py -v
python3 -m py_compile scripts/update_usage_direction.py scripts/setup_workroot.py scripts/upgrade_workroot.py
```

Expected: pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/ai_workroot/runtime/legacy_seed scripts tests docs/history/0.9.530/scripts
git commit -m "Move legacy helper scripts into package"
```

## Phase 5: Move Legacy CLI Parser and Dispatch

**Files:**
- Create: `src/ai_workroot/cli/legacy_seed.py`
- Modify: `scripts/workroot_cli.py`
- Modify: `tests/test_workroot_cli.py`
- Modify: `tests/test_workroot_cli_discovery.py`
- Modify: `tests/smoke/test_clean_package_cli.py`
- Archive: `docs/history/0.9.530/scripts/workroot_cli.py`

- [ ] **Step 1: Add package legacy CLI tests**

Add or update tests so legacy parser behavior can be exercised from:

```python
from ai_workroot.cli.legacy_seed import build_parser, main
```

Keep wrapper tests for `scripts/workroot_cli.py`.

Run:

```bash
PYTHONPATH=src python3 -m unittest tests/test_workroot_cli.py -v
```

Expected before implementation: package import fails.

- [ ] **Step 2: Move parser and hidden command dispatch**

Move legacy command parser and handlers from `scripts/workroot_cli.py` into `ai_workroot.cli.legacy_seed`.

Keep package Clean CLI primary help unchanged in `ai_workroot.cli.main`.

- [ ] **Step 3: Keep script compatibility**

Make `scripts/workroot_cli.py` call the package legacy CLI wrapper while preserving direct script usage.

- [ ] **Step 4: Run focused validation**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests/test_workroot_cli.py tests/test_workroot_cli_discovery.py tests/smoke/test_clean_package_cli.py -v
python3 -m py_compile scripts/workroot_cli.py src/ai_workroot/cli/legacy_seed.py
```

Expected: pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/ai_workroot/cli/legacy_seed.py scripts/workroot_cli.py tests docs/history/0.9.530/scripts/workroot_cli.py
git commit -m "Move legacy CLI compatibility into package"
```

## Phase 6: Move Legacy Operation Manifest Out of Core

**Files:**
- Create: `src/ai_workroot/runtime/legacy_seed/operation_manifest.py`
- Modify: `src/ai_workroot/core/extensions.py`
- Modify: `tests/test_workroot_cli_discovery.py`
- Modify: `tests/test_architecture_contracts.py`

- [ ] **Step 1: Add manifest ownership tests**

Assert legacy operation recipes are loaded from `ai_workroot.runtime.legacy_seed.operation_manifest`, while `ai_workroot.core.extensions` keeps stable capability types only.

Run:

```bash
PYTHONPATH=src python3 -m unittest tests/test_workroot_cli_discovery.py tests/test_architecture_contracts.py -v
```

Expected before implementation: fail if legacy recipes still only live in core.

- [ ] **Step 2: Move operation manifest behavior**

Move recipe data and legacy script-command references out of core. Keep any public function names needed by callers through import-compatible forwarding if current tests require them.

- [ ] **Step 3: Run validation**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests/test_workroot_cli_discovery.py tests/test_architecture_contracts.py tests/unit/test_core_models.py -v
python3 -m py_compile src/ai_workroot/core/extensions.py src/ai_workroot/runtime/legacy_seed/operation_manifest.py
```

Expected: pass.

- [ ] **Step 4: Commit**

Run:

```bash
git add src/ai_workroot/core/extensions.py src/ai_workroot/runtime/legacy_seed/operation_manifest.py tests
git commit -m "Move legacy operation manifest out of core"
```

## Phase 7: Move Release Validation Authority

**Files:**
- Create: `src/ai_workroot/runtime/release_validation.py`
- Modify: `src/ai_workroot/runtime/doctor.py`
- Modify: `scripts/validate_kernel.py`
- Modify: `tests/test_0529_release_gates.py`
- Modify: `tests/test_public_seed_surface.py`
- Modify: `tests/smoke/test_clean_release_validator.py`

- [ ] **Step 1: Add package validation tests**

Update tests so package validation logic is imported from:

```python
from ai_workroot.runtime.release_validation import validate_release_surface
```

Keep script wrapper tests that prove `scripts/validate_kernel.py --release` remains callable.

Run:

```bash
PYTHONPATH=src python3 -m unittest tests/test_0529_release_gates.py tests/test_public_seed_surface.py tests/smoke/test_clean_release_validator.py -v
```

Expected before implementation: fail on missing package validation import.

- [ ] **Step 2: Move package-owned validation logic**

Move active release-surface logic into `ai_workroot.runtime.release_validation`. Keep historical checks that are only about old kernel files in the script or wrap them carefully if they are still required by tests.

- [ ] **Step 3: Keep validate_kernel compatibility**

Keep `scripts/validate_kernel.py --release` working. It may call package validation plus any historical validation still owned by the script.

- [ ] **Step 4: Run validation**

Run:

```bash
PYTHONPATH=src python3 -m ai_workroot doctor --release
python3 scripts/validate_kernel.py --release
PYTHONPATH=src python3 -m unittest tests/test_0529_release_gates.py tests/test_public_seed_surface.py tests/smoke/test_clean_release_validator.py -v
```

Expected: pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/ai_workroot/runtime/release_validation.py src/ai_workroot/runtime/doctor.py scripts/validate_kernel.py tests
git commit -m "Move release validation into package"
```

## Phase 8: Final Compatibility and Clean Architecture Audit

**Files:**
- Modify: tests as needed.
- Modify: docs handoff only if requested.

- [ ] **Step 1: Re-run script import audit**

Run:

```bash
rg -n "from scripts|import scripts|scripts\\." tests src docs > /tmp/ai-workroot-script-import-audit-after.txt || true
```

Expected: remaining script imports are limited to wrapper tests, docs history, and explicit compatibility tests.

- [ ] **Step 2: Run full validation**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile $(find src scripts -name "*.py")
PYTHONPATH=src python3 -m ai_workroot doctor --release
python3 scripts/validate_kernel.py --release
scripts/dev/validate-release.sh
git diff --check origin/main...HEAD
```

Expected: all commands pass.

- [ ] **Step 3: Run Clean Mode smoke**

Run:

```bash
TMPDIR="$(mktemp -d)"
AI_WORKROOT_HOME="$TMPDIR/ai-workroot-home" PYTHONPATH=src python3 -m ai_workroot init --name "Migration Smoke" --directory "$TMPDIR/user-workroot" --no-native-agent-entry
find "$TMPDIR/user-workroot" -maxdepth 2 -type f -print
AI_WORKROOT_HOME="$TMPDIR/ai-workroot-home" PYTHONPATH=src python3 -m ai_workroot doctor --cwd "$TMPDIR/user-workroot"
```

Expected: user directory has no managed state files; doctor passes or reports only expected non-blocking warnings.

- [ ] **Step 4: Produce final handoff**

Include:

```text
branch
commit
changed files
package-owned modules added
script wrappers preserved
legacy compatibility status
test output
known limitations
explicit note that Part 2 compatibility removal is not done
```

- [ ] **Step 5: Commit final docs/test cleanups**

Run only if final docs or tests changed:

```bash
git add docs tests
git commit -m "Document compatibility-preserving script migration results"
```

## Part 2 Reminder

Do not perform these actions in Part 1:

- remove script wrapper paths;
- force users to call only `workroot legacy ...`;
- delete wrapper compatibility tests;
- remove historical archives;
- tag, release, merge, or push without explicit instruction.
