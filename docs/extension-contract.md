# Extension Contract

AI Workroot should be simple for ordinary users and extensible for serious work.

This document defines how role capabilities, tools, local runtimes, indexes, and databases can extend a Workroot without weakening the core protocol.

## Core Must Stay Stable

The core protocol owns:

- subject boundary
- work lifecycle
- asset model
- release, tombstone, redaction, and deletion rules
- relationship and retrieval discipline
- context and handoff discipline
- managed state and user asset boundaries

Extensions may add capability-specific structure, but they must not redefine these core rules.

The system should not restrict what useful work a Workroot can contain. Extensions and user-approved folders may create domain-specific structure, workflows, scripts, and indexes as long as they preserve stable contracts and do not turn extension-generated state into the only source of truth.

## Permission Hints

AI Workroot uses permission hints, not a heavy permission system.

Every non-trivial extension should declare:

- what it reads
- what it writes
- whether it touches private or sensitive material
- whether it needs network access
- whether it needs secrets or external accounts
- whether it can perform destructive actions
- whether it writes durable memory, generated stores, or runtime caches

Agents should use these hints to decide when to ask the user for confirmation.

Permission hints are not ACL, RBAC, sandboxing, encryption, identity provider integration, or enterprise audit. They are a compact risk declaration that can evolve into stronger models later.

## Extension Types

Valid extension types include:

- role capability
- domain workflow
- tool adapter
- local runtime configuration
- capability-specific registry
- optional local database
- optional vector or relationship index
- export/import adapter

Extensions should be added only when they solve a real recurring problem.

## Capability Rules

A capability may add:

- managed capability records
- task templates or checklists
- capability-specific indexes
- scripts or helper commands
- local data manifests
- operating notes for a role or domain

A capability must not:

- move durable knowledge out of managed Workroot records without an explicit export
- make an extension database or generated index the only source of truth
- require one model, agent, provider, or operating system
- hide important task state outside Workroot records
- weaken privacy, release, deletion, or tombstone rules
- redefine core records to fit one role

If a capability needs more structure, it should add its own documented registry or manifest instead of changing the core schema.

## Manifest And Contract Rules

Extensions should move toward compact manifests.

Markdown can explain the extension. A YAML or JSON manifest should declare the extension's operational contract when the extension becomes repeatable.

Recommended manifest fields:

- `id`
- `name`
- `type`
- `version`
- `purpose`
- `read_scope`
- `write_scope`
- `privacy_level`
- `requires_confirmation`
- `network_access`
- `secret_access`
- `destructive_action`
- `source_paths`
- `output_paths`
- `runtime_stores`
- `rebuild_command`

Structured manifests should stay small enough for agents and validators to read cheaply.

## Local Runtime Rules

Real Workroots may need local credentials, tool settings, MCP servers, or machine-specific paths.

Those belong in local ignored files or documented local runtime configuration. They do not belong in public docs, durable knowledge entries, task notes, examples, or committed config.

## Database And Index Rules

Managed SQLite is the current core Workroot runtime fact store. Extension databases and generated indexes are accelerators.

They must be:

- optional unless explicitly required by a documented extension contract
- rebuildable
- disposable
- documented by a manifest when non-trivial
- excluded from public commits by default
- cleaned or rebuilt when material is released, tombstoned, redacted, or deleted

Use the simplest store that fits the workload:

- SQLite for extension-local lookup, FTS, relationships, and lightweight state
- DuckDB for local analytical or tabular workloads
- vector indexes for optional future semantic retrieval when keyword and link traversal are insufficient
- relationship indexes for dense relationship navigation

## Context Budget Rule

Extensions must not become default startup context.

An extension should be loaded only when:

- the active task needs it
- a registry or manifest says it applies
- the user asks for it
- an agent reaches it through explicit retrieval

Long extension explanations, examples, source data, generated outputs, caches, and old run logs should not be read by default.

## User Experience Rule

Extensions must not make the first-use experience harder.

Ordinary users should still be able to start with:

```text
I want this Workroot to help me with [area]. Please set it up with me, then help me start my first real task.
```

The agent may use extension rules behind the scenes, but the user should not need to learn the extension architecture before doing work.

## Review Checklist

Before accepting an extension, check:

- Does it serve a real personal workflow?
- Does it keep durable state inspectable?
- Does it preserve the subject boundary?
- Does it keep startup context small?
- Does it document any new registry, database, or cache?
- Does it declare permission hints?
- Does it stay outside default startup context unless truly required?
- Does it provide compact structured metadata when it becomes repeatable?
- Does it avoid provider, model, agent, and operating-system lock-in?
- Does it preserve privacy and forgetting rules?
- Can it be removed without breaking core Workroot continuity?
