# Phase 2 State And Adapter Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Move managed state, Native Agent Entry, diagnostics, and packaged templates into their new ownership modules and remove the old import paths.

**Architecture:** New modules hold implementation. Old modules are removed after imports are updated. Package data follows the template move.

**Tech Stack:** Python 3.9 standard library, `importlib.resources`, setuptools package data, `unittest`.

---

## Files

- Create: `src/ai_workroot/state/`
- Create: `src/ai_workroot/agent_entry/`
- Create: `src/ai_workroot/diagnostics/`
- Create: `src/ai_workroot/templates/`
- Delete: old modules under `src/ai_workroot/storage/`, `src/ai_workroot/agent/`, and selected `src/ai_workroot/runtime/`.
- Modify: `pyproject.toml`
- Modify: tests that assert package layout and template loading.

## Tasks

### Task 1: State Package Migration

- [x] Add tests that import `ai_workroot.state.sqlite`, `state.jsonl`, `state.migrations`, `state.locks`, `state.environment`, `state.registry`, and `state.layout`.
- [x] Verify those tests fail before migration.
- [x] Move implementation from `storage/*` into `state/*`.
- [x] Move `runtime/environment.py`, `runtime/registry.py`, and `runtime/paths.py` implementation into `state/environment.py`, `state/registry.py`, and `state/layout.py`.
- [x] Delete old modules after updating imports; do not add re-export shims.
- [x] Update internal imports to prefer `state.*`.
- [x] Run state, migrations, paths, and environment storage tests.

### Task 2: Agent Entry And Templates

- [x] Add tests that `ai_workroot.agent_entry.native` renders Codex and Claude templates.
- [x] Verify those tests fail before migration.
- [x] Move `agent/native_entry.py` implementation to `agent_entry/native.py`.
- [x] Move `resources/templates/native_agent_entry` to `templates/native_agent_entry`.
- [x] Update `TEMPLATE_PACKAGE` and `pyproject.toml` package data.
- [x] Remove old `agent.native_entry` and `resources` packages after updating imports.
- [x] Run agent bootstrap and agent entry tests.

### Task 3: Diagnostics

- [x] Add tests that `ai_workroot.diagnostics.doctor.run_doctor` and `run_release_doctor` are importable.
- [x] Move `runtime/doctor.py` implementation to `diagnostics/doctor.py`.
- [x] Move `runtime/release_validation.py` implementation to `diagnostics/release_validation.py`.
- [x] Remove old runtime modules after updating imports.
- [x] Update internal imports to prefer `diagnostics.*`.
- [x] Run doctor and release surface tests.
