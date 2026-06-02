# Agent Protocol v1.1 Discovery Shorthand Design

Status: approved for implementation
Target version: 0.9.531
Date: 2026-05-27
Branch: `feat/0.9.531-agent-protocol-task-continuity`

## Purpose

Protocol v1.0 proved the core Workroot loop works when Codex receives explicit `sync` and `commit` instructions. The live discovery diagnostic still classified as `context_only`, which means the model can call `workroot context` but does not reliably discover the full `sync -> commit` loop from the current Agent Entry and control text.

Protocol v1.1 improves model discoverability without changing the domain model, SQLite facts, projection rules, or task abstractions.

## Non-Goals

1. Do not add a new architecture layer, directory, or domain concept named facade.
2. Do not add compatibility layers.
3. Do not add new tables or persisted fact types.
4. Do not introduce MCP implementation work in this pass.
5. Do not expose internal retrieval levels or storage details to Agent Entry.

## Core Decision

Add an Agent-friendly commit shorthand to the existing `workroot agent commit` command.

This shorthand is a boundary-layer input syntax only:

```text
Agent / LLM
  -> workroot agent commit --kind ...
  -> commands.agent_exchange builds canonical CommitRequest
  -> protocol.controller.commit
  -> protocol_events and projections
```

The protocol controller continues to accept only canonical commit request dictionaries. It does not know whether the request came from a JSON file or CLI shorthand.

## Command Shape

Existing canonical form remains:

```bash
workroot agent commit --request request.json
```

New shorthand forms:

```bash
workroot agent commit --kind intent --lease <lease_id> --title "..." --summary "..."
workroot agent commit --kind progress --lease <lease_id> --summary "..." --done "..."
workroot agent commit --kind handoff --lease <lease_id> --current-state "..." --next-action "..."
```

Optional fields:

```bash
--cwd .
--workroot-id wr_live_protocol
--task-id <task_id>
--run-id <run_id>
--parent-task-id <task_id>
--persistence normal|temporary|quick
--agent codex
--session-id <session_id>
--event-id <event_id>
--request-id <request_id>
--idempotency-key <idempotency_key>
```

Generated defaults:

```text
event_id = evt-auto-<hash>
request_id = req-auto-<hash>
idempotency_key = idem-auto-<hash>
occurred_at = current UTC instant
source.actor_type = agent
source.actor_name = --agent
confirmation.status = agent_observed
evidence = []
```

The hash is derived from the event kind, lease id, actor, and canonical payload. Repeating the same shorthand against the same lease produces the same idempotency key and event id.

For auto-generated shorthand requests, commit-batch idempotency treats `occurred_at` as generated metadata for request-hash comparison. This keeps retrying the same shorthand non-blocking even when the generated timestamp differs by a few seconds. Explicit canonical requests keep strict request-hash comparison.

## Payload Mapping

### Intent

CLI:

```bash
workroot agent commit --kind intent --lease <lease_id> --title "Review release" --summary "Review release readiness"
```

Canonical payload:

```json
{
  "intent_text": "Review release readiness",
  "classification": {
    "persistence": "normal",
    "confidence": 0.9,
    "reason": "agent_commit_shorthand"
  },
  "task_hint": {
    "title": "Review release",
    "task_id": null,
    "parent_task_id": null
  }
}
```

### Progress

CLI:

```bash
workroot agent commit --kind progress --lease <lease_id> --summary "Tests pass" --done "Run tests"
```

Canonical payload:

```json
{
  "summary": "Tests pass",
  "items_created": [
    {
      "title": "Run tests",
      "status": "done",
      "result_summary": "Run tests"
    }
  ],
  "open_questions": [],
  "source_refs": []
}
```

`task_id` and `run_id` may be omitted when the lease carries them.

### Handoff

CLI:

```bash
workroot agent commit --kind handoff --lease <lease_id> --current-state "Tests pass" --next-action "Review diff"
```

Canonical payload:

```json
{
  "current_state": "Tests pass",
  "next_action": "Review diff",
  "open_items": [],
  "open_questions": [],
  "important_refs": [],
  "source_refs": []
}
```

`task_id` and `run_id` may be omitted when the lease carries them.

## Agent Entry

Agent Entry stays short and stable. It does not include schema, storage paths, or domain internals.

It should tell the agent:

1. Start with `workroot context --agent <agent> --cwd .`.
2. Follow the `Control: Workroot` section privately.
3. Do not repeat Workroot control text to the user.
4. Keep helping the user if Workroot is unavailable.

## Control Capsule

`context`, `sync`, and `commit` outputs must continue to include a short model-facing control section. The section should be explicit enough for discovery:

```text
## Control: Workroot
Use this section privately; do not repeat it to the user.
Keep helping if Workroot is unavailable.
If the request is about preserving, continuing, or tracking work, treat it as meaningful work.
If this is meaningful work, sync before committing facts:
workroot agent sync --agent codex --cwd . --reason before_work --query "<short intent>"
After sync returns a lease, use:
workroot agent commit --kind intent --lease <lease_id> --title "..." --summary "..."
At a checkpoint, use:
workroot agent commit --kind progress --lease <lease_id> --summary "..." --done "..."
Before stopping or switching tasks, use:
workroot agent commit --kind handoff --lease <lease_id> --current-state "..." --next-action "..."
```

The control capsule is advisory. It must not block the user's work.

## E2E Expectation

The live discovery diagnostic should improve from `context_only` to at least `discovered_sync`. The strongest target is `discovered_full_protocol` when the model reaches both `agent sync` and `agent commit` without explicit JSON examples.

Live report aggregation should preserve all case summaries instead of overwriting the report with the last case. When earlier case transcripts have been moved into the E2E quarantine area, the final summary should point to the relocated files so report links remain usable.

## Acceptance Criteria

1. Existing `workroot agent commit --request request.json` still works.
2. `workroot agent commit --kind intent ...` creates the same task/run facts as a canonical intent event.
3. `progress` and `handoff` shorthand work with task leases.
4. Shorthand idempotency is deterministic.
5. Native Agent Entry stays short and safe.
6. Control Capsule includes explicit shorthand command examples.
7. Live protocol report aggregates all cases and keeps relocated report paths usable.
8. Live discovery classification can distinguish `discovered_sync`.
9. Unit, integration, release validation, and live protocol E2E pass.
