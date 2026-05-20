# Spec: 0.9.529 Hardening Review Fixes

## Status

Draft

## Priority

P0

## Background

AI Workroot 0.9.529 shipped the Clean Native Context Foundation. A follow-up review identified hardening gaps in concurrency, token budget enforcement, retrieval fairness, repository-level safety filtering, graph signal rendering, SQLite schema evolution, CLI ergonomics, test file layout, legacy command exposure, FTS observability, and runtime config merging.

This Spec defines a focused fix iteration for the existing review branch. It does not create a new release, tag, or merge target. It keeps the 0.9.529 architecture intact while tightening behavior and tests around edge cases.

## Goals

- Make Clean Mode registry writes safe under concurrent init and developer bootstrap.
- Enforce hard token limits with conservative local estimation and final fallback behavior.
- Prevent always candidates from starving explicit, FTS, or graph-derived context candidates.
- Apply default repository-level safety filtering for blocked candidate safety policies.
- Render only relation-backed graph edges in the Graph Signals section.
- Add SQLite schema migration state and document or test the per-Workroot database invariant.
- Improve CLI flags for Native Agent Entry and hard token limit overrides.
- Remove test-like files from outside `tests/`.
- Reduce legacy command exposure in default Clean Mode help without removing legacy commands.
- Record FTS query fallback information in debug traces.
- Deep-merge nested Context Guide runtime-hint overrides.
- Keep `workroot_context.py` fixes localized and record larger module splitting as follow-up work.

## Non-goals

- This Spec does not merge into `main`.
- This Spec does not create a tag or release.
- This Spec does not remove legacy public-seed commands.
- This Spec does not fully refactor `workroot_context.py` into multiple modules.
- This Spec does not change the global User Profile layer.
- This Spec does not make Windows PowerShell validation a blocker.

## Scope

### Included

- File-locking for Clean Mode registry writes.
- Concurrency regression tests for duplicate `workroot init` and `bootstrap-dev`.
- Conservative token estimation and final hard-limit fallback.
- Candidate pool fairness for explicit, FTS, graph, and active-task sources.
- Repository and Context Guide safety policy regression tests.
- Relation-backed graph signal rendering and trace separation for seed explanations.
- SQLite schema migration marker support with old database migration tests.
- CLI parser fixes for Native Agent Entry flags and hard token limit override.
- Test file audit cleanup for `scripts/test_new_task.py`.
- Default help isolation for legacy seed commands.
- FTS fallback trace reporting.
- Deep runtime config merge.
- Follow-up note for large `workroot_context.py` modularization.

### Excluded

- Full migration away from `space/ + .workroot/`.
- New release notes for a new version.
- Full GUI or C-end installer behavior.
- Remote LLM, embedding, or vector database integration.
- Large-scale codebase reorganization.

## Dependencies

- `002-clean-mode-installation.spec.md`
- `003-managed-state-layout.spec.md`
- `004-bootstrap-process.spec.md`
- `006-doctor-command.spec.md`
- `007-context-guide-builder.spec.md`
- `008-materialized-context-candidates.spec.md`
- `009-fts-indexing-and-retrieval.spec.md`
- `010-debug-trace-and-observability.spec.md`
- `011-cli-user-flows.spec.md`
- `013-sqlite-cache-and-provenance-graph.spec.md`
- `015-context-guide-modes-budgets-and-confidence.spec.md`

## Requirements

### Functional Requirements

FR-001: Workroot registry writes during `workroot init` must be protected by a registry-level lock.

FR-002: Concurrent `workroot init` against the same user directory must produce at most one active Workroot registration.

FR-003: Concurrent `bootstrap-dev` for the same repository must be idempotent and must produce at most one registry entry for that developer Workroot ID.

FR-004: Context Package token estimation must be conservative for English, CJK, no-whitespace, and code-heavy content.

FR-005: Hard token limit enforcement must trim graph signals, FTS matches, selected candidates, and finally fall back to a minimal package if needed.

FR-006: Debug trace must record hard-limit trim steps and final fallback status.

FR-007: Candidate pool construction must not allow many `always` candidates to starve explicit, FTS, graph, or active-task candidates.

FR-008: Repository-level candidate queries must exclude blocked safety policies by default.

FR-009: Repository-level candidate queries may include blocked safety policies only through an explicit audit/debug flag.

FR-010: Context Guide must continue to drop `never-auto`, `needs-confirmation`, and `sensitive` safety policies.

