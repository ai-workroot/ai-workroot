# Protocol and Task Continuity Repair Design

Date: 2026-06-01
Target release line: 0.9.531
Branch: `feat/0.9.531-agent-protocol-task-continuity`
Status: review draft

## Purpose

This repair makes the Workroot Agent Protocol and task-continuity loop usable in real long-running work.

The current branch has the right broad architecture direction, but the 50-round live E2E exposed that the system does not yet preserve one continuous task reliably. The largest failure is not one CLI bug. It is a chain across sync focus resolution, task projection, packet guidance, asset/index persistence, runtime read views, and E2E validation.

This design keeps the current domain model. It does not add more domain entities. It repairs how the existing entities are selected, projected, indexed, viewed, and tested.

## Evidence From The 50-Round Live Run

Live E2E run root:

```text
<live-e2e-sandbox>/run-2026-06-01-09-02-21-d3eb3dfc
```

Founder Operator role results:

- 50 remote Codex/LLM rounds completed, but the harness failed.
- Workroot commands: 432.
- Failed commands: 44.
- `start-work` was called 40 times.
- SQLite ended with 40 active `tasks` and 40 active `task_runs`.
- All 40 tasks were `role=normal`, `process_level=L1`, `retention_policy=until_closed`.
- Duplicate or near-duplicate task titles appeared repeatedly:
  - `Six-week pricing and onboarding cadence`: 5
  - `Founder operating plan asset`: 4
  - `Update founder operating plan`: 4
  - `Risk checkpoint`: 3
- User directory remained mostly clean. Expected user asset existed:
  - `results/founder-operating-plan.md`
- System runtime facts mostly landed in SQLite:
  - `cache/workroot.sqlite`
  - `logs/context-requests.jsonl`
- A zero-byte `<stateDirectory>/workroot.sqlite` also appeared. It is not canonical and should be treated as a diagnostic anomaly, not as a store to read from or migrate into.
- Semantic runtime directories were mostly empty:
  - `assets/`
  - `context/`
  - `diagnostics/`
  - `handoffs/`
  - `indexes/`
  - `relationships/`
  - `state/`
  - `tasks/`
- Local FTS gap:
  - `context_candidates_fts` had 20 rows.
  - `indexed_files`, `indexed_chunks`, `indexed_chunks_fts`, and `context_recall_hints` had no useful data for this run.
- Asset gap:
  - The same user-visible path produced 10 separate asset rows.
  - `content_hash` was empty for every asset row.

## Target Outcome

A single long-running Founder Operator scenario should behave like one continuous work thread.

Expected outcome after this repair:

- Repeated work on the same long-cycle task does not create a new root task each round.
- `sync` resolves the current task by default when there is a reliable active focus.
- `commit(intent)` creates a task only when the work is truly new or explicitly switched.
- Erroneous repeated `start-work` calls attach to an existing task when the semantic boundary is the same.
- `TaskRun` does not proliferate as an active orphan process record.
- Protocol packets are copyable and contain the exact next Workroot call the LLM should ask the Agent to make.
- Missing lease, missing continuation fields, and plain-text signal arguments do not produce raw CLI failures.
- User-visible assets are tracked as stable logical assets, with path, hash, provenance, and FTS chunks.
- Runtime read views are generated from SQLite into system-space directories.
- E2E validation measures per-round deltas and detects task proliferation directly.
- User directories remain free of Workroot runtime files.

## Non-Goals

This repair does not:

- Introduce DuckDB, MySQL, external Elasticsearch, or another persistent store.
- Move SQLite away from `<stateDirectory>/cache/workroot.sqlite`.
- Add new domain entities.
- Implement the future L1/L2/L3 context disclosure strategy.
- Make `context/builder.py` decide the current task. Current-task selection remains in protocol/focus strategy.
- Store uncommitted transient chat fragments in Workroot.
- Require the user to understand leases, task ids, runtime paths, tables, or indexing internals.

## Architecture Principles

1. SQLite is the canonical fact store.

   Files under system-space semantic directories are rebuildable read views, diagnostics, or manifests. They are not a second source of truth.

2. `sync` is read-only for domain facts.

   `sync` can resolve focus, issue a lease, and return context/contract guidance. It must not create `Task`, `TaskRun`, inbox records, assets, decisions, or summaries.

3. `commit` is the only durable protocol fact entrance.

   Durable task, run, item, handoff, asset, decision, relationship, context-candidate, and index facts are produced by projecting committed protocol events.

4. The Agent and LLM see a small stable protocol.

   They should learn `sync` and `commit`, not internal table names, storage paths, projection rules, or recall internals.

5. Workroot must not block useful user work.

   If a protocol write is malformed, missing refs, or cannot locate a Workroot, Workroot returns guidance and lets the Agent continue. It should not create dirty durable facts when location is unsafe.

6. Current-task resolution is a protocol/strategy responsibility.

   The context builder may budget, filter, and render context. It must not independently choose "current task".

7. Runtime views support inspection and debugging.

   Runtime view files exist so developers and future tools can inspect state without opening SQLite. They must be rebuildable from SQLite.

## Existing Domain Entities And Their Roles

No new entities are introduced.

