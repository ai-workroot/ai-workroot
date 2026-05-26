# Spec: 0.9.530 Focused Hardening

## Status

Accepted for 0.9.530; legacy-command requirement superseded by `041-runnable-legacy-compat-removal.spec.md`

## Priority

P1

## Background

0.9.530 has completed the Clean Workroot architecture reset in broad form: active product implementation lives under `src/ai_workroot/`, Public Seed is quarantined, legacy capability is preserved, Context Control is local-first, and Release Control is enforced across active context paths.

Final review found several focused hardening gaps. These gaps do not require a new architecture direction, but they do affect milestone confidence, release safety, E2E safety semantics, and documentation consistency.

## Goals

- Make release validation fast and deterministic.
- Close direct `context_recall_hint` release/redaction/deletion leakage in derived indexes.
- Align E2E harness behavior with sandbox, opt-in, and user-owned directory rules.
- Make Relationship Network release target mapping explicit and robust.
- Remove active-looking stale script plans and local absolute paths from current docs.
- Keep this pass small, test-driven, and compatible with existing legacy capability.

## Non-goals

- Do not redesign the 0.9.530 architecture.
- Do not add MCP implementation.
- Do not add vector database, remote embedding, or remote LLM dependency.
- Do not lose useful Public Seed era capabilities; runnable legacy compatibility removal is governed by Spec 041.
- Do not add broad SQLite foreign-key enforcement in this pass.
- Do not expose a full Work/Asset/Release/Relationship product CLI in this pass.
- Do not run long E2E unless explicitly requested.

## Scope

### Included

- Release surface validation and release doctor performance.
- Release-derived index safety for direct `context_recall_hint` targets.
- E2E runner and harness safety semantics.
- Relationship node canonical target mapping.
- Docs/plans cleanup for active architecture consistency.
- Minor CLI/help and test warning cleanup where directly related.

### Excluded

- Compatibility removal.
- Full authoring CLI.
- Heavy schema redesign.
- Live-agent E2E execution.
- GUI or installer redesign.

## Dependencies

- `028-system-health-validation-and-checkbot.spec.md`
- `031-compatibility-preserving-script-migration.spec.md`
- `036-e2e-sandbox-and-destructive-operation-safety.spec.md`
- `037-release-derived-index-safety-hardening.spec.md`
- `038-active-context-control-parity-hardening.spec.md`
- `039-publication-authoring-index-doctor-hardening.spec.md`

## Requirements

### Functional Requirements

FR-001: Release surface validation must use Git-native file lists instead of recursively scanning the entire worktree and calling `git check-ignore` per file.

FR-002: Release doctor must not traverse `.git`.

FR-003: Release doctor must still reject tracked or unignored generated stores, generated managed state, local metadata, and private residue.

FR-004: Direct strict release targets of type `context_recall_hint` must sanitize `context_recall_hints`, `context_recall_hints_fts`, materialized hint candidates, and candidate FTS rows.

FR-005: Doctor release-derived index safety must detect direct `context_recall_hint` leaks.

FR-006: E2E suites must remain opt-in only through `AI_WORKROOT_RUN_E2E=1`.

FR-007: E2E runner must create or report a preserved sandbox run root under the standard sandbox base unless a caller explicitly supplies a validated run root.

FR-008: E2E user-directory validation must allow pre-existing user-owned `logs/`, `cache/`, `state/`, `context/`, `registry/`, `handoffs/`, `.workroot/`, and `.ai-workroot/` directories when AI Workroot did not create or own them as managed state.

FR-009: Live-agent E2E must fail closed if it would run from the real repository checkout.

FR-010: Relationship nodes must support explicit canonical release targets or enforce the current typed-node identity convention.

FR-011: Release resolution for relationship signals must use canonical relationship node targets when present.

FR-012: Current docs must not contain local absolute developer paths outside explicit history or incident archives.

FR-013: Current docs must not present old root-level Workroot script paths as active product implementation or current agent workflow.

FR-014: Superseded by Spec 041. `workroot legacy --help` must fail as an invalid active command after runnable legacy compatibility removal.

### Non-functional Requirements

NFR-001: All fixes must remain standard-library-only.

NFR-002: Release validation should stay fast on local working trees with generated ignored files.

NFR-003: E2E safety code must stay small and auditable.

NFR-004: Schema changes must be migration-safe for existing SQLite files.

NFR-005: Tests must not depend on the developer's real home, GitHub, SSH, or global environment.

## Proposed Design

### Concepts

Release surface:
The Git-tracked and unignored files that could be committed or shipped. Ignored local files are allowed by default and should not slow release validation.

Direct ContextRecallHint release:
A ReleaseRecord, Redaction, or DeletionRecord whose canonical target is `context_recall_hint:<hint_id>`, not the hint's underlying asset/task/action target.

Canonical relationship target:
The Workroot object a relationship node represents. `node_id` may be an internal graph ID; `target_type` and `target_id` identify the release target when they exist.

