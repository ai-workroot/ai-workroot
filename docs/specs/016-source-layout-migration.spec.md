# Spec 016 — Source Layout Migration

Status: accepted
Target: 0.9.530

## Purpose

Migrate product logic from `scripts/` into `src/ai_workroot/` without losing capabilities.

## Strategy

1. Create new package structure.
2. Move or wrap CLI entry.
3. Move product logic into command-first, capability-owned package modules.
4. Keep scripts as wrappers/dev utilities only.
5. Do not delete old capability until mapped and tested.

## Product logic target mapping

| Old script area | New module |
|---|---|
| workroot paths/state | state/model + state/environment + state/layout |
| sqlite schema | state/sqlite |
| context guide | context/model + context/builder + retrieval providers |
| candidates/FTS | retrieval/providers + state/sqlite |
| bootstrap | commands/bootstrap_dev + agent_entry/native |
| agent entry | agent_entry/native + templates/native_agent_entry |
| doctor | diagnostics/model + diagnostics/doctor |
| CLI | cli/ + commands/ |
| install | install/ |

## Formatting requirement

All Python source must be normally formatted.

No collapsed one-line files.

Add validation:

- py_compile all `src` and remaining `scripts`.
- max line length guard for Python files, with reasonable threshold.
- JSON files pretty printed.

## Active tree quarantine

Move or retire:

```text
space/
.workroot/
AGENTS.md
CLAUDE.md
.idea/
```

## Acceptance

- `src/ai_workroot` importable.
- `python -m ai_workroot --help` works.
- remaining scripts are wrappers/dev only.
- old capabilities have mapping and tests.
