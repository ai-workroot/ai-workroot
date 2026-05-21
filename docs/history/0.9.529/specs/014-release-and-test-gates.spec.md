# Spec: Release and Test Gates

## Status

Draft

## Priority

P0

## Background

AI Workroot 0.9.529 changes core product behavior, storage layout, bootstrap, CLI, Context Guide, SQLite, and Clean Mode guarantees. Release must be gated by automated tests, manual verification, documentation review, and explicit version or tag decisions.

## Goals

- Define what must pass before 0.9.529 release.
- Define required test categories.
- Define manual Clean Mode and bootstrap verification.
- Define documentation requirements.
- Define version and tag decision criteria.
- Preserve branch, review, merge, and push discipline.

## Non-goals

- This Spec does not create a release.
- This Spec does not create branches, commits, tags, or pushes.
- This Spec does not define implementation plans.
- This Spec does not replace individual feature Specs.

## Scope

### Included

- Release readiness gates.
- Test categories.
- Manual verification.
- Documentation gate.
- Version and tag decision rules.
- Git workflow expectations.

### Excluded

- Concrete feature implementation details, covered by Specs 001 through 013.
- CI provider configuration unless added during implementation.
- Release notes content beyond required topics.

## Dependencies

- Core project decisions: Clean Mode; managed state outside the user directory; controlled bootstrap; high-quality Context Guide; Materialized Context Candidates; local-first explainable retrieval without a P0 vector dependency; debug traces; branch-and-review Git workflow; English-first docs and comments.
- `001-project-structure-and-naming.spec.md`
- `002-clean-mode-installation.spec.md`
- `003-managed-state-layout.spec.md`
- `004-bootstrap-process.spec.md`
- `005-migrations.spec.md`
- `006-doctor-command.spec.md`
- `007-context-guide-builder.spec.md`
- `008-materialized-context-candidates.spec.md`
- `009-fts-indexing-and-retrieval.spec.md`
- `010-debug-trace-and-observability.spec.md`
- `011-cli-user-flows.spec.md`
- `012-native-agent-entry.spec.md`
- `013-sqlite-cache-and-provenance-graph.spec.md`
- `015-context-guide-modes-budgets-and-confidence.spec.md`

## Requirements

### Functional Requirements

FR-001: Release gate must include automated unit tests for path resolution, Clean Mode guards, migrations, doctor, context selection, candidates, FTS, debug traces, Native Agent Entry, and SQLite graph.

FR-002: Release gate must include integration tests for install, init, context, doctor, and bootstrap-dev.

FR-003: Release gate must include manual verification that user directories remain clean by default.

FR-004: Release gate must verify no vector database or embedding provider is required for P0.

FR-005: Release gate must verify Context Guide hot path makes no remote calls.

FR-006: Release gate must verify docs and CLI copy use Workroot terminology.

FR-007: Release gate must verify no generated caches, SQLite files, debug traces, local metadata, or private residue are included in public release artifacts unless explicitly intended.

FR-008: Any version bump or tag must have an explicit reason and approval before execution.

FR-009: Meaningful implementation changes must happen on a branch, be reviewed, then merged to main and pushed.

FR-010: Bootstrap must not auto-commit, auto-tag, or auto-release.

FR-011: Release gate must verify Context Guide latency and token budgets are loaded from runtime hints or built-in defaults, not scattered hardcoded constants.

FR-012: Release gate must verify Context Packages include mode, confidence, latency, token usage, and fallback metadata.

FR-013: Release gate must verify Codex, Claude, and default agent budgets are represented and bounded.

FR-014: Release gate must verify Deep Mode is explicit and not used silently in normal startup.

FR-015: Release gate must verify `AGENTS.md` and `CLAUDE.md` remain short launcher files and do not embed full Context Packages.

### Non-functional Requirements

NFR-001: Release checks must be repeatable.

NFR-002: Release checks must produce actionable failure messages.

NFR-003: Release process must protect local-first and privacy guarantees.

NFR-004: Release process must avoid unnecessary scope expansion beyond P0 and critical P1.

NFR-005: Release docs must be English-first.

## Proposed Design

### Concepts

- Release candidate: A state that has passed automated tests and is ready for manual verification.
- Release gate: Required checks before version bump, tag, or publication.
- Version decision: Explicit maintainer decision to bump version or create tag.
- Test gate: Automated and manual checks mapped to Specs.

### Data Model

Release checklist item:

```json
{
  "id": "clean-mode-default-no-user-state",
  "category": "manual",
  "status": "pass",
  "evidence": "temporary init directory inspected",
  "checkedAt": "2026-05-19T00:00:00Z"
}
```

### File Layout

Release artifacts and docs may live in:

```text
CHANGELOG.md
docs/release-checklist.md
docs/specs/
tests/
```

Generated files must be excluded from public release surface:

```text
*.sqlite
*.sqlite3
*.db
*.duckdb
*.wal
global-cache/
cache/
logs/
context/debug/
.ai-workroot-local/
```

### CLI / API

Release validation may use:

