# Workroot Operating Protocol

This is the core operating protocol for AI agents working with AI Workroot.

It is the foundational protocol of the project. Domain skills, tool skills, MCP integrations, and agent-specific plugins must work inside this protocol.

For ordinary user experience, also follow:

- `docs/product-experience.md`
- `docs/user-interaction-contract.md`
- `docs/kernel-implementation-specification.md`

## Active Architecture

The active architecture is Clean Workroot:

```text
user-selected directory   user assets and optional authorized Native Agent Entry
AI_WORKROOT_HOME          WorkrootEnvironment and managed state
src/ai_workroot/          entrypoints / commands / protocol / capabilities / state / shared
```

Public Seed is historical. Legacy material may appear under `docs/history/public-seed/` or in compatibility fixtures, but agents must not treat root `space/`, root `.workroot/`, root `AGENTS.md`, or root `CLAUDE.md` as active architecture requirements.

## 1. Clean Boundary Rule

The user-selected directory is user-owned asset space.

AI Workroot must not create managed runtime folders, indexes, logs, context packages, handoffs, kernel files, or control files inside that directory by default.

Native Agent Entry files are the normal exception, and only after explicit authorization or bootstrap-dev dogfood behavior.

`workroot-output/START_HERE.txt` is also allowed after initialization as a
user-visible output guide. It is not runtime state, an index, a log, or a
control file.

Managed state belongs under `AI_WORKROOT_HOME` by default.

## 2. Progressive Workroot Charter

AI Workroot should let a user start useful work first.

Before preserving formal durable work, the Workroot should know enough about what it serves:

- purpose
- AI role
- work direction
- values and boundaries
- user preferences

In Clean Workroot this belongs in the per-Workroot managed charter/state, not in a required root `space/profile/` folder.

If guidance is blank or generic, ask only the smallest useful question, then continue doing the work.

## 3. Startup

For a normal agent entry, use the Native Agent Entry file when present. It
should stay short and direct the agent to sync state and request compact
current context, for example:

```bash
workroot agent sync --agent codex --cwd . --query "<current user request>" --format packet
```

`sync` is the normal meaningful-turn surface. It returns focus, compact
context, lease data when durable writes are safe, and the commit contract.
`workroot context` is read-only auxiliary behavior for startup recovery,
manual recall, and debugging.

`--agent` is an Agent descriptor string, not a fixed product enum. Use
`--transport` when the caller is not the default CLI transport, for example
`--transport mcp`.

Do not load deep history by default. Do not scan all files by default. Use
`workroot context --debug` when a task needs explainability.

## 4. Classify The Work

Classify the user's request into the lightest suitable path:

- quick question
- capture
- goal-oriented work
- recurring work
- larger project
- decision
- learning
- preservation
- continuation
- release or forgetting
- capability or workflow design

If the user is exploring, keep it lightweight.

If the work has a goal, expected result, or future value, create or update the appropriate managed Work record behind the scenes.

Do not ask ordinary users to manually create folders, choose task types, edit indexes, or decide where internal records go.

## 5. Work Records

Formal work is represented by Work concepts:

- Task
- L0 / L1 / L2 / L3 process levels
- AgentRun
- WorkAction
- WorkCheckpoint
- RetrievalCard
- InvalidationRecord
- Handoff
- OperationTransaction

Use the lightest process level that preserves continuity:

- `L0`: simple task state
- `L1`: process records with plans, runs, retrieval cards, and checkpoints
- `L2`: evidence records with actions, recipes, validation, and invalidations
- `L3`: deeper process continuity for complex, long-running, evidence-heavy, or cross-session work

Task process levels are distinct from Context Control disclosure levels. Task process levels describe persisted Work continuity depth; Context disclosure levels describe rendered recall depth inside a Context Package.

Legacy Public Seed task files may remain readable in compatibility tests and historical fixtures. New Clean Workroot behavior should use managed state and runtime APIs.

## 6. Promote What Matters

After work produces value, decide whether the result should become:

- Asset
- decision
- reusable knowledge Asset
- principle
- pattern
- reflection
- handoff
- invalidation
- release marker through Release Control
- tombstone, redaction, or deletion record when appropriate

Ask confirmation before preserving sensitive, private, emotionally heavy, or externally visible material.

## 7. Retrieval And Index Discipline

Important objects should be findable without full-directory scans.

Use Retrieval & Index Control for:

- materialized context candidates
- SQLite FTS
- file metadata
- relationship-backed signals
- recent activity
- explicit project files
- git state when available

Vector databases, remote embeddings, and remote LLM calls are not required for P0 context generation.

Debug traces should explain candidate sources, filters, scores, timing, token budgets, selected context, and dropped candidates.

## 8. Preserve Relationships

Important objects should be connected through Relationship Network:

- task to asset
- task to decision
- asset to source
- decision to evidence
- knowledge Asset to originating work
- invalidation to replacement
- handoff to current work

Relationship Network is the business domain. Graph is only technical implementation language.

## 9. Release Control

Release Control manages active, quiet, archived, tombstone, redacted, and deleted recall states.

Rules:

- Preserve useful lessons before release when possible.
- Tombstone is a first-class entity, not `TombstoneMarker`.
- Redacted, deleted, and safety-sensitive content must not enter ordinary context.
- Deletion requires explicit user choice and should retain only minimal audit information.
- Release Control overlays recallable objects without mutating their factual identity.

## 10. Handoff

Before ending a long session or when context may be lost:

1. update relevant Work state
2. preserve useful Assets or decisions
3. update Relationship Network links
4. write or update a Handoff record
5. ensure Context Control can recover the next step

The next agent should not need to reconstruct state from chat history.

## 11. Respect Portability

Never trap durable context in one agent's private memory.

If something matters, write it into the Workroot through the appropriate managed state, Asset, Relationship Network, Release Control, or authorized user-visible publication path.

Agents can change. Models can change. The Workroot remains.

## 12. Respect The Human

AI Workroot is not a productivity whip.

It should help people work, remember, understand, decide, release what no longer needs to stay active, and grow with more clarity and steadiness.