FR-011: Graph Signals must contain only real relation-backed graph edges.

FR-012: Selected seed node explanations must be exposed separately from Graph Signals, preferably in debug trace.

FR-013: SQLite must track schema migration state through `schema_migrations` or `PRAGMA user_version`.

FR-014: Existing old SQLite databases must be upgraded idempotently when initialized.

FR-015: Per-Workroot SQLite database scoping must be documented and covered by tests if graph tables do not include `workroot_id`.

FR-016: Candidate update helpers must be scoped by `workroot_id` or explicitly protected by tested per-Workroot database invariants.

FR-017: `--native-agent-entry` and `--no-native-agent-entry` must be mutually exclusive.

FR-018: `workroot context` must support `--hard-token-limit`.

FR-019: Debug output must show effective target and hard token budgets and their source.

FR-020: Test-like Python files must live under `tests/` or be renamed so audit commands do not report test functions outside `tests/`.

FR-021: Default Clean Mode CLI help must not present legacy seed commands as the primary user path.

FR-022: FTS `sqlite3.OperationalError` fallbacks must be graceful and visible in debug trace.

FR-023: Runtime Context Guide config overrides must deep-merge nested dictionaries.

FR-024: Large `workroot_context.py` modularization must be recorded as follow-up if not completed in this iteration.

### Non-functional Requirements

NFR-001: Fixes must remain local-first and must not introduce cloud dependencies.

NFR-002: Fixes must not introduce vector database or remote embedding dependencies.

NFR-003: Concurrency locks must work on macOS/Linux with the standard library.

NFR-004: Lock files must live under AI Workroot system home, not inside the user directory.

NFR-005: Token estimation must prefer conservative over undercounting behavior.

NFR-006: Final fallback context must remain useful enough to report metadata, current state, and guardrails.

NFR-007: All tests must run with `python3 -m unittest discover -s tests -v`.

NFR-008: Changes must avoid broad refactors outside the reviewed surfaces.

## Proposed Design

### Concepts

- Registry lock: A process-level file lock under AI Workroot home that serializes registry reads and writes.
- Conservative token estimate: A local heuristic that counts whitespace tokens, CJK characters, punctuation-heavy code segments, and long no-whitespace runs more defensibly than `split()`.
- Final hard-limit fallback: A minimal Context Package rendered when normal trimming cannot satisfy `hardTokenLimit`.
- Relation-backed graph signal: A graph signal derived from an actual active graph edge using an approved relation.
- Seed explanation: Debug-only metadata explaining why selected candidate/source IDs were used to query the graph.
- Per-Workroot DB invariant: Each Workroot has its own `cache/workroot.sqlite`; graph tables are scoped by database path rather than by `workroot_id` columns.

### Data Model

