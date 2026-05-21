# 0.9.530 Compatibility-Preserving Final Scripts-to-Source Migration Design

## Status

Draft execution design for `feat/0.9.530-clean-workroot-domain-reset`.

## Decision Summary

The remaining scripts-to-source migration has two explicitly named phases.

The package-ownership phase completes the first 0.9.530 architecture implementation while keeping compatibility. All mature behavior that still lives in `scripts/` moves into package-owned modules under `src/ai_workroot/`, but old script entry points, import paths, and legacy command paths continue to work through wrappers or compatibility adapters.

The Compatibility Removal phase is a later branch/version that removes compatibility after package ownership has shipped, been reviewed, and has a clear removal checklist. The Compatibility Removal phase is not part of the current implementation.

This resolves the current tension between two valid goals:

- the product architecture must stop putting active implementation logic in scripts;
- the first completed version must not break existing local calls, tests, or legacy Public Seed capabilities.

## Non-Negotiable Compatibility Contract for Package Ownership

The package-ownership phase must preserve these compatibility surfaces:

- `scripts/workroot_cli.py` remains callable.
- `scripts/workroot_cli.py init/list/status/context/doctor/bootstrap-dev` continues to delegate to the active package Clean Workroot CLI/runtime.
- Hidden legacy Public Seed commands such as `task`, `run`, `action`, `artifact`, `retrieval-card`, `checkpoint`, `invalidation`, `mind`, `session`, `continue`, and `batch` continue to work for compatibility.
- Small helper scripts remain callable: `new_task.py`, `list_tasks.py`, `setup_workroot.py`, `update_usage_direction.py`, `upgrade_workroot.py`, `add_registry_row.py`, and `rebuild_sqlite.py`.
- `scripts/validate_kernel.py` remains callable for historical/release checks while package-owned validation becomes the primary architecture target.
- Tests that intentionally verify legacy compatibility may continue to import script wrappers, but production tests should move to package imports where behavior has been migrated.
- Archiving under `docs/history/0.9.530/scripts/` means preserving a historical snapshot. It does not mean removing the callable script wrapper in Part 1.

The package-ownership phase must not remove old capabilities, rename old script paths out from under users, or require callers to switch to new APIs immediately.

## Target Architecture for Package Ownership

The package becomes the implementation owner. Scripts become compatibility surfaces.

```text
src/ai_workroot/
  runtime/
    legacy_seed/
      __init__.py
      client.py
      models.py
      time.py
      filesystem.py
      registries.py
      batch.py
      session.py
      task_creation.py
      task_listing.py
      setup.py
      profile.py
      upgrade.py
      registry_tools.py
      operation_manifest.py
      sqlite_rebuild.py
  cli/
    legacy_seed.py
  runtime/
    release_validation.py

scripts/
  workroot_client.py          compatibility re-export/wrapper
  workroot_cli.py             compatibility CLI wrapper
  new_task.py                 compatibility wrapper
  list_tasks.py               compatibility wrapper
  setup_workroot.py           compatibility wrapper
  update_usage_direction.py   compatibility wrapper
  upgrade_workroot.py         compatibility wrapper
  add_registry_row.py         compatibility wrapper
  rebuild_sqlite.py           compatibility wrapper
  validate_kernel.py          compatibility/dev validation wrapper
```

The `legacy_seed` name is intentional. It preserves old Public Seed capabilities without treating Public Seed as the active Clean Workroot architecture.

## Ownership Boundaries

| Area | Part 1 package owner | Compatibility surface |
|---|---|---|
| Task/run/action/artifact/checkpoint/invalidation/mind/session/batch behavior | `ai_workroot.runtime.legacy_seed.client` plus focused helper modules | `scripts/workroot_client.py`, hidden legacy CLI |
| Legacy CLI parser and command dispatch | `ai_workroot.cli.legacy_seed` | `scripts/workroot_cli.py` |
| New task helper | `ai_workroot.runtime.legacy_seed.task_creation` | `scripts/new_task.py` |
| Task listing helper | `ai_workroot.runtime.legacy_seed.task_listing` | `scripts/list_tasks.py` |
| Guided setup helper | `ai_workroot.runtime.legacy_seed.setup` | `scripts/setup_workroot.py` |
| Usage-direction helper | `ai_workroot.runtime.legacy_seed.profile` | `scripts/update_usage_direction.py` |
| Public Seed upgrade helper | `ai_workroot.runtime.legacy_seed.upgrade` | `scripts/upgrade_workroot.py` |
| Registry row helper | `ai_workroot.runtime.legacy_seed.registry_tools` | `scripts/add_registry_row.py` |
| Legacy SQLite rebuild helper | `ai_workroot.runtime.legacy_seed.sqlite_rebuild` | `scripts/rebuild_sqlite.py` |
| Operation manifest/recipes | `ai_workroot.runtime.legacy_seed.operation_manifest` | package manifest API, legacy references |
| Release/kernel validation | `ai_workroot.runtime.release_validation` where safe | `scripts/validate_kernel.py` |

