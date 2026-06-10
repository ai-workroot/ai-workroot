# Spec 045 - Sync Owner Binding And Lease Guard

Status: planned for the 0.9.531 hardening line
Depends on: `042-agent-protocol-context-strategy.spec.md`,
`043-continuity-owner-and-evidence-hardening.spec.md`

## Purpose

Define the sync-owned task-continuity contract after the 2026-06-10 live
novice Chinese service-owner E2E regression.

The regression proved that removing `workroot context` from the per-turn main
loop is architecturally correct but incomplete. `sync` must inherit the
continuity anchor that `context` previously supplied every turn. Workroot must
not trust an Agent or LLM `phase=starting, work_kind=task` signal as the final
task-boundary decision.

This spec keeps the existing domain model. It must not introduce Project,
Initiative, SubTask, L1/L2/L3 entities, or new durable owner tables.

## Failure Model

The failed run produced:

- 9 active Tasks for one long-running business direction.
- 6 active normal root Tasks.
- 0 current handoffs.
- 1 missing asset registration even though the user-visible file existed.
- 1 asset attached to the wrong task owner.

The direct cause was not Chinese text. The direct cause was that `context`
previously repeated current task, handoff, and refs into the LLM context every
turn. After the main loop became `sync`/`commit`, `sync` still trusted
`phase=starting, work_kind=task` too strongly and did not supply an equivalent
continuity owner anchor.

## Design Principles

1. `sync` is the main protocol entry for meaningful turns.
2. `workroot context` remains read-only startup, recovery, or debugging
   behavior outside the normal turn loop. Recall inside a normal user turn
   should use `sync` with `intended_action=inspect`.
3. WorkSignal is a semantic hint, not a durable fact and not the final task
   boundary decision.
4. Workroot decides owner binding before issuing a lease.
5. Ambiguity is non-blocking. Workroot may withhold durable persistence while
   the Agent continues helping the user.
6. The LLM-visible packet must use concise action language. Internal owner
   classifications are not ordinary LLM concepts.
7. Machine contracts may carry small stable binding metadata for CLI, MCP, and
   SDK adapters.

## Three-Layer Contract

### Internal Strategy Layer

Workroot may use an internal `FocusBinding` result:

```text
binding_type:
  existing_task
  child_work
  new_root
  inbox
  workroot_capture
  ambiguous

task_id
run_id
root_task_id
confidence
reason
allowed_events
required_before_stop
write_policy
```

This is internal strategy state. It is allowed in debug traces and tests. It is
not the primary LLM-facing protocol vocabulary.

### Machine Contract Layer

`sync` may include compact binding data inside `workroot_contract`:

```json
{
  "binding": {
    "mode": "continue_existing",
    "confidence": "high",
    "refs": {
      "task": "task-...",
      "run": "run-...",
      "root": "task-..."
    },
    "reason": "single_active_normal_task"
  }
}
```

Allowed `binding.mode` values:

```text
continue_existing
start_new
temporary
capture_workroot
clarify
```

This contract is for adapters. It must stay stable and small.

### LLM-Readable Layer

The private packet should explain what to do, not how Workroot internally
classified it. Examples:

```text
Continue the existing work: 家政培训门店月度经营方向梳理.
Do not start a new task for this request.
Next call: commit a checkpoint with the provided lease.
```

The packet must not require the LLM to learn internal names such as
`owner_kind`, `FocusBinding`, or disclosure levels.

## Sync Owner Resolution

`sync` resolves owner binding in this order:

1. Valid `known_state.task_id` or `known_state.run_id`.
2. Exactly one valid selected ref in `WorkSignal.refs`.
3. Multiple valid refs only when every ref resolves to the same task owner.
4. Existing asset path or asset ref owner.
5. Current single active normal root when the request is not explicitly inbox
   and not safely proven to be a new root.
6. High-confidence bounded task match across title, summary, run goal, input
   summary, handoff, and asset identity.
7. Temporary inbox when WorkSignal explicitly asks for inbox work.
8. New root only when no reliable existing owner is available or the request
   is explicitly scoped as a separate root and cannot safely attach to the
   current normal root.
