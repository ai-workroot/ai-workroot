# Scripts to Source Migration Status

## Status

0.9.530 scripts closure is complete for the active Clean Workroot product path.

This document records the 0.9.530 compatibility-preserving state. It is superseded for current active paths by `docs/specs/041-runnable-legacy-compat-removal.spec.md`: runnable legacy compatibility is removed, and old source is preserved only as non-runnable archive material under `docs/history/public-seed/code-archive/`.

Active Clean Workroot product logic lives under `src/ai_workroot/`. The
`scripts/` tree is now a support surface only:

- `scripts/dev/`: developer, release validation, review export, and smoke helpers.
- historical 0.9.530 only: `scripts/compat/` and `scripts/legacy/public_seed/` were temporary compatibility surfaces.

This was not Compatibility Removal at the time. Current active paths no longer keep those callable compatibility surfaces.

For example, active Context Control is implemented in
`src/ai_workroot/runtime/context.py`; the legacy Context Guide source is now archived as non-runnable history.

## Migration Rules

- Clean user-facing commands should use `python -m ai_workroot` or the installed `workroot` console script.
- New Clean Workroot product behavior must not be added under `scripts/`.
- Runnable legacy compatibility must not be restored as a fallback.
- `scripts/` root must not contain Python implementation files.

## File Matrix

