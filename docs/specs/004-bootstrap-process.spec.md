# Spec: Bootstrap Process

## Status

Draft

## Priority

P0

## Background

Bootstrap is a core AI Workroot concept. The system must be able to create its first managed state, evolve through migrations, verify through doctor, and then serve runtime commands. AI Workroot also needs a developer-only bootstrap workflow so the AI Workroot project can dogfood AI Workroot without turning Bootstrap Mode into a consumer product mode.

This Spec defines bootstrap phases and the `bootstrap-dev` workflow while preserving Clean Mode.

## Goals

- Create the first Workroot state through a controlled bootstrap process.
- Support developer-only bootstrap for the AI Workroot project repository.
- Keep bootstrap compatible with Clean Mode.
- Run migrations and doctor as part of bootstrap.
- Avoid automatic commits, tags, or release actions.

## Non-goals

- This Spec does not define general user onboarding copy beyond bootstrap commands.
- This Spec does not implement migrations.
- This Spec does not define Context Guide selection logic.
- This Spec does not create team collaboration or hosted bootstrap.

## Scope

### Included

- Bootstrap phases.
- First managed state creation.
- Developer-only `workroot bootstrap-dev`.
- Required bootstrap scripts.
- Relationship to migrations, doctor, and runtime.
- `.ai-workroot-local/` developer local review directory.

### Excluded

- Clean Mode init details, covered by `002-clean-mode-installation.spec.md`.
- Migration implementation details, covered by `005-migrations.spec.md`.
- Doctor checks, covered by `006-doctor-command.spec.md`.
- Release gates, covered by `014-release-and-test-gates.spec.md`.

## Dependencies

- Core project decisions: Clean Mode; managed state outside the user directory; controlled bootstrap; high-quality Context Guide; Materialized Context Candidates; local-first explainable retrieval without a P0 vector dependency; debug traces; branch-and-review Git workflow; English-first docs and comments.
- `001-project-structure-and-naming.spec.md`
- `002-clean-mode-installation.spec.md`
- `003-managed-state-layout.spec.md`
- `005-migrations.spec.md`
- `006-doctor-command.spec.md`
- `012-native-agent-entry.spec.md`
- `013-sqlite-cache-and-provenance-graph.spec.md`

## Requirements

### Functional Requirements

FR-001: Bootstrap must create AI Workroot home if it does not exist.

FR-002: Bootstrap must initialize global config and registry files.

FR-003: Bootstrap must initialize a per-Workroot managed state directory.

FR-004: Bootstrap must run pending migrations before runtime commands use the state.

FR-005: Bootstrap must run doctor after initialization and migrations.

FR-006: `workroot bootstrap-dev` must verify that the current directory is the AI Workroot Git repository before applying developer bootstrap behavior.

FR-007: `workroot bootstrap-dev` must register the current repository as a Clean Mode Workroot.

FR-008: `workroot bootstrap-dev` may create `.ai-workroot-local/` only as an explicit developer bootstrap artifact.

FR-009: `.ai-workroot-local/` must be added to `.gitignore` by the developer bootstrap workflow.

FR-010: Bootstrap must not automatically commit, tag, push, or create releases.

FR-011: Bootstrap must not create managed state inside the user directory except explicitly authorized Native Agent Entry files and developer-only `.ai-workroot-local/`.

FR-012: `workroot bootstrap-dev` must initialize per-Workroot SQLite at `<stateDirectory>/cache/workroot.sqlite` so `workroot context` and `workroot doctor` work immediately after bootstrap.

FR-013: `workroot bootstrap-dev` must use a real current UTC timestamp unless a test injects an explicit timestamp.

### Non-functional Requirements

NFR-001: Bootstrap must work without network access.

NFR-002: Bootstrap must be idempotent and safe to re-run.

NFR-003: Bootstrap must be explainable through doctor diagnostics.

NFR-004: Bootstrap must use local user permissions only.

NFR-005: Bootstrap must complete with clear failure messages when prerequisites are missing.

## Proposed Design

### Concepts

- System bootstrap: Creation of AI Workroot home and global managed state.
- Workroot bootstrap: Creation of one Workroot's managed state.
- Developer bootstrap: Explicit dogfooding workflow for the AI Workroot project repository.
- Runtime readiness: State has correct schema version, required files, SQLite tables, and doctor pass.

### Data Model

Bootstrap state marker:

```json
{
  "bootstrapVersion": "0.1",
  "workrootVersion": "0.9.529",
  "schemaVersion": "0.1",
  "mode": "clean",
  "createdAt": "2026-05-19T00:00:00Z",
  "lastDoctorStatus": "pass"
}
```

Developer local metadata is optional and must remain local-only:

```text
.ai-workroot-local/
  drafts/
  reviews/
  patches/
  context-packages/
```

### File Layout

Bootstrap writes managed state under:

```text
<AI_WORKROOT_HOME>/
<AI_WORKROOT_HOME>/workroots/<workrootId>/
```

Developer bootstrap may write:

```text
<repo>/.ai-workroot-local/
<repo>/.gitignore
<repo>/AGENTS.md
<repo>/CLAUDE.md
```