| Entity | Canonical storage | Role in this repair |
| --- | --- | --- |
| `protocol_commit_batches` | SQLite | Idempotent batch boundary. Same key plus same semantic hash returns the same response. Same key plus different semantic hash returns `idempotency_key_conflict`. |
| `protocol_events` | SQLite | Agent semantic fact ingress after `commit`. Events can be `applied`, `quarantined`, or rejected at batch level. |
| `exchange_leases` | SQLite | Short-lived write authority and state snapshot. Leases bind allowed event kinds and optionally task/run refs. |
| `state_versions` | SQLite | Version clock for workroot, task, run, asset, decision, event log, context, and indexes. |
| `tasks` | SQLite | User work boundary. Temporary work is still a `Task` with `role=inbox`, not a different type. Long-cycle work is a normal `Task` with stable root/parent refs. |
| `task_runs` | SQLite | Current execution episode under a task. It should be reused while the same task is continuing; it should not become one active run per accidental start-work call. |
| `task_items` | SQLite | Agent-produced work steps, statuses, and results. Items are process state under a task/run, not new task types. |
| `task_summaries` | SQLite | Current compact semantic summary for recall and handoff. Generated from committed progress/checkpoint facts, not raw chat logs. |
| `handoffs` | SQLite | Resume-ready view of current state and next action. It is not a fact source independent of protocol events. |
| `assets` | SQLite | Logical user-visible or managed asset records. Same path should normally update one logical asset record, not create repeated independent assets. |
| `asset_path_history` | SQLite | Path observation history for an asset. |
| `asset_provenance` | SQLite | Source event and provenance links for an asset. |
| `relationship_nodes` and `relationship_edges` | SQLite | Graph projection linking tasks to assets, decisions, and other recall targets. |
| `context_candidates` and FTS | SQLite | L1/L2-style searchable metadata and summaries for context retrieval. |
| `indexed_files`, `indexed_chunks`, `indexed_chunks_fts` | SQLite | Local file/chunk FTS for deeper evidence recall. |
| `context_packages`, `context_traces`, selections, trims | SQLite | Context builder trace and audit data. |

## Root Cause Analysis

### 1. Focus resolution prefers new work too aggressively

Current behavior:

- `resolve_sync_focus()` returns `new_work` when durable markers such as design, review, implement, task, plan, or long-running are detected.
- It only resolves continuation first for startup or explicit continuation reasons/signals.
- In a long-cycle role, many normal follow-up user requests contain durable markers, so the resolver asks for a new `intent`.

Root cause:

The focus strategy treats "durable work marker" as "new task boundary". Those are different decisions.

Correct behavior:

A durable marker means "this may need persistence". It does not mean "create a new task". If an active accepted focus exists and the new request is semantically close, Workroot should continue the current task.

### 2. `project_intent` creates task ids from event ids

Current behavior:

- `project_intent()` creates `task_id = stable_id("task", event_id)` unless payload explicitly includes `task_hint.task_id`.
- Live LLM calls produce different event ids, so semantically repeated start-work events become new tasks.

Root cause:

Task identity is event-derived instead of work-boundary-derived.

Correct behavior:

An intent projection must first try to attach to an existing accepted task. Only if no accepted current or similar active task exists should it create a new task.

### 3. The packet is not deterministic enough for live LLM/Agent loops

Current behavior:

- The lease appears in refs and in adapter hints, but the LLM still drops it.
- Some accepted shape names differ between internal contract and CLI shape names.
- Missing continuation fields and missing asset title produce raw command failures.
- `--known-state` and `--work-signal` require JSON. The LLM sometimes passes plain text.
- The Agent makes help/status calls because it is uncertain about exact syntax.

Root cause:

The protocol response is conceptually right but not operationally copyable enough. It tells the LLM what Workroot means, but not always exactly what to ask the Agent to run.

Correct behavior:

Each packet must include one small natural-language instruction and one exact copyable command template. Required values should be inline and shape-specific.

### 4. CLI validation turns recoverable protocol friction into failed commands

Current behavior:

- Missing `--lease` raises a local CLI error before the protocol controller can return `resync_required`.
- Missing `--state/--next` raises a local CLI error.
- Plain-text `--work-signal` and `--known-state` fail JSON parsing.

Root cause:

The CLI adapter is acting as a strict validator instead of a tolerant protocol transport.

Correct behavior:

For protocol commands, malformed or incomplete semantic input should return a structured Workroot response with `agent_may_continue=true`, not a raw nonzero CLI failure, unless the syntax is completely unparseable.

### 5. Asset projection uses event identity instead of logical asset identity

Current behavior:

- Each asset commit without explicit `asset_id` becomes `asset-<event_id>`.
- Same `current_path` produces many current asset records.
- `content_hash` stays empty.
- File body is not indexed into `indexed_files` or `indexed_chunks_fts`.

Root cause:

The projection records "an asset event happened", but it does not resolve "which logical asset does this event describe?".

Correct behavior:

For user-visible assets, a relative path inside the user directory is a strong identity signal. The projection should resolve or create a stable logical asset, compute hash when readable, update path/provenance history, and index textual content.

### 6. Runtime directories are created but not populated

Current behavior:

- System-space semantic dirs exist.
- Runtime facts are mostly in SQLite.
- Developers see empty `tasks/`, `handoffs/`, `assets/`, `relationships/`, `indexes/`, `context/`, `diagnostics/`, `state/`.

Root cause:

The architecture says these directories can hold read models, exports, and diagnostics, but no projection writer builds those views.

Correct behavior:

After relevant commits and context builds, Workroot should write small rebuildable read views into the existing semantic directories.

### 7. E2E validation masks and amplifies failures

Current behavior:

- The 50-round role repeats a 10-round script five times.
- The harness marks every round after first quarantine as failed because it checks cumulative quarantine status.
- It does not enforce task proliferation thresholds directly.

