# Spec 047 - Compact Packet, Focus Guard, And Sync Trace

Status: planned for the 0.9.531 hotfix line
Depends on:

- `042-agent-protocol-context-strategy.spec.md`
- `045-sync-owner-binding-and-lease-guard.spec.md`
- `046-protocol-context-hardening-followup.spec.md`

## Purpose

This spec closes the follow-up gaps found by the 20-round live mixed-complexity
E2E run after Spec 046.

The stable Agent loop remains:

```text
sync -> commit
```

`context` remains read-only auxiliary behavior for startup, recovery, manual
inspection, and debugging. It must not return to the ordinary per-turn loop.

This spec does not introduce new domain entities. It hardens the existing
protocol, packet rendering, owner binding, adapter tolerance, runtime
diagnostics, and E2E assertions.

## Failure Model

The live run succeeded at the test-harness level but still showed product-level
failures:

- Sync packets averaged about 4.3 KB and reached about 5.6 KB.
- Packets repeated WorkSignal rules on every turn.
- Packets duplicated the same CLI command in `call.command_template` and
  `adapter_hint.cli`.
- Some `open` and `done` items contained repeated text such as `X: X`.
- The LLM sometimes sent a wrong WorkSignal:

  ```json
  {
    "phase": "starting",
    "work_kind": "task",
    "intended_action": "plan",
    "boundary": "separate_work"
  }
  ```

  for quick answers or decisions inside current work.
- Workroot trusted that signal too strongly and issued start-work leases.
- A decision that belonged to the current founder task was attached to a newly
  created task.
- Checkpoint commits sometimes used `state` and `next` fields before retrying
  with the accepted checkpoint fields.
- The live harness checked expected positive shapes, but did not fail when a
  round created an unexpected start-work task or attached a fact to the wrong
  owner.
- Because normal turns no longer call `workroot context`, sync packet quality
  did not have a dedicated lightweight trace.

## Design Principles

1. The protocol semantics are stable across CLI, MCP, HTTP, and SDK adapters.
2. Transport-specific command strings are adapter rendering, not core protocol
   truth.
3. WorkSignal is a semantic hint from the LLM. It is not the final task-boundary
   decision.
4. Workroot must decide owner binding before issuing a write lease.
5. A false start-work signal should not create durable task facts.
6. Ambiguity is non-blocking. Workroot may withhold durable persistence while
   the Agent continues helping the user.
7. Ordinary packets should be compact and useful. Debug packets may be verbose.
8. Runtime diagnostics should be logs and derived runtime views, not new domain
   facts.
9. E2E must test both required positive behavior and forbidden negative
   behavior.

## Compact Packet Contract

The default private packet is compact. It should contain:

- privacy marker;
- current focus and confidence;
- next protocol action;
- concise reason;
- one transport-rendered call template when a call is needed;
- stable refs needed by the next call;
- only the shape-specific rules needed for the current action.

Default packet output should not include:

- full JSON body;
- duplicate `adapter_hint.cli` when it is identical to
  `call.command_template`;
- full WorkSignal teaching text every turn;
- debug effects or internal contract objects;
- internal owner classifications such as `owner_kind`, `FocusBinding`, or
  disclosure-layer names.

Debug or verbose packet output may include the full JSON body for diagnosis.
The normal `--format packet` surface remains model-readable Markdown.

### Transport Boundary

Core packet data should represent protocol semantics:

```text
action
shape
lease
fields
refs
write status
output rule summary
```

CLI command strings, MCP tool-call instructions, and HTTP request examples are
transport renderers. A future MCP renderer must be able to use the same core
protocol packet without depending on CLI-only fields.

For this hotfix line, the CLI packet may still render one copyable CLI command
for usability. It must not render the same command twice.

## Focus Guard Contract

Owner resolution must treat `boundary=separate_work` as a hint, not a command.
Start-work leases are allowed only after Workroot determines that creating a
new durable task is safer than attaching to an existing owner.

Resolution priority:

1. Valid `known_state`.
2. Valid `WorkSignal.refs`.
3. Existing asset, decision, candidate, chunk, or task refs that resolve to one
   owner.
4. Explicit asset path owner.
5. Decision, asset, checkpoint, handoff, and continuation facts attached to the
   current or related owner when a reliable owner exists.