E2E run root:
A validated `run-*` child under the E2E sandbox base. E2E artifacts are preserved by default for human review.

### Data Model

Add nullable columns to `relationship_nodes`:

```text
target_type TEXT
target_id TEXT
```

Add an index:

```text
idx_relationship_nodes_workroot_target
  ON relationship_nodes(workroot_id, target_type, target_id)
```

Existing rows remain valid. Resolver behavior:

1. If `target_type` and `target_id` are present, use those as canonical release target.
2. Else fallback to legacy convention: `node_type` is target type and `node_id` is target id.

No broad foreign-key migration is required.

### File Layout

Likely changed files:

```text
src/ai_workroot/diagnostics/release_validation.py
src/ai_workroot/release/operations.py
src/ai_workroot/state/sqlite.py
src/ai_workroot/release/filter.py
src/ai_workroot/retrieval/providers/relationship_provider.py
src/ai_workroot/relationships/operations.py
src/ai_workroot/relationships/model.py
src/ai_workroot/cli/main.py
tests/unit/test_release_operations.py
tests/unit/test_diagnostics_doctor.py
tests/unit/test_release_target_resolver.py
tests/unit/test_relationship_operations.py
tests/smoke/test_clean_release_validator.py
split repository/docs contract tests under tests/contracts/
tests/contracts/test_e2e_opt_in_policy.py
tests/e2e/runner.py
tests/e2e/harness.py
tests/e2e/persona_smoke.py
tests/e2e/longrun.py
docs/history/0.9.530/plans/
docs/specs/036-e2e-sandbox-and-destructive-operation-safety.spec.md
docs/release-checklist.md
```

### CLI / API

Release doctor stays:

```bash
python -m ai_workroot doctor --release
```

E2E runner stays opt-in:

```bash
AI_WORKROOT_RUN_E2E=1 python3 -m tests.e2e.runner --suite safety
AI_WORKROOT_RUN_E2E=1 python3 -m tests.e2e.runner --suite persona-smoke
AI_WORKROOT_RUN_E2E=1 python3 -m tests.e2e.runner --suite longrun
```

Legacy command handling is superseded by Spec 041: active CLI rejects legacy namespaces as invalid commands.

### Runtime Behavior

Release validation:

1. Read tracked files through `git ls-files`.
2. Read untracked unignored files through `git ls-files --others --exclude-standard`.
3. Validate only those release-surface files.
4. Ignore ignored local files such as `.idea/`, root `AGENTS.md`, root `CLAUDE.md`, `.ai-workroot-local/`, and `__pycache__/`.
5. Fall back to bounded filesystem scanning only when Git is unavailable.

Direct ContextRecallHint release:

1. Release sanitization identifies hint ids by direct `hint_id` and by underlying target.
2. It sanitizes hint rows, hint FTS rows, materialized hint candidate rows, and candidate FTS rows.
3. Doctor detects leaks in all of those places.

E2E:

1. Runner requires `AI_WORKROOT_RUN_E2E=1`.
2. Runner resolves a sandbox run root under `~/tmp/ai-workroot-e2e-sandboxes` when one is not explicitly supplied.
3. Safety suite may remain lightweight, but persona and longrun artifacts should be preserved when launched through the runner.
4. User-owned directory names are allowed if they are not AI Workroot managed state.
5. Live-agent E2E is not implemented in this pass, but safety helpers must fail closed for real repository cwd.

Relationships:

1. `create_relationship_node()` accepts optional canonical target fields.
2. Provider upsert helpers accept optional canonical target fields.
3. Release resolver uses canonical target fields when available.
4. Old rows remain compatible.

### Error Handling

- Release validation reports actionable paths and reasons.
- Direct hint sanitization should tolerate missing optional FTS tables by failing closed in doctor but not crashing release creation.
- E2E unsafe roots and unsafe live cwd raise `ValueError`.
- Relationship node target fields must either both be present or both be absent.

### Security / Privacy

- Release validation must not leak ignored local files into release checks.
- Direct hint strict releases must remove sensitive text from derived local indexes.
- E2E must not run live-agent actions in the real source checkout.
- Docs must not publish local absolute developer paths as current guidance.

### Compatibility

- Existing SQLite databases without `target_type` and `target_id` on `relationship_nodes` migrate in place.
- Legacy relationship node rows retain fallback behavior.
- Existing E2E direct programmatic helpers may remain, but runner is the recommended execution path.
- Legacy Public Seed commands remain available under compatibility paths.

## Acceptance Criteria

AC-001:
Given ignored `.idea/` and `__pycache__/` files
When release doctor runs
Then it passes or fails based on release-surface files only, not ignored local files.

AC-002:
Given an unignored generated SQLite file
When release doctor runs
Then it fails with a generated store diagnostic.

AC-003:
Given a direct redaction target `context_recall_hint:h1`
When the redaction is created
Then `context_recall_hints`, `context_recall_hints_fts`, materialized candidate, and candidate FTS no longer contain the original sensitive text.

