# Scripts to Source Migration Status

## Status

0.9.530 is an architecture alignment checkpoint, not the final scripts-to-source migration.

The final migration has two explicitly named phases:

- The package-ownership phase completes package ownership while preserving existing script and legacy CLI compatibility.
- The Compatibility Removal phase removes or narrows compatibility in a later branch/version after separate approval.

Clean Workroot active runtime should move toward `src/ai_workroot/` as the product implementation. The `scripts/` directory is being narrowed to wrappers, development tools, validation tools, and legacy Public Seed compatibility. Legacy capability must remain preserved until it is explicitly mapped, tested, and replaced.

The full completion design for the remaining migration is now split into:

- `scripts-to-src-migration-architecture.md`
- `scripts-to-src-migration-detailed-design.md`
- `docs/specs/023-active-package-cli-and-legacy-isolation.spec.md`
- `docs/specs/024-work-and-asset-runtime-migration.spec.md`
- `docs/specs/025-storage-and-migrations-migration.spec.md`
- `docs/specs/026-retrieval-indexing-and-context-control-migration.spec.md`
- `docs/specs/027-release-relationship-and-safety-migration.spec.md`
- `docs/specs/028-system-health-validation-and-checkbot.spec.md`
- `docs/specs/029-install-dev-scripts-and-wrappers.spec.md`
- `docs/specs/030-test-suite-and-public-seed-quarantine.spec.md`

## Migration Rules

- Clean user-facing commands should be available through `python -m ai_workroot` and the installed `workroot` wrapper.
- `scripts/bootstrap-dev.sh` and `scripts/install.sh` are wrappers and may remain.
- Public Seed and historical tools must be labeled as legacy where they are not part of Clean Workroot active architecture.
- Do not remove legacy task/run/action/session/handoff capabilities until replacement modules and tests exist.
- Do not remove old script compatibility in Part 1; convert scripts to wrappers or compatibility adapters instead.
- Archiving script implementations under `docs/history/0.9.530/scripts/` preserves snapshots only. It does not remove the callable script wrapper in Part 1.
- Do not reintroduce root `space/`, root `.workroot/`, root tracked `AGENTS.md`, or root tracked `CLAUDE.md` as active architecture.

## File Matrix