Root cause:

The harness validates "any bad history exists" instead of "what changed this round", and it does not encode the core continuity invariant.

Correct behavior:

E2E should snapshot before/after counts per round, validate deltas, and assert that a single long-cycle scenario stays under a low task/run proliferation threshold.

## Target Flow

### Flow 1: Agent startup or context load

1. User opens an Agent inside a registered Workroot user directory.
2. Agent may load native entry files and may call:

   ```text
   workroot context --agent codex --cwd . --query "<current user intent>"
   ```

3. Workroot resolves the Workroot from `cwd`.
4. Workroot renders a small startup context:
   - protocol guidance
   - current continuity summary if one exists
   - selected recall candidates
   - budget/debug metadata only when requested
5. Startup context is read-only. It does not create task facts.

Important constraint:

The system must not rely on the Agent remembering startup context forever. Every later `sync` or `commit` packet must be self-contained enough to continue the protocol loop.

### Flow 2: Sync before meaningful work

1. Agent/LLM asks Workroot to sync:

   ```text
   workroot agent sync --agent codex --cwd . --reason before_work --format packet --query "<short intent>"
   ```

2. Workroot resolves:
   - Workroot by `cwd`
   - current accepted task/run from known state, current handoff, active/incomplete run, recent task, or semantic match
   - whether this is quick, continuation, guarded, explicit new work, or ambiguous
3. `sync` returns:
   - directive
   - lease
   - compact continuity context
   - private packet with exact next call

Sync never creates a task.

### Flow 3: First durable task creation

If no accepted current task exists and the user request is durable, `sync` returns `call.shape=start_work`.

The LLM asks the Agent to run a command like:

```text
workroot agent commit --format packet --shape start-work --lease <lease> --title "<task title>" --summary "<stable goal>" --persistence normal --cwd .
```

Projection behavior:

1. Validate lease and event.
2. Search for existing attach target:
   - explicit task refs from payload
   - task/run refs from lease
   - latest current handoff
   - latest active or incomplete run
   - active task with normalized title/query similarity
3. If no target exists, create a new `Task` and `TaskRun`.
4. If a target exists, attach to the existing `Task` and reuse or ensure one current `TaskRun`.
5. Return a new task-scoped lease and packet.

### Flow 4: Continued progress on the same task

For follow-up user requests that are semantically within the same long-cycle task:

1. `sync` should resolve `kind=continuation`, not `new_work`.
2. The packet should prefer `checkpoint`, `asset`, `decision`, or `continuation`, not `start_work`.
3. `commit(checkpoint)` updates:
   - `task_runs.output_summary`
   - current `task_summaries`
   - `task_items`
   - context candidates
   - state versions
   - runtime read views

Repeated checkpoint or done/open item text should update an existing logical item when the title matches closely within the same task, rather than creating event-id-only duplicate items.

### Flow 5: User-visible asset creation

When the Agent creates or updates a user-visible file:

1. Agent writes the file under the user directory.
2. Agent commits the asset:

   ```text
   workroot agent commit --format packet --shape asset --lease <lease> --title "<asset title>" --asset-kind document --path "results/founder-operating-plan.md" --summary "<what this asset contains>" --status current --cwd .
   ```

3. Workroot resolves the path against the registered user directory.
4. If the path is readable text:
   - compute `content_hash`
   - upsert logical asset identity by normalized path when no explicit asset id exists
   - append asset path/provenance records
   - upsert `context_candidates`
   - populate `indexed_files`, `indexed_chunks`, and `indexed_chunks_fts`
   - link task to asset in relationship graph
   - write derived `assets/manifest.json`
5. If the file is missing or unreadable:
   - record asset metadata only when the event is still meaningful and locatable
   - add a warning
   - do not block the Agent

### Flow 6: Decision capture

When a stable decision is made:

```text
workroot agent commit --format packet --shape decision --lease <lease> --title "<decision title>" --decision "<decision>" --reason-text "<reason>" --scope task --cwd .
```

Projection behavior:

- Create/update a decision-style `context_candidate`.
- Link the current task to the decision in relationship graph.
- Bump task/context state versions.
- Write relationship and context read views.

No separate `decisions` table is added in this repair.

### Flow 7: Handoff before stopping or switching

Before stopping, switching, or when Workroot says `required_before_stop` includes continuation:

```text
workroot agent commit --format packet --shape continuation --lease <lease> --state "<current state>" --next "<next useful action>" --cwd .
```

Projection behavior:

- Supersede previous current handoff for the task.
- Insert current handoff.
- Update current summary next actions.
- Mark the current run as resumable rather than leaving many active orphan runs.
- Return `safe_to_stop` or a task-scoped continuation lease.
- Write `handoffs/current.md`, `handoffs/current.json`, `state/current.json`, and `tasks/current.json`.

### Flow 8: Next session resume

When a new session starts:

1. Agent calls context or sync.
2. Focus resolver finds:
   - current handoff
   - latest incomplete/active run
   - current summary
   - active task
3. Workroot returns a packet that says this is continuation and gives a checkpoint/continuation command template.
4. The LLM continues the same task without asking the user about internal task ids.

## Focus Resolution Repair

### Decision order

The focus resolver should use this order:

1. Guarded action detection.

   If user intent implies publish, release, delete, redact, or forget, return guarded guidance. Durable write is limited until confirmation.

