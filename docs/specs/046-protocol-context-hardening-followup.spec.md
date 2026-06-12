# Spec 046 - Protocol And Context Hardening Follow-up

Status: accepted for the 0.9.531 hotfix line
Target: 0.9.531 hotfix line
Depends on:

- `042-agent-protocol-context-strategy.spec.md`
- `044-sqlite-schema-migrations.spec.md`
- `045-sync-owner-binding-and-lease-guard.spec.md`

This spec supersedes Specs 042 and 045 only for the narrow behaviors explicitly
listed here: WorkSignal boundary semantics, retrieval provider
transaction/schema boundaries, malformed-commit friction recording, generic
Native Agent Entry fallback, local dogfood Agent Entry cleanup, and ordinary
context reason rendering.

## Purpose

This spec closes six follow-up gaps found during the 0.9.531 protocol/context
hardening review.

The goal is not to add new domain concepts. The goal is to make the current
protocol boundary, storage boundary, diagnostics, Agent Entry rendering, and
ordinary context rendering consistent with the architecture already accepted in
Specs 042, 044, and 045.

## Scope

Included:

- Explicit language-neutral expression of a legitimate separate durable work
  boundary.
- Retrieval provider cleanup so SQLite schema ownership and transaction
  ownership stay centralized.
- Protocol-friction diagnostics for malformed commit quarantine.
- Generic Native Agent Entry rendering for unknown Agent descriptors.
- Local dogfood Agent Entry cleanup for ignored root `AGENTS.md` and
  `CLAUDE.md`.
- Ordinary context package rendering that hides implementation-flavored scoring
  reason labels while keeping debug visibility.

Excluded:

- New Task, Project, Initiative, SubTask, RecallPlan, or diagnostic domain
  entities.
- New durable tables for the six fixes.
- Backward compatibility for experimental pre-release WorkSignal variants.
- Per-turn `workroot context` in the normal Agent loop.
- Public exposure of internal owner binding, disclosure layer names, or scoring
  internals.

## Architectural Principles

1. The stable Agent loop remains `sync -> commit`.
2. `context` remains read-only auxiliary behavior for startup, recovery, manual
   recall, or debugging.
3. WorkSignal is protocol input, not a durable fact.
4. Workroot decides owner binding before issuing a lease.
5. Durable Task creation still happens only through
   `commit(shape=start_work)`.
6. Malformed protocol input must not block Agent work, but it must leave enough
   diagnostics to debug the run.
7. SQLite DDL and migration records belong only to the centralized migration
   runner in `src/ai_workroot/state/sqlite.py`.
8. Retrieval providers are query/write helpers, not schema managers and not
   transaction owners.
9. Ordinary LLM context should be useful and small. Debug metadata belongs in
   debug traces, not in the normal context map.

## Problem 1: Separate Durable Work Boundary Is Not Reliable

### Current Failure

The current sync focus logic can bind a legitimate new durable task request to
the only active normal task:

```text
phase=starting, work_kind=task, intended_action=plan
```

When a single active normal task exists, `focus.py` may downgrade the request to
continuation unless `_forces_new_root()` returns true. `_forces_new_root()` looks
for concern values such as `new_task_boundary`, but `work_signal.py` drops those
values because they are not in the `CONCERNS` whitelist.

This means the protocol cannot reliably express:

```text
The user is starting a separate long-running work item.
```

### Design Decision

Add one optional WorkSignal field:

```text
boundary
```

Allowed values:

```text
continue_current
separate_work
uncertain
```

The default is omitted, not `auto`. Missing `boundary` means Workroot should use
the existing owner-resolution priority from Spec 045.

Rationale:

- A work boundary is task-continuity semantics, not a "concern".
- It is language-neutral and compact.
- It does not expose internal concepts such as `root_task_id`,
  `FocusBinding`, `owner_kind`, or disclosure layers.
- It lets the LLM normalize user language without Workroot relying on
  multilingual keyword dictionaries.

### WorkSignal Contract

Updated WorkSignal fields:

```text
phase
work_kind
intended_action
boundary
focus
concerns
refs
```

Rules:

- `boundary=separate_work` requests a separate durable work boundary.
- `boundary=continue_current` requests attachment to the current accepted
  focus, if a safe focus exists.
- `boundary=uncertain` tells Workroot not to guess. Sync should return a
  non-blocking focus-refinement contract when no reliable owner is available.
