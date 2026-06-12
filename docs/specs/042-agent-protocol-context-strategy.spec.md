# Spec 042 — Agent Protocol And Context Strategy

Status: accepted for the 0.9.531 feature line
Target: 0.9.531+

## Purpose

Define the current Agent Protocol and context strategy contract after task
continuity, language-independent WorkSignal handling, lease-aware writes,
layered context recall, and multi-Agent entry support.

This spec replaces the public need for detailed Agent workflow process plans.

## Protocol Actions

The stable Agent Protocol has two semantic actions:

```text
sync
commit
```

`workroot context` is a read-only startup/context wrapper. It is not a third
durable protocol action.

Durable facts must enter through `commit` only.

## Agent Descriptor

`--agent` is an Agent descriptor string, not a closed product enum.

Workroot must not add product-specific branches for Codex, Claude, Cursor,
Hermes, OpenClaw, or future Agent names.

`--transport` is adapter metadata. It defaults to `cli` and may be passed by
future MCP or SDK adapters.

Supported CLI surfaces:

```text
workroot context --agent <agent> --transport <transport>
workroot agent sync --agent <agent> --transport <transport>
workroot agent commit --agent <agent> --transport <transport>
```

Commit shorthand may preserve source metadata:

```text
transport
client
agent_version
thread_id
channel_id
```

These fields belong to protocol event source metadata. They must not change
Task, TaskRun, Asset, Decision, Handoff, or Relationship semantics.

## Per-Turn Protocol Entry

For a meaningful user turn, Agent Entry should instruct the Agent to call:

```bash
workroot agent sync --agent <agent> --cwd . --query "<current user request>" --format packet
```

`sync` is the main state-alignment entry. It returns compact context, focus,
lease data when durable writes are safe, and shape-specific commit contracts.

`workroot context` remains a read-only auxiliary wrapper for startup recovery,
manual recall, and debugging. It is not the normal per-turn entry and must not
be required every turn.

`--query` carries the current user request. It is user-language content, not
the primary control plane. Workroot may use `--query` for local text matching
inside sources allowed by the recall plan, but it must not use natural-language
keywords in `--query` to choose disclosure depth or deep retrieval.

If the Agent/LLM can infer a compact WorkSignal before sync, it may also pass
`--work-signal`. Missing or malformed WorkSignal must not block the user's
work.

## WorkSignal

WorkSignal is runtime protocol input. It is not a task, a run, a durable fact,
or a recall-plan entity.

Fields:

```text
phase
work_kind
intended_action
boundary
focus
concerns
refs
```

Rules:

- `focus` stays in the user's language.
- Other semantic fields use stable enum values.
- `refs` may carry Workroot refs returned by earlier context.
- `boundary` may carry `continue_current`, `separate_work`, or `uncertain`.
- Invalid or unknown values are dropped or downgraded without blocking.
- Workroot must not use multilingual keyword dictionaries as the durable
  control mechanism.

The LLM normalizes user language into WorkSignal. Workroot validates the
stable semantics and decides internal strategy.

If WorkSignal is missing or malformed, Workroot must continue non-blockingly
with conservative shallow recall. Missing WorkSignal may reduce recall depth,
but it must not stop the Agent from answering the user.

Semantic priority:

```text
explicit refs or known_state
-> WorkSignal semantic fields
-> lease/state focus
-> bounded semantic matching
-> conservative fallback
```

`--query` remains useful for scoring candidates after a plan has selected the
allowed source families. It must not be the primary mechanism for deciding
whether Workroot should create work, attach to work, or open deep evidence.

Temporary side work has one special boundary rule:

```text
phase=switching + work_kind=inbox + no refs/known_state
```

means "start a new temporary inbox boundary". Workroot must not silently attach
that turn to the only existing active inbox just because one exists. If the
same signal includes explicit refs or known state, Workroot may continue the
referenced inbox instead.

New durable work has one explicit boundary rule:

```text
phase=starting + startable durable work_kind + durable intended_action + boundary=separate_work
```

Startable durable work kinds include goal-bearing work such as `task`,
`investigation`, `implementation`, `review`, `decision`, `learning`,
`authoring`, and `operations`. They do not include `quick`, `inbox`, or
`continuation`. `continuation` must bind to existing accepted focus through
known state, refs, lease/state focus, or bounded matching; if no reliable owner
is found, Workroot returns a non-blocking focus-refinement sync contract.

`phase=starting` without `boundary=separate_work`, `phase=planning`, or
`phase=switching + work_kind=task` is not enough to create a new root task when
a reliable owner can be selected. Without a reliable owner, Workroot returns a
non-blocking focus-refinement sync contract instead of creating a task fact.

Evidence-oriented user intent is represented by stable semantics, not by
matching the user's language. The Agent/LLM may use any language to understand
the user, then pass:

```json
{
  "intended_action": "inspect",
  "concerns": ["needs_evidence"]
}
```

Equivalent shorthand actions such as `explain`, `rationale`, `evidence`,
`source`, `proof`, and `justify` are normalized to `inspect` plus
`needs_evidence`. This requests evidence-oriented recall without depending on
English, Chinese, or any other natural-language keyword table inside Workroot.
Deep evidence chunks still require explicit refs; otherwise Workroot returns a
compact reference map and summaries.

## Lease

`sync` may issue a lease for durable writes.

Lease state protects:

- Workroot ownership;
- task/run focus;
- observed state versions;
- allowed event kinds;
- optional write policy.

