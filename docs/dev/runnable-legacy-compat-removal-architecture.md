# Runnable Legacy Compatibility Removal Architecture

## Status

Implemented closure document. This note is retained because release contracts still
verify that runnable Public Seed compatibility remains removed from active AI
Workroot paths.

## Purpose

Remove the runnable Public Seed compatibility layer from active AI Workroot paths
while preserving historical code as non-runnable archive material for review.

The target boundary is:

- active Clean Workroot behavior lives under `src/ai_workroot/`;
- active CLI users cannot invoke `workroot legacy ...`;
- active runtime, storage, indexing, doctor, release validation, scripts, and tests do not depend on legacy modules;
- old Public Seed code remains inspectable in history, but not importable or executable as a compatibility surface.

## Definitions

Active path:
Runtime code, CLI commands, package modules, scripts, tests, release gates, and current documentation that describe or execute Clean Workroot behavior.

Runnable legacy compatibility:
Any command, script, module, or default test path that keeps old Public Seed behavior executable after Clean Workroot replacements exist. Examples include `workroot legacy ...`, `scripts/legacy/public_seed/*.py`, `scripts/compat/workroot_cli.py`, and `src/ai_workroot/runtime/legacy_*`.

Historical archive:
Non-runnable material under `docs/history/` retained for review and migration reasoning. Archived code uses `.py.txt` so it is not importable, compiled, packaged, or treated as active source.

## Closure State

The active package no longer contains hidden legacy command dispatch. The former
compatibility chain through CLI, runtime, storage, and indexing legacy modules is
closed and retained only as historical archive material:

```text
docs/history/public-seed/code-archive/**/*.py.txt
```

The `scripts/` tree no longer exposes compatibility wrappers or
quarantined-but-runnable Public Seed entry points:

```text
scripts/compat/
scripts/legacy/public_seed/
scripts/dev/new_task_smoke.py
```

Tests and release docs validate the absence of those paths.

## Target State

### Source Package

Allowed active package structure:

```text
src/ai_workroot/
  entrypoints/
    cli/
    native_agent/
  commands/
  protocol/
  capabilities/
    composition/
    work/
    assets/
    relationships/
    retrieval/
    context/
    release/
    handoff/
    system_health/
  state/
  shared/
```

Disallowed active package content:

```text
src/ai_workroot/**/legacy_*.py
src/ai_workroot/runtime/legacy_seed/
src/ai_workroot/**/public_seed*
```

The active CLI owns only:

```text
init
list
status
context
doctor
bootstrap-dev
agent
```

`workroot legacy ...` is removed, not hidden.

### Scripts

Allowed active scripts:

```text
scripts/
  README.md
  dev/
    README.md
    bootstrap-dev.sh
    bootstrap-dev.ps1
    export-review-zip.sh
    validate-release.sh
```

Disallowed active scripts:

```text
scripts/compat/
scripts/legacy/
scripts/dev/new_task_smoke.py
```

Installers live under `install/unix/install.sh` and `install/windows/install.ps1`.

### Historical Archive

Historical code is preserved under:

```text
docs/history/public-seed/code-archive/
```

The archive includes:

```text
docs/history/public-seed/code-archive/MANIFEST.md
docs/history/public-seed/code-archive/**/*.py.txt
```

The archive is for inspection only:

- no tests import it;
- no scripts execute it;
- package discovery does not include it;
- active `py_compile` commands do not compile it;
- release validation treats it as historical documentation.

## Capability Parity Rules

Removing runnable compatibility must not remove current product capability. Each useful legacy capability must have an active owner or be explicitly retired.