- Explicit `known_state` or valid `refs` remain stronger than `boundary`.
- If `boundary=separate_work` conflicts with explicit refs or known state,
  Workroot must not attach arbitrarily. It should return a non-blocking
  clarification/refinement sync response without a durable write lease.
- `concerns` remains for risk or need flags such as `needs_evidence`,
  `may_publish`, `may_be_sensitive`, and `uncertain_task_boundary`.
- New work boundary values must not be routed through `concerns`.

### Sync Behavior

When the signal is:

```json
{
  "phase": "starting",
  "work_kind": "task",
  "intended_action": "plan",
  "boundary": "separate_work",
  "focus": "user-language focus"
}
```

`sync` should:

1. Resolve the request as new durable work unless explicit refs/known state
   contradict it.
2. Return a start-work lease that allows `intent`.
3. Return a private packet telling the Agent/LLM to commit a start-work event.
4. Avoid attaching the new request to the existing active normal task merely
   because only one active normal task exists.

When `boundary` is missing and exactly one active normal task exists, Spec 045
still applies: Workroot may continue the existing task unless stronger signals
prove a separate boundary.

### User/LLM-Facing Guidance

Native Agent Entry should explain the protocol in ordinary action language:

```text
When the user clearly starts a separate long-running work item, add
boundary=separate_work to WorkSignal.
```

It should not mention `root`, `owner_kind`, `FocusBinding`, or internal layer
names.

## Problem 2: Retrieval Providers Still Mutate Schema And Commit

### Current Failure

Retrieval provider functions still contain provider-local schema mutation and
transaction commits:

- `candidate_provider.py` calls `_ensure_candidate_columns()` and commits.
- `sqlite_fts.py` calls `_ensure_indexed_file_source_columns()` and commits.

This violates Spec 044 because schema ownership and migration records should be
centralized in `state/sqlite.py`. It also violates transaction ownership:
projection code should be able to write protocol events, projections, indexes,
and runtime views in one controlled transaction boundary.

### Design Decision

Retrieval providers must become schema-neutral and transaction-neutral.

Allowed:

- Read from existing retrieval tables.
- Insert/update retrieval rows as part of the caller's active transaction.
- Raise normal SQLite errors if the database was not initialized correctly.

Not allowed:

- `ALTER TABLE`, `CREATE TABLE`, `DROP TABLE`, or virtual-table rebuilds inside
  retrieval providers.
- `conn.commit()` inside retrieval providers.
- Provider-local migration fallbacks for old experimental schemas.

### Schema Ownership

`src/ai_workroot/state/sqlite.py` remains the only SQLite DDL owner.

If retrieval schema changes in the future:

1. Add or modify centralized migration logic in `state/sqlite.py`.
2. Add migration tests under the existing environment/storage test surface.
3. Keep provider functions free of DDL and commits.

### Transaction Ownership

Callers decide when to commit or roll back.

Examples:

- Protocol projection may insert an asset, index its chunks, update candidates,
  and write event effects under one projection savepoint.
- Unit tests that call providers directly may commit explicitly when they want
  to observe committed state.

## Problem 3: Malformed Commit Quarantine Misses Protocol Friction

### Current Failure

Malformed commit event items can return:

```text
status=quarantined
warnings=["invalid_event_schema"]
```

but no protocol-friction record is written for the validation failure. This
makes runtime diagnosis undercount malformed commit input.

### Design Decision

The validation branch in commit application must record one friction item per
rejected batch before returning.

Required friction fields:

```text
action=commit
source_layer=protocol_controller
stage=validation
code=invalid_event_schema
result_status=quarantined
request_id
lease_id
idempotency_key
shape
details
```

Rules:

- `shape` should be inferred from valid-looking raw item `kind` values when
  possible.
- If the batch contains multiple inferred shapes, use `batch`.
- If no shape can be inferred, leave it empty rather than guessing.
- `details` should include compact invalid-item metadata, not full raw payloads
  that may be large or sensitive.
- Diagnostics remain runtime logs/views, not new durable domain facts.

## Problem 4: Native Agent Entry Is Too Product-Specific

### Current Failure

Native Agent Entry rendering currently supports only:

```text
codex
claude
```

Unknown Agent descriptors raise an error even though the protocol CLI accepts
arbitrary `--agent` values.

This conflicts with the multi-Agent direction of Spec 042.

### Design Decision

Native Agent Entry rendering should support a generic fallback template for any
safe Agent descriptor.

Resolution order:

1. Use product-specific template when a maintained template exists, such as
   `AGENTS.md.template` for Codex or `CLAUDE.md.template` for Claude.
