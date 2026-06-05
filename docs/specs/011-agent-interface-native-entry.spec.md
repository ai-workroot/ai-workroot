# Spec 011 — Agent Interface and Native Agent Entry

Status: accepted
Target: 0.9.530

## Purpose

Define how Codex, Claude, and generic agents enter a Workroot.

## Domain name

The domain is Agent Interface. Native Agent Entry is one capability inside it.

## Templates

Templates must be committed:

```text
src/ai_workroot/entrypoints/native_agent/templates/...
```

Generated root files must not be committed:

```text
/AGENTS.md
/CLAUDE.md
```

## Native Entry content

Native Entry must be short and only instruct:

```text
workroot context --agent <agent> --cwd .
```

It must not include:

- absolute managed state path;
- Workroot ID;
- AI_WORKROOT_HOME;
- logs;
- handoffs;
- indexes;
- debug trace;
- context package history.

## Managed block

Only the AI Workroot managed block may be updated.

User content outside managed block must be preserved.

## Authorization

User explicit authorization required before writing Native Entry in a user directory.

bootstrap-dev may generate local root entries because the developer invoked bootstrap-dev, but they must be ignored.

## Agent-ready Workroot

A registered Workroot can exist without Native Entry.

An agent-ready Workroot requires Native Entry.

## Acceptance

- `AGENTS.md` and `CLAUDE.md` generated from templates.
- generated files are ignored in bootstrap-dev.
- no private state path in generated entry.
- user content outside managed block preserved.
- default repo does not track generated entry files.