AC-004:
Given a direct deletion target `context_recall_hint:h1` with leaked hint text
When Doctor release-derived index safety runs
Then it reports the leak.

AC-005:
Given a user directory that already contains user-owned `logs/` and `cache/`
When E2E validates the directory after Clean Workroot init
Then validation passes if AI Workroot state remains under `AI_WORKROOT_HOME`.

AC-006:
Given E2E runner without `AI_WORKROOT_RUN_E2E=1`
When any suite is selected
Then runner exits non-zero before executing tests.

AC-007:
Given E2E runner with opt-in
When `--dry-run` is used
Then it prints selected suites and the planned sandbox without executing E2E cases.

AC-008:
Given a relationship node `node_id=graph-node-1`, `node_type=asset`, `target_type=asset`, and `target_id=asset-1`
When a relationship signal is evaluated
Then release target resolution includes `asset:asset-1`.

AC-009:
Given current docs outside history or incident archives
When docs hygiene tests run
Then no local absolute developer-home paths are present.

AC-010:
Given default Clean Mode help
When `workroot --help` runs
Then legacy command groups remain hidden.

AC-011:
Superseded by Spec 041. Given legacy help, when `workroot legacy --help` runs, then the command fails as invalid.

## Test Plan

### Unit Tests

- Release validation uses Git file lists and ignores ignored files.
- Direct `context_recall_hint` redaction/deletion sanitizes hint rows and FTS rows.
- Doctor detects direct hint target leaks.
- Relationship node canonical target mapping works with `node_id != target_id`.
- Legacy help delegation returns useful output.

### Integration Tests

- Release doctor runs against the current repo.
- E2E harness validates user-owned `logs/` and `cache/`.
- E2E runner dry-run preserves opt-in semantics.

### Manual Verification

- Run `PYTHONPATH=src python3 -m ai_workroot doctor --release`.
- Run `scripts/dev/validate-release.sh`.
- Run E2E safety suite only if explicitly needed:

```bash
AI_WORKROOT_RUN_E2E=1 PYTHONPATH=src python3 -m tests.e2e.runner --suite safety
```

Do not run persona-smoke or longrun unless explicitly requested.

## Migration / Rollback

Relationship node schema migration:

1. Add nullable columns if missing.
2. Add target index if missing.
3. Existing rows keep fallback behavior.

Rollback is a normal Git revert before external users rely on the new columns. If a database already has the columns, old code should ignore them.

## Observability / Debugging

- Release doctor output remains text-based and actionable.
- E2E runner prints selected suites and sandbox path.
- E2E command logs include cwd and command details.
- Doctor release-derived index findings include table and target reference.

## Task Breakdown

T1: Release validation fast path
- Change: Replace recursive release surface scanning with Git file list scanning.
- Files likely affected: `src/ai_workroot/diagnostics/release_validation.py`, `tests/smoke/test_clean_release_validator.py`, split release-gate contract tests under `tests/contracts/`.
- Verification: release validation tests, `doctor --release`, `validate-release.sh`.

T2: Direct ContextRecallHint release safety
- Change: Sanitize and detect direct `context_recall_hint` targets.
- Files likely affected: `src/ai_workroot/release/operations.py`, `src/ai_workroot/state/sqlite.py`, release safety tests.
- Verification: direct hint redaction/deletion tests and doctor leak tests.

T3: E2E harness safety semantics
- Change: Preserve runner sandboxes, add dry-run sandbox output, allow user-owned state-like directory names, fail live E2E on real repo cwd.
- Files likely affected: `tests/e2e/runner.py`, `tests/e2e/harness.py`, `tests/e2e/safety.py`, E2E policy tests, E2E specs.
- Verification: opt-in policy tests and safety suite only.

T4: Relationship canonical target mapping
- Change: Add optional relationship node canonical target fields and resolver support.
- Files likely affected: `src/ai_workroot/state/sqlite.py`, `src/ai_workroot/relationships/operations.py`, `src/ai_workroot/retrieval/providers/relationship_provider.py`, `src/ai_workroot/release/filter.py`.
- Verification: relationship runtime and release resolver tests.

T5: Docs and small quality closure
- Change: Archive active-looking execution plans, clean local paths and old canonical scripts, improve legacy help, clean obvious SQLite ResourceWarnings.
- Files likely affected: `docs/history/0.9.530/plans/`, `docs/specs/`, `docs/release-checklist.md`, `src/ai_workroot/cli/main.py`, tests.
- Verification: docs hygiene tests, CLI discovery tests, full unittest discovery.

## Risks

- Git-native release validation may miss non-Git fallback behavior if implemented too narrowly.
- Relationship schema migration can break old in-memory test DBs if column additions are incomplete.
- E2E runner changes can accidentally execute longrun if opt-in checks are weakened.
- Docs cleanup can erase useful historical context if history/current boundaries are not explicit.

## Open Questions

None.