`src/ai_workroot/core/extensions.py` should retain stable capability concepts only. Legacy operation recipes that still mention script commands belong in `runtime/legacy_seed/operation_manifest.py`, not in core.

## Package-Ownership Migration Phases

### Phase 0: Baseline and Audit

Input:

- current clean branch state;
- existing test suite;
- current script import audit.

Output:

- baseline commands pass;
- list of tests that still import script modules is captured;
- no implementation code changes yet.

Validation:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile $(find src scripts -name "*.py")
PYTHONPATH=src python3 -m ai_workroot doctor --release
python3 scripts/validate_kernel.py --release
scripts/dev/validate-release.sh
git diff --check origin/main...HEAD
rg -n "from scripts|import scripts|scripts\\." tests src docs
```

### Phase 1: Create Legacy Seed Package Shell

Input:

- current script files;
- existing legacy tests.

Output:

- `src/ai_workroot/runtime/legacy_seed/` exists;
- package has no behavior change yet;
- import-boundary tests understand that `legacy_seed` is compatibility-owned.

Validation:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_import_boundaries -v
python3 -m py_compile $(find src scripts -name "*.py")
```

### Phase 2: Move Neutral Primitives and Registry Helpers

Move low-risk definitions from `scripts/workroot_client.py` first:

- `CreatedTask`;
- `ProcessRecord`;
- time helpers;
- slug/timestamp helpers;
- CSV registry read/write helpers;
- file lock helpers;
- filesystem copy/restore/remove helpers;
- markdown helper functions.

Scripts re-export these names so old imports continue to work.

Validation:

```bash
PYTHONPATH=src python3 -m unittest tests/test_registry_store.py tests/test_workroot_client.py -v
python3 -m py_compile $(find src scripts -name "*.py")
```

### Phase 3: Move `WorkrootClient` as a Compatibility Runtime Facade

Move the complete legacy `WorkrootClient` into `ai_workroot.runtime.legacy_seed.client` in the first pass. Do not rewrite the internal behavior while moving it. Behavior refactoring can happen after package ownership and compatibility tests are stable.

`scripts/workroot_client.py` becomes a thin re-export wrapper:

```python
from ai_workroot.runtime.legacy_seed.client import *
```

Wrapper tests must prove legacy import paths still expose the same public names.

Validation:

```bash
PYTHONPATH=src python3 -m unittest tests/test_workroot_client.py tests/test_workroot_cli.py -v
python3 -m py_compile $(find src scripts -name "*.py")
```

### Phase 4: Move Small Legacy Helper Scripts One by One

Move one helper at a time and run targeted tests after each move.

Order:

1. `list_tasks.py` -> `legacy_seed.task_listing`;
2. `new_task.py` -> `legacy_seed.task_creation`;
3. `add_registry_row.py` -> `legacy_seed.registry_tools`;
4. `rebuild_sqlite.py` -> `legacy_seed.sqlite_rebuild`;
5. `update_usage_direction.py` -> `legacy_seed.profile`;
6. `setup_workroot.py` -> `legacy_seed.setup`;
7. `upgrade_workroot.py` -> `legacy_seed.upgrade`.

Each script remains a callable wrapper with the same command-line arguments.

Validation after each file:

```bash
PYTHONPATH=src python3 -m unittest <targeted-test-file> -v
python3 -m py_compile $(find src scripts -name "*.py")
```

### Phase 5: Move Legacy CLI Parser and Dispatch

