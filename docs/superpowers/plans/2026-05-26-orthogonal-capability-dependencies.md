# Orthogonal Capability Dependencies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove remaining package-level cycles and enforce one-way, orthogonal capability dependencies.

**Architecture:** Release Control owns release evaluation. Relationship Network owns relationship writes and traversal signals. Retrieval consumes release policy for read-side filtering and does not own relationship canonical writes.

**Tech Stack:** Python 3.9 standard library, `unittest`, AST import scanning.

---

## Tasks

### Task 1: Static Dependency Graph Contract

**Files:**
- Modify: `tests/unit/test_import_boundaries.py`

- [x] Add a package graph test that scans `src/ai_workroot/**/*.py`, builds package edges, asserts no cycles, and asserts all package edges are in the allowed dependency map.
- [x] Run `PYTHONPATH=src python3 -m unittest tests.unit.test_import_boundaries` and verify it fails on the current `retrieval -> release -> retrieval` cycle and the `relationships -> retrieval` edge.

### Task 2: Release Evaluation Ownership

**Files:**
- Create: `src/ai_workroot/release/evaluation.py`
- Modify: `src/ai_workroot/release/operations.py`
- Modify: `src/ai_workroot/retrieval/providers/release_provider.py`
- Modify: `tests/unit/test_release_target_resolver.py`

- [x] Move `ReleaseEvaluation`, release target evaluation, release level normalization, release level ranking, and release target existence checks into `release/evaluation.py`.
- [x] Update `release/operations.py` to use `release.evaluation`, not `retrieval.providers.release_provider`.
- [x] Update `retrieval/providers/release_provider.py` to import `evaluate_release_targets` from `release.evaluation`.
- [x] Update tests to import `evaluate_release_targets` from `ai_workroot.release.evaluation`.
- [x] Run `PYTHONPATH=src python3 -m unittest tests.unit.test_release_target_resolver tests.unit.test_import_boundaries`.

### Task 3: Relationship Network Ownership

**Files:**
- Modify: `src/ai_workroot/relationships/model.py`
- Modify: `src/ai_workroot/relationships/operations.py`
- Delete: `src/ai_workroot/retrieval/providers/relationship_provider.py`
- Modify: `src/ai_workroot/context/builder.py`
- Modify: `tests/integration/test_context_retrieval_selection.py`
- Modify: `tests/negative/test_release_protection_relationships.py`
- Modify: `tests/unit/test_release_target_resolver.py`

- [x] Move `RelationshipSignal` into `relationships/model.py`.
- [x] Move relationship traversal query logic into `relationships/operations.py`.
- [x] Update Context Control to call `relationships.operations.relationship_signals_for_sources`.
- [x] Update tests to seed relationships through `relationships.operations.create_relationship_node` and `create_relationship_edge`.
- [x] Delete the retrieval relationship provider.
- [x] Run relationship, context retrieval, release resolver, and import-boundary tests.

### Task 4: Current Contract Docs And Fixtures

**Files:**
- Modify: `docs/validation/acceptance-checklist.md`
- Modify: `docs/release-checklist.md`
- Modify: `tests/smoke/test_clean_release_validator.py`

- [x] Update current validation docs to list the new active package structure.
- [x] Update release checklist follow-up paths from old `runtime/context.py` to `context/builder.py`.
- [x] Update smoke test fixtures to use new source paths.
- [x] Run `PYTHONPATH=src python3 -m unittest tests.smoke.test_clean_release_validator tests.contracts.test_current_docs_contract`.

### Task 5: Final Verification

**Files:**
- No new source files beyond the tasks above.

- [x] Run `PYTHONPATH=src python3 -m unittest discover`.
- [x] Run `PYTHONPATH=src python3 -m compileall -q src tests scripts`.
- [x] Run `PYTHONPATH=src PATH="$PWD/.venv/bin:$PATH" scripts/dev/validate-release.sh`.
- [x] Run a package graph scan and confirm no cycles.
