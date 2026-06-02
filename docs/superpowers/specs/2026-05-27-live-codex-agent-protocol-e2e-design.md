# Live Codex Agent Protocol E2E Design

Status: approved for implementation
Target version: 0.9.531 follow-up
Date: 2026-05-27
Branch: `feat/0.9.531-agent-protocol-task-continuity`

## Purpose

This design adds a real end-to-end test suite for the Codex Client, the remote model, and Workroot protocol interaction.

The existing `live-agent` suite proves that Codex can run inside a sandbox and call `workroot context`. It does not prove the new protocol loop:

```text
context/sync -> commit(intent) -> commit(progress) -> commit(handoff) -> next sync/context continues correctly
```

This design introduces a new opt-in suite, `live-protocol`, that validates the actual Agent/model behavior and the persisted Workroot facts produced by that behavior.

## Goals

1. Run the real Codex CLI against a sandbox Workroot.
2. Allow the remote model to decide and execute Workroot CLI calls.
3. Verify the Agent sees model-readable Workroot protocol guidance.
4. Verify protocol calls produce correct SQLite facts.
5. Verify continuation can resume from task summary and handoff.
6. Verify degraded protocol paths do not block user work.
7. Capture transcripts, command logs, final model messages, and database summaries for review.
8. Keep all remote-model tests opt-in and sandboxed.

## Non-goals

1. Do not make remote LLM calls part of default unit, integration, smoke, release validation, or longrun E2E.
2. Do not require live E2E to be deterministic enough for every CI run.
3. Do not introduce a remote model dependency into Workroot runtime code.
4. Do not test every Agent implementation in this suite. This suite targets Codex Client first.
5. Do not turn the discovery diagnostic into a release-blocking gate until the Native Agent Entry and protocol text are mature enough.

## Existing Baseline

Current live E2E files:

```text
tests/e2e/live_agent.py
tests/e2e/live_agent_cases.py
tests/e2e/runner.py
```

Current behavior:

- Requires `AI_WORKROOT_RUN_E2E=1`.
- Requires `AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1` for `live-agent`.
- Copies Codex auth/config allowlisted files into sandbox `CODEX_HOME`.
- Runs `codex exec` against sandbox user directories.
- Uses `--ephemeral`, `--skip-git-repo-check`, and `--sandbox workspace-write`.
- Verifies Codex can call `python3 -m ai_workroot context --agent codex --cwd . --query 'Clean Mode' --debug`.

Missing behavior:

- No `workroot agent sync`.
- No `workroot agent commit`.
- No persisted protocol event assertions.
- No task/run/summary/handoff assertions.
- No continuation assertions.
- No degraded commit assertion.
- No wrapper-level command audit.

## Suite Shape

Add a new E2E suite:

```text
live-protocol -> tests.e2e.live_protocol_cases
```

It uses the same explicit opt-ins:

```bash
AI_WORKROOT_RUN_E2E=1
AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1
```

Run command:

```bash
AI_WORKROOT_RUN_E2E=1 \
AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1 \
PYTHONPATH=src \
python3 -m tests.e2e.runner --suite live-protocol
```

Optional WebSocket/remote Codex transport:

```bash
AI_WORKROOT_E2E_CODEX_REMOTE=ws://127.0.0.1:PORT
```

When set, the harness appends:

```text
--remote <AI_WORKROOT_E2E_CODEX_REMOTE>
```

to `codex exec`.

## Participants

### Codex CLI

Runs non-interactively through `codex exec`.

### Remote model

Receives the prompt, Workroot command outputs, and model-readable protocol guidance. It chooses shell commands through Codex.

### Workroot CLI

The live process invokes `python3 -m ai_workroot` through a sandbox wrapper named `workroot`.

### Command audit wrapper

The wrapper logs each Workroot command before executing it. The log is the canonical proof that the Agent/model made the expected calls.

### SQLite state

The test reads managed SQLite under sandbox `AI_WORKROOT_HOME` to verify facts, projections, and statuses.

## Sandbox Layout

For each run:

```text
run-root/
  ai-workroot-home/
  home/
    .codex/
  user-dirs/
    live-protocol/
  transcripts/
    live-protocol/
      <case>/
        prompt.txt
        codex-stdout.txt
        codex-stderr.txt
        codex-last-message.txt
        workroot-command-log.jsonl
        db-summary.json
  reports/
    live-protocol-summary.json
```

The existing `prepare_run_root()` safety sentinels remain required.

## Workroot Wrapper

The harness creates:

```text
run-root/bin/workroot
```

The wrapper:

1. Appends one JSON line to `WORKROOT_COMMAND_LOG`.
2. Executes `python3 -m ai_workroot "$@"`.
3. Preserves stdout, stderr, and exit code.

Logged fields:

```json
{
  "argv": ["agent", "sync", "..."],
  "cwd": "/sandbox/user-dirs/live-protocol",
  "returncode": 0,
  "startedAt": "2026-05-27T00:00:00Z",
  "endedAt": "2026-05-27T00:00:02Z"
}
```

The wrapper is a test harness artifact, not product code.

## Case 1: Guided Minimal Protocol Loop

### Purpose

Prove the real Codex Client and remote model can execute the full protocol loop when given concise tool-use instructions.

### Prompt

The prompt tells Codex:

1. You are in a sandbox Workroot user directory.
2. Use the `workroot` command from PATH.
3. First call `workroot context --agent codex --cwd . --query "Live protocol guided loop" --debug`.
4. Then call `workroot agent sync` with a high-level `work_signal`.
5. Commit one intent event.
6. Commit one progress event with a summary and one done item.
7. Commit one handoff event.
8. Call `workroot agent sync` again with `reason=continue`.
9. Reply with `LIVE_PROTOCOL_GUIDED_OK` and a short summary.