Move the hidden legacy parser/dispatch path from `scripts/workroot_cli.py` into `ai_workroot.cli.legacy_seed`.

Keep these rules:

- primary Clean commands continue to delegate to package Clean CLI/runtime;
- legacy Public Seed commands remain hidden from primary Clean help;
- existing direct script usage still works;
- legacy wording is clear when legacy commands are invoked.

Validation:

```bash
PYTHONPATH=src python3 -m unittest tests/test_workroot_cli.py tests/test_workroot_cli_discovery.py tests/smoke/test_clean_package_cli.py -v
python3 -m py_compile $(find src scripts -name "*.py")
```

### Phase 6: Move Legacy Operation Manifest Out of Core

Move operation recipes and legacy script-command examples from `src/ai_workroot/core/extensions.py` into `ai_workroot.runtime.legacy_seed.operation_manifest`.

Core keeps only stable extension/capability concepts. Legacy command recipes remain available through compatibility APIs and tests.

Validation:

```bash
PYTHONPATH=src python3 -m unittest tests/test_workroot_cli_discovery.py tests/test_architecture_contracts.py tests.unit.test_core_models -v
```

### Phase 7: Move Package Release Validation Authority

Move release-surface logic that belongs to active package health checks into `ai_workroot.runtime.release_validation`. Keep `scripts/validate_kernel.py` as a wrapper/dev compatibility entry point.

Validation:

```bash
PYTHONPATH=src python3 -m ai_workroot doctor --release
python3 scripts/validate_kernel.py --release
PYTHONPATH=src python3 -m unittest tests/test_0529_release_gates.py tests/test_public_seed_surface.py tests/smoke/test_clean_release_validator.py -v
```

### Phase 8: Archive Original Script Snapshots

For every script converted into a wrapper, preserve the pre-wrapper implementation under:

```text
docs/history/0.9.530/scripts/
```

This is traceability only. The callable script remains in `scripts/`.

Validation:

```bash
git ls-files docs/history/0.9.530/scripts
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

### Phase 9: Final Package-Ownership Gate

Package ownership is complete only when all of these are true:

- active logic is package-owned;
- script files are wrappers, developer tools, or explicitly documented compatibility adapters;
- legacy command surfaces still work;
- package tests are authoritative for migrated behavior;
- wrapper tests prove compatibility;
- Clean Workroot primary help remains clean;
- no managed state is written into user directories by default;
- root Public Seed layout does not return as active architecture.

Validation:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile $(find src scripts -name "*.py")
PYTHONPATH=src python3 -m ai_workroot doctor --release
python3 scripts/validate_kernel.py --release
scripts/dev/validate-release.sh
git diff --check origin/main...HEAD
```

## Compatibility Removal Phase Plan

The Compatibility Removal phase is intentionally not implemented in this branch unless separately approved.

The Compatibility Removal phase may remove or narrow compatibility only after package ownership is reviewed. Its expected work:

- remove direct script re-export compatibility where no longer needed;
- require legacy commands to go through a single explicit `workroot legacy ...` namespace or remove them if retired;
- move or delete script-wrapper tests that only exist for compatibility;
- update docs to stop advertising old script entry points;
- keep historical snapshots under `docs/history/`;
- add migration notes for users who still call old paths.

The Compatibility Removal phase must have its own branch, Spec, tests, and review.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Capability loss during file movement | Move one capability group at a time; keep wrappers; run targeted legacy tests after each move. |
| Compatibility accidentally removed in the package-ownership phase | Add wrapper tests for old script paths and legacy CLI commands. |
| New package modules become a copy of old architecture | Put legacy behavior under `runtime/legacy_seed/`; keep Clean Workroot runtime separate. |
| Core becomes polluted with legacy recipes | Move operation recipes to `runtime/legacy_seed/operation_manifest.py`; keep core concepts stable. |
| Massive test movement hides regressions | Convert tests gradually; keep old tests until package tests pass. |
| Clean Mode regresses while migrating legacy code | Run Clean Mode smoke and release doctor after each larger phase. |
| Historical archive is mistaken for active code | Keep archives under `docs/history/`; release validators ignore docs history as active surface. |

## Open Questions

None blocking.

The current decision is explicit: preserve compatibility in the package-ownership phase, remove compatibility only in a future Compatibility Removal phase after separate approval.
