# Spec: Runnable Legacy Compatibility Removal

## Status

Draft

## Priority

P0

## Background

AI Workroot 0.9.530 moved the active architecture to Clean Workroot. Before this removal work, the repository still included a runnable legacy Public Seed compatibility layer: the active CLI accepted a hidden `workroot legacy ...` command, package modules under `src/ai_workroot` implemented legacy behavior, and scripts/tests/docs treated compatibility as available.

This Spec removes runnable legacy compatibility while preserving historical Public Seed code as non-runnable archive material for review.

## Goals

- Remove all active package imports and modules for runnable legacy compatibility.
- Remove `workroot legacy ...` from the package CLI.
- Remove runnable legacy and compatibility script surfaces.
- Keep historical Public Seed code available as non-runnable archive material.
- Preserve active Clean Workroot capability through active modules and tests.
- Update docs, release gates, and tests to match the new boundary.

## Non-goals

- Do not bump the project version.
- Do not create a tag or release.
- Do not merge this branch into `main`.
- Do not delete historical Public Seed knowledge.
- Do not migrate real user directories.
- Do not introduce MCP, vector databases, remote embeddings, or remote LLM dependencies.
- Do not preserve runnable legacy compatibility.

## Scope

### Included

- Active CLI legacy command removal.
- Package legacy module archival and removal from active source.
- Script compatibility and Public Seed runtime surface removal.
- Test migration from compatibility assertions to active boundary and capability assertions.
- Documentation and release validation updates.
- Historical non-runnable archive manifest.

### Excluded

- New product CLI for every retired legacy operation.
- Automatic Public Seed to Clean Workroot data migration.
- Long E2E execution unless separately requested.
- Changes to release publication.

## Dependencies

- `023-active-package-cli-and-legacy-isolation.spec.md`
- `031-compatibility-preserving-script-migration.spec.md`
- `032-part2-capability-parity-small-specs.spec.md`
- `038-active-context-control-parity-hardening.spec.md`
- `040-0530-focused-hardening.spec.md`
- `docs/dev/runnable-legacy-compat-removal-architecture.md`

## Requirements

### Functional Requirements

FR-001: The package CLI must not define, hide, dispatch, or delegate a `legacy` command.

FR-002: `python -m ai_workroot legacy --help` must fail as an unknown command.

FR-003: Active package source under `src/ai_workroot` must not contain `legacy_*.py`, `runtime/legacy_seed`, or Public Seed compatibility modules.

FR-004: Active package source must not import modules whose import path contains `.legacy_`, `.legacy_seed`, or `.public_seed`.

FR-005: `scripts/compat` and `scripts/legacy` must not exist as runnable compatibility surfaces.

FR-006: Historical legacy code must be archived under `docs/history/public-seed/code-archive` using non-runnable file names.

FR-007: The historical archive must include a manifest listing original paths, archived paths, and active replacement or retirement status.

FR-008: Release validation must not call `scripts/compat/validate_kernel.py` or any legacy Public Seed script.

FR-009: Default tests must not import legacy modules.

FR-010: Active Clean Workroot init/list/status/context/doctor/bootstrap-dev flows must continue to work.

FR-011: Active docs must state that runnable legacy compatibility has been removed from active paths.

FR-012: Historical docs may mention legacy/Public Seed as history, but must not present runnable compatibility as current behavior.

### Non-functional Requirements

NFR-001: The removal must keep the active package standard-library-only.

NFR-002: Tests must not depend on a real user home, GitHub, SSH, or global environment.

NFR-003: Historical archive files must not be included in package discovery or py_compile active source commands.

NFR-004: The implementation must be reviewable in small file groups.

NFR-005: The branch must remain unreleased until explicitly approved.

## Proposed Design

### Concepts

Runnable legacy compatibility:
A still-executable old Public Seed path kept for backwards compatibility after Clean Workroot replacement exists.

Historical archive:
Non-runnable source snapshots stored for review and migration reasoning. Archive files are not active source.

Active owner:
The Clean Workroot module or concept that owns a capability formerly covered by Public Seed scripts.

### Data Model

No runtime schema migration is required for compatibility removal. Existing active SQLite schema stays authoritative.

The archive manifest is Markdown:

```text
| Original path | Archived path | Active replacement | Status |
```

Status values:

- archived-only
- replaced
- retired
- deferred-active-cli

### File Layout

Allowed active layout after this Spec:

```text
src/ai_workroot/
install/
scripts/dev/
tests/
docs/history/public-seed/code-archive/
```

Disallowed active layout after this Spec:

```text
src/ai_workroot/**/legacy_*.py
src/ai_workroot/runtime/legacy_seed/
scripts/compat/
scripts/legacy/
```

### CLI / API

Active command set:

```text
workroot init
workroot list
workroot status
workroot context
workroot doctor
workroot bootstrap-dev
```

Removed command set:

```text
workroot legacy ...
scripts/compat/workroot_cli.py
scripts/legacy/public_seed/*.py
```

### Runtime Behavior

Clean Workroot runtime behavior continues through:

- `ai_workroot.commands.init_workroot`
- `ai_workroot.state.registry`
- `ai_workroot.capabilities.context.builder`
- `ai_workroot.capabilities.system_health.doctor`
- `ai_workroot.commands.bootstrap_dev`
- `ai_workroot.capabilities.work.operations`
- `ai_workroot.capabilities.assets.operations`
- `ai_workroot.capabilities.release.operations`
- `ai_workroot.capabilities.relationships.operations`
- `ai_workroot.state.sqlite`
- `ai_workroot.capabilities.retrieval.providers.*`