2. Explicit known state.

   If `known_state.task_id` and optional `known_state.run_id` point to an accepted active/paused/blocked task, continue that task.

3. Explicit task switch or explicit new task.

   If the user says "start a new task", "separate this from the previous task", or sync reason is `before_task_switch`, allow new intent if no strong current continuation should be preserved first.

4. Current handoff.

   Latest current handoff for an active/paused/blocked task is a strong current focus.

5. Current active or incomplete run.

   Latest active/incomplete run under an active/paused/blocked task is a strong current focus.

6. Recent active task.

   Latest updated active task is a medium current focus.

7. Semantic match against active task titles/summaries.

   Compare normalized query/signal focus with active task title, current summary, next action, and recent item titles.

8. Quick answer classification.

   A quick request stays non-persistent only when there is no durable marker and no active focus requiring continuation.

9. Durable work classification.

   Durable marker means persistence may be needed. It creates a new task only if no current focus matches and the request is not continuation.

10. Ambiguous fallback.

   If several tasks score too close, return `continue_without_persistence` or ask Agent to sync with a clearer short intent. Do not create a new task by default.

### Required behavior change

Current durable markers must stop being direct `new_work` triggers.

For a long-cycle task, requests like "review the plan", "update the asset", "decide risk checkpoint", "summarize next step", or "continue the cadence" should resolve to the current task unless the user explicitly starts a new boundary.

### Suggested scoring

Use deterministic local scoring first. Do not call a model.

Signals:

- known task/run valid: +100
- current handoff: +80
- latest incomplete/active run: +70
- latest active task: +45
- title token overlap: +0 to +40
- summary/next-action overlap: +0 to +30
- same user-visible asset path referenced by recent task: +25
- explicit continuation marker: +20
- explicit new task marker against candidate: -80
- closed/archived/released task: not eligible except explicit reopen later

Decision:

- score >= 70: continuation high confidence
- score 45-69 and next candidate gap >= 15: continuation medium confidence
- score < 45 or gap < 15: ambiguous or new work depending explicit boundary

## Task Projection Repair

### `commit(intent)` rules

`commit(intent)` remains the only task creation entrance, but it should not blindly create a task.

Projection algorithm:

1. Load lease.
2. Normalize intent:
   - title
   - summary
   - persistence
   - parent/root refs
   - optional task id
3. Resolve attach target:
   - explicit payload `task_id`
   - lease task ref
   - parent/root ref
   - current handoff task
   - latest active/incomplete run task
   - semantic match among active tasks
4. If attach target is found:
   - update existing task `updated_at`
   - keep title unless existing title is blank or new title is materially better
   - ensure a usable run
   - return effect `task_attached`
5. If no attach target is found:
   - create `Task`
   - create `TaskRun`
   - return effect `task_created`

### Task identity

For new task creation, event-derived ids are still acceptable as physical ids. The repair is not to make ids semantic. The repair is to avoid creating a new physical id when the semantic task boundary already exists.

### Temporary inbox tasks

Temporary work still uses `Task`:

- `role=inbox`
- `process_level=L0`
- `retention_policy=rolling_7d`
- `visibility=implicit`

Promotion to normal task remains a state metadata update, not a separate entity.

### Parent/root relationships

No `Project`, `Initiative`, or `SubTask` entity is added.

If the user or Agent supplies a parent task, store:

- `parent_task_id`
- `root_task_id`

Every task remains a `Task`. Parent/child is relationship structure, not a type split.

### TaskRun semantics

For this repair, `TaskRun` means the active execution episode for a task, not every LLM message and not every accidental start-work event.

Rules:

- First true new task creates one run.
- Continuation uses the task's current active/incomplete run.
- A repeated `start_work` that attaches to an existing task does not create a new active run unless no usable run exists.
- Handoff should mark the run resumable with the existing status vocabulary. Use `incomplete` for a run that intentionally stops with a handoff.
- A completed task run is produced only when the Agent explicitly marks progress as completed or the task is closed.

Acceptance target for a single 50-round repeated long-cycle scenario:

- Active root tasks: 1 preferred, no more than 3.
- Active/incomplete runs for the same root task: 1 preferred, no more than 5.
- No repeated start-work commands should produce repeated root tasks.

### TaskItem projection

Task items should be deduped within a task by normalized title when no explicit `item_id` is supplied.

Rules:

- Same normalized title under same task updates existing item.
- Status transition rules still apply.
- Repeated `done` item should not create another duplicate done row.
- Result summary can be refreshed.
- Event provenance stays in `source_event_id` or metadata.

## Protocol Packet Repair

### Packet goals

The packet must be:

- private
- small
- LLM-readable
- copyable
- self-contained
- stable across future adapters

The packet may include JSON because adapters and LLMs handle structured data well, but it must also include natural-language meaning and an exact command line so the LLM can ask the Agent to call Workroot correctly.

### Packet shape

Keep one packet response format. Do not create separate public/private protocol concepts.

Recommended packet sections:

~~~text
## Workroot Private Packet

Use privately. Do not show this to the user.

Meaning:
- Work: <focus and summary>
- Next Workroot call: <sync|commit|none>
- Why: <short reason>

Exact next call:
<copyable command template>

Required facts:
- <field>: <meaning>

