# Agent Operation Layer Specification

## Purpose

AI Workroot v0.9.528 will keep the file-first architecture and add a thin Agent Operation Layer.

The goal is to make ordinary agent work fast, deterministic, and safe without requiring agents to read long documents, inspect source code, or discover CLI behavior by trial and error.

This specification addresses the issues found during the four demo stress runs:

- global agent skills such as Superpowers can add startup cost and should not be treated as Workroot startup context
- Workroot startup context is still too broad for ordinary tasks
- CLI happy paths are not obvious
- registry writes are not concurrency-safe
- Mind source/path semantics are confusing
- task updates overwrite the global human continuation page
- multi-task sessions need a separate session-level continuation update

## Scope

In scope for v0.9.528:

- add a compact agent fast-start file
- add a user-owned startup guidance extension point
- adjust startup read order to prefer fast-start over long product contracts
- add CLI discovery commands
- add CLI happy-path and batch commands
- add registry locking and atomic writes
- fix Mind path/source semantics while preserving compatibility
- stop Mind promotion from overwriting task user-visible outputs by default
- separate task-local updates from session/global continuation updates
- add tests for concurrency, happy path, Mind behavior, and continuation aggregation

Out of scope for v0.9.528:

- HTTP server
- FTP server
- background daemon
- database as source of truth
- workflow engine
- replacing CSV registries
- changing the core `space/ + .workroot/` architecture

## Architecture

The file-first Workroot remains the source of truth.

The new Agent Operation Layer is a convenience and safety layer made of:

- compact startup instructions
- a machine-readable Agent Operation Manifest
- high-level CLI commands
- a registry storage helper with locking and atomic writes
- batch operations for common task flows
- session-level continuation commands

The layer must reduce agent reasoning and file reading, not hide durable state in a service.

Normal agents should read:

```bash
python3 scripts/workroot_cli.py manifest --format json
python3 scripts/workroot_cli.py schema --format json
python3 scripts/workroot_cli.py recipe batch-12-tasks --format json
```

They should not read `scripts/workroot_client.py` unless debugging or changing AI Workroot itself.

## Agent Fast Start

Create:

```text
.workroot/kernel/boot/agent-fast-start.md
```

This file is the first agent-facing operational shortcut. It should be short enough to read on every meaningful Workroot task.

It must explain:

- pure greeting: answer directly; do not read workspace files
- user startup guidance: for meaningful work, read optional `space/profile/startup.md` after kernel fast-start
- continue intent: read `space/work/continue.md`, then `.workroot/runtime/context/handoff.md`, then only relevant task briefs
- new formal task: use CLI happy path; do not ask the user to manage internal folders
- preservation: prefer high-level CLI commands over manual registry edits
- task lookup: use `.workroot/runtime/index/task_registry.csv` before reading task directories
- deep context: read long docs only when editing product behavior, protocol behavior, architecture, or kernel
- external skills: skills are not Workroot startup context unless the user explicitly asks for them

### How Agents Read It

Agents do not discover `agent-fast-start.md` by intuition.

It is loaded through the Workroot entrypoint chain:

1. Root `AGENTS.md` tells agents the default startup context.
2. `.workroot/kernel/boot/read-order.json` lists the default read order.
3. `agent-fast-start.md` is included in that default read order.
4. Long documents such as `docs/user-interaction-contract.md` remain conditional.

Proposed default read order:

```json
[
  "AGENTS.md",
  "START_HERE_FOR_HUMANS.md",
  ".workroot/kernel/boot/boot.md",
  ".workroot/kernel/boot/agent-fast-start.md",
  ".workroot/kernel/agent/output_style.md",
  ".workroot/kernel/boot/read-order.json"
]
```

`docs/user-interaction-contract.md` should move out of the default read order. It should be read only when first-use behavior is unclear, product behavior is being edited, or user experience rules need deeper guidance.

## User Startup Guidance

`AGENTS.md` and `.workroot/kernel/*` define the Workroot protocol. Users should not edit kernel files to customize ordinary startup behavior.

Add one optional user-owned startup file:

```text
space/profile/startup.md
```

This file is for durable user or team guidance that should shape meaningful work, such as collaboration style, output preferences, business terms, project conventions, and team boundaries.

It is not read for a pure greeting.

It is read only after the kernel fast-start when the user starts or continues meaningful work:

1. read the kernel startup context
2. read `.workroot/kernel/boot/agent-fast-start.md`
3. if it exists, read `space/profile/startup.md`
4. if continuing work, read `space/work/continue.md`
5. read only relevant task context

Priority:

```text
latest explicit user instruction
> Workroot kernel protocol
> user startup guidance
> current task context
> external skills and agent defaults
```

The user startup file can guide style, preferences, and team conventions.
It cannot override kernel protocol, safety rules, registry discipline,
or internal subject-anchor rules for durable preservation.

The file should remain short. If it grows too large, a future version should add a generated summary rather than making agents read a long custom document at startup.

## CLI Discovery

Add commands:

```bash
python3 scripts/workroot_cli.py quickstart
python3 scripts/workroot_cli.py manifest --format json
python3 scripts/workroot_cli.py schema
python3 scripts/workroot_cli.py schema --format json
python3 scripts/workroot_cli.py recipe task-l0-report
python3 scripts/workroot_cli.py recipe task-l1-report
python3 scripts/workroot_cli.py recipe task-l2-evidence
python3 scripts/workroot_cli.py recipe batch-12-tasks --format json
python3 scripts/workroot_cli.py doctor
```

`quickstart` prints the smallest useful command sequence for common agent work.

`manifest --format json` prints the operation contract agents should use instead of reading implementation source.

`schema` prints machine-readable and human-readable constraints:

- task statuses
- process levels
- owner scopes
- visibility values
- action types
- artifact audiences
- Mind types
- Mind temperatures
- release levels
- single-path registry fields
- multi-path registry fields
- timestamp rules

`recipe` prints executable examples for common flows.

`doctor` checks the current Workroot state and explains validation failures in operational language.

These commands exist so agents do not read `workroot_client.py` or `validate_kernel.py` just to learn valid values.

## CLI Happy Paths

Add high-level commands:

```bash
python3 scripts/workroot_cli.py task complete ...
python3 scripts/workroot_cli.py batch apply --file plan.json
python3 scripts/workroot_cli.py session summarize ...
python3 scripts/workroot_cli.py continue rebuild ...
```

### `task complete`

`task complete` handles the most common single-task completion flow:

- create or update task state
- write a user-visible report
- register an artifact with size and sha256
- optionally add run
- optionally add action
- optionally add retrieval card
- optionally add checkpoint
- optionally promote Mind
- update task `brief.md`, `handoff.md`, `todo.md`, and `index.md`

It must not update global `space/work/continue.md` unless explicitly requested.

### `batch apply`

`batch apply` accepts a JSON plan and applies several operations under one registry lock.

It is the preferred path for multi-record updates because it reduces repeated process startup and avoids partial registry writes.

The v0.9.528 implementation uses a transaction journal under:

```text
.workroot/runtime/transactions/
```

Before applying operations, it backs up the file-first areas that batch operations can touch:

- `.workroot/runtime/index`
- `.workroot/runtime/work/tasks`
- `.workroot/runtime/context`
- `space/work`
- `space/mind`
- explicit artifact, Mind, or invalidation paths named in the batch plan

If any later operation fails, the batch restores those areas and records journal status `rolled_back`. If all operations succeed, the journal records `committed`.

For v0.9.528, `batch apply` should support common lightweight operations:

- `task.create`
- `task.update`
- `run.add`
- `artifact.add`
- `action.add`
- `checkpoint.add`
- `retrieval_card.add`
- `invalidation.add`
- `mind.add`
- `session.summarize`

It is not a workflow engine. It must not add branching, retries, scheduling, dependency graphs, or background execution.

The following heavier semantic operations remain outside batch support for v0.9.528:

- `decision.add`
- release operations
- forget/tombstone operations

### `session summarize`

`session summarize` updates session/global human continuation state:

- `space/work/continue.md`
- `.workroot/runtime/context/current.md`
- `.workroot/runtime/context/handoff.md`

It accepts explicit task ids and produces a multi-task summary.

For multi-task sessions, agents can pass `--from-registry --recent N` to select active, paused, blocked, and recent closed/released tasks without constructing a long command line.

### `continue rebuild`

`continue rebuild` derives a continuation page from registries.

It should:

- read `task_registry.csv`
- select active, paused, blocked, and recent closed tasks
- optionally filter by priority
- read only selected task `brief.md` or `handoff.md`
- write a human-readable `space/work/continue.md`

