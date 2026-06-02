# Live Task Continuity E2E Design

Date: 2026-06-01
Target release line: 0.9.531
Branch: `feat/0.9.531-agent-protocol-task-continuity`

## Purpose

Add an opt-in remote E2E suite that validates the Workroot private packet protocol and task-continuity model across five realistic roles. The suite is not part of default local tests or release validation. It is a high-cost live audit for Codex Client, the remote model, and Workroot persistence.

## Scope

The suite covers five roles:

- founder/operator long-cycle planning
- software engineer implementation work
- analyst/researcher investigation work
- inbox/adhoc temporary conversation
- product manager multi-session planning

Each role runs 10 rounds by default and supports 1-20 rounds for debugging or pressure runs. The official confidence run is 10 or more rounds per role.

## Safety

All writes happen under the E2E `run-root` sandbox. The harness must never clean, delete, or quarantine paths outside a validated `run-*` sandbox root with sentinels. Workroot command logs, command stdout/stderr artifacts, transcripts, and audit reports are written under `run-root/transcripts` and `run-root/reports`, never into the user directory.

The user directory may contain only initial user files, native Agent entry files, and expected user-visible assets created by the scenario. Runtime files such as command logs, JSON request files, transcripts, SQLite files, cache folders, and debug summaries are treated as pollution.

## Protocol Coverage

Each role should exercise:

- startup/context alignment
- `sync`
- `commit --shape start-work`
- `commit --shape checkpoint`
- `commit --shape continuation`

Across the five-role suite, at least one role should exercise:

- temporary task creation with `persistence=temporary`
- user-visible asset capture
- stable decision capture
- continuation from a previous handoff
- non-blocking behavior when Workroot guidance is missing or incomplete

## Audit Output

The suite writes:

```text
reports/live-task-continuity-summary.json
reports/live-task-continuity-audit.md
transcripts/live-task-continuity/<role>/round-XX/
```

Each round records prompt, stdout, stderr, last model message, Workroot command log, command output artifacts, and a database summary after the round.

The final audit summarizes:

- command counts by semantic action
- packet output sizes
- task, run, item, summary, handoff, asset, relationship, context candidate, event, and batch counts
- protocol event statuses
- runtime files in system space
- unexpected runtime artifacts in user space
- expected user-visible asset existence
- continuity pass/fail per role

## Pass Criteria

A strict live run passes only when:

- every Codex invocation exits with code 0;
- each role creates at least one task and one task run;
- each role records at least one current handoff or continuation;
- each role records applied protocol events;
- no user directory runtime pollution is detected;
- expected user-visible assets exist where a scenario asks for them;
- no protocol event is invalid or quarantined unless the scenario explicitly expects degradation.

The suite remains opt-in because live model behavior is expensive and can vary.
