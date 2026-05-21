# Changelog

## 0.9.530 - 2026-05-20

- Reset the active architecture to Clean Workroot.
- Added the package structure under `src/ai_workroot/` with Core / Contracts / Runtime / Storage / Indexing / Agent / CLI boundaries.
- Added managed Workroot environment state under `AI_WORKROOT_HOME`.
- Added bootstrap-dev dogfood support using `workroot.project.json`, ignored Native Agent Entry files, and local `.ai-workroot-local/` staging.
- Added Release Control, Relationship Network, Retrieval & Index Control, Context Control, System Health, and extension boundary models.
- Quarantined the old Public Seed root layout into `docs/history/public-seed/`.
- Preserved legacy Public Seed capability tests through explicit historical fixtures.

## 0.9.529 - 2026-05-20

- Added the Clean Native Context Foundation: Clean Mode init, managed state outside user directories, SQLite context candidates, local FTS retrieval, Context Guide output, debug traces, doctor checks, Native Agent Entry, and developer bootstrap.
- Hardened context selection so query, FTS, relationship signals, safety policy, and token budgets affect selected context.
- Kept vector databases, remote embedding, and remote LLM calls out of the P0 context hot path.

## 0.9.528 - 2026-05-15

- Rewrote the README around the expert-facing value proposition: context sovereignty, work lifecycle, cross-agent continuation, layered memory, and deliberate forgetting.
- Centralized current-version references so ordinary documentation does not need patch-version edits on every release.
- Added the Work Process Layer with stable task paths under `.workroot/runtime/work/tasks/`.
- Added `L0`, `L1`, and `L2` process levels for proportional task records.
- Added run, action, retrieval-card, checkpoint, and invalidation registries.
- Added a lightweight file-first Workroot Client and thin CLI for task-process writes, with task status stored in records instead of directory names.
- Added the Agent Operation Layer: compact fast-start guidance, operation manifest, JSON schema, and directly usable batch recipes.
- Added batch transaction journals and rollback coverage for task records, registries, continuation files, `space/work`, `space/mind`, artifacts, and invalidations.
- Extended batch operations to support runs, Mind entries, invalidations, session summaries, and path-list normalization.
- Added registry-driven session summaries so agents can update continuation without passing long task id lists.
- Split task-local state updates from session/global continuation updates to avoid multi-task overwrite conflicts.
- Kept legacy `active/` and `closed/` task paths readable while removing status paths from the public seed.

## 0.9.527 - 2026-05-15

- Added a human-first quick start.
- Moved deeper founding intention into docs.
- Added identity gate before formal work.
- Added forgetting, release, tombstone, lifecycle, context, and longevity policies.
- Added local SQLite rebuild and validation helpers.
- Switched the public release license to Apache-2.0 with a NOTICE for project name and brand boundaries.
- Added trademark policy and DCO-style contribution rule.
- Added launch and discovery guidance for repository description, topics, and messaging.
- Added the Daily Loop as the practical rhythm for everyday AI Workroot use.
- Clarified the philosophy-led, engineering-grounded design order.
- Added contributor expectations and maintainer contact guidance.

## 0.0.2

- Added the AI Workroot architecture.
- Added the Workroot operating protocol.
- Added identity, mind, workspace, agent, capabilities, config, resources, and inbox layers.
- Added Codex and Claude Code entrypoints.
- Added task, index, and optional retrieval extension points.

## 0.0.1 - 2026-05-14

- Created the AI Workroot origin seed.
- Established initial mission, brief, roadmap, and agent guidance.
