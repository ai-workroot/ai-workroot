# Phase 3 Capability Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Move remaining product behavior into capability-owned modules, remove `core/` and `contracts/`, and update architecture contracts.

**Architecture:** Capability packages own local models and behavior. `shared/` owns only stable cross-capability primitives. Old layer-first packages are deleted and must not be restored as import shims.

**Tech Stack:** Python 3.9 standard library, SQLite, `unittest`, static import-boundary tests.

---

## Files

- Create: `src/ai_workroot/context/`
- Create: `src/ai_workroot/retrieval/`
- Create: `src/ai_workroot/release/`
- Create: `src/ai_workroot/work/`
- Create: `src/ai_workroot/assets/`
- Create: `src/ai_workroot/relationships/`
- Create: `src/ai_workroot/shared/`
- Delete: legacy modules under `runtime/`, `indexing/`, `core/`, and `contracts/` after imports are updated.
- Modify: architecture docs and import-boundary tests.

## Tasks

### Task 1: Context, Retrieval, And Release

- [x] Add import tests for `ai_workroot.context.builder`, `ai_workroot.retrieval.providers.*`, and `ai_workroot.release.operations`.
- [x] Move `runtime/context.py` implementation to `context/builder.py`.
- [x] Move `indexing/global_indexes.py` and `indexing/providers/*` implementation to `retrieval/`.
- [x] Move `runtime/release.py` implementation to `release/operations.py`.
- [x] Move `core/release.py`, `core/context.py`, and `core/retrieval.py` into capability-local model modules.
- [x] Remove old runtime, indexing, and core modules after updating imports.
- [x] Run context, release protection, recall hint, release target, and global index tests.

### Task 2: Work, Assets, Relationships, And Shared

- [x] Add import tests for `ai_workroot.work.operations`, `ai_workroot.assets.operations`, `ai_workroot.relationships.operations`, and `ai_workroot.shared`.
- [x] Move `runtime/work.py`, `runtime/assets.py`, and `runtime/relationships.py` implementation into matching capability packages.
- [x] Move `runtime/time.py` into `work/time.py`.
- [x] Move `core/work.py`, `core/assets.py`, `core/relationships.py`, `core/common.py`, `core/environment.py`, `core/agent.py`, `core/health.py`, and `core/extensions.py` to their natural capability or `shared/` location.
- [x] Remove old modules after updating imports.
- [x] Run work/assets/relationships/time and capability model tests.

### Task 3: Contracts And Architecture Contract Cleanup

- [x] Move standard-library-only protocol modules from `contracts/` into `shared/contracts/`.
- [x] Remove old `contracts/*` modules after updating imports.
- [x] Update import-boundary tests to express new command-first/capability-owned rules and forbid old compatibility packages.
- [x] Update architecture docs to replace old layer-first structure with command-first structure.
- [x] Run full verification.