JSON:
```json
{
  "v": "workroot.packet.v1",
  "rules": ["private_do_not_show_user", "continue_if_workroot_unavailable"],
  "work": {
    "focus": "continuation",
    "summary": "...",
    "state": "...",
    "next": "...",
    "refs": {"task": "...", "run": "..."}
  },
  "call": {
    "action": "commit",
    "shape": "checkpoint",
    "when": "at_checkpoint",
    "required": ["lease", "summary"],
    "optional": ["done", "open", "blocked"],
    "command": "workroot agent commit --format packet --shape checkpoint --lease ... --summary \"...\" --cwd .",
    "capture_rule": "stable_facts_only"
  },
  "write": {
    "accepted": true,
    "status": "applied"
  }
}
```
~~~

### Stable packet fields

| Field | Required | Meaning |
| --- | --- | --- |
| `v` | yes | Packet version. Stable adapter-independent contract. |
| `rules` | yes | Small private behavior constraints. |
| `work.focus` | yes | Workroot's current focus classification. |
| `work.summary` | no | Compact current task or intent summary. |
| `work.state` | no | Resume-ready current state. |
| `work.next` | no | Next useful action. |
| `work.refs.task` | no | Opaque task ref for Agent/LLM to pass back only when asked. |
| `work.refs.run` | no | Opaque run ref for Agent/LLM to pass back only when asked. |
| `call.action` | yes | `sync`, `commit`, or `none`. |
| `call.shape` | no | Required commit shape when action is `commit`. |
| `call.when` | yes | Human-readable timing, such as `now`, `at_checkpoint`, `before_stop_or_switch`, `after_user_visible_file_created`. |
| `call.reason` | no | Why this call is requested. |
| `call.required` | yes for commit | Required semantic fields. |
| `call.optional` | no | Optional semantic fields that improve continuity. |
| `call.command` | yes when action is not `none` | Exact copyable CLI command template for current adapter. |
| `call.capture_rule` | no | Short rule telling the LLM what kind of fact to summarize. |
| `write.accepted` | yes | Whether the previous write was accepted. |
| `write.status` | yes | `applied`, `not_recorded`, `resync_required`, `quarantined`, `rejected`, or equivalent protocol result. |
| `write.warning` | no | Compact non-blocking warning. |

### Shape semantics

| Shape | When Workroot should ask for it | Required fields |
| --- | --- | --- |
| `start_work` | Only when a new durable or temporary task boundary should be created. | `lease`, `title`, `summary`, `persistence` |
| `checkpoint` | Meaningful progress, result, summary, or task-item update. | `lease`, `summary` |
| `continuation` | Before stopping, switching, or leaving incomplete work. | `lease`, `state` or `next` |
| `asset` | After a user-visible file is created or materially updated. | `lease`, `title`, `asset_kind`, `path`, `summary`, `status` |
| `decision` | After a stable decision is made. | `lease`, `title`, `decision`, `reason_text`, `scope` |
| `state_update` | Explicit task state or metadata change. | `lease`, `target`, `change` |

### Important naming cleanup

Use one LLM-facing shape vocabulary:

- `start_work`
- `checkpoint`
- `continuation`
- `asset`
- `decision`
- `state_update`

Avoid returning `continuation_checkpoint` in one layer and requiring `continuation` in another. The CLI may accept hyphenated aliases (`start-work`, `state-update`), but the packet vocabulary should be stable.

## CLI Adapter Repair

The CLI is a protocol adapter, not the owner of protocol semantics.

### Tolerant parsing

Change behavior:

- `--known-state` accepts JSON object or plain text. Plain text becomes `{"note": "<raw>"}`.
- `--work-signal` accepts JSON object or plain text. Plain text becomes `{"focus": "<raw>"}` or `{"note": "<raw>"}` with no failure.
- Missing `--lease` in `agent commit --shape ... --format packet` should return structured `resync_required`, not local `ValueError`.
- Missing shape-specific semantic fields should return structured guidance when possible, not raw failure.

Exit policy:

- Unknown command or syntax parser failure can remain nonzero.
- Protocol semantic rejection should exit 0 with `result.accepted=false` and `agent_may_continue=true`.
- This keeps the Agent moving while making the failure visible to diagnostics.

### Exact command templates

Packet command templates must always include:

- `--format packet`
- `--cwd .` when cwd is available
- `--lease <lease>` when commit is requested
- shape-specific required fields

Examples:

```text
workroot agent sync --agent codex --cwd . --reason continue --format packet --query "<short current user intent>"
```

```text
workroot agent commit --format packet --shape checkpoint --lease lease_xxx --summary "<stable progress summary>" --cwd .
```

```text
workroot agent commit --format packet --shape continuation --lease lease_xxx --state "<current state>" --next "<next useful action>" --cwd .
```

```text
workroot agent commit --format packet --shape asset --lease lease_xxx --title "<asset title>" --asset-kind document --path "<relative path>" --summary "<asset summary>" --status current --cwd .
```

## Non-Blocking Error Handling

### Cannot locate Workroot

If commit cannot locate a Workroot from `cwd`, `workroot_id`, or lease:

- Do not persist event fragments.
- Do not create tasks.
- Return `ok=true`, `agent_may_continue=true`, `result.recorded=false`, `status=not_recorded`.
- Packet asks the Agent to sync again if durable continuity is still relevant.

This avoids dirty data without blocking user work.

### Missing or rejected lease

If Workroot can locate the Workroot but lease is missing, expired, conflicting, or unsafe:

- Do not project domain facts.
- Prefer not to store a domain event as applied.
- If the event is minimally identifiable and useful for diagnostics, it may be stored as quarantined under the located Workroot.
- Return `resync_required`.
- Packet includes exact `sync` command.

### Shape input incomplete