```bash
python3 -m pytest
python3 scripts/validate_kernel.py
workroot doctor
workroot context --agent codex --cwd . --debug
```

Exact implementation commands may differ after CLI packaging, but gates must remain equivalent.

### Runtime Behavior

Release flow:

1. Create a branch for implementation work.
2. Implement P0 and critical P1 scope in reviewable steps.
3. Run automated tests.
4. Run Clean Mode manual verification.
5. Run bootstrap-dev manual verification.
6. Review docs and CLI copy.
7. Review diff for generated/private files.
8. Decide whether version bump or tag is needed.
9. Only after explicit approval, commit, merge, push, and tag as appropriate.

### Error Handling

- If any P0 gate fails, release candidate is blocked.
- If manual verification cannot be performed on an OS, record it as a known gap rather than claiming pass.
- If generated files appear in public release surface, block release.
- If version/tag rationale is missing, block tag creation.

### Security / Privacy

Release gate must scan for secrets, private local paths, generated state, SQLite databases, debug traces, and local review materials. Native Agent Entry templates must not include private paths or IDs.

### Compatibility

Release gate must verify macOS/Linux behavior and include Windows script syntax or CI verification. Future XDG migration is out of P0 but should not be blocked by current defaults.

## Acceptance Criteria

AC-001:
Given a release candidate
When automated tests run
Then all P0 unit and integration tests pass before release approval.

AC-002:
Given Clean Mode init
When manual verification inspects the user directory
Then no managed state files or folders are present by default.

AC-003:
Given Context Guide hot path
When release verification runs
Then no remote LLM, remote embedding, vector database, or full user directory scan is required.

AC-004:
Given developer bootstrap
When manual verification runs
Then `.ai-workroot-local/` is Git ignored and no commit or tag is created automatically.

AC-005:
Given a proposed tag or version bump
When release review occurs
Then the rationale is documented and explicitly approved before execution.

## Test Plan

### Unit Tests

- Path resolver tests.
- Clean Mode guard tests.
- Migration runner tests.
- Doctor check tests.
- Context Guide scoring and filtering tests.
- Context Guide mode, confidence, runtime hints, and budget tests.
- Candidate lifecycle tests.
- FTS chunking and search tests.
- Debug trace schema tests.
- Native Agent Entry merge tests.
- SQLite graph tests.

### Integration Tests

- Install script smoke test where feasible.
- `workroot init` Clean Mode test.
- `workroot context` package generation test.
- `workroot context --debug` trace test.
- `workroot context --mode quality --debug` trace test.
- `workroot context --deep` explicit request test.
- Agent-specific token budget test.
- `workroot doctor` healthy and unhealthy fixture tests.
- `workroot bootstrap-dev` preflight and temporary-repo test.

### Manual Verification

- Fresh install on macOS/Linux.
- Windows install or script syntax check.
- Clean Mode init with Native Agent Entry declined.
- Clean Mode init with Native Agent Entry authorized.
- Bootstrap-dev on the AI Workroot repository.
- Diff review for generated state, private paths, and terminology.
- Inspect Native Agent Entry files for short launcher behavior.
- Inspect Context Package metadata for mode, confidence, latency, token usage, and fallback status.

## Migration / Rollback

Release rollback follows Git workflow. If release work is not approved, do not merge. If a tag has not been pushed, delete it locally only with explicit approval. If a published release tag exists, do not move it casually; create a corrective release or follow an explicitly approved emergency procedure.

## Observability / Debugging

Release evidence should include:

- test command outputs;
- doctor output;
- context debug trace summary;
- context mode, confidence, and token budget summary;
- manual verification notes;
- generated/private file scan results;
- version/tag rationale if applicable.

## Task Breakdown

T1: Add automated release checks
- Change: Ensure tests cover each P0 feature boundary, including context modes, confidence, runtime hints, and agent budgets.
- Files likely affected: `tests/`, validation scripts.
- Verification: Full test suite passes.

T2: Add generated file scan
- Change: Validate public release surface excludes caches, SQLite, debug traces, logs, and local metadata.
- Files likely affected: validation scripts.
- Verification: Fixture test catches generated files.

T3: Add manual checklist
- Change: Update release checklist with Clean Mode, bootstrap, context mode/budget/confidence, short entry files, and no-vector checks.
- Files likely affected: `docs/release-checklist.md`.
- Verification: Checklist reviewed against Specs.

T4: Add terminology gate
- Change: Scan docs and CLI help for forbidden product positioning in new release surfaces.
- Files likely affected: validation scripts, tests.
- Verification: Test fails on forbidden phrase in new docs.

T5: Add version/tag approval gate
- Change: Document criteria for version bump or tag.
- Files likely affected: release docs.
- Verification: Manual review confirms no tag action without approval.

## Risks

- Release scope can expand if P1 and future commands are pulled into P0.
- Existing legacy docs may trigger terminology scans unless scans are scoped carefully.
- Manual verification can be skipped under time pressure without a hard checklist.
- SQLite or debug files may accidentally enter release artifacts.

## Open Questions

None.
