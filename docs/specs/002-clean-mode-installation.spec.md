# Spec: Clean Mode Installation

## Status

Draft

## Priority

P0

## Background

Clean Mode is the default consumer-facing AI Workroot mode. In Clean Mode, the user-selected directory is the visible user asset space. AI Workroot must not place managed state, indexes, runtime files, logs, cache, context packages, or control folders inside that directory by default.

This Spec defines installation and initialization behavior that preserves user directory cleanliness while still allowing explicit, user-authorized Native Agent Entry files.

## Goals

- Keep user-selected directories clean by default.
- Initialize a Workroot without creating managed state inside the user directory.
- Require explicit authorization before writing user-facing generated files such as `AGENTS.md` or `CLAUDE.md`.
- Verify Clean Mode after init.
- Preserve local-first behavior.

## Non-goals

- This Spec does not define the full managed state directory layout.
- This Spec does not define migrations beyond initial creation.
- This Spec does not define Context Guide selection logic.
- This Spec does not implement a cloud setup or hosted account flow.

## Scope

### Included

- Clean Mode init behavior.
- User directory permission and cleanliness checks.
- Explicit authorization for Native Agent Entry files.
- Installer relationship to first Workroot creation.
- Verification rules for user directory cleanliness.

### Excluded

- Detailed state layout, covered by `003-managed-state-layout.spec.md`.
- Bootstrap developer workflow, covered by `004-bootstrap-process.spec.md`.
- Native Agent Entry file contents and managed block rules, covered by `012-native-agent-entry.spec.md`.
- CLI command matrix, covered by `011-cli-user-flows.spec.md`.

## Dependencies

- Core project decisions: Clean Mode; managed state outside the user directory; controlled bootstrap; high-quality Context Guide; Materialized Context Candidates; local-first explainable retrieval without a P0 vector dependency; debug traces; branch-and-review Git workflow; English-first docs and comments.
- `001-project-structure-and-naming.spec.md`
- `003-managed-state-layout.spec.md`
- `006-doctor-command.spec.md`
- `011-cli-user-flows.spec.md`
- `012-native-agent-entry.spec.md`

## Requirements

### Functional Requirements

FR-001: `workroot init` must default to Clean Mode.

FR-002: `workroot init` must create Workroot managed state outside the user-selected directory by default.

FR-003: `workroot init` must not create `.workroot/`, `.ai-workroot/`, `state/`, `registry/`, `handoffs/`, `context/`, `logs/`, `cache/`, `runtime/`, or `continue.md` inside the user-selected directory by default.

FR-004: `workroot init` must ask for explicit authorization before creating or modifying `AGENTS.md` or `CLAUDE.md`.

FR-005: `workroot init` must support a non-interactive flag that disables Native Agent Entry file creation.

FR-006: `workroot init` must validate that the user directory exists or can be created when the user requests a new directory.

FR-007: `workroot init` must validate read and write permissions without leaving test files behind.

FR-008: `workroot init` must register the user directory binding in managed state.

FR-009: `workroot init` must run doctor or a doctor-compatible validation after initialization.

FR-010: Install scripts may offer to run `workroot init --wizard`, but must not silently initialize a user directory.

### Non-functional Requirements

NFR-001: Clean Mode init must work without network access.

NFR-002: Clean Mode init must be safe to cancel before state registration is complete.

NFR-003: Clean Mode init must provide clear, non-technical messages for ordinary users.

NFR-004: Clean Mode init must be idempotent when re-run against an already registered directory.

NFR-005: Clean Mode init must avoid absolute private paths inside Native Agent Entry files.

## Proposed Design

### Concepts

- Clean Mode: Default mode where the user directory stores user assets and managed state lives in AI Workroot home.
- User authorization: An explicit wizard answer or non-interactive flag that allows writing Native Agent Entry files.
- Cleanliness check: A verification pass that detects managed state artifacts in the user directory.

### Data Model

Clean Mode registration record:

```json
{
  "workrootId": "wr_example",
  "name": "Example Workroot",
  "mode": "clean",
  "userDirectory": "/path/to/user/directory",
  "stateDirectory": "/path/to/ai-workroot-home/workroots/wr_example",
  "status": "active",
  "createdAt": "2026-05-19T00:00:00Z",
  "lastActiveAt": "2026-05-19T00:00:00Z"
}
```

Directory binding record:

```json
{
  "workrootId": "wr_example",
  "canonicalUserDirectory": "/path/to/user/directory",
  "bindingType": "exact",
  "createdAt": "2026-05-19T00:00:00Z"
}
```

### File Layout

Allowed by default inside user directory:

```text
user-created files
docs/
notes/
outputs/
references/
src/
tests/
```

Allowed only after explicit authorization:

```text
AGENTS.md
CLAUDE.md
```

Not allowed by default inside user directory:

```text
.workroot/
.ai-workroot/
state/
registry/
handoffs/
context/
logs/
cache/
runtime/
continue.md
```

Managed state must be created under AI Workroot home:

```text
<AI_WORKROOT_HOME>/workroots/<workrootId>/
```

### CLI / API

Required CLI behavior:

```bash
workroot init --wizard
workroot init --name "Example" --directory /path/to/dir --no-native-agent-entry
workroot init --name "Example" --directory /path/to/dir --native-agent-entry codex,claude
```

Default interactive wizard behavior:

```text
Enable Native Agent Entry files in this directory? [y/N]
```

Default non-interactive behavior:

- no Native Agent Entry files unless explicitly requested;
- no generated user-directory files unless explicitly requested.

### Runtime Behavior

Init flow:

1. Resolve AI Workroot home.
2. Collect or validate Workroot name and user directory.
3. Canonicalize the user directory path.
4. Check for an existing nearest registered Workroot.
5. Validate directory permissions with a temporary test file that is deleted immediately.
6. Create managed state directory.
7. Register Workroot and directory binding.
8. Initialize minimum state and SQLite structures.
9. Optionally create or update Native Agent Entry files after authorization.
10. Run doctor validation.

### Error Handling

- If the user directory cannot be read, report the path and required read permission.
- If the user directory cannot be written and creation was requested, report the path and required write permission.
- If a permission test file cannot be deleted, report cleanup instructions.
- If managed state would be created inside the user directory, fail unless the user explicitly configured that unsupported development override.
- If a conflicting Workroot binding exists, report the existing Workroot and ask for an explicit rebind command.

### Security / Privacy

Clean Mode must not copy user content into global knowledge. Init may store canonical directory paths in local managed state. Native Agent Entry files must not contain private Workroot IDs, state directory paths, usernames, absolute system paths, logs, handoffs, or indexes unless a future explicit diagnostic mode is approved.

### Compatibility

Existing directories with user content must be supported. Existing `AGENTS.md` or `CLAUDE.md` files must not be overwritten; Native Agent Entry uses managed blocks defined in `012-native-agent-entry.spec.md`.

## Acceptance Criteria

AC-001:
Given a user-selected directory
When AI Workroot is initialized in Clean Mode without Native Agent Entry authorization
Then no default control files or generated folders are created inside that user directory.

AC-002:
Given a user-selected directory
When `workroot init --no-native-agent-entry` completes
Then managed state exists under AI Workroot home and not inside the user directory.

AC-003:
Given a user authorizes Codex Native Agent Entry
When init completes
Then only the authorized managed block is added to `AGENTS.md`.

AC-004:
Given an existing `AGENTS.md`
When Native Agent Entry is authorized
Then content outside the AI Workroot managed block is preserved.

AC-005:
Given init runs a permission test
When init completes or fails
Then no permission test file remains in the user directory.

AC-006:
Given Clean Mode init completes
When doctor runs
Then doctor reports Clean Mode as passing.

## Test Plan

### Unit Tests

- Test Clean Mode forbidden path detection.
- Test user directory permission test cleanup on success and failure.
- Test init option parsing for `--no-native-agent-entry` and `--native-agent-entry`.
- Test existing Native Agent Entry file merge behavior through the Native Agent Entry module.

### Integration Tests

- Initialize a temporary user directory and assert only authorized files appear.
- Initialize with custom `AI_WORKROOT_HOME` and assert state is created there.
- Initialize with existing `AGENTS.md` and assert only managed block changes.
- Run doctor after init and assert Clean Mode passes.

### Manual Verification

- Run install script and decline first Workroot creation.
- Run `workroot init --wizard` and decline Native Agent Entry.
- Inspect the user directory manually for generated state artifacts.

## Migration / Rollback

If init fails before registration, delete the partially created managed state directory. If init fails after registration, mark the Workroot registration as `failed` or remove it through a rollback journal. User directory files must not be removed except for temporary permission test files or authorized Native Agent Entry managed blocks.

## Observability / Debugging

Init should record a local managed-state setup event. Doctor should report:

- user directory path;
- managed state path;
- Clean Mode pass/fail;
- unauthorized generated files found in user directory;
- Native Agent Entry authorization status.

## Task Breakdown

T1: Add Clean Mode path guard
- Change: Implement detection for forbidden managed-state paths inside user directories.
- Files likely affected: future init module, `tests/`.
- Verification: Unit test rejects each forbidden path.

T2: Add permission test cleanup
- Change: Create and delete a random hidden permission test file.
- Files likely affected: future init module.
- Verification: Integration test confirms no test file remains.

T3: Add init registration flow
- Change: Create managed state and append Workroot registry and directory binding records.
- Files likely affected: future state module, CLI module.
- Verification: Init integration test inspects registry records.

T4: Add Native Agent Entry authorization
- Change: Wire explicit wizard and non-interactive flags into Native Agent Entry generation.
- Files likely affected: CLI module, Native Agent Entry module.
- Verification: Tests confirm no file write without authorization.

T5: Add post-init doctor
- Change: Run doctor-compatible checks after init.
- Files likely affected: CLI module, doctor module.
- Verification: Init fails or warns with actionable diagnostics when Clean Mode is violated.

## Risks

- Existing user directories may already contain `.workroot/` or similar folders unrelated to AI Workroot.
- Users may expect agent entry files to be created automatically for convenience.
- Permission tests can behave differently on network filesystems.
- Nested Workroots require careful nearest-binding behavior.

## Open Questions

None.
