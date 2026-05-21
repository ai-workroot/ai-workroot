# Spec 019 — Full Test and Migration Plan

Status: accepted
Applies to: 0.9.530

## Purpose

This spec binds implementation to explicit migration and test coverage. 0.9.530 is too large to rely on normal happy path tests.

## Migration requirements

1. Preserve old Public Seed material in history/fixtures before removing from active root.
2. Back up old SQLite DB before destructive schema changes.
3. Do not rely on root AGENTS/CLAUDE or `.workroot/kernel/VERSION` for bootstrap-dev.
4. Replace global user profile with operator preferences and policy defaults.
5. Convert knowledge/decision/result concepts to Asset subtypes.
6. Convert Graph business language to Relationship Network.
7. Preserve old run/action/checkpoint/retrieval-card/invalidation capabilities.
8. Preserve release/tombstone/redaction/deletion semantics.

## Test requirements

1. Unit tests for core behavior.
2. Contract import isolation tests.
3. Storage/schema integration tests.
4. Runtime flow tests.
5. Indexing provider tests.
6. Context Control tests.
7. Agent Interface tests.
8. Release Control protection tests.
9. Relationship Network tests.
10. System Health / Doctor tests.
11. bootstrap-dev smoke.
12. Clean Workroot smoke.
13. Negative tests for retired Public Seed assumptions.

## Acceptance

Implementation is incomplete if it lacks either migration handling or negative tests.