| Script | Current role | Target module or disposition | Status | Risk | Current tests | Migration priority |
|---|---|---|---|---|---|---|
| `scripts/add_registry_row.py` | Historical registry maintenance helper | Legacy Public Seed support or `src/ai_workroot/storage/` maintenance command | Legacy retained | Could mutate old registry layout if used as Clean path | Legacy kernel/release tests | P2 |
| `scripts/list_tasks.py` | Historical task listing helper | Legacy command under future `workroot legacy task list` or retired after Work module migration | Legacy retained; active Work runtime started | Old task registry semantics may confuse Clean Workroot users | Legacy task tests; `tests/unit/test_runtime_work.py` | P1 |
| `scripts/new_task.py` | Historical task creation helper | Minimal Work service now exists under `src/ai_workroot/runtime/work.py`; legacy helper remains compatibility-scoped | Legacy retained; active path started | Creates Public Seed task files, not Clean Workroot state | Legacy public-seed tests; `tests/unit/test_runtime_work.py` | P1 |
| `scripts/new_task_smoke.py` | Historical smoke helper | Move under `tests/fixtures` or retire after test split | Deferred | Test-like helper can be mistaken for active product code | Release surface audit | P2 |
| `scripts/rebuild_sqlite.py` | Legacy public-seed SQLite rebuild tool | Historical compatibility only | Legacy labeled | Must not be documented as Clean Workroot setup | 0.9.529 release gates | P2 |
| `scripts/setup_workroot.py` | Historical setup helper | Superseded by `ai_workroot.runtime.init` for Clean Workroot | Legacy retained | May create old layout if used directly | Legacy tests | P2 |
| `scripts/update_usage_direction.py` | Historical profile helper | Future Agent/User preference runtime service | Legacy retained | Writes Public Seed profile files | Legacy profile tests | P2 |
| `scripts/upgrade_workroot.py` | Historical upgrade helper | Future migration adapter if still needed | Deferred | Could imply Public Seed active migration path | Legacy tests | P3 |
| `scripts/validate_kernel.py` | Release validation and historical contract checks | Keep as release/dev validation tool | Active dev tool | Must distinguish historical checks from Clean Workroot release gates | `tests/test_0529_release_gates.py`, smoke validator | P1 |
| `scripts/workroot_agent_entry.py` | 0.9.529 native entry implementation | Superseded by `src/ai_workroot/agent/native_entry.py` | Legacy retained | Duplicate behavior can drift | Native Agent Entry tests | P1 |
| `scripts/workroot_bootstrap.py` | 0.9.529 bootstrap implementation | Superseded by `src/ai_workroot/runtime/bootstrap.py`; keep only for legacy CLI compatibility | Legacy retained | Old Public Seed repo identity checks must not be Clean path | Bootstrap-dev tests use package and wrapper path | P1 |
| `scripts/workroot_candidates.py` | 0.9.529 context candidate provider | Superseded by `src/ai_workroot/indexing/providers/candidate_provider.py` | Partial migration | Old and new candidate semantics can diverge | Context tests | P1 |
| `scripts/workroot_cli.py` | Legacy CLI with hidden Public Seed commands and some clean commands | Clean commands should delegate to `ai_workroot.cli.main`; legacy commands move under future `workroot legacy` | Partial migration | Users may invoke old clean flow directly | CLI and bootstrap compatibility tests | P0 |
| `scripts/workroot_client.py` | Mature Public Seed task/run/action/artifact client | Minimal Work/Asset/Release/Relationship services now exist under `src/ai_workroot/runtime/`; legacy client remains compatibility-scoped | Active path started; compatibility retained | Highest legacy capability loss risk until legacy CLI surfaces are fully mapped | Legacy client tests; runtime service tests | P0 |
| `scripts/workroot_context.py` | Mature 0.9.529 Context Guide | Partially superseded by `src/ai_workroot/runtime/context.py`; ContextRecallHint materialization now active | Partial migration | Context behavior regression risk | Context, indexing, ContextRecallHint, release-filter tests | P0 |
| `scripts/workroot_doctor.py` | 0.9.529 doctor | Superseded by `src/ai_workroot/runtime/doctor.py`; keep as legacy compatibility until script CLI migration | Partial migration | Old doctor checks may imply old architecture | Doctor tests | P1 |
| `scripts/workroot_indexing.py` | 0.9.529 FTS/indexing | Partially superseded by `src/ai_workroot/indexing/providers/sqlite_fts.py`, `context_recall_hint_provider.py`, and `global_indexes.py` | Partial migration | Duplicate FTS/index schemas must stay explicitly scoped | Indexing, ContextRecallHint, global index tests | P1 |
| `scripts/workroot_migrations.py` | 0.9.529 migrations | Future `src/ai_workroot/storage/migrations.py` | Deferred | Old migration assumptions may not fit Clean schema | Migration tests | P2 |
| `scripts/workroot_operation_manifest.py` | Legacy operation manifest/recipes | Preserve as legacy capability registry input or move to contracts later | Deferred | Operation recipes still reference old script commands | Architecture contract tests | P2 |
| `scripts/workroot_paths.py` | 0.9.529 path/state resolution | Superseded by `src/ai_workroot/runtime/bootstrap.py`, `runtime/environment.py`, and `runtime/registry.py` | Partial migration | Path rules must stay Clean Mode compatible | Init/bootstrap tests | P1 |
| `scripts/workroot_sqlite.py` | 0.9.529 SQLite schema | Superseded by `src/ai_workroot/storage/sqlite.py`; retain for legacy tests | Partial migration | Old schema includes historical `knowledge_items` table | SQLite/indexing tests | P1 |
| `scripts/workroot_state.py` | 0.9.529 managed state registry | Superseded by `src/ai_workroot/runtime/environment.py` and `storage/jsonl_registry.py` | Partial migration | Registry concurrency and duplicate handling must stay protected | Registry/bootstrap tests | P1 |

## Current Clean Path

The current Clean Workroot path is:

```text
python -m ai_workroot init
python -m ai_workroot list
python -m ai_workroot status
python -m ai_workroot context
python -m ai_workroot doctor
python -m ai_workroot bootstrap-dev
```

The installed `workroot` wrapper points to the same package entry point.

## Deferred Work

- Continue moving mature Work/Asset/operation logic from `scripts/workroot_client.py` into `src/ai_workroot/`; minimal active runtime services now exist, but legacy CLI parity is not complete.
- Convert `scripts/workroot_cli.py` clean commands into thin package delegation or isolate legacy commands under `legacy`.
- Split the old Context Guide into Context Control, Retrieval & Index Control, and trace persistence modules.
- Keep unit, integration, smoke, negative, legacy compatibility, and release validation discoverable through the default test command.
- Add a clean review/export packaging command that excludes ignored local state.