If a shape-native CLI call lacks required semantic fields:

- Do not project domain facts.
- Return packet guidance listing missing fields.
- Exit 0 for packet/json/guidance formats.
- Record diagnostics only when Workroot is safely located.

### Projection conflict

If projection detects a hard conflict, such as invalid state transition:

- Roll back the projection savepoint.
- Mark event quarantined or reject batch depending conflict class.
- Return `agent_may_continue=true`.
- Packet asks for sync before retry.

## Asset And Local FTS Repair

### Logical asset identity

When no explicit `asset_id` is supplied:

- If `path` is a relative user-directory path, derive a stable logical id from normalized path.
- If path is not usable, fall back to event id.

This changes repeated commits for `results/founder-operating-plan.md` from 10 independent current assets to one logical asset with updated provenance/history.

### Path and content safety

Rules:

- Resolve relative paths inside registered user directory.
- Reject or warn on paths that escape the user directory.
- Do not read binary or oversized files into context indexes.
- Store file metadata and warning even if content is not indexed.

### Hashing

For readable file assets:

- Compute a content hash.
- Store it in `assets.content_hash`.
- If unchanged hash is seen again, update provenance and timestamps without duplicating chunks.

### FTS indexing

On asset commit:

- Upsert `indexed_files` using stable file id based on workroot id and relative path.
- Split text into deterministic chunks.
- Upsert `indexed_chunks`.
- Upsert `indexed_chunks_fts`.
- Update `index_manifests` or `state_versions` to show index freshness.

For initial user files:

- Do not index the entire user directory indiscriminately during startup.
- The context builder may still show top-level fallback file candidates.
- A future explicit index rebuild command can index broader user-selected files.
- For this repair, ensure committed assets are indexed because those are deliberate user-visible outputs.

### Context candidates

Asset and decision projections should keep `context_candidates` current:

- candidate id should point to the logical asset/decision, not event-specific duplicates
- summary should be concise and recall-friendly
- domains should include task id, asset kind, and path

## Runtime Read Views

### Decision

Use existing per-Workroot semantic directories as derived read-view locations. Do not add a second `runtime/` directory in this repair.

Rationale:

- The state directory itself is system runtime space.
- Existing directories already express the semantic boundary.
- Adding `runtime/` would make two runtime concepts: `runtime/` plus `tasks/`, `assets/`, `context/`, and so on.
- The E2E field currently named `runtimeDirectory` should be corrected to report semantic runtime view directories and file counts.

### View files to generate

All files below are derived and rebuildable from SQLite.

```text
<stateDirectory>/
  state/
    current.json
  tasks/
    current.json
    active.json
  handoffs/
    current.md
    current.json
  assets/
    manifest.json
  relationships/
    summary.json
  indexes/
    manifest.json
  context/
    latest.md
    latest-trace.json
  diagnostics/
    protocol-friction.json
```

### Update triggers

After commit projection:

- update `state/current.json`
- update task/run/handoff/asset/relationship/index views touched by effects
- update `diagnostics/protocol-friction.json` when warnings, quarantine, rejected batches, or protocol parse friction occur

After context build:

- update `context/latest.md`
- update `context/latest-trace.json`

After index rebuild or asset indexing:

- update `indexes/manifest.json`
- update `assets/manifest.json`

### Read-view consistency

Rules:

- View writer reads SQLite after the transaction commits or within the same transaction before final commit.
- If writing a view file fails, domain projection still succeeds, but diagnostics record the view write failure.
- View files are not read by protocol projection as canonical state.
- A maintenance command can rebuild all view files from SQLite.
- Unexpected root-level stores such as `<stateDirectory>/workroot.sqlite` are diagnostic findings. New runtime flows should not create or depend on that file.

## Relationship Repair

Once task reuse is fixed, relationship quality improves automatically because assets and decisions attach to the stable root task.

Additional repair:

- Use stable logical target ids for assets.
- Upsert task-to-asset and task-to-decision edges.
- Avoid event-specific duplicate edges for the same task and same logical target.
- Export `relationships/summary.json` as a derived view.

No graph database is introduced.

## Context Continuity Implications

This repair does not implement full L1/L2/L3 disclosure, but it prepares the necessary substrate:

- L1 metadata: `tasks`, `task_summaries`, `context_candidates`, relationship summaries.
- L2 summaries: current summaries, handoffs, asset summaries, decision summaries.
- L3 evidence: indexed file chunks, relationship evidence, source refs.

The current context builder should continue to budget/filter/render. It should consume the improved canonical facts and indexes, but current-task selection remains upstream in protocol focus resolution.

## E2E Harness Repair

### Round-level snapshots

Before and after each round, capture:

- protocol event count by status and kind
- task count by status/role/process level/root
- run count by status/task/root
- asset count by path/hash
- indexed file/chunk counts
- command count by semantic action
- command failures by reason

Round validation should compare deltas, not cumulative historical state.

### Correct quarantine assertion

Current failure:

- Once quarantine exists, every later round fails.

Repair:

- A round fails for quarantine only when new quarantined events are created in that round and the scenario did not expect degraded behavior.

### Task proliferation assertions

For single-role long-cycle mode:

- root active normal tasks should stay under a small threshold
- duplicate normalized task titles should be flagged
- repeated `start_work` should not produce repeated root tasks

Suggested threshold for repeated Founder Operator 50-round stress:

- total normal L1 root tasks <= 3
- active normal L1 root tasks <= 2
- task runs <= 5 unless scenario explicitly starts new runs