Lease data is protocol control data. It may influence context strategy, commit
guards, debug traces, and recovery behavior. It must not be rendered as normal
user-facing context.

Temporary or side work may carry a lease write policy such as:

```json
{
  "expected_start_work_persistence": "temporary",
  "expected_task_role": "inbox",
  "source": "work_signal"
}
```

If a commit conflicts with the lease policy, Workroot should reject or defer
the unsafe durable projection while returning non-blocking recovery guidance.

A rejected commit response must make same-shape retry loops unlikely. The
private packet for a rejected write must say that the Agent should not retry the
same commit unchanged, and that persistence should be retried only after a
fresh sync returns a lease whose contract allows the matching shape.

## Commit Shapes

LLM-facing shorthand shapes map to durable protocol event kinds:

```text
start_work   -> intent
checkpoint   -> progress
continuation -> handoff
state_update -> state
asset        -> asset
decision     -> decision
```

Task creation must happen through `commit(shape=start_work)`, not `sync` or
`context`.

Asset commits require an explicit path to a user-visible asset.

`sync` responses must expose shape-specific commit contracts so the Agent/LLM
does not need to infer shorthand fields from help output. For example,
`decision` requires `decision` and `reason_text`; `summary` is not a valid
replacement for a decision payload.

## Context Strategy

Context strategy is internal policy. It should decide recall before fetching
detailed context.

Required order:

```text
focus boundary
-> context policy
-> safety and budget constraints
-> disclosure plan
-> recall plan
-> plan-constrained retrieval
-> final budget fit
-> rendering
```

The boundary decision belongs before retrieval. Context Builder receives the
resolved focus and RecallPlan; it does not decide which task is current.

The Context Builder is the recall-plan executor. It must not independently
decide which retrieval families to query. It may only call providers named by
the active RecallPlan, and it may only use mode settings as inputs to strategy
and budget sizing.

The disclosure model is layered internally:

```text
L1: orientation map, task/run/handoff metadata, refs
L2: summaries, decisions, assets, relationships, handoff summaries
L3: scoped evidence, indexed chunks, source snippets, raw references
```

These layer names are implementation language. They should not be exposed as
ordinary LLM-facing protocol vocabulary.

## Recall Rules

Context recall should be:

- WorkSignal-first;
- focus/ref/known-state aware;
- lease-aware as an internal strategy signal;
- bounded by token and latency budgets;
- filtered by release/safety state before rendering;
- non-blocking when data is missing or malformed.

Deep evidence retrieval must be scoped. Workroot should not fetch broad raw
history first and then trim it down.

RecallPlan source names are internal execution contracts. The current source
families are:

```text
current_task
current_handoff
task_summary
context_recall_hints
context_candidates
ref_candidates
relationships
indexed_chunks
ref_indexed_chunks
fallback_user_assets
```

Rules:

- `context_candidates` and `context_recall_hints` are shallow map/summary
  sources. They may use `--query` for matching even when WorkSignal is absent.
- `relationships` is enabled only when the plan allows relationship context.
- `ref_indexed_chunks` is the normal deep evidence source. It requires stable
  WorkSignal semantics plus explicit refs and must remain bounded.
- `indexed_chunks` is reserved for explicitly planned bounded knowledge lookup;
  evidence-oriented turns should prefer ref-scoped chunks.
- `fallback_user_assets` is disabled unless explicitly named by the plan.
- A quick or answer-only plan must not pull relationship signals, deep evidence,
  or user-directory fallback assets.
- The same WorkSignal must produce the same strategy across user languages.
- Evidence lookup must include explicit refs before scoped evidence chunks can
  be enabled. Task/run focus can help rank map and summary sources, but it must
  not open broad raw evidence by itself.
- Lease signals may narrow recall when state is stale, conflicted, or
  interrupted, but they are not a primary lookup key and are not rendered as
  normal context.

## Recovery And Diagnostics

Ambiguous focus should return candidate refs and a sync-next contract instead
of allowing unsafe durable writes. The Agent can pass the chosen ref back in
WorkSignal `refs` on the next sync.

Malformed or missing WorkSignal, missing lease, rejected commit, expired lease,
and quarantined protocol events are protocol friction. They must not block the
user's work, but they should be visible in runtime diagnostics.

The runtime diagnostics view includes:

```text
protocol event status counts
commit batch status counts
rejected commit batch count
protocol-friction JSONL summaries by code, stage, and source layer
```

This lets local validation distinguish "there was historical friction" from
"this turn introduced new friction".

## Asset Output Rules

Initialization may create:

```text
workroot-output/START_HERE.txt
```

This is a user-visible guide and output destination, not runtime state.

Default and user-declared output rules belong in managed state. Agents should
use those rules when producing future user-visible assets.

## Non-Goals

This spec does not introduce:

- new Agent Protocol actions beyond `sync` and `commit`;
- new L1/L2/L3 storage entities;
- Workroot-side LLM classification;
- remote embedding or vector database requirements;
- public exposure of lease internals;
- product-specific Agent branches.

## Acceptance

- `workroot context --agent <any-string>` works for registered Workroots.
- `--transport` flows through context, sync, and commit.
- `context` remains read-only.
- `sync` issues leases and commit contracts.
- `commit` is the only durable Agent fact entry.
- WorkSignal drives strategy without relying on natural-language keyword
  tables as the primary control plane.
- Context output remains bounded and hides internal layer/lease details from
  ordinary user-facing content.