9. Ambiguous non-blocking response when no owner can be selected safely.

`phase=starting, work_kind=task` is not enough by itself to create a new root
when there is exactly one active normal root. In that case Workroot should bind
to the active normal root unless an explicit selected ref or a future stable
protocol field proves a separate root boundary.

When multiple active normal roots exist and no owner can be selected, a
startable durable WorkSignal may create a new root only if it is safer than
attaching to an arbitrary existing root. Otherwise Workroot returns clarify.

## Lease Owner Guard

Leases remain the write authority. A task-scoped lease should carry binding
policy:

```json
{
  "binding_mode": "continue_existing",
  "binding_task_ref": "task-...",
  "binding_run_ref": "run-...",
  "binding_root_ref": "task-...",
  "binding_confidence": "high",
  "binding_reason": "single_active_normal_task"
}
```

Commit guards must reject unsafe projection when:

- the lease is missing for durable task-bound facts;
- event kind is not allowed by the lease;
- asset path or title conflicts with the lease owner and an existing asset
  owner is known;
- continuation or handoff is requested while focus is ambiguous.

Rejected writes remain non-blocking and must return recovery guidance that
asks for a fresh `sync` with the current focus or path.

## Asset Owner Resolution

Asset owner resolution order:

1. Existing asset path owner.
2. Existing asset ref owner.
3. Current sync binding owner.
4. Lease owner when it does not conflict with path or title.
5. Single active normal root.
6. Workroot-level asset capture when owner is unclear.

An asset should never be attached to a recent task lease when the path or title
clearly belongs elsewhere.

## Asset-First Output Contract

When the current user request contains an explicit relative output path, Workroot
should treat the turn as producing a user-visible asset regardless of the user's
language. This is a protocol-level path signal, not a natural-language keyword
rule.

If sync can bind the request to a reliable task owner, it should issue a
task-scoped lease whose allowed events still include normal continuation events
but whose immediate required-before-stop shapes include:

```text
asset
continuation
```

The private packet must then prefer `asset` as the next commit shape:

```text
create or update the user-visible file
commit it as an asset with its relative path
then preserve current state and next useful action before stopping
```

This avoids a failure mode where the Agent writes the file and only commits a
continuation, leaving the asset out of Workroot facts and future recall. After
the asset commit succeeds, Workroot may issue the next lease that asks for
continuation before stop.

## Handoff And Stop Contract

`phase=pausing`, `phase=stopping`, or a stop-like `before_task_switch` sync
must prefer a continuation commit contract when a reliable owner exists.

When the commit contract requires continuation before stop, packet shape
selection must prefer `continuation` over `checkpoint`.

If the Agent does not commit a continuation, Workroot must not block user work,
but protocol diagnostics should record the missed stop-preservation signal.

## Diagnostics

Runtime diagnostics use two surfaces:

```text
<stateDirectory>/logs/protocol-friction.jsonl
<stateDirectory>/diagnostics/protocol-friction.json
```

The JSONL file is the runtime event stream. The diagnostics JSON file is a
derived runtime view. Neither is a durable domain model. Together they must
count:

- `new_root_downgraded_to_continuation`
- `owner_conflict`
- `missing_lease`
- `asset_registration_rejected`
- `handoff_missing_before_stop`
- `context_called_in_main_loop`
- `sync_recovered_after_context_error`

Rejected commit batches must produce a friction entry with stage, code, shape,
request id, lease id when present, and recovery action.

## Acceptance Criteria

The 20-round `live-novice-chinese-service-owner` E2E should satisfy:

- active normal root tasks stay at 1, or at most 2 when a true separate normal
  root is intentionally opened;
- ordinary sub-work such as checklists, announcements, activity plans, and
  review tables attach to the current root or its child task;
- all expected user-visible assets are registered;
- asset relationships point at the correct owner;
- at least one current handoff or current continuation view exists;
- `workroot context` is not required every round and is not the normal recall
  mechanism inside a user turn;
- LLM/user-visible output does not expose L1/L2/L3, `FocusBinding`, or
  internal owner-kind labels.
