# Instantiate A Workroot

Use this guide when turning the AI Workroot starter into a concrete personal, team, role, project, or organization workspace.

## 1. Copy The Starter

For ordinary users, prefer the simpler flow in `docs/user-sop.md`: download the project, rename only the outer folder, open it with an AI agent, define identity, and start working.

This document is for advanced users, maintainers, or agents that need a more explicit setup process.

Copy the starter directory into a new outer directory for the concrete subject.

Examples:

```text
my-ai-workspace
team-quality-workspace
product-thinking-partner
```

Do not keep the original starter repository history unless the new Workroot is intended to be developed as a fork.

Do not rename internal protocol folders such as `space`, `.workroot`, or `docs`.

## 2. Define Identity

This is required before formal work begins.

For the simplest first use, read `START_HERE_FOR_HUMANS.md` and ask an AI agent to guide the setup.

Fill in:

- `space/profile/profile.md`
- `space/profile/roles.md`
- `space/profile/values.md`
- `space/profile/preferences.md`

Minimum identity:

- who or what this Workroot represents
- what role the AI should play
- what direction, work, or life area it should support
- what values, boundaries, or preferences it should respect

Keep this concise. Detailed history belongs in `space/mind/`. The identity can evolve after the first task.

## 3. Reset Active Context

For a new Workroot, `.workroot/runtime/context/current.md` and `.workroot/runtime/context/handoff.md` should start with no active task.

## 4. Start The First Internal Task Record

This section is for advanced users and agents. Ordinary users should only describe the work in natural language and let the AI agent handle this.

Create an internal task record under one of:

- `.workroot/runtime/work/tasks/`

Use the internal work structure defined in `docs/kernel-implementation-specification.md`.

Optional helper:

```bash
python3 scripts/new_task.py "My first task" --goal "Start the first useful piece of work"
python3 scripts/new_task.py "My project" --owner-scope personal --visibility internal
python3 scripts/new_task.py "Evidence review" --process-level L2
```

## 5. Update Registries

When durable objects are created, update the CSV registries in `.workroot/runtime/index/`.

If a local SQLite index is used, it must be rebuildable from these file sources.

For team or sub-agent scenarios:

- use `owner_scope` in `task_registry.csv` to identify whether work belongs to a person, team, role, or organization
- use `link_registry.csv` to connect parent work, delegated sub-work, participants, outputs, decisions, and Mind entries
- add capability-specific registries only when a real role or domain workflow needs more structure

Optional helpers:

```bash
python3 scripts/rebuild_sqlite.py
python3 scripts/validate_kernel.py
python3 scripts/add_registry_row.py link source_type=task source_id=my-task relation=produced target_type=artifact target_id=my-artifact created_at=2026-05-14
```

## 6. Promote What Matters

After a task creates reusable value, promote the right parts into:

- `space/mind/memory/`
- `space/mind/knowledge/`
- `space/mind/principles/`
- `space/mind/decisions/`
- `space/mind/patterns/`
- `space/mind/reflections/`
- `space/mind/invalidated/`
- `space/mind/released/`

Do not keep long-term understanding only inside task files.

Use `space/mind/_templates/` when creating durable Mind entries if templates exist.
