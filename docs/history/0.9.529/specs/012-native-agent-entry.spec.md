# Spec: Native Agent Entry

## Status

Draft

## Priority

P0

## Background

Native Agent Entry lets Codex and Claude Code enter Workroot mode naturally when users open a Workroot directory. The architecture allows `AGENTS.md` and `CLAUDE.md` in the user directory because they are agent-native entry files, not managed Workroot state. However, Clean Mode requires explicit authorization before AI Workroot writes generated files into the user directory.

## Goals

- Provide optional Native Agent Entry files for Codex and Claude Code.
- Preserve Clean Mode by requiring explicit authorization.
- Avoid absolute paths, state paths, private IDs, handoffs, logs, indexes, and runtime state in entry files.
- Keep entry files short; they are launch instructions, not full Workroot Context Packages.
- Preserve existing user content through managed blocks.
- Keep hooks out of 0.9.529.

## Non-goals

- This Spec does not define Hooks integration.
- This Spec does not define MCP server integration.
- This Spec does not make Native Agent Entry mandatory.
- This Spec does not store managed state in user entry files.

## Scope

### Included

- `AGENTS.md` and `CLAUDE.md` generation and update rules.
- Managed block format.
- Authorization requirements.
- Agent command content.
- Entry file size and content boundaries.
- Existing file preservation.

### Excluded

- Clean Mode init flow, covered by `002-clean-mode-installation.spec.md`.
- CLI command matrix, covered by `011-cli-user-flows.spec.md`.
- Context Guide internals, covered by `007-context-guide-builder.spec.md`.
- Context mode and token budget policy, covered by `015-context-guide-modes-budgets-and-confidence.spec.md`.

## Dependencies

- Core project decisions: Clean Mode; managed state outside the user directory; controlled bootstrap; high-quality Context Guide; Materialized Context Candidates; local-first explainable retrieval without a P0 vector dependency; debug traces; branch-and-review Git workflow; English-first docs and comments.
- `001-project-structure-and-naming.spec.md`
- `002-clean-mode-installation.spec.md`
- `007-context-guide-builder.spec.md`
- `011-cli-user-flows.spec.md`
- `015-context-guide-modes-budgets-and-confidence.spec.md`

## Requirements

### Functional Requirements

FR-001: Native Agent Entry file creation must require explicit user authorization.

FR-002: Codex entry must use `AGENTS.md`.

FR-003: Claude Code entry must use `CLAUDE.md`.

FR-004: Entry files must instruct agents to run `workroot context --agent <agent> --cwd .`.

FR-005: Entry files must not contain absolute system paths.

FR-006: Entry files must not contain managed state directory paths.

FR-007: Entry files must not contain private Workroot IDs when avoidable.

FR-008: Entry files must not contain runtime state, handoffs, logs, indexes, or debug traces.

FR-009: Existing files must not be overwritten.

FR-010: Updates must be limited to `<!-- AI_WORKROOT_BEGIN -->` and `<!-- AI_WORKROOT_END -->` managed blocks.

FR-011: Hooks must not be used in 0.9.529.

FR-012: Entry files must remain concise and must not embed a full Context Package.

FR-013: Entry files must describe fallback behavior if `workroot context` fails.

FR-014: Entry files must mention that Workroot managed state must not be written into the user directory.

FR-015: Entry files may recommend agent-appropriate context commands but must not hardcode token budgets or latency policy.

### Non-functional Requirements

NFR-001: Entry files must be short enough for agents to read quickly; target size is 1-3 KB per entry file.

NFR-002: Entry files must be portable across machines.

NFR-003: Entry files must be safe to commit in user projects if the user chooses.

NFR-004: Entry file generation must be idempotent.

NFR-005: Entry content must be English-first.

## Proposed Design

### Concepts

- Native Agent Entry file: Agent-native instruction file in the user directory.
- Managed block: The only section AI Workroot owns inside an entry file.
- Authorization: Explicit wizard answer or CLI flag permitting entry file creation or update.

### Data Model

Native Agent Entry config:

```json
{
  "codex": true,
  "claudeCode": true,
  "authorizedAt": "2026-05-19T00:00:00Z",
  "managedBlockVersion": "0.1"
}
```

### File Layout

Optional user directory files:

```text
AGENTS.md
CLAUDE.md
```

Managed block:

````md
<!-- AI_WORKROOT_BEGIN -->
...
<!-- AI_WORKROOT_END -->
````

No other user directory files are part of Native Agent Entry in P0.

### CLI / API

Relevant CLI:

```bash
workroot init --native-agent-entry codex,claude
workroot init --no-native-agent-entry
workroot agent sync
```

`workroot agent sync` is P1. P0 may implement sync behavior through init and bootstrap only.

