# Command First Source Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Upgrade the 0.9.530 source tree from layer-first modules to command-first, capability-owned modules without changing public CLI behavior, SQLite schema, release semantics, or context package semantics.

**Architecture:** Keep `cli/` as a thin terminal adapter, add `commands/` as reusable application entrypoints, move implementation ownership into capability modules, and remove old layer-first package paths. The migration is mechanical first: relocate modules, update imports, and tighten architecture tests after behavior is protected.

**Tech Stack:** Python 3.9 standard library, `unittest`, SQLite, setuptools package data, existing `workroot` CLI.

---

## Scope

In scope:

- Add `commands/` for application command entrypoints.
- Move managed state support from `storage/` and selected `runtime/` modules into `state/`.
- Move Native Agent Entry implementation from `agent/` to `agent_entry/`.
- Move packaged templates from `resources/templates/` to top-level `templates/`.
- Move context, retrieval, release, work, assets, relationships, diagnostics, and shared primitives into capability-owned modules.
- Remove legacy import compatibility shims for 0.9.530.
- Update tests and architecture docs to describe the new structure.

Out of scope:

- No public CLI behavior changes.
- No SQLite schema changes.
- No context output semantic changes.
- No release/tombstone/redaction behavior changes.
- No ORM, framework, OpenSpec, MCP server, GUI, or new agent adapter.
- No speculative empty modules beyond packages required for active migrated code.

## Phase Plans

- `docs/superpowers/plans/2026-05-26-phase-1-command-entry.md`
- `docs/superpowers/plans/2026-05-26-phase-2-state-adapters.md`
- `docs/superpowers/plans/2026-05-26-phase-3-capability-contracts.md`

## Global Verification

- [x] Run baseline before edits:

```bash
PYTHONPATH=src python3 -m unittest discover
PYTHONPATH=src python3 -m ai_workroot --help
PYTHONPATH=src python3 -m ai_workroot --version
```

Expected: tests pass, CLI help renders primary commands, version remains `AI Workroot 0.9.530`.

- [x] After each phase, run the narrow phase test plus:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_import_boundaries
PYTHONPATH=src python3 -m unittest tests.smoke.test_package_entrypoint tests.smoke.test_cli_discovery
```

Expected: pass.

- [x] Final verification:

```bash
PYTHONPATH=src python3 -m unittest discover
PYTHONPATH=src python3 -m compileall -q src tests scripts
PYTHONPATH=src python3 -m ai_workroot --help
PYTHONPATH=src python3 -m ai_workroot --version
```

Expected: all commands pass.