### Command friction metrics

Audit should include:

- total Workroot commands
- help/status command count
- failed commands by reason
- missing lease count
- missing continuation fields count
- plain-text JSON parse recovery count
- asset missing field count
- context byte trend

The E2E should not pass if the Agent can only succeed by making many help calls and failed attempts.

### Scenario realism

The repeated 10-round script remains useful for stress, but it is not enough.

After this repair, add a separate single-role long-cycle scenario with 50 unique, layered turns:

- task start
- context refresh
- checkpoint
- file asset creation
- asset update
- decision
- risk review
- task item completion
- interruption
- continuation
- temporary side question
- return to main task
- final handoff

This can be a second validation step after the deterministic repair passes.

## Implementation Slices

This is the recommended implementation order. Each slice should have tests before broad live E2E.

### Slice 1: Focus and task projection

Files likely touched:

- `src/ai_workroot/protocol/focus.py`
- `src/ai_workroot/protocol/projections.py`
- `tests/unit/test_protocol_sync_focus_v2.py`
- `tests/unit/test_protocol_task_continuity_v2.py`
- `tests/unit/test_protocol_projections.py`

Work:

- Change durable marker handling to prefer current focus.
- Add semantic active task matching.
- Add intent attach/dedupe behavior.
- Add task item title dedupe.
- Adjust TaskRun reuse and handoff run status behavior.

### Slice 2: Protocol packet and CLI tolerance

Files likely touched:

- `src/ai_workroot/protocol/packet.py`
- `src/ai_workroot/protocol/response.py`
- `src/ai_workroot/commands/agent_exchange.py`
- `src/ai_workroot/entrypoints/cli/main.py`
- `tests/unit/test_protocol_packet.py`
- `tests/unit/test_agent_exchange_command.py`
- `tests/unit/test_protocol_commit_reliability_v2.py`

Work:

- Unify shape names.
- Add exact `call.command`.
- Include natural-language meaning plus JSON.
- Parse plain text signal/state safely.
- Return structured protocol responses for missing lease and missing fields.

### Slice 3: Asset identity and FTS indexing

Files likely touched:

- `src/ai_workroot/protocol/projections.py`
- `src/ai_workroot/capabilities/retrieval/providers/sqlite_fts.py`
- possibly a focused helper under `src/ai_workroot/capabilities/assets/` or `src/ai_workroot/capabilities/retrieval/`
- `tests/unit/test_protocol_projections.py`
- new or existing integration tests for asset indexing

Work:

- Resolve asset paths safely.
- Derive stable asset ids from path.
- Compute content hash.
- Upsert FTS file/chunk rows.
- Refresh context candidates.

### Slice 4: Runtime read views

Files likely touched:

- new focused writer module under existing state or protocol boundary, for example `src/ai_workroot/state/runtime_views.py`
- `src/ai_workroot/protocol/controller.py`
- `src/ai_workroot/capabilities/context/builder.py`
- `src/ai_workroot/state/environment.py` only if directory constants need clarification
- integration tests for generated view files

Work:

- Generate derived views after commit/context.
- Add rebuild function.
- Update E2E summary fields away from misleading `runtimeDirectory`.

This is not a new domain layer. It is an output adapter for SQLite read models.

### Slice 5: E2E harness repair

Files likely touched:

- `tests/e2e/live_task_continuity.py`
- `tests/e2e/live_task_continuity_cases.py`
- related report/audit helpers

Work:

- Add before/after DB snapshots per round.
- Validate per-round deltas.
- Add task proliferation assertions.
- Add command friction audit.
- Preserve artifacts and never clean live run outputs unless inside owned sentinel sandbox.

### Slice 6: Documentation alignment

Files likely touched:

- `docs/architecture/003-runtime-layout.md`
- protocol/task continuity specs under `docs/superpowers/specs/`
- relevant implementation plans

Work:

- Document semantic runtime read views.
- Clarify SQLite as canonical source.
- Clarify that `sync` is read-only and `commit(intent)` is task creation entrance.
- Clarify no `runtime/` directory is added in this repair unless the team explicitly reverses that decision.

## Test Plan

### Unit tests

Focus resolver:

- Durable marker plus current handoff resolves continuation.
- Durable marker plus active run resolves continuation.
- Explicit "start a new task" creates new-work directive.
- Ambiguous active candidates return non-persistent ambiguous guidance.
- Quick question with no durable marker stays quick.

Projection:

- First intent creates task/run.
- Repeated similar intent attaches to existing task.
- Repeated similar intent does not create another active run when a usable run exists.
- Temporary intent creates `role=inbox`, `process_level=L0`, `retention_policy=rolling_7d`.
- Task items dedupe by normalized title.
- Handoff supersedes previous current handoff and marks run resumable.

Packet:

- Packet includes exact command with lease.
- Packet shape names match CLI accepted shapes.
- Continuation packet includes `--state` and `--next`.
- Asset packet includes `--title`, `--asset-kind`, `--path`, `--summary`, `--status`.

CLI:

- Plain-text `--work-signal` does not fail.
- Plain-text `--known-state` does not fail.
- Missing lease returns structured `resync_required` packet with exit 0 for packet format.
- Missing continuation fields returns structured guidance, not raw failure.

Assets/FTS:

- Same path upserts same logical asset.
- Content hash is stored.
- Text asset populates indexed file/chunk/FTS tables.
- Path escaping user directory is rejected or warned without indexing.

Runtime views:

- Commit writes expected semantic view files.
- Context build writes latest context view and trace.
- Views are rebuildable from SQLite.

### Integration tests

- Run sync -> commit intent -> commit checkpoint -> commit asset -> commit decision -> commit continuation -> next sync.
- Verify one task, one logical asset, current handoff, relationship edges, indexed chunks, and runtime views.

### Live E2E

After unit/integration tests pass:

1. Run a small local or live 5-round smoke for one role.
2. Run the 5-role 10-round live suite.
3. Run the existing 50-round repeated Founder Operator stress.
4. Then run a new 50-unique-turn single-role scenario.

Do not clean the run root after live E2E. The artifacts are part of the review.

## Acceptance Criteria

### Functional

- A long-cycle 50-round Founder Operator run does not create 40 tasks.
- Repeated start-work attempts attach to existing current task when semantic boundary is the same.
- Checkpoints, assets, decisions, and handoffs attach to the same task.
- Next sync can resume from current handoff/summary without user intervention.
- User-visible asset path is tracked once logically and indexed.

### Protocol

- Packet always tells the LLM the next Workroot action in natural language and a copyable command.
- LLM/Agent does not need to know Workroot ids when cwd can locate the Workroot.
- Missing lease or malformed semantic fields do not block user work.
- Protocol responses preserve `agent_may_continue=true`.

### Storage

- Canonical facts remain in `<stateDirectory>/cache/workroot.sqlite`.
- New runs do not create or depend on root-level `<stateDirectory>/workroot.sqlite`.
- System-space semantic runtime directories contain derived view files after meaningful work.
- User directory contains only user files, native Agent entries, and expected user-visible assets.
- No uncommitted transient chat fragments are stored.

### Retrieval readiness

- `context_candidates_fts` remains populated for summaries.
- `indexed_files`, `indexed_chunks`, and `indexed_chunks_fts` are populated for committed text assets.
- Relationship graph links stable task to stable asset/decision targets.

### E2E

- Harness uses per-round delta validation.
- Quarantine failure is based on new quarantine in the round, not cumulative historical quarantine.
- Audit reports task proliferation, command friction, context size trend, runtime view files, and user-space pollution.

## Risks And Mitigations

### Risk: Over-attaching unrelated work to the current task

Mitigation:

- Require explicit new-task markers to override current focus.
- Use semantic score and gap threshold.
- Return ambiguous non-persistent guidance when candidates are too close.
- Keep user work non-blocking while avoiding dirty durable projection.

### Risk: Path-derived asset id hides versions

Mitigation:

- Treat path-derived id as current logical asset identity.
- Preserve each event in protocol events and provenance.
- Preserve path observations in `asset_path_history`.
- Future versioning can be added without changing this repair's user-facing behavior.

### Risk: Runtime read views become another source of truth

Mitigation:

- Document views as rebuildable only.
- Never use them as canonical projection input.
- Add rebuild tests from SQLite.

### Risk: CLI becomes too permissive and hides real bugs

Mitigation:

- Structured protocol rejection still records diagnostics when safely located.
- E2E reports protocol friction counts.
- Unknown command/parser syntax errors remain nonzero.

### Risk: FTS indexes too much user content

Mitigation:

- This repair indexes committed assets, not the entire user directory.
- Broader index rebuild remains explicit/future.

## Traceability Matrix

| E2E problem | Repair area | Expected proof |
| --- | --- | --- |
| 40 active tasks/runs | Focus + intent attach + run reuse | 50-round stress has <= 3 root tasks and <= 5 runs |
| Missing `--lease` failures | Packet exact command + CLI tolerance | Missing lease returns structured resync packet; live failure count drops |
| Missing continuation fields | Packet required fields + CLI guidance | Continuation packet includes state/next; no raw CLI failure |
| Plain-text JSON parse failures | CLI tolerant parsing | Plain-text signal/state args accepted as notes |
| Asset missing title/path | Packet required fields + structured missing-field response | Asset command template includes title/path; missing fields do not crash CLI |
| Cumulative quarantine false failures | E2E delta validation | Later rounds fail only on newly created quarantine |
| Empty semantic runtime dirs | Runtime read-view writer | Expected files under state/tasks/handoffs/assets/context/etc. |
| Empty file/chunk FTS | Asset indexing | Indexed files/chunks populated after asset commit |
| Duplicate asset rows for same path | Logical asset identity | Same path upserts one logical asset with provenance/history |

## Open Decisions For Review

1. Runtime read-view location.

   Proposed decision: use existing semantic directories, not a new `runtime/` directory. This corrects the currently misleading E2E `runtimeDirectory` field and keeps the state layout smaller.

2. TaskRun count target.

   Proposed decision: reuse the current active/incomplete run for continued work and do not create a new run for every Agent round. A truly new run should be explicit or created only when no usable run exists.

3. Asset versioning.

   Proposed decision: stable logical asset per path for current view; protocol events/provenance/path history preserve the update history. Full version entities are out of scope.

4. Broader user-file indexing.

   Proposed decision: index committed assets now; do not crawl/index the whole user directory in this repair.

## Self-Review

- No new domain entity is introduced.
- `sync` remains read-only.
- `commit(intent)` remains the only task creation entrance.
- SQLite remains canonical.
- Runtime files are derived read views.
- Agent/LLM protocol remains `sync` and `commit`.
- Non-blocking behavior is preserved.
- The design directly addresses every major 50-round E2E failure.
- Future L1/L2/L3 recall is not implemented here, but the data substrate is improved for it.