### Runtime Behavior

Generation rules:

1. Check authorization.
2. Read existing file if present.
3. If managed block exists, replace only managed block.
4. If no managed block exists, append managed block with clear separation.
5. Preserve all user content outside managed block.
6. Validate generated content for forbidden paths and state details.

Codex block content:

````md
<!-- AI_WORKROOT_BEGIN -->
# AI Workroot Agent Entry

Before answering, editing, creating files, or making decisions in this directory, obtain the current Workroot context:

```bash
workroot context --agent codex --cwd .
```

Use the returned Context Package for current focus, active task, recent decisions, handoffs, artifact guidance, and write-routing rules.

Do not write Workroot managed state into this directory.

If the context command fails, keep working from explicit user instructions only for low-risk questions, and ask the user to run `workroot doctor` before making major changes.
<!-- AI_WORKROOT_END -->
````

Claude block content should reference `AGENTS.md` when present and run:

```bash
workroot context --agent claude --cwd .
```

### Error Handling

- If authorization is missing, do not write files.
- If a file cannot be read, abort without writing.
- If a file has malformed managed block markers, abort and ask for manual review.
- If generated content contains forbidden absolute paths or state paths, abort.
- If write fails, preserve original file.

### Security / Privacy

Entry files may be committed or shared by users. They must not contain private local paths, state locations, IDs, logs, handoff text, debug trace content, or indexes.

### Compatibility

Existing `AGENTS.md` and `CLAUDE.md` files may belong to user projects. Managed block updates must preserve existing content. If `CLAUDE.md` supports including `AGENTS.md`, the generated block may use that pattern only when safe.

## Acceptance Criteria

AC-001:
Given no authorization
When init runs
Then no `AGENTS.md` or `CLAUDE.md` file is created.

AC-002:
Given Codex authorization
When entry generation runs
Then `AGENTS.md` contains an AI Workroot managed block instructing `workroot context --agent codex --cwd .`.

AC-003:
Given an existing `AGENTS.md` with user content
When entry generation runs
Then user content outside the managed block is unchanged.

AC-004:
Given a generated entry file
When content is inspected
Then it contains no absolute state path, private Workroot ID, logs, handoffs, indexes, or debug traces.

AC-005:
Given malformed managed block markers
When entry generation runs
Then it aborts and does not rewrite the file.

AC-006:
Given a generated entry file
When its content is inspected
Then it is a short launcher that tells agents to run `workroot context`, not a full Context Package.

AC-007:
Given a generated entry file
When `workroot context` fails
Then the entry instructions tell agents to use low-risk explicit user instructions only and ask for `workroot doctor` before major changes.

## Test Plan

### Unit Tests

- Test managed block insertion into empty and existing files.
- Test managed block replacement.
- Test malformed marker detection.
- Test forbidden content validation.
- Test authorization gate.
- Test generated file size stays within the configured entry-file target.
- Test fallback instruction is present.

### Integration Tests

- Run Clean Mode init with and without Native Agent Entry.
- Run bootstrap-dev and verify authorized entry updates.
- Confirm existing file content is preserved.

### Manual Verification

- Open generated entry files and read them as Codex and Claude Code would.
- Confirm no private local path appears.
- Confirm hooks are not installed.

## Migration / Rollback

Rollback of Native Agent Entry should remove or replace only the managed block when explicitly requested. It must not delete user-authored content or remove files entirely unless the file was created by AI Workroot and the user explicitly approves deletion.

## Observability / Debugging

Doctor should report Native Agent Entry status:

- not configured;
- configured for Codex;
- configured for Claude Code;
- malformed block;
- forbidden content detected.

## Task Breakdown

T1: Add managed block utility
- Change: Insert, replace, and validate managed blocks.
- Files likely affected: Native Agent Entry module.
- Verification: Unit tests for file merge cases.

T2: Add generated content templates
- Change: Add concise Codex and Claude Code managed block templates with context command, fallback behavior, and no embedded Context Package.
- Files likely affected: Native Agent Entry module, templates if used.
- Verification: Snapshot tests.

T3: Add authorization gate
- Change: Require init/bootstrap flags or wizard answer before writing.
- Files likely affected: init module, bootstrap module, CLI module.
- Verification: Integration test confirms no unauthorized files.

T4: Add doctor check
- Change: Validate managed blocks and forbidden content.
- Files likely affected: doctor module.
- Verification: Doctor fixture detects malformed block.

## Risks

- Users may already rely on custom `AGENTS.md` or `CLAUDE.md` semantics.
- Entry files could accidentally expose local paths if templates are not validated.
- Default-enabled entry files would conflict with Clean Mode expectations, so explicit authorization is required.

## Open Questions

None.
