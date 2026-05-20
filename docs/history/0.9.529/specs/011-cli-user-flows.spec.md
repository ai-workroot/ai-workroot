# Spec: CLI User Flows

## Status

Draft

## Priority

P0

## Background

AI Workroot 0.9.529 needs a minimal but coherent CLI path for installation, initialization, bootstrap, status, doctor, and context generation. The CLI must preserve Clean Mode safe defaults and avoid requiring users to understand managed state internals.

## Goals

- Define P0 CLI commands and safe defaults.
- Support init, bootstrap-dev, doctor, status, list, and context generation.
- Keep ordinary user flows simple.
- Keep developer bootstrap explicit.
- Avoid hidden writes to the user directory.

## Non-goals

- This Spec does not define a GUI.
- This Spec does not define MCP server behavior.
- This Spec does not define cloud account setup.
- This Spec does not define future task, knowledge, or semantic recall commands.

## Scope

### Included

- P0 command behavior.
- Install-to-first-Workroot flow.
- Clean Mode CLI defaults.
- Context generation command behavior.
- Context mode, Deep request, debug, and budget override command behavior.
- Bootstrap developer command surface.
- Safe error messages.

### Excluded

- Native Agent Entry content details, covered by `012-native-agent-entry.spec.md`.
- Doctor checks, covered by `006-doctor-command.spec.md`.
- Release policy, covered by `014-release-and-test-gates.spec.md`.

## Dependencies

- Core project decisions: Clean Mode; managed state outside the user directory; controlled bootstrap; high-quality Context Guide; Materialized Context Candidates; local-first explainable retrieval without a P0 vector dependency; debug traces; branch-and-review Git workflow; English-first docs and comments.
- `001-project-structure-and-naming.spec.md`
- `002-clean-mode-installation.spec.md`
- `003-managed-state-layout.spec.md`
- `004-bootstrap-process.spec.md`
- `006-doctor-command.spec.md`
- `007-context-guide-builder.spec.md`
- `012-native-agent-entry.spec.md`
- `015-context-guide-modes-budgets-and-confidence.spec.md`

## Requirements

### Functional Requirements

FR-001: P0 CLI must include `workroot init`.

FR-002: P0 CLI must include `workroot list`.

FR-003: P0 CLI must include `workroot status`.

FR-004: P0 CLI must include `workroot context`.

FR-005: P0 CLI must include `workroot doctor`.

FR-006: P0 CLI must include `workroot bootstrap-dev`.

FR-007: `workroot init` must default to Clean Mode.

FR-008: `workroot context` must not perform heavy maintenance on the hot path.

FR-009: `workroot bootstrap-dev` must be clearly labeled developer-only.

FR-010: CLI must not create Native Agent Entry files without explicit authorization.

FR-011: CLI must support text output for users and JSON output where useful for tooling.

FR-012: CLI help must use Workroot terminology consistently.

FR-013: `workroot context` must support `--mode fast|standard|quality`.

FR-014: `workroot context` must support explicit `--deep`.

FR-015: `workroot context` must support `--target-tokens` and `--max-latency-ms` overrides bounded by runtime configuration.

FR-016: `workroot context` output must include Context Metadata with mode, confidence, latency, token usage, and fallback status.

FR-017: `workroot context --debug` must include mode, confidence, budget, challenger counts, selected candidates, filtered candidates, and timing in the debug trace.

### Non-functional Requirements

NFR-001: CLI P0 flows must work offline.

NFR-002: CLI must not require admin permissions.

NFR-003: CLI errors must be actionable and concise.

NFR-004: CLI must support macOS, Linux, and Windows paths.

NFR-005: CLI must be testable through subprocess integration tests.

## Proposed Design

### Concepts

- User flow: A small command sequence that produces a useful result.
- Safe default: Behavior that avoids hidden user directory writes and remote calls.
- Developer command: Command intended for maintainers, not ordinary users.

### Data Model

CLI commands operate on data models defined in other Specs:

- Workroot registry;
- directory bindings;
- managed state metadata;
- Context Package;
- doctor result.

### File Layout

CLI must write:

```text
<AI_WORKROOT_HOME>/
```

CLI may write inside user directory only for:

```text
AGENTS.md
CLAUDE.md
```

and only after explicit authorization, or for user-requested product artifacts unrelated to managed state in future flows.

### CLI / API

P0 commands:

```bash
workroot init
workroot init --wizard
workroot list
workroot status
workroot context --agent codex --cwd .
workroot context --agent codex --cwd . --debug
workroot context --agent codex --cwd . --mode fast
workroot context --agent codex --cwd . --mode standard
workroot context --agent codex --cwd . --mode quality
workroot context --agent codex --cwd . --deep
workroot context --agent codex --cwd . --target-tokens 4000
workroot context --agent codex --cwd . --max-latency-ms 3000
workroot doctor
workroot doctor --format json
workroot bootstrap-dev
```

P1 commands:

```bash
workroot refresh
workroot search
workroot stats
workroot graph export
workroot cache rebuild
workroot agent sync
```

Future commands:

```bash
workroot mcp
workroot task promote
workroot knowledge organize
workroot trace
```