No runtime fallback to legacy code is allowed.

### Error Handling

Calling a removed command uses normal argparse behavior:

```text
invalid choice: 'legacy'
```

The CLI does not offer a compatibility replacement for legacy commands.

### Security / Privacy

Removing runnable compatibility reduces accidental writes to old `space/ + .workroot/` layouts. Clean Mode still prevents generated runtime state from being written into user-selected directories unless explicitly authorized through Native Agent Entry files.

### Compatibility

This Spec intentionally removes backwards runtime compatibility for legacy Public Seed commands. Historical source remains archived. Users who need old behavior must use a previous tag or inspect the archive.

## Acceptance Criteria

AC-001:
Given the active package CLI
When `PYTHONPATH=src python3 -m ai_workroot --help` runs
Then only Clean Workroot commands are shown.

AC-002:
Given the active package CLI
When `PYTHONPATH=src python3 -m ai_workroot legacy --help` runs
Then the command exits non-zero with an invalid command error.

AC-003:
Given the source package
When active package files are scanned
Then no active file path contains `legacy`.

AC-004:
Given active package Python files
When import statements are scanned
Then none import legacy or public-seed modules.

AC-005:
Given the scripts tree
When scripts are listed
Then no `scripts/compat` or `scripts/legacy` directory exists.

AC-006:
Given the historical archive
When archive files are listed
Then old legacy code exists as `.py.txt` files with a manifest.

AC-007:
Given release validation
When `scripts/dev/validate-release.sh` runs
Then it does not call legacy validators or compatibility scripts.

AC-008:
Given a temporary Clean Workroot
When init/list/status/context/doctor are run
Then state stays outside the user directory and commands pass.

AC-009:
Given bootstrap-dev
When it runs in a temporary repo copy with temporary `AI_WORKROOT_HOME`
Then SQLite initializes and context/doctor work.

## Test Plan

### Unit Tests

- Import boundary test for no active legacy modules.
- Import boundary test for no active legacy imports.
- CLI parser test for unknown `legacy`.
- Archive manifest test for expected archived files.
- Release doctor test for no active legacy paths.

### Integration Tests

- Clean Workroot init/list/status/context/doctor through `python -m ai_workroot`.
- Bootstrap-dev through `scripts/dev/bootstrap-dev.sh`.
- Release validation through `scripts/dev/validate-release.sh`.

### Manual Verification

- Inspect `docs/history/public-seed/code-archive/MANIFEST.md`.
- Inspect `python -m ai_workroot --help`.
- Inspect changed docs for current architecture wording.

## Migration / Rollback

No runtime data migration is required. Rollback is a branch revert before merge. If a required active capability is missing, add active implementation and tests rather than restoring runnable legacy compatibility.

## Observability / Debugging

Release doctor and boundary tests provide debugging output:

- active legacy path findings;
- import boundary failures;
- release surface failures;
- Clean Workroot smoke command output.

## Task Breakdown

T1: Add legacy removal design and Spec
- Change: Add architecture and Spec docs.
- Files likely affected: `docs/dev/runnable-legacy-compat-removal-architecture.md`, `docs/specs/041-runnable-legacy-compat-removal.spec.md`.
- Verification: Docs exist and are referenced by implementation plan.

T2: Add failing boundary tests
- Change: Replace compatibility-preserving tests with legacy-removal boundary tests.
- Files likely affected: `tests/unit/test_import_boundaries.py`, split repository/docs contract tests under `tests/contracts/`, `tests/smoke/test_cli_discovery.py`.
- Verification: New tests fail against current runnable legacy code.

T3: Remove active CLI legacy dispatch
- Change: Delete hidden `legacy` parser and dispatcher.
- Files likely affected: `src/ai_workroot/entrypoints/cli/main.py`.
- Verification: `python -m ai_workroot legacy --help` exits non-zero.

T4: Archive package legacy modules
- Change: Move legacy source snapshots to non-runnable archive and delete active package modules.
- Files likely affected: `src/ai_workroot/**/legacy*`, `docs/history/public-seed/code-archive/*`.
- Verification: Active package scan finds no legacy paths.

T5: Remove runnable legacy scripts
- Change: Remove `scripts/compat`, `scripts/legacy`, and legacy dev smoke.
- Files likely affected: `scripts/*`, `scripts/dev/validate-release.sh`.
- Verification: Scripts boundary tests pass.

T6: Migrate tests and docs
- Change: Remove or rewrite tests that assert compatibility availability; update docs/release checklist.
- Files likely affected: `tests/*`, `README.md`, `ROADMAP.md`, `docs/release-checklist.md`, `docs/architecture/*`, `docs/history/0.9.530/dev/*`.
- Verification: Default unittest discovery passes.

T7: Full validation
- Change: None unless validation finds issues.
- Files likely affected: any failing boundary.
- Verification: Run full command set from this Spec.

## Risks

- A useful legacy behavior may not yet have an active owner.
- Tests may accidentally be deleted instead of migrated to active behavior.
- Historical archive may be mistaken for active code if `.py` extensions remain.
- Docs may retain compatibility language and confuse reviewers.
- Shell scripts may still reference removed paths.

## Open Questions

None. The implementation boundary is: no runnable legacy compatibility; preserve non-runnable historical archive.