2. Otherwise use one generic Native Agent Entry template.

The generic template must:

- contain the same stable `sync/commit` protocol guidance;
- insert the sanitized Agent descriptor into command examples;
- avoid product-specific behavior;
- avoid local absolute paths;
- pass the existing managed-block validator.

Safe Native Agent Entry descriptors are lowercase ASCII strings matching:

```text
[a-z0-9._-]{1,64}
```

Rendering should reject unsafe descriptors rather than quoting arbitrary user
input into command examples. This safety rule is for template generation only;
protocol event source metadata may still record richer adapter metadata through
the existing metadata fields.

Agent descriptors are protocol metadata. They do not change Task, Asset,
Decision, Handoff, Relationship, context, or lease semantics.

## Problem 5: Local Ignored Root Agent Entry Files Are Stale

### Current Failure

The local ignored root files:

```text
AGENTS.md
CLAUDE.md
```

still contain older guidance that says `workroot context` may be used for
read-only recall. The tracked templates already say recall inside a normal user
turn should use `sync` with `intended_action=inspect`.

These files are ignored and are not release artifacts, but they are important
for local dogfooding because the Agent reads them.

### Design Decision

Implementation should refresh local ignored root Agent Entry files from the
current templates after template changes.

Rules:

- Do not treat ignored local files as public release surface.
- Do not commit ignored local files.
- Verify local dogfood files no longer contradict the `sync`-first loop.
- Keep the tracked template as the source of truth.

If a future developer wants a stronger guard, it should be a local/dev check,
not a release contract that depends on ignored files.

## Problem 6: Ordinary Context Exposes Technical Reason Labels

### Current Failure

Ordinary context rendering currently includes implementation-flavored labels:

```text
candidate-fts-match
relationship-edge
file-fts-match
```

These are useful for debugging retrieval behavior, but they are not useful
ordinary LLM context. They increase context noise and expose scoring mechanics.

### Design Decision

Split ordinary context rendering from debug context rendering.

Ordinary context map should render compact stable references:

```text
- Title [Ref: candidate:<id>]
- Path or title [Ref: chunk:<id>]
```

Allowed ordinary labels:

```text
Ref
Related
Evidence
Summary
Status
```

Debug trace may continue to render:

```text
candidate-fts-match
relationship-edge
file-fts-match
scoring
recallSources
```

Rules:

- Provider match reasons remain internal scoring/debug data.
- `Status` is reserved for user/LLM-meaningful safety or release annotations
  such as `tombstone`; it must not carry provider scoring reasons.
- Normal context must not expose internal disclosure layer names.
- Normal context must not expose `FocusBinding`, `owner_kind`, lease internals,
  or provider scoring labels.
- Debug mode must preserve enough information to investigate recall quality.

## Updated Protocol Flow

### Startup Or Recovery

```text
Agent may call context
  -> Workroot returns read-only startup/recovery guidance
  -> no durable facts are created
```

This is auxiliary. It is not required every turn.

### Meaningful User Turn

```text
User speaks naturally
  -> LLM/Agent optionally normalizes compact WorkSignal
  -> Agent calls sync with query and optional WorkSignal
  -> Workroot resolves focus boundary
  -> Workroot chooses context strategy and returns compact context
  -> Workroot may issue lease and shape-specific commit contract
  -> Agent does the work
  -> Agent calls commit for durable facts requested by the lease
```

### Separate Durable Work Example

Input semantics:

```text
The user moves from an existing hiring task to a new pricing strategy task.
```

WorkSignal:

```json
{
  "phase": "starting",
  "work_kind": "task",
  "intended_action": "plan",
  "boundary": "separate_work",
  "focus": "pricing strategy"
}
```

Expected sync result:

```text
focus=new durable work
lease allows intent
private packet asks for start_work commit
```

Expected commit:

```text
commit(shape=start_work) -> projection creates Task/TaskRun
```

### Existing Work Continuation Example

Input semantics:

```text
The user asks for the next version of the current operating plan.
```

WorkSignal:

```json
{
  "phase": "executing",
  "work_kind": "continuation",
  "intended_action": "edit",
  "boundary": "continue_current",
  "focus": "current operating plan"
}
```

Expected sync result:

```text
focus=current accepted task
lease allows progress/asset/continuation as appropriate
private packet asks for the relevant commit shape
```

### Evidence Request Example

Input semantics:

```text
The user asks why a prior recommendation was made and wants supporting detail.
```

WorkSignal:

```json
{
  "phase": "orienting",
  "work_kind": "review",
  "intended_action": "inspect",
  "boundary": "continue_current",
  "concerns": ["needs_evidence"],
  "focus": "the prior recommendation"
}
```

Expected context behavior:

```text
sync may return summaries and refs first
deep evidence requires explicit refs or bounded accepted focus
ordinary context hides scoring reasons
debug context keeps scoring reasons
```

## Affected Files

Expected implementation files:

- `docs/specs/README.md`
- `docs/specs/042-agent-protocol-context-strategy.spec.md`
- `docs/specs/045-sync-owner-binding-and-lease-guard.spec.md`
- `src/ai_workroot/protocol/work_signal.py`
- `src/ai_workroot/protocol/focus.py`
- `src/ai_workroot/protocol/packet.py`
- `src/ai_workroot/protocol/controller.py`
- `src/ai_workroot/capabilities/retrieval/providers/candidate_provider.py`
- `src/ai_workroot/capabilities/retrieval/providers/sqlite_fts.py`
- `src/ai_workroot/capabilities/context/builder.py`
- `src/ai_workroot/entrypoints/native_agent/native.py`
- `src/ai_workroot/entrypoints/native_agent/templates/*.template`
- local ignored root `AGENTS.md` and `CLAUDE.md`

Expected test files:

- `tests/unit/test_protocol_models.py`
- `tests/unit/test_protocol_sync_focus_v2.py`
- `tests/unit/test_protocol_controller.py`
- `tests/unit/test_protocol_commit_reliability_v2.py`
- `tests/unit/test_context_candidate_provider.py`
- `tests/unit/test_sqlite_fts_provider.py`
- `tests/integration/test_environment_storage.py`
- `tests/integration/test_context_retrieval_selection.py`
- `tests/unit/test_context_wrapper_v2.py`
- Native Agent Entry tests under the existing test surface.

## Testing Plan

Required regression tests:

1. With one active normal task, a sync request carrying
   `boundary=separate_work` returns a start-work intent lease instead of binding
   to the active task.
2. With one active normal task and no separate boundary, a normal continuation
   still binds to the active task.
3. WorkSignal parsing accepts `boundary=separate_work`,
   `boundary=continue_current`, and `boundary=uncertain`, and drops unknown
   boundary values non-blockingly.
4. New work boundary values are not routed through `concerns`.
5. Malformed commit input returns quarantined and records one
   `stage=validation`, `code=invalid_event_schema` protocol-friction item.
6. Retrieval providers perform no `ALTER TABLE`, `CREATE TABLE`, `DROP TABLE`,
   or `commit()` during provider calls.
7. Fresh SQLite initialization and old-shape migration tests still prove
   centralized schema setup.
8. `render_native_agent_entry("cursor")` or another unknown safe descriptor
   renders generic sync-first guidance instead of raising unsupported-agent.
9. Ordinary context output does not contain provider reason labels such as
   `candidate-fts-match`, `file-fts-match`, or `relationship-edge`.
10. Debug context output still contains enough retrieval/scoring trace to debug
    recall behavior.
11. Local ignored root Agent Entry files match the sync-first template guidance
    after implementation cleanup.

Suggested verification commands:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_models
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_sync_focus_v2
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_controller
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_commit_reliability_v2
PYTHONPATH=src python3 -m unittest tests.unit.test_context_candidate_provider
PYTHONPATH=src python3 -m unittest tests.unit.test_sqlite_fts_provider
PYTHONPATH=src python3 -m unittest tests.integration.test_environment_storage
PYTHONPATH=src python3 -m unittest tests.integration.test_context_retrieval_selection
PYTHONPATH=src python3 -m unittest discover -v
python3 -m compileall -q src scripts
git diff --check
```

If `scripts/dev/validate-release.sh` cannot run because local tooling such as
`ruff` is missing, the implementation report must say that explicitly.

## Acceptance Criteria

- A legitimate separate durable task can be expressed without relying on user
  language keywords and without overloading `concerns`.
- Task continuity remains conservative when no separate boundary is expressed.
- No retrieval provider owns schema migration or transaction commit.
- Malformed commit quarantine is visible in protocol-friction diagnostics.
- Unknown Agent descriptors can receive a generic Native Agent Entry.
- Local dogfood Agent Entry files do not contradict tracked templates.
- Normal LLM context is smaller and cleaner, while debug traces remain useful.
- No new domain entity or durable table is introduced.
- The main protocol loop remains `sync/commit`.