### Runtime Behavior

Install flow:

1. Install CLI to user-level binary location.
2. Create AI Workroot home and global config.
3. Ask whether to create first Workroot.
4. If yes, run `workroot init --wizard`.

Init flow:

1. Ask Workroot name.
2. Choose existing or new directory.
3. Validate permissions.
4. Check nested Workroots.
5. Create managed state.
6. Optionally create Native Agent Entry files after authorization.
7. Run doctor.

Context flow:

1. Resolve Workroot from cwd.
2. Resolve Context Guide mode, runtime hints, and agent token budget.
3. Generate Context Package.
4. Write managed package and optional trace.
5. Print package.

### Error Handling

- Unknown command: show closest P0 commands.
- No Workroot resolved: suggest `workroot init`.
- Pending migration: suggest migration command or doctor.
- Dirty Clean Mode boundary: suggest doctor details.
- Context unavailable: suggest `workroot doctor`.
- Invalid context mode: show supported modes.
- Deep context unavailable or reserved: explain that `--deep` is explicit and report the supported behavior for this version.
- Token or latency override beyond hard limit: reject or cap consistently and show the configured bound.

### Security / Privacy

CLI must not call remote services in P0 flows. CLI must not print file bodies or secrets in ordinary output. Debug output must be opt-in.

### Compatibility

Install locations:

```text
macOS/Linux: ~/.local/bin/workroot
Windows: %LOCALAPPDATA%\AIWorkroot\bin\workroot.exe
```

P0 CLI may initially be implemented in Python standard library or a packaged binary, but behavior must remain stable.

## Acceptance Criteria

AC-001:
Given a new installation
When install completes
Then AI Workroot home exists and no user Workroot is created unless the user chooses it.

AC-002:
Given `workroot init --wizard`
When the user declines Native Agent Entry
Then the user directory receives no generated files.

AC-003:
Given a registered Workroot
When `workroot context --agent codex --cwd .` runs
Then a Context Package with Context Metadata is printed.

AC-004:
Given a registered Workroot
When `workroot doctor --format json` runs
Then valid JSON is printed.

AC-005:
Given `workroot bootstrap-dev`
When the current directory is not the AI Workroot repository
Then the command aborts with a developer preflight message.

AC-006:
Given `workroot context --agent codex --cwd . --mode quality --debug`
When the command runs
Then output and debug trace record Quality Mode or an explicit reserved-mode fallback.

AC-007:
Given `workroot context --agent codex --cwd . --deep`
When the command runs
Then Deep Mode is treated as explicitly requested and is not silently substituted without trace.

AC-008:
Given `workroot context --target-tokens 999999`
When the configured hard limit is lower
Then the CLI rejects or caps the override and reports the bound.

## Test Plan

### Unit Tests

- Test argument parsing.
- Test command help copy.
- Test safe default option values.
- Test error message mapping.
- Test context mode and budget flag parsing.
- Test invalid context mode errors.

### Integration Tests

- Run `workroot init` in a temporary directory.
- Run `workroot list` and `workroot status`.
- Run `workroot context` and `workroot doctor`.
- Run `workroot context --mode quality --debug`.
- Run `workroot context --deep`.
- Run `workroot bootstrap-dev` preflight in valid and invalid directories.

### Manual Verification

- Install on macOS/Linux.
- Install on Windows.
- Run first Workroot wizard and inspect user directory cleanliness.

## Migration / Rollback

CLI commands rely on migration readiness from `005-migrations.spec.md`. If a command starts a transaction and fails, it must rollback its managed state writes or mark state as failed with recovery instructions.

## Observability / Debugging

CLI should support `--debug` only where useful and safe. Doctor and Context Guide debug traces are primary observability surfaces. CLI errors should include command suggestions.

Context CLI debug behavior must surface trace path or JSON fields that include mode, confidence, token budget, selected candidates, filtered candidates, and timing.

## Task Breakdown

T1: Add P0 command skeleton
- Change: Add command parser for init, list, status, context, doctor, and bootstrap-dev.
- Files likely affected: CLI module.
- Verification: CLI help tests.

T2: Wire init and list/status
- Change: Connect Clean Mode init and registry listing.
- Files likely affected: CLI module, state module.
- Verification: Init/list/status integration test.

T3: Wire context and doctor
- Change: Connect Context Guide and Doctor to CLI, including mode, Deep, debug, token, and latency flags.
- Files likely affected: CLI module, context module, doctor module.
- Verification: CLI integration tests.

T4: Wire bootstrap-dev
- Change: Connect developer bootstrap flow.
- Files likely affected: CLI module, bootstrap module.
- Verification: Bootstrap preflight tests.

T5: Add install script CLI flow
- Change: Add user-level install scripts and first Workroot prompt.
- Files likely affected: `scripts/install.sh`, `scripts/install.ps1`.
- Verification: Script syntax and manual install checks.

## Risks

- CLI can become too broad if P1 commands enter P0.
- Wizard defaults can accidentally authorize user directory writes.
- Existing scripts use project-local CLI names and may need careful transition.

## Open Questions

None.