It must not scan every task directory unless requested with an explicit deep mode.

## Registry Store

Create a small registry storage helper inside `scripts/workroot_client.py` or a new focused module:

```text
scripts/workroot_registry.py
```

Responsibilities:

- ensure registry headers
- read rows
- append rows
- update rows
- serialize writers with a filesystem lock
- write through a temporary file
- atomically replace the target CSV

Lock path:

```text
.workroot/runtime/locks/workroot.lock
```

Transaction journal path:

```text
.workroot/runtime/transactions/
```

The CSV files remain the source of truth. The lock protects file-first writes; it does not introduce a daemon.

## Mind Path And Source Semantics

Current behavior:

```bash
mind add --source-path ...
```

acts as the Mind entry path, not the source path. This is confusing.

New behavior:

- `--path`: explicit Mind entry path
- `--from-path`: source file path
- `--from-task-id`: source task id
- `--source-path`: deprecated compatibility alias for `--path`

Mind entries still write `mind_registry.source_path` as the Mind entry file path because that is the existing registry schema.

Source relationships should be written to `link_registry.csv`:

- `file -> mind`
- `task -> mind`
- `artifact -> mind` when available

Mind promotion must not change the task `user_visible_output_path` by default. Reports remain the normal user-visible output.

If an agent intentionally wants the Mind entry to become the task output, it must pass:

```bash
--set-task-output
```

## Continuation Model

`space/work/continue.md` is a human-facing continuation page. It is not the source of truth and it is not a single-task status file.

Task-local operations must update only task-local files:

- `task.json`
- `brief.md`
- `handoff.md`
- `todo.md`
- `index.md`
- task row in `task_registry.csv`

Global continuation must be updated only by:

- `session summarize`
- `continue rebuild`
- explicit global update options

This prevents the last task update in a multi-task session from overwriting the entire continuation view.

## Superpowers And External Skills

Superpowers are external agent behavior, not AI Workroot protocol.

AI Workroot must not require Superpowers.

Recommended operating modes:

- ordinary Workroot user mode: disable Superpowers or use a clean agent profile
- AI Workroot engineering mode: Superpowers may be enabled for planning, debugging, TDD, and verification

The Workroot startup contract should state that external skills/plugins are not part of the default Workroot read context unless the user explicitly requests them.

## Backward Compatibility

Existing commands must continue to work.

Compatibility rules:

- keep `mind add --source-path` working as a deprecated alias for `--path`
- keep existing registry schemas for v0.9.528
- do not remove current task, run, action, artifact, checkpoint, retrieval-card, invalidation, or Mind commands
- add warnings in CLI help where a parameter is deprecated or easily confused

## Tests

Add or update tests for:

- default read order includes `agent-fast-start.md`
- default read order excludes `docs/user-interaction-contract.md`
- startup contract documents optional `space/profile/startup.md`
- pure greeting path does not require reading `space/profile/startup.md`
- `quickstart`, `schema`, and `recipe` print expected constraints and examples
- registry writes are atomic
- concurrent registry append/update does not corrupt headers or lose rows
- `mind add --path` writes Mind entry path
- `mind add --from-path` creates link registry relationships
- `mind add` does not overwrite task user-visible output by default
- `task complete` creates report, artifact metadata, and task state
- `batch apply` applies common lightweight records under one transaction
- `session summarize` writes multi-task continuation
- `continue rebuild` reads registry first and only selected task briefs
- `validate_kernel.py` passes after each happy-path recipe
- `validate_kernel.py --release` passes after release-safe demo flows

## Acceptance Criteria

The v0.9.528 implementation is accepted when:

- a new agent can learn the happy path from `agent-fast-start.md` and `workroot_cli.py quickstart`
- users have a documented startup customization point outside kernel files
- no agent needs to read `workroot_client.py` or `validate_kernel.py` to discover normal CLI usage
- four demo roles can complete L0/L1/L2 flows with materially fewer CLI calls
- concurrent registry writes do not produce header mismatch
- Mind promotion does not replace report output unless explicitly requested
- multi-task sessions produce a combined `continue.md`
- all tests pass
- `python3 scripts/validate_kernel.py` passes
- `python3 scripts/validate_kernel.py --release` passes
