# Task Management Continuity P0.1 Design

## Goal

Finish the task-management layer needed for reliable Workroot-Agent continuity after the 0.9.531 P0 protocol loop.

This is not a broad context-builder rewrite. P0.1 completes the task-related gaps that directly affect continuity:

- Protocol errors must return structured JSON so agents can recover deterministically.
- Task execution must support structured TaskItems so an agent can stop and another agent can resume from the latest item state.
- Temporary conversational work must be represented as `Task(role=inbox, process_level=L0)`, not as a separate Inbox entity.

## Chase Back

The design traces back to these settled constraints:

- Protocol actions remain only `sync` and `commit`.
- `sync` may create only an exchange lease; it must not create Task, TaskRun, TaskItem, Inbox, Handoff, Asset, or uncommitted chat fragments.
- `commit` is the only Agent fact entry. Every durable Agent fact is appended to `protocol_events` before projection.
- Transient chat buffer is Agent-local. Workroot stores only committed summary-level facts.
- All work is modeled as `Task`; temporary work is `Task(role=inbox, process_level=L0)`.
- No `Project`, `Initiative`, `StandingGoal`, `SubTask`, `TemporaryTask`, or `InboxEntity` concept is introduced.
- SQLite remains `<stateDirectory>/cache/workroot.sqlite`.
- Runtime views remain optional and under `<stateDirectory>/runtime`.

## Scope

### In Scope

1. Structured protocol error response:
   - `sync` and `commit` catch `ProtocolError` and return the normal protocol error envelope.
   - CLI `workroot agent *` prints JSON for protocol-level validation failures.
   - Invalid transport JSON remains a CLI transport error.

2. TaskItem process control:
   - Add `task_items` table.
   - `commit(progress)` projects `items_created` and `items_updated`.
   - TaskItem statuses: `todo`, `doing`, `done`, `blocked`, `canceled`.
   - TaskItem updates can mark work as done and preserve result summaries.
   - Continuity context includes open TaskItems and recently done TaskItems.

3. Inbox/temporary task lifecycle:
   - `commit(intent, classification.persistence=temporary)` creates `Task(role=inbox, process_level=L0)`.
   - Temporary task uses `retention_policy=rolling_7d` and `visibility=implicit`.
   - The same TaskRun, progress, handoff, and TaskItem flow works for temporary tasks.
   - `commit(state)` can archive an inbox task or promote it to normal work by changing role/process level/visibility/retention.

4. Complete task status transitions:
   - Align protocol projection transitions with the spec state machine:
     `active -> archived`, `paused -> archived`, `closed -> archived`, `archived -> released`, etc.

5. Backlog record:
   - Record tomorrow's deferred items: Decision/Asset/Guidance/Correction/Invalidation projections, runtime view materialization, parent-child rollups, deeper context recall, and automatic summary compaction.

### Out Of Scope

- DuckDB.
- New protocol actions beyond `sync` and `commit`.
- New domain entity types for Project/Initiative/SubTask/TemporaryTask/InboxEntity.
- Deep Context Builder retrieval strategy.
- User-space asset directory policy.
- Model-driven automatic summarization.

## Domain Model

### Task

`Task` remains the universal work unit.

Temporary task:

```text
role = inbox
process_level = L0
task_kind = inbox
retention_policy = rolling_7d
visibility = implicit
```

Normal task:

```text
role = normal
process_level = L1/L2/L3
task_kind = task
retention_policy = until_closed
visibility = normal
```

Promotion changes an existing inbox task into normal work. It does not create a different entity.

### TaskRun

`TaskRun` represents one agent execution run for a task. It remains the place for run goal/input/output summaries.

### TaskItem

`TaskItem` is a structured process-control unit under a Task.

Fields:

```text
item_id
workroot_id
task_id
run_id
title
status
item_order
detail
result_summary
source_event_id
created_at
updated_at
completed_at
metadata_json
```

Status lifecycle:

```text
todo -> doing
todo -> done
todo -> blocked
todo -> canceled
doing -> todo
doing -> done
doing -> blocked
doing -> canceled
blocked -> doing
blocked -> done
blocked -> canceled
done -> terminal
canceled -> terminal
```

TaskItem facts are projected from `commit(progress)`:

```json
{
  "items_created": [
    {"item_id": "item-1", "title": "Implement schema", "status": "todo"}
  ],
  "items_updated": [
    {"item_id": "item-1", "status": "done", "result_summary": "Schema added."}
  ]
}
```

## Protocol Flow

### New Temporary Task

```text
Agent -> sync(before_work, query)
Workroot -> directive=commit_required, lease allows intent
Agent -> commit(intent, classification.persistence=temporary)
Workroot -> protocol_events append
Workroot -> Task(role=inbox,L0) + TaskRun projection
Workroot -> task lease allows progress/handoff/state
```

### Structured Process Progress

```text
Agent -> commit(progress, summary, items_created/items_updated)
Workroot -> protocol_events append
Workroot -> TaskRun output_summary update
Workroot -> TaskSummary current update
Workroot -> TaskItem create/update
Workroot -> state versions bump
Workroot -> next task lease
```

### Stop And Resume

```text
Agent -> commit(handoff)
Workroot -> current handoff
Next Agent -> sync(continue, known_state)
Workroot -> context includes summary + handoff + open/recent TaskItems
```

### Promote Temporary Task

```text
Agent -> commit(state, {"target_type":"task","target_id":"task-x","to_role":"normal","to_process_level":"L1"})
Workroot -> update same Task role/process_level/visibility/retention_policy
```

### Archive Temporary Task

```text
Agent -> commit(state, {"target_type":"task","target_id":"task-x","from_status":"active","to_status":"archived"})
Workroot -> update same Task status=archived
```

## Dependency Boundary

The dependency direction remains:

```text
cli -> commands -> protocol -> context/state
work/assets/handoff -> state
```

`work`, `assets`, and `handoff` must not import `protocol`.

`protocol` may write projections transactionally with direct SQL because it coordinates protocol event projection. It must not call helpers that auto-commit.

## Testing Strategy

- Unit tests for protocol error responses.
- Unit tests for task_items schema and upgrade presence.
- Unit tests for `progress` item creation/update.
- Unit tests for temporary intent creation.
- Unit tests for promote/archive state behavior.
- Integration test for temporary task with TaskItems, handoff, and resume continuity.
- Import boundary tests remain green.

## Deferred Backlog For Tomorrow

- Decision projection.
- Asset projection and publication lifecycle.
- Guidance and global user rule preservation.
- Correction and invalidation projections.
- Parent-child task rollup summaries.
- Runtime Markdown views under `<stateDirectory>/runtime`.
- Context Builder recall policy for decisions/assets/guidance/invalidation/parent rollup.
- Model-driven summary compaction.