| current path | current role | target location | status | core product logic remains in scripts | tests covering it | removal risk |
|---|---|---|---|---|---|---|
| `scripts/README.md` | scripts directory contract | `scripts/README.md` | dev-helper | no | `tests/contracts/test_repository_surface.py` | low |
| `scripts/compat/README.md` | compat wrapper contract | `scripts/compat/README.md` | wrapper | no | `tests/contracts/test_repository_surface.py` | low |
| `scripts/compat/install.ps1` | Windows install compatibility wrapper | `install/windows/install.ps1` | wrapper | no | `tests/contracts/test_release_gates.py`, syntax where available | medium on Windows |
| `scripts/compat/install.sh` | Unix install compatibility wrapper | `install/unix/install.sh` | wrapper | no | `tests/contracts/test_release_gates.py`, `scripts/dev/validate-release.sh` | low |
| `scripts/compat/validate_kernel.py` | historical/release validation wrapper | `src/ai_workroot/runtime/legacy_seed/kernel_validation.py` | wrapper | no | `tests/contracts/test_repository_surface.py`, legacy kernel contract coverage, `tests/contracts/test_release_gates.py` | medium; release baseline depends on it |
| `scripts/compat/workroot_agent_entry.py` | Native Agent Entry compatibility wrapper | `src/ai_workroot/agent/native_entry.py` | wrapper | no | `tests/unit/test_agent_entry.py` | low |
| `scripts/compat/workroot_bootstrap.py` | bootstrap compatibility wrapper | `src/ai_workroot/runtime/bootstrap.py` | wrapper | no | `tests/integration/test_bootstrap_dev.py`, `tests/integration/test_agent_bootstrap.py` | low |
| `scripts/compat/workroot_cli.py` | legacy CLI compatibility wrapper | `src/ai_workroot/cli/legacy_seed.py` and `src/ai_workroot/cli/main.py` | wrapper | no | legacy CLI coverage, `tests/smoke/test_cli_discovery.py`, `tests/integration/test_init_cli.py` | high; many legacy tests invoke it |
| `scripts/compat/workroot_doctor.py` | legacy doctor compatibility wrapper | `src/ai_workroot/runtime/legacy_doctor.py` and `src/ai_workroot/runtime/doctor.py` | wrapper | no | legacy doctor coverage, `tests/unit/test_runtime_doctor.py` | medium |
| `scripts/compat/workroot_migrations.py` | migration compatibility wrapper | `src/ai_workroot/storage/migrations.py` | wrapper | no | `tests/unit/test_migrations.py` | medium |
| `scripts/compat/workroot_paths.py` | path compatibility wrapper | `src/ai_workroot/runtime/paths.py` | wrapper | no | `tests/unit/test_paths.py`, init tests | low |
| `scripts/compat/workroot_state.py` | managed state compatibility wrapper | `src/ai_workroot/runtime/state.py` | wrapper | no | `tests/unit/test_state.py`, bootstrap/init tests | medium |
| `scripts/dev/README.md` | developer helper contract | `scripts/dev/README.md` | dev-helper | no | `tests/contracts/test_repository_surface.py` | low |
| `scripts/dev/bootstrap-dev.ps1` | developer bootstrap wrapper | `src/ai_workroot/runtime/bootstrap.py` | dev-helper | no | syntax where available; bootstrap smoke | medium on Windows |
| `scripts/dev/bootstrap-dev.sh` | developer bootstrap wrapper | `src/ai_workroot/runtime/bootstrap.py` | dev-helper | no | `tests/integration/test_agent_bootstrap.py`, smoke tests | low |
| `scripts/dev/export-review-zip.sh` | review export helper | `scripts/dev/export-review-zip.sh` | dev-helper | no | `tests/smoke/test_clean_release_validator.py` | low |
| `scripts/dev/new_task_smoke.py` | legacy multilingual smoke helper | `src/ai_workroot/runtime/legacy_seed/task_creation.py` | dev-helper | no | legacy task coverage | low |
| `scripts/dev/validate-release.sh` | release validation helper | package doctor, compile checks, shell syntax checks | release validation helper | no | `tests/smoke/test_clean_release_validator.py` | medium |
| `scripts/legacy/README.md` | legacy area contract | `scripts/legacy/README.md` | legacy-quarantine | no | `tests/contracts/test_repository_surface.py` | low |
| `scripts/legacy/public_seed/README.md` | Public Seed quarantine contract | `scripts/legacy/public_seed/README.md` | legacy-quarantine | no | `tests/contracts/test_repository_surface.py` | low |
| `scripts/legacy/public_seed/add_registry_row.py` | legacy registry row maintenance wrapper | `src/ai_workroot/runtime/legacy_seed/registry_tools.py` | legacy-quarantine | no | legacy registry coverage | medium |
| `scripts/legacy/public_seed/list_tasks.py` | legacy task listing wrapper | `src/ai_workroot/runtime/legacy_seed/task_listing.py` | legacy-quarantine | no | legacy task coverage | medium |
| `scripts/legacy/public_seed/new_task.py` | legacy task creation wrapper | `src/ai_workroot/runtime/legacy_seed/task_creation.py` | legacy-quarantine | no | legacy task coverage | medium |
| `scripts/legacy/public_seed/rebuild_sqlite.py` | legacy Public Seed SQLite rebuild wrapper | `src/ai_workroot/runtime/legacy_seed/sqlite_rebuild.py` | legacy-quarantine | no | `tests/contracts/test_release_gates.py` | medium |
| `scripts/legacy/public_seed/setup_workroot.py` | legacy guided setup wrapper | `src/ai_workroot/runtime/legacy_seed/setup.py` | legacy-quarantine | no | legacy setup coverage | medium |
| `scripts/legacy/public_seed/update_usage_direction.py` | legacy profile update wrapper | `src/ai_workroot/runtime/legacy_seed/profile.py` | legacy-quarantine | no | legacy profile coverage | medium |
| `scripts/legacy/public_seed/upgrade_workroot.py` | legacy Public Seed upgrade wrapper | `src/ai_workroot/runtime/legacy_seed/upgrade.py` | legacy-quarantine | no | legacy upgrade coverage | high for old fixtures |
| `scripts/legacy/public_seed/workroot_candidates.py` | legacy candidate compatibility wrapper | `src/ai_workroot/indexing/legacy_candidates.py` | legacy-quarantine | no | legacy candidate coverage | medium |
| `scripts/legacy/public_seed/workroot_client.py` | legacy Workroot client compatibility wrapper | `src/ai_workroot/runtime/legacy_seed/client.py` | legacy-quarantine | no | legacy client coverage, legacy CLI coverage | high; mature legacy capability |
| `scripts/legacy/public_seed/workroot_context.py` | legacy Context Guide compatibility wrapper | `src/ai_workroot/runtime/legacy_context.py` | legacy-quarantine | no | legacy context coverage | high; mature legacy context behavior |
| `scripts/legacy/public_seed/workroot_indexing.py` | legacy FTS compatibility wrapper | `src/ai_workroot/indexing/legacy_fts.py` | legacy-quarantine | no | legacy indexing coverage | medium |
| `scripts/legacy/public_seed/workroot_operation_manifest.py` | legacy operation manifest wrapper | `src/ai_workroot/runtime/legacy_seed/operation_manifest.py` | legacy-quarantine | no | `tests/smoke/test_cli_discovery.py`, architecture contract tests | medium |
| `scripts/legacy/public_seed/workroot_sqlite.py` | legacy SQLite compatibility wrapper | `src/ai_workroot/storage/legacy_sqlite.py` | legacy-quarantine | no | legacy SQLite coverage | medium |

## Current Clean Path

The active Clean Workroot path is:

```text
python -m ai_workroot init
python -m ai_workroot list
python -m ai_workroot status
python -m ai_workroot context
python -m ai_workroot doctor
python -m ai_workroot bootstrap-dev
```

The installed `workroot` wrapper points to `ai_workroot.cli.main:main`.

## Remaining Compatibility Boundary

The compatibility layer described in this 0.9.530 checkpoint is no longer active. Spec 041 removes runnable compatibility and keeps source snapshots under `docs/history/public-seed/code-archive/`.