6. Single active normal task when the request is not explicitly inbox and not
   safely proven to be a separate durable root.
7. High-confidence semantic match against task title, summary, run goal,
   input summary, handoff, and asset identity.
8. Temporary inbox only when WorkSignal explicitly asks for inbox work.
9. New durable root only when no reliable existing owner is available or the
   request is safely proven to be separate long-running work.
10. Ambiguous non-blocking response when no owner can be selected safely.

### Guarded Shape Rules

When the signal requests `boundary=separate_work` but the request is a fact that
normally belongs to existing work:

- `work_kind=decision` or `intended_action=decide` must first try current or
  related owner binding.
- asset-shaped requests or explicit relative paths must first try current,
  path, or related owner binding.
- checkpoint, handoff, and continuation requests must not create a new root
  when any reliable current owner exists.
- only true task-start intent should receive a start-work lease.

When the model misclassifies a quick answer as startable durable work, Workroot
may withhold durable persistence instead of creating a task. It must not block
the Agent from answering.

## Forgiving Adapter Contract

The CLI adapter may recover safe shape-field mistakes before a protocol request
is built:

- For `checkpoint`, if `summary` is missing but `state`, `current_state`,
  `next`, or `next_action` exists, synthesize a concise summary from those
  fields.
- For `checkpoint`, if item fields are provided, keep mapping them to progress
  items.
- Record recoverable protocol friction when this mapping is used.
- Do not recover unsafe cases such as missing asset path, missing decision
  text, or missing start-work intent.

This is adapter tolerance, not a change to the durable domain model.

## Sync Trace Contract

Normal sync calls should write a lightweight runtime log:

```text
<stateDirectory>/logs/sync-packets.jsonl
```

Each record should be safe and compact:

```json
{
  "eventId": "sync_packet_...",
  "workrootId": "wr_...",
  "requestId": "req_...",
  "agent": "codex",
  "transport": "cli",
  "focus": "continuation",
  "confidence": "high",
  "action": "commit",
  "shape": "asset",
  "packetBytes": 2100,
  "taskBound": true,
  "runBound": true,
  "compact": true,
  "trimmedOpenItems": 2,
  "trimmedDoneItems": 1,
  "occurredAt": "2026-06-11T00:00:00Z"
}
```

The trace must not store raw uncommitted chat fragments. It may store packet
size, protocol classification, owner-binding presence, and trim counts.

If runtime views summarize this log, the summary belongs under diagnostics.
It is not a new fact source.

## Strict E2E Contract

The live task-continuity harness must fail when:

- a round without expected `start_work` creates a start-work commit;
- a decision-only round creates a task;
- a quick-answer round creates durable task facts;
- an expected decision or asset owner does not match the intended task;
- active normal root task count exceeds the scenario threshold;
- sync packet average or maximum size exceeds the configured budget;
- `workroot context` is used in every normal round;
- user-visible final output leaks packet JSON, leases, refs, `owner_kind`, or
  disclosure-layer names.

The harness should continue preserving raw transcripts and command artifacts
for local diagnosis, but those artifacts remain local E2E outputs and are not
public docs.

## Implementation Plan

1. Add packet tests for compact output, no duplicate CLI command, no full JSON
   in default packet, open/done de-duplication, and debug/verbose retention.
2. Add focus tests for false `boundary=separate_work` on decision, asset, and
   checkpoint-style follow-up turns.
3. Add adapter tests for safe checkpoint `state`/`next` recovery and friction
   recording.
4. Add sync trace tests for a compact JSONL record without raw query payload.
5. Add E2E harness assertions for unexpected start-work, owner drift, and sync
   packet size budgets.
6. Implement the smallest code changes needed to pass those tests.
7. Run focused tests, full unit tests, release validation, and then a live E2E
   when requested.

## Acceptance Criteria

- Default packet output is materially smaller and does not duplicate CLI
  command strings.
- The default packet does not include a full JSON body.
- Full packet JSON remains available through debug or verbose rendering.
- False start-work WorkSignals do not create new tasks when the request should
  attach to current decision, asset, checkpoint, handoff, or continuation work.
- Safe checkpoint field misuse is recovered and logged as recoverable friction.
- Sync writes lightweight packet diagnostics without storing raw user requests.
- Live E2E fails when unexpected task creation or owner drift occurs.
- Existing local validation remains green.
