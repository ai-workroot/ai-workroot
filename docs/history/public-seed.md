# Historical Public Seed

Public Seed was the early transparent AI Workroot layout built around tracked `space/` and `.workroot/` directories.

It is retired as active architecture in 0.9.530.

## Preserved Location

The historical files are preserved under:

```text
docs/history/public-seed/
```

This includes the old agent entry files, profile/work/mind directories, kernel contracts, extension registry, runtime indexes, and templates.

## Why It Remains

The history is kept for:

- legacy capability preservation review
- migration reasoning
- compatibility tests
- architecture history
- old Public Seed tooling fixtures

It must not be copied back into active root as current architecture.

## Active Replacement

Current architecture is Clean Workroot:

- user-selected directories stay clean by default
- managed state lives under `AI_WORKROOT_HOME`
- WorkrootEnvironment owns registry and bindings
- source code lives under `src/ai_workroot/`
- Native Agent Entry files are generated locally only with authorization or bootstrap-dev dogfood behavior

## Testing Rule

Legacy tests may copy `docs/history/public-seed/` into a temporary directory when they need the old layout.

Current architecture tests must not require tracked root `space/`, `.workroot/`, `AGENTS.md`, or `CLAUDE.md`.
