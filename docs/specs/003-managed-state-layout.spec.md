# Spec: Managed State Layout

## Status

Draft

## Priority

P0

## Background

AI Workroot 0.9.529 requires managed state to live outside the user-selected directory by default. Managed state includes Workroot registries, context guides, context packages, debug traces, handoffs, tasks, indexes, runtime data, kernel data, internal metadata, logs, graph data, and caches.

This Spec defines AI Workroot home path resolution, global state layout, per-Workroot state layout, OS-specific defaults, and custom state directory behavior.

## Goals

- Provide a predictable local managed state location.
- Keep managed state outside user directories by default.
- Support `AI_WORKROOT_HOME` for custom state location.
- Define global and per-Workroot state directories.
- Preserve rebuildability for caches and generated stores.

## Non-goals

- This Spec does not define user directory initialization behavior.
- This Spec does not define each SQLite table.
- This Spec does not define Context Guide selection logic.
- This Spec does not define cloud sync or hosted state.

## Scope

### Included

- AI Workroot home path resolution.
- Global registry and global cache layout.
- Per-Workroot managed state layout.
- OS defaults for macOS, Linux, and Windows.
- Custom state directory behavior.
- Relationship to Clean Mode.

### Excluded

- Bootstrap flow details, covered by `004-bootstrap-process.spec.md`.
- Migration execution, covered by `005-migrations.spec.md`.
- SQLite table definitions, covered by `013-sqlite-cache-and-provenance-graph.spec.md`.
- Doctor checks, covered by `006-doctor-command.spec.md`.

## Dependencies

- Core project decisions: Clean Mode; managed state outside the user directory; controlled bootstrap; high-quality Context Guide; Materialized Context Candidates; local-first explainable retrieval without a P0 vector dependency; debug traces; branch-and-review Git workflow; English-first docs and comments.
- `001-project-structure-and-naming.spec.md`
- `002-clean-mode-installation.spec.md`
- `005-migrations.spec.md`
- `013-sqlite-cache-and-provenance-graph.spec.md`

## Requirements

### Functional Requirements

FR-001: AI Workroot home must resolve from `AI_WORKROOT_HOME` when set.

FR-002: On macOS and Linux, AI Workroot home must default to `~/.ai-workroot/` for 0.9.529.

FR-003: On Windows, AI Workroot home must default to `%LOCALAPPDATA%\AIWorkroot\`.

FR-004: Global registry files must live under `<AI_WORKROOT_HOME>/registry/`.

FR-005: Global indexes must live under `<AI_WORKROOT_HOME>/global-index/`.

FR-006: Global SQLite cache must live under `<AI_WORKROOT_HOME>/global-cache/global.sqlite`.

FR-007: Per-Workroot managed state must live under `<AI_WORKROOT_HOME>/workroots/<workrootId>/`.

FR-008: Per-Workroot context packages, debug traces, logs, graph exports, maintenance records, and cache must live under the per-Workroot managed state directory.

FR-009: Path resolution must reject or warn when the managed state directory is inside the user directory for Clean Mode.

FR-010: State layout initialization must be idempotent.

### Non-functional Requirements

NFR-001: State layout creation must work offline.

NFR-002: Paths must be stored in UTF-8 compatible JSON or JSONL.

NFR-003: The layout must be understandable and inspectable by advanced users.

NFR-004: Generated stores must be rebuildable unless a downstream Spec explicitly marks the graph store as primary with export and backup.

NFR-005: The layout must avoid admin permissions.

## Proposed Design

### Concepts

- AI Workroot home: Local user-level system space for all Workroot managed state.
- Global layer: Registry, directory bindings, aliases, relationships, global indexes, global cache, and user-level preferences.
- Per-Workroot state: Managed state for one Workroot, keyed by `workrootId`.
- Rebuildable store: A generated index or cache that can be rebuilt from canonical files and registries.

### Data Model

Global config:

```json
{
  "version": "0.9.529",
  "schemaVersion": "0.1",
  "createdAt": "2026-05-19T00:00:00Z",
  "defaultMode": "clean"
}
```

Per-Workroot metadata:

```json
{
  "version": "0.9.529",
  "schemaVersion": "0.1",
  "workrootId": "wr_example",
  "name": "Example Workroot",
  "mode": "clean",
  "userDirectory": "/path/to/user/directory",
  "stateDirectory": "/path/to/ai-workroot-home/workroots/wr_example",
  "createdAt": "2026-05-19T00:00:00Z",
  "updatedAt": "2026-05-19T00:00:00Z"
}
```

### File Layout

AI Workroot home:

```text
<AI_WORKROOT_HOME>/
  config.json
  registry/
    workroots.jsonl
    directory-bindings.jsonl
    aliases.jsonl
    relationships.jsonl
  agent-guides/
    common.md
    codex.md
    claude-code.md
  user/
    profile.md
    preferences.md
    global-principles.md
    agent-overrides/
  global-index/
    workroots.index.jsonl
    tasks.index.jsonl
    assets.index.jsonl
    knowledge.index.jsonl
    decisions.index.jsonl
    handoffs.index.jsonl
    time.index.jsonl
  global-cache/
    global.sqlite
  workroots/
    <workrootId>/
      workroot.json
      agent/
      state/
      tasks/
      handoffs/
      assets/
      knowledge/
      graph/
      indexes/
      context/
      maintenance/
      concurrency/
      logs/
      cache/