The prompt may describe the JSON request shape because this test verifies that the real Agent can execute the protocol, not whether it can discover the protocol from nothing.

### Required command sequence

The audit log must include:

```text
context --agent codex --cwd .
agent sync
agent commit
agent commit
agent commit
agent sync
```

The test does not require exact argument order, only semantic command classification.

### SQLite assertions

For the sandbox Workroot:

```text
tasks count == 1
task_runs count == 1
task_summaries current count == 1
handoffs current count == 1
protocol_events kinds include intent, progress, handoff
protocol_events statuses for those events are applied
protocol_commit_batches statuses are completed or partial only when explicitly expected
no invalid protocol_events
no quarantined protocol_events
```

### Final message assertion

`codex-last-message.txt` must include:

```text
LIVE_PROTOCOL_GUIDED_OK
```

## Case 2: Continuation From Handoff

### Purpose

Prove a second live Codex session can continue from the first session's persisted Workroot state.

### Flow

1. Reuse the Workroot from Case 1.
2. Launch a second `codex exec`.
3. Ask Codex to continue the previous live protocol task.
4. Require it to call `workroot agent sync --reason continue` or `workroot context`.
5. Require it to report the previous handoff/summary in the final answer.

### Assertions

```text
task count remains 1
latest sync/context command occurred in command log
final message contains LIVE_PROTOCOL_CONTINUE_OK
final message mentions the previous progress summary or handoff next action
no new task is created unless explicitly justified by a new intent event
```

## Case 3: Degraded Commit Does Not Block User Work

### Purpose

Prove a degraded protocol condition preserves safe facts when possible and does not prevent the remote model from completing the user-visible answer.

### Flow

The harness creates an expired task lease before launching Codex:

1. Create task/run through deterministic local setup or prior protocol commit.
2. Expire the current lease in SQLite.
3. Launch Codex with the expired lease ID and ask it to commit progress.
4. Codex calls `workroot agent commit`.
5. Workroot returns `agent_may_continue=true` and degraded/partial status.
6. Codex replies with `LIVE_PROTOCOL_DEGRADED_OK`.

### Assertions

```text
response contains agent_may_continue=true
batch_status is partial or degraded
warnings include lease_expired
safe progress summary is stored in task_summaries
final message contains LIVE_PROTOCOL_DEGRADED_OK
no user directory runtime files are created
```

This case can be implemented as a guided live case. The remote model does not need to invent the expired lease; the harness provides it.

## Case 4: Discovery Diagnostic From Context Control

### Purpose

Measure whether the current Native Agent Entry plus `workroot context` output is enough for Codex to discover the protocol loop.

### Flow

1. Initialize a Workroot with native Codex entry.
2. Prompt Codex only to follow the local Workroot instructions and preserve the work if Workroot asks it to.
3. Do not provide explicit `agent sync/commit` JSON examples.
4. Inspect the command log for whether Codex called `agent sync` or `agent commit`.

### Result Classification

This test is diagnostic at first:

```text
discovered_full_protocol
context_only
no_workroot_call
failed
```

It should not fail the suite unless Codex cannot run safely or the command log is missing. The diagnostic classification is written to `db-summary.json` and `live-protocol-summary.json`.

## Safety

The suite must fail closed unless both opt-ins are present:

```text
AI_WORKROOT_RUN_E2E=1
AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1
```

The suite must:

- never run with the repository as Codex cwd;
- never use the real user directory as a Workroot;
- put `HOME`, `AI_WORKROOT_HOME`, and `CODEX_HOME` under the E2E run root;
- copy only allowlisted Codex auth/config files;
- preserve transcripts and reports under sandbox run root;
- avoid destructive shell prompts;
- use `--sandbox workspace-write`;
- use `--skip-git-repo-check`;
- use `--ephemeral`;
- use `--ignore-rules` to prevent unrelated local rules from changing behavior.

## Failure Reporting

On failure, the test should show paths to:

```text
prompt.txt
codex-stdout.txt
codex-stderr.txt
codex-last-message.txt
workroot-command-log.jsonl
db-summary.json
live-protocol-summary.json
```

The test failure message should include the first actionable reason:

```text
missing expected command: agent commit
missing applied progress event
missing current handoff
Codex returned non-zero
remote LLM opt-in missing
```

## Acceptance Criteria

The implementation is accepted when:

1. `python3 -m tests.e2e.runner --list` includes `live-protocol`.
2. Runner rejects `live-protocol` without `AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1`.
3. Dry run works with both opt-ins.
4. Guided live protocol loop passes on a real Codex Client.
5. Continuation from handoff passes on a real Codex Client.
6. Degraded commit live case passes on a real Codex Client.
7. Discovery diagnostic produces a classification report.
8. Command audit log proves Workroot commands were called.
9. SQLite summary proves facts were projected correctly.
10. User directory validation proves runtime artifacts stayed out of user space.

## Commands

Focused non-remote checks:

```bash
PYTHONPATH=src python3 -m unittest tests.e2e.safety_cases -v
PYTHONPATH=src python3 -m unittest tests.e2e.live_protocol_cases -v
```

Real remote run:

```bash
AI_WORKROOT_RUN_E2E=1 \
AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1 \
PYTHONPATH=src \
python3 -m tests.e2e.runner --suite live-protocol
```

Optional WebSocket run:

```bash
AI_WORKROOT_RUN_E2E=1 \
AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1 \
AI_WORKROOT_E2E_CODEX_REMOTE=ws://127.0.0.1:PORT \
PYTHONPATH=src \
python3 -m tests.e2e.runner --suite live-protocol
```
