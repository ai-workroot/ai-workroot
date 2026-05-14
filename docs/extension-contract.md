# Extension Contract

AI Workroot should be simple for ordinary users and extensible for serious work.

This document defines how role capabilities, tools, local runtimes, indexes, and databases can extend a Workroot without weakening the core protocol.

## Core Must Stay Stable

The core protocol owns:

- identity boundary
- task lifecycle
- Mind model
- core registries
- privacy and forgetting rules
- context and handoff discipline
- file-first source of truth

Extensions may add capability-specific structure, but they must not redefine these core rules.

The kernel should not restrict what useful work a workspace can contain. Extensions and user-space folders may create domain-specific structure, workflows, scripts, and indexes as long as they preserve the stable kernel contracts and do not turn generated state into the only source of truth.

## Permission Hints

AI Workroot v0.9.527 uses permission hints, not a heavy permission system.

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
- optional vector or graph index
- export/import adapter

Extensions should be added only when they solve a real recurring problem.

## Capability Rules

A capability may add:

- files under `.workroot/extensions/capabilities/<capability-id>/`
- task templates or checklists
- capability-specific indexes
- scripts or helper commands
- local data manifests
- operating notes for a role or domain

A capability must not:

- move durable knowledge out of `space/mind/`
- make a database the only source of truth
- require one model, agent, provider, or operating system
- hide important task state outside Workroot files
- weaken privacy, release, deletion, or tombstone rules
- redefine the core registries to fit one role

If a capability needs more structure, it should add its own documented registry instead of changing the core registry schema.

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

Those belong in local ignored files or documented local runtime configuration. They do not belong in public docs, Mind entries, task notes, examples, or committed config.

See `.workroot/kernel/config/` and local ignored runtime files.

## Database And Index Rules

SQLite, DuckDB, vector indexes, and graph indexes are accelerators.

They must be:

- optional
- rebuildable
- disposable
- documented by a manifest when non-trivial
- excluded from public commits by default
- cleaned or rebuilt when material is released, tombstoned, redacted, or deleted

Use the simplest store that fits the workload:

- SQLite for local lookup, relationships, and lightweight state
- DuckDB for local analytical or tabular workloads
- vector indexes for semantic retrieval when keyword and link traversal are insufficient
- graph indexes for dense relationship navigation

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
Read AGENTS.md and START_HERE_FOR_HUMANS.md.
Help me set up my identity in this AI Workroot.
```

The agent may use extension rules behind the scenes, but the user should not need to learn the extension architecture before doing work.

## Review Checklist

Before accepting an extension, check:

- Does it serve a real personal, team, or role workflow?
- Does it keep files as the durable source of truth?
- Does it preserve the identity boundary?
- Does it keep startup context small?
- Does it document any new registry, database, or cache?
- Does it declare permission hints?
- Does it stay outside default startup context unless truly required?
- Does it provide compact structured metadata when it becomes repeatable?
- Does it avoid provider, model, agent, and operating-system lock-in?
- Does it preserve privacy and forgetting rules?
- Can it be removed without breaking core Workroot continuity?
