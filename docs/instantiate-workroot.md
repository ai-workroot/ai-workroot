# Instantiate A Workroot

Use this guide when turning AI Workroot into a concrete personal Workroot.

For ordinary users, prefer the simpler flow in `docs/user-sop.md`: choose a directory, initialize it with AI Workroot, give a small usage direction, and start useful work.

This document is for advanced users, maintainers, or agents that need a more explicit setup process.

## 1. Choose The User Directory

Choose or create a directory for the user's own assets.

Examples:

```text
my-ai-workroot
my-life-workroot
product-thinking-partner
```

Clean Workroot treats this directory as user content space. It should not receive managed runtime state, indexes, logs, handoffs, or control files by default.

## 2. Initialize Clean Workroot State

Initialize the Workroot through the CLI:

```bash
workroot init --name "My Workroot" --directory ./my-ai-workroot
```

Use `--no-native-agent-entry` when the user directory must remain entirely unchanged.

Use `--native-agent-entry` only when the user explicitly authorizes short launcher files for AI agents.

Managed state is stored under `AI_WORKROOT_HOME` by default. This includes the Workroot registry, per-Workroot state, SQLite indexes, context packages, diagnostics, relationship projections, release records, and cache files.

## 3. Define Usage Direction

This is required before formal durable work begins.

For the simplest first use, read `START_HERE_FOR_HUMANS.md` and ask an AI agent to guide the setup.

Minimum guidance:

- who or what this Workroot represents
- what role the AI should play
- what direction, work, or life area it should support
- what values, boundaries, or preferences it should respect

Keep this concise. Detailed history can evolve after the first task.

## 4. Start The First Work Record

This section is for advanced users and agents. Ordinary users should only describe the work in natural language and let the AI agent handle this.

Use the active CLI and Runtime APIs to create or update managed work state. Do not ask ordinary users to create internal files or choose storage locations.

The preferred user-facing flow is:

```text
I want this Workroot to help me with [area]. Please set it up with me, then help me start my first real task.
```

## 5. Update Managed State

When durable objects are created, update the corresponding managed records:

- work records
- run and action records
- asset records
- decision records
- checkpoint records
- relationship records
- release, tombstone, redaction, and deletion records
- retrieval and context records

Generated SQLite and cache stores are accelerators. They must remain local-first and inspectable, and they must not become hidden archives of redacted or deleted material.

## 6. Promote What Matters

After work creates reusable value, promote the right parts into durable records:

- memory
- knowledge
- principles
- decisions
- patterns
- reflections
- invalidations
- release records

Do not keep long-term understanding only inside chat history.

## Legacy Public Seed

The old Public Seed layout is preserved for history and compatibility tests under `docs/history/public-seed/`. It is not the active setup path for new Clean Workroots.

`scripts/rebuild_sqlite.py` remains legacy public seed tooling for the historical fixture. Clean Workroot users should use `workroot init`, `workroot context`, and `workroot doctor`, which use managed state under `AI_WORKROOT_HOME`.