Only `AGENTS.md` and `CLAUDE.md` managed blocks are allowed as Native Agent Entry outputs. `.ai-workroot-local/` is developer-only and Git ignored.

### CLI / API

Required commands:

```bash
workroot bootstrap-dev
scripts/bootstrap-dev.sh
scripts/bootstrap-dev.ps1
```

Bootstrap phases:

```text
preflight
home-init
registry-init
workroot-state-init
sqlite-init
migration
native-agent-entry-sync
doctor
ready
```

### Runtime Behavior

`workroot bootstrap-dev` flow:

1. Verify current directory is the AI Workroot repository.
2. Verify CLI is installed or callable.
3. Resolve AI Workroot home.
4. Register current repository as a Clean Mode Workroot.
5. Initialize managed state outside the repository.
6. Initialize SQLite and graph tables.
7. Create `.ai-workroot-local/` for developer review materials.
8. Add `.ai-workroot-local/` to `.gitignore`.
9. Generate or update authorized Native Agent Entry managed blocks.
10. Run migrations.
11. Run doctor.

### Error Handling

- If the current directory is not the AI Workroot repository, abort.
- If Git is unavailable for developer bootstrap verification, abort with a prerequisite message.
- If `.gitignore` cannot be updated, fail before creating local review materials unless `--no-local-review-dir` is provided.
- If doctor fails, report state as initialized but not ready.
- If migrations fail, runtime readiness must remain false.

### Security / Privacy

Bootstrap must not expose private local paths in Native Agent Entry files. Developer local review materials must be Git ignored. Bootstrap must not call remote services.

### Compatibility

Bootstrap must tolerate existing AI Workroot public-seed files in the repository. It must treat the existing repository `.workroot/` as project source content, while 0.9.529 managed runtime state for the registered Workroot lives under AI Workroot home.

## Acceptance Criteria

AC-001:
Given AI Workroot home does not exist
When bootstrap runs
Then global config and registry directories are created in AI Workroot home.

AC-002:
Given the AI Workroot repository
When `workroot bootstrap-dev` runs
Then the repository is registered as a Clean Mode Workroot.

AC-003:
Given developer bootstrap completes
When the repository is inspected
Then managed state exists outside the repository.

AC-004:
Given developer bootstrap creates `.ai-workroot-local/`
When `.gitignore` is inspected
Then `.ai-workroot-local/` is ignored.

AC-005:
Given bootstrap completes
When doctor runs
Then doctor reports bootstrap state and schema state as passing.

AC-006:
Given bootstrap runs
When Git history is inspected
Then no commit, tag, push, or release was created by bootstrap.

## Test Plan

### Unit Tests

- Test repository verification logic.
- Test bootstrap phase ordering.
- Test idempotent bootstrap state marker behavior.
- Test `.gitignore` entry insertion.

### Integration Tests

- Run `workroot bootstrap-dev` in a temporary copy of the repository.
- Run bootstrap twice and verify no duplicate registry records.
- Run bootstrap with migration pending and verify doctor runs after migration.

### Manual Verification

- Run bootstrap on macOS/Linux.
- Run bootstrap script on Windows or in Windows CI.
- Inspect repository for only expected developer-local and Native Agent Entry changes.

## Migration / Rollback

Bootstrap must write a rollback journal. If bootstrap fails before registry commit, remove newly created empty managed state directories. If failure occurs after registry commit, mark bootstrap status as failed and provide `workroot doctor` repair instructions. `.gitignore` changes and Native Agent Entry managed blocks should be reversible by explicit repair or uninstall command, not silently removed.

## Observability / Debugging

Bootstrap must log phase timings and final doctor status to managed state. `workroot doctor` must show bootstrap readiness, migration status, SQLite readiness, Clean Mode boundary status, and Native Agent Entry status.

## Task Breakdown

T1: Add bootstrap preflight
- Change: Verify repository identity, CLI availability, path boundaries, and Git availability for developer bootstrap.
- Files likely affected: future bootstrap module, scripts.
- Verification: Unit tests for pass and fail preflight cases.

T2: Add bootstrap state creation
- Change: Initialize global and per-Workroot managed state.
- Files likely affected: state module, bootstrap module.
- Verification: Integration test inspects managed state.

T3: Add migration and doctor sequence
- Change: Run migrations before doctor and mark runtime readiness.
- Files likely affected: bootstrap module, migration module, doctor module.
- Verification: Integration test confirms ordering.

T4: Add developer local directory handling
- Change: Create `.ai-workroot-local/` and update `.gitignore`.
- Files likely affected: bootstrap module, scripts.
- Verification: Integration test confirms `.gitignore` entry.

T5: Add platform scripts
- Change: Add `scripts/bootstrap-dev.sh` and `scripts/bootstrap-dev.ps1`.
- Files likely affected: `scripts/`.
- Verification: Shellcheck or syntax validation where available, plus manual script run.

## Risks

- The existing repository contains public-seed `.workroot/`, which can confuse Clean Mode expectations.
- Developer bootstrap writes a local directory into the repository, which must remain explicitly developer-only.
- Re-running bootstrap must not duplicate registry entries or managed blocks.

## Open Questions

None.
