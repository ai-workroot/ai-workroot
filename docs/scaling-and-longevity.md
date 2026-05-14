# Scaling And Longevity

AI Workroot is designed for long-term use.

It should still be usable after months, years, and decades of heavy work. A growing Workroot must not force every future agent to read the full past, rebuild every index for every small change, or treat all old knowledge as equally relevant forever.

This document defines the long-term engineering principles for keeping a Workroot durable, fast, portable, and psychologically healthy.

## Core Principle

The Workroot must grow like a living mind, not like an ever-expanding chat log.

That means:

- startup context stays small
- task history is summarized and archived
- durable knowledge has lifecycle metadata
- indexes are layered and rebuildable
- local databases are accelerators, not sources of truth
- old knowledge can become cold, superseded, invalidated, released, tombstoned, or deleted
- large data and generated caches do not pollute the core repository

## Long-Term Risks

AI Workroot must explicitly guard against:

- context explosion from reading too much history
- slow directory traversal from too many files in active paths
- slow full index rebuilds after every small change
- stale knowledge returning as if it were current
- conflicting memories and old decisions without replacement links
- Git repository bloat from generated data and large artifacts
- private or deleted material surviving inside caches or derived indexes
- agent-specific private memory replacing the Workroot source of truth

## Context Budget

Agents must not use the full Workroot as startup context.

Default startup should read only:

- `AGENTS.md`
- `START_HERE_FOR_HUMANS.md`
- `.workroot/kernel/boot/boot.md` when available
- concise identity files under `space/profile/`
- `.workroot/runtime/context/current.md`
- `.workroot/runtime/context/handoff.md`
- relevant registry rows
- active work `brief.md`, `handoff.md`, and artifact indexes when needed

Agents should avoid reading by default:

- old `scratch.md`
- task `archive/`
- large outputs
- raw data files
- released or tombstone entries
- generated databases and caches

When deeper history is needed, retrieve it through indexes and explicit links.

Future kernel versions should formalize this through a compact boot layer:

```text
.workroot/kernel/boot/
  boot.md
  read-order.json
  context-budget.json
```

The boot layer should define the normal read order and context budget. Long architecture, philosophy, protocol, extension, and archive documents should be loaded only when the current task requires them.

## Progressive Loading Levels

Long-lived Workroots should use progressive loading:

| Level | Purpose |
| --- | --- |
| L0 boot context | smallest startup contract |
| L1 active context | identity, active brief, current handoff |
| L2 kernel index | map of kernel docs and contracts |
| L3 work and mind indexes | task, artifact, decision, mind, and link registries |
| L4 extension index | relevant capability, skill, MCP, adapter, and driver metadata |
| L5 deep context | old tasks, raw sources, archives, released context, tombstones |

Agents should move downward only as the work requires it.

## Temperature Model

Every durable object should be treated as one of several retrieval temperatures:

- `hot`: active work and current operating context
- `warm`: frequently useful knowledge, principles, decisions, and patterns
- `cold`: historical material preserved for traceability, not default recall
- `archived`: retained for explicit review
- `released`: intentionally removed from normal recall
- `tombstone`: a minimal memorial marker, not normal memory
- `deleted`: removed by explicit user choice, with no hidden detailed archive

Temperature is a retrieval policy, not a moral judgment. It helps future agents find the right level of context without dragging the whole past into the present.

## Lifecycle Metadata

Long-lived registries should support lifecycle fields over time.

Recommended fields:

- `created_at`
- `updated_at`
- `status`
- `temperature`
- `confidence`
- `last_used_at`
- `superseded_by`
- `review_after`
- `source_paths`

Not every v0.9.527 file needs every field on day one. But future schemas and tools should move toward this model.

See `.workroot/kernel/config/` for lifecycle and time policy in the v0.9.527 kernel architecture.

## Knowledge Aging

Knowledge is not always permanent.

Agents should mark or link knowledge when it becomes:

- confirmed
- tentative
- superseded
- obsolete
- invalidated
- released

Old knowledge should not be silently deleted just because it is old. It should be replaced, downgraded, archived, invalidated, or released according to the user's intention and evidence.

## Task Closure

Completed tasks should not remain heavy active context.

Before closing a task, agents should:

1. update `brief.md` with the final effective summary
2. record decisions in `decisions.md`
3. move durable outputs into `outputs/`
4. move noisy process material into `archive/`
5. promote reusable lessons into `space/mind/`
6. update registries and relationships
7. leave `handoff.md` short and useful

Future agents should prefer the task summary and indexes over old scratch history.

## File And Directory Scale

Avoid putting unlimited files in one active directory.

For high-volume Workroots, prefer date or topic partitioning:

```text
.workroot/runtime/work/closed/2026/...
space/mind/knowledge/2026/...
space/files/2026/...
```

Keep active directories small enough for quick listing, search, and review.

Large binary files, raw datasets, generated databases, build outputs, and caches should be excluded from Git unless they are intentional samples.

## Database Strategy

Use databases by workload:

- SQLite: local lookup, indexes, relationship traversal, lightweight state
- DuckDB: local analytical work, tabular profiling, reproducible reports
- vector index: semantic retrieval when keyword/index traversal is not enough
- graph index: relationship navigation when links become dense

All databases must be:

- optional
- local-first
- rebuildable from files or manifests
- disposable without losing durable knowledge
- excluded from public commits by default

## Storage Format Discipline

Use the right format for the layer:

- Markdown for doctrine, explanations, and human-readable summaries
- JSON for required v0.9.527 kernel contracts
- YAML or JSON for future human-authored extension manifests when explicitly supported
- JSON Schema for validation
- CSV for simple row-oriented registries
- SQLite, DuckDB, vector indexes, graph indexes, and caches for rebuildable acceleration

The source of truth should remain file-first and portable. Generated stores should never become the only copy of durable knowledge.

## Rebuild And Incremental Update

Every acceleration layer should support two paths:

- full rebuild for recovery, portability, and trust
- incremental update for daily performance

v0.9.527 may use full rebuild for simplicity. Future versions should add incremental index update when registry size makes full rebuild expensive.

Full rebuild must remain available even after incremental update exists.

## Cache And Deletion Discipline

Deletion must include derived stores.

When a user deletes, redacts, or releases material, agents must consider:

- Markdown source files
- CSV registries
- SQLite or DuckDB indexes
- vector indexes
- graph indexes
- exports and backups
- temporary caches

Derived indexes must not become hidden archives.

## Backup, Export, And Portability

A mature Workroot should be easy to move.

The minimum portable set is:

- identity
- mind
- work summaries, task briefs, decisions, indexes, and outputs
- registries
- configuration
- manifests for optional data stores

Generated local databases can be rebuilt after export, import, restore, or relocation.

## Practical v0.9.527 Rule

AI Workroot v0.9.527 should be simple to start, but it must already encode the long-term rules:

- never read all history by default
- never load the full kernel by default
- never load every extension by default
- never store durable knowledge only in a database
- never keep generated indexes as the only copy
- never treat old knowledge as current without status
- never let released, tombstoned, redacted, or deleted material survive as hidden cache
- always summarize before archive
- always preserve relationships through indexes
- always leave future agents a small continuation path

The goal is not to make the first version heavy. The goal is to prevent the first version from creating structural debt that makes a ten-year Workroot collapse.