| Legacy capability | Active owner | Status |
| --- | --- | --- |
| Task registry | `ai_workroot.capabilities.work`, `tasks` table | Preserved |
| Run registry | `task_runs` table and protocol projection APIs | Preserved |
| Action registry | `protocol_events`, task items, and projected work facts | Preserved |
| Artifact registry | `ai_workroot.capabilities.assets`, `assets` tables | Preserved |
| Decision records | Asset records with decision/result types | Preserved |
| Retrieval card registry | ContextRecallHint and retrieval/index providers | Preserved/renamed |
| Checkpoint registry | Task run progress, handoff, and projected state | Preserved |
| Invalidation registry | Release Control and invalidation records | Preserved |
| Mind registry | Assets, ContextRecallHint, Relationship Network | Preserved as active concepts; old name retired |
| Link registry | Relationship Network | Preserved/renamed |
| Batch rollback | `operation_transactions`; full CLI deferred | Partially preserved/deferred |
| Session summarize / continue | Handoff and Context Control state | Preserved/deferred UX |
| Context policy | Context Control runtime hints and budgets | Preserved |
| Forgetting / tombstone / redaction / deletion | Release Control | Preserved |
| Storage policy | `ai_workroot.state`, SQLite, JSONL logs, and runtime views | Preserved |
| Permission/privacy/globalization/extension policies | Active docs, protocol contracts, and shared contracts | Preserved |
| Global index/cache | `ai_workroot.capabilities.retrieval.global_indexes`, environment layout | Preserved |
| Agent startup/interface | `ai_workroot.entrypoints.native_agent`, templates, and Agent Protocol | Preserved |
| Retrieval interface | Retrieval contracts and providers | Preserved |
| MCP/export/import | Not active in current release | Deferred |
| Legacy Public Seed CLI | No active owner | Retired |
| Legacy kernel validator | Release doctor and `scripts/dev/validate-release.sh` | Replaced |

If a required product behavior is found to lack an active owner, this branch should add or repair active Clean Workroot behavior. It must not keep runnable legacy compatibility as a fallback.

## Test Strategy

Boundary tests control this branch:

- package import boundary: `src/ai_workroot` has no active legacy modules;
- import boundary: active source has no `legacy_*`, `legacy_seed`, or `public_seed` imports;
- CLI boundary: `python -m ai_workroot legacy --help` fails;
- scripts boundary: `scripts/compat` and `scripts/legacy` do not exist;
- release gate boundary: `scripts/dev/validate-release.sh` does not call legacy validators;
- docs boundary: active docs do not promise runnable legacy compatibility;
- archive boundary: historical code exists as `.py.txt` with a manifest;
- capability smoke: Clean Workroot init/list/status/context/doctor/bootstrap-dev still work.

E2E remains opt-in and is not part of default validation unless explicitly requested.

## Migration Plan

1. Add formal Spec and implementation plan.
2. Add failing negative tests for the new boundaries.
3. Remove `workroot legacy` dispatch from active CLI.
4. Archive package legacy modules as `.py.txt`, then remove them from `src/ai_workroot`.
5. Archive or remove runnable legacy scripts from `scripts/compat` and `scripts/legacy`.
6. Rewrite release gates and docs.
7. Migrate tests that validate active behavior to package modules.
8. Retire tests that only validate removed compatibility behavior.
9. Run full validation.

## Rollback

Rollback is a branch revert before merge. The branch should not keep a partial compatibility state where `workroot legacy` is gone but tests/docs still depend on runnable legacy code, or where legacy modules are archived but active behavior lacks replacement tests.

## Acceptance Criteria

- `PYTHONPATH=src python3 -m ai_workroot --help` shows only Clean Workroot commands.
- `PYTHONPATH=src python3 -m ai_workroot legacy --help` fails as unknown command.
- `find src/ai_workroot -path '*legacy*' -o -name '*legacy*'` returns no active package files.
- `scripts/compat` and `scripts/legacy` do not exist.
- `scripts/dev/validate-release.sh` runs only active Clean Workroot validation.
- Default unit discovery passes without importing legacy modules.
- Historical code archive exists and is non-runnable.
- Clean Workroot smoke tests pass.
- No version bump, tag, release, or merge occurs in this branch.
