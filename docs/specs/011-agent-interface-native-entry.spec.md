# Spec 011 — Agent Interface and Native Agent Entry

Status: accepted; amended for 0.9.531 Agent Protocol
Target: 0.9.530 base, 0.9.531 protocol amendment

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
workroot agent sync --agent <agent> --cwd . --query "<current user request>" --format packet
```

`workroot agent sync` is the normal meaningful-turn entry. `workroot context`
is read-only auxiliary behavior for startup recovery, manual recall, or
debugging; it must not be required for every turn.

`--agent` is an Agent descriptor string. It is not limited to Codex or Claude
at the protocol level. Native Entry templates may remain product-specific
where the local Agent platform requires product-specific filenames.

`--transport` defaults to `cli`. Future MCP or SDK entrypoints should preserve
the same protocol semantics and pass their transport descriptor through the
entry adapter.

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
- generated entry instructs meaningful turns to call `workroot agent sync`
  with `--format packet` and pass `--query`.