Add SQLite migration state:

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
  migration_id TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL
);
```

Use migration IDs such as:

- `001-initial-schema`
- `002-context-candidate-use-count`

If a database already contains older tables but lacks `schema_migrations`, initialization records the current required migrations after applying missing additive schema changes.

### File Layout

Allowed in user-selected directory:

- Existing user files.
- Optional authorized Native Agent Entry files: `AGENTS.md`, `CLAUDE.md`.

Not allowed in user-selected directory by default:

- Registry lock files.
- SQLite databases.
- Context packages.
- Debug traces.
- Runtime state.
- Legacy `space/` or `.workroot/` generated directories.

Managed lock path:

```text
<AI_WORKROOT_HOME>/concurrency/locks/registry.lock
```

Per-Workroot SQLite path:

```text
<AI_WORKROOT_HOME>/workroots/<workroot_id>/cache/workroot.sqlite
```

### CLI / API

`workroot init`:

```text
workroot init --native-agent-entry
workroot init --no-native-agent-entry
```

These flags are mutually exclusive.

`workroot context`:

```text
workroot context --agent codex --cwd . --target-tokens 3000 --hard-token-limit 4000
```

Default `workroot --help` should emphasize:

```text
quickstart, init, list, status, bootstrap-dev, context, manifest, doctor
```

Legacy commands remain available under `workroot legacy ...` or hidden from default help in this iteration.

### Runtime Behavior

Init and bootstrap:

1. Resolve AI Workroot home.
2. Acquire registry lock.
3. Create or validate global home layout.
4. Re-read registry files inside the lock.
5. Reject duplicate user directories and duplicate Workroot IDs.
6. Write state and registry records.
7. Release lock.
8. Apply non-registry side effects such as Native Agent Entry after registry state is safe.

Context generation:

1. Load config with deep merge.
2. Resolve target and hard token budgets.
3. Query FTS and candidate FTS with traceable fallback capture.
4. Build a candidate pool from source buckets and truncate globally without starving explicit, FTS, graph, or active-task candidates.
5. Filter blocked safety policies before selection.
6. Render only relation-backed graph signals.
7. Enforce hard token limit with conservative estimates.
8. If trimming all optional content still exceeds the hard limit, render a minimal fallback package and record it in trace.

### Error Handling

- Lock acquisition timeout reports the lock path and exits with an actionable message.
- Concurrent duplicate init reports the existing Workroot ID.
- FTS operational errors do not fail context generation but are recorded in trace.
- Invalid hard token CLI values fail through argparse or Context Guide validation.
- Old SQLite databases are migrated idempotently.

### Security / Privacy

- Registry locks and SQLite migrations are local only.
- No managed state is written into the user-selected directory.
- Debug traces may include paths and candidate metadata under managed state only.
- Blocked safety policies remain excluded by default.

### Compatibility

- Existing 0.9.529 Workroot state must continue to initialize and pass doctor.
- Existing SQLite databases lacking `schema_migrations` must be upgraded in place.
- Legacy public-seed commands remain available for compatibility.
- Per-Workroot graph tables without `workroot_id` are acceptable only because each Workroot has a separate SQLite database.

## Acceptance Criteria

AC-001:
Given two concurrent `workroot init` processes targeting the same user directory
When both complete
Then exactly one succeeds and at most one active registry record exists for that directory.

AC-002:
Given two concurrent `bootstrap-dev` runs for the same repository
When both complete
Then one initializes or both report reuse, and the registry contains one Workroot record for the bootstrap ID.

AC-003:
Given CJK text without spaces
When token estimation runs
Then the estimate increases with character count and does not collapse to one token.

AC-004:
Given code with long no-whitespace symbols
When token estimation runs
Then the estimate is conservative enough to trigger hard-limit trimming.

AC-005:
Given a hard token limit lower than the fully rendered package
When graph, FTS, and candidates are trimmed
Then debug trace records removed items and any final fallback.

AC-006:
Given many `always` candidates and one explicit FTS match
When candidate pool is built
Then the explicit match is included or scored before truncation.

AC-007:
Given candidates with blocked safety policies
When repository query runs without audit flag
Then blocked candidates are excluded.

AC-008:
Given selected graph seed nodes and one relation edge
When Context Package renders
Then Graph Signals contain the relation-backed edge and do not contain selected-node pseudo signals.

AC-009:
Given an old SQLite database without `schema_migrations`
When initialization runs
Then required tables exist and migrations are recorded.

AC-010:
Given both `--native-agent-entry` and `--no-native-agent-entry`
When `workroot init` parses arguments
Then the CLI exits with a mutual-exclusion error.

AC-011:
Given `workroot context --hard-token-limit 100`
When Context Guide resolves budget
Then debug trace shows hard budget 100 and its source.

AC-012:
Given audit commands search for test files
When the repository is scanned
Then no test-like Python files exist outside `tests/`.

AC-013:
Given FTS raises `sqlite3.OperationalError`
When context generation continues
Then trace records the error and fallback.

AC-014:
Given a runtime hint overriding only one nested field
When config loads
Then unspecified nested defaults remain present.

## Test Plan

### Unit Tests

- Registry lock helper acquires and releases lock.
- Conservative token estimator covers English, CJK, code, and no-whitespace strings.
- Deep merge preserves nested defaults.
- Candidate repository query filters blocked safety policies by default and includes them only with audit flag.
- SQLite initialization creates `schema_migrations`.
- Old SQLite fixture migration records required migration IDs.

### Integration Tests

- Concurrent `workroot init` duplicate directory test.
- Concurrent `bootstrap-dev` idempotency test.
- Context Guide hard token final fallback test.
- Candidate pool starvation tests for explicit, FTS, graph, and active-task candidates.
- Relation-backed graph signal rendering test.
- CLI mutual exclusion and `--hard-token-limit` tests.
- FTS OperationalError debug trace test.

### Manual Verification

- Clean Mode smoke.
- Duplicate userDirectory smoke.
- Unsafe Workroot ID smoke.
- Native Agent Entry smoke.
- Bootstrap-dev smoke, including second run.
- SQLite schema report.
- Context Guide behavior report with safety candidates, FTS match, graph relation, weak query-only node, and hard token trim.

## Migration / Rollback

SQLite migrations are additive and idempotent. If schema migration fails, initialization should leave the database file in place and report the migration error through the caller. Registry lock files are transient and may remain only as diagnostic files if a process crashes.

Rollback for this branch is Git rollback of the commit before merge. No release or tag is created in this iteration.

## Observability / Debugging

Debug trace must include:

- token budget target, hard limit, estimated use, and source;
- hard-limit trim steps;
- final fallback status;
- FTS fallback errors;
- candidate pool source counts;
- selected candidates and dropped candidates;
- graph seed explanations separate from relation-backed graph signals;
- timing information.

Doctor should continue to report SQLite schema status and runtime hint validity.

## Task Breakdown

T1: Add registry lock and concurrency tests
- Change: Add registry lock helper under managed home and wrap init/bootstrap registry decisions.
- Files likely affected: `scripts/workroot_state.py`, `scripts/workroot_bootstrap.py`, `tests/test_workroot_init_cli.py`, `tests/test_workroot_bootstrap_dev.py`.
- Verification: Concurrent init/bootstrap regression tests.

T2: Harden token estimation and hard-limit fallback
- Change: Replace whitespace token estimate, add final fallback rendering, record trim steps.
- Files likely affected: `scripts/workroot_context.py`, `tests/test_workroot_context.py`.
- Verification: English, CJK, code, and final fallback tests.

T3: Fix candidate pool starvation
- Change: Collect source buckets before global truncation and preserve explicit/FTS/graph/active-task candidates.
- Files likely affected: `scripts/workroot_context.py`, `tests/test_workroot_context.py`.
- Verification: Starvation regression tests.

T4: Add repository-level safety filtering
- Change: Default filter blocked safety policies and add explicit audit flag.
- Files likely affected: `scripts/workroot_candidates.py`, `tests/test_workroot_candidates.py`, `tests/test_workroot_context.py`.
- Verification: Repository and Context Guide safety tests.

T5: Clean graph signal rendering
- Change: Remove selected-node pseudo signals from Graph Signals and trace seed explanations separately.
- Files likely affected: `scripts/workroot_context.py`, `tests/test_workroot_context.py`.
- Verification: Graph signals only include relation-backed edges.

T6: Add SQLite migration state and scoping tests
- Change: Add `schema_migrations`, old DB migration path, per-Workroot DB invariant tests, and workroot-scoped candidate updates where practical.
- Files likely affected: `scripts/workroot_sqlite.py`, `scripts/workroot_candidates.py`, `tests/test_workroot_sqlite.py`, `tests/test_workroot_candidates.py`.
- Verification: Old DB fixture migration tests.

T7: Fix CLI flags and help exposure
- Change: Make Native Agent Entry flags mutually exclusive, add `--hard-token-limit`, and hide or isolate legacy commands from default help.
- Files likely affected: `scripts/workroot_cli.py`, `tests/test_workroot_cli_discovery.py`, `tests/test_workroot_init_cli.py`, `tests/test_workroot_context.py`.
- Verification: CLI parsing and help tests.

T8: Move or rename test-like script
- Change: Move `scripts/test_new_task.py` to `tests/` or rename it so audit commands do not report it outside tests.
- Files likely affected: `scripts/test_new_task.py`, `tests/test_new_task_script.py` or release checklist docs/tests.
- Verification: Test audit commands.

T9: Record maintainability follow-up
- Change: Add follow-up note for splitting `workroot_context.py` into budget/token/render/trace modules.
- Files likely affected: `docs/release-checklist.md` or `docs/plans/`.
- Verification: Review note exists and no broad refactor is introduced.

T10: Full validation and smoke
- Change: Run full required validation and smoke checks.
- Files likely affected: none.
- Verification: Required commands pass and outputs are captured in final handoff.

## Risks

- Concurrency tests may be timing-sensitive if not designed with process barriers.
- Token heuristics can overestimate; this is acceptable for hard-limit safety but may trim more context.
- Hiding legacy commands from help may affect existing power users.
- SQLite migration changes must remain idempotent for existing databases.
- Large `workroot_context.py` changes can increase regression risk; this iteration must keep fixes localized.

## Open Questions

None for this iteration. Larger `workroot_context.py` modularization is intentionally deferred to a separate branch.