```

The user-selected directory must not receive this layout in Clean Mode.

### CLI / API

Required resolver API behavior:

```text
resolve_ai_workroot_home(env, platform) -> Path
resolve_workroot_state_dir(workroot_id) -> Path
assert_clean_mode_boundary(user_directory, state_directory)
```

Relevant CLI:

```bash
workroot status
workroot doctor
workroot init
```

### Runtime Behavior

All commands that need managed state must resolve AI Workroot home before reading or writing. Commands must create missing parent directories only for the state they own and only after path boundary checks pass.

Nested Workroots are allowed. The nearest registered directory binding resolves the current Workroot, and each Workroot has isolated managed state.

### Error Handling

- If `AI_WORKROOT_HOME` is set to an invalid path, fail with the invalid path and reason.
- If state initialization lacks permission, fail with the state path and required permission.
- If state path is inside the user directory in Clean Mode, fail with a Clean Mode boundary error.
- If `workroot.json` is missing or malformed, doctor should suggest bootstrap, migration, or repair actions.

### Security / Privacy

Managed state is local and may contain summaries, paths, indexes, context packages, traces, logs, and graph relationships. It must not be silently synced or sent to remote services. Permissions should be user-level. Secrets should not be written to debug traces or agent entry files.

### Compatibility

0.9.529 uses `~/.ai-workroot/` for macOS and Linux even though future versions may support XDG paths. Future path migrations must be handled by `005-migrations.spec.md`.

## Acceptance Criteria

AC-001:
Given `AI_WORKROOT_HOME` is set
When a command resolves AI Workroot home
Then the override path is used.

AC-002:
Given no override on macOS or Linux
When a command resolves AI Workroot home
Then `~/.ai-workroot/` is used.

AC-003:
Given no override on Windows
When a command resolves AI Workroot home
Then `%LOCALAPPDATA%\AIWorkroot\` is used.

AC-004:
Given a Clean Mode user directory
When managed state is initialized
Then state is created under `<AI_WORKROOT_HOME>/workroots/<workrootId>/`.

AC-005:
Given a managed state path inside the user directory
When Clean Mode boundary validation runs
Then the command fails before writing state.

## Test Plan

### Unit Tests

- Test AI Workroot home resolution with and without `AI_WORKROOT_HOME`.
- Test platform-specific defaults.
- Test boundary validation for state inside user directory.
- Test idempotent layout creation.

### Integration Tests

- Initialize a Workroot with temporary `AI_WORKROOT_HOME`.
- Resolve nested Workroots and assert nearest binding wins.
- Run `workroot status` against initialized state.

### Manual Verification

- Inspect generated AI Workroot home after init.
- Confirm user directory has no managed layout.
- Confirm Windows path behavior in a Windows environment or CI job.

## Migration / Rollback

Initial layout creation must use a transaction or rollback journal. If any required directory or file cannot be created, remove newly created empty directories when safe and mark partial state as failed if registry records were already written.

Future migrations must use `005-migrations.spec.md` and must not move user assets.

## Observability / Debugging

Doctor and `workroot status` should report:

- resolved AI Workroot home;
- current Workroot ID;
- user directory;
- managed state directory;
- schema version;
- layout health.

Debug output must avoid printing secrets or file contents.

## Task Breakdown

T1: Add path resolver
- Change: Implement `AI_WORKROOT_HOME` and platform default resolution.
- Files likely affected: future path module, CLI module.
- Verification: Unit tests for macOS, Linux, Windows, and override.

T2: Add layout initializer
- Change: Create global and per-Workroot directories idempotently.
- Files likely affected: future state module.
- Verification: Integration test verifies all required directories.

T3: Add boundary guard
- Change: Reject Clean Mode state paths inside user directories.
- Files likely affected: future state module, init module.
- Verification: Unit test covers direct and nested path violations.

T4: Add status inspection
- Change: Show resolved state paths and schema metadata.
- Files likely affected: CLI module.
- Verification: CLI test checks output fields.

## Risks

- Environment overrides can point to removable or network drives with unusual behavior.
- Existing users may expect state inside the project from the public seed architecture.
- Windows path normalization can cause duplicate bindings if not canonicalized.

## Open Questions

None.
