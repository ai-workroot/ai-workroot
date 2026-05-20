# 0.9.530 Clean Workroot Architecture Reset — Final Master Plan

> This is an imported package snapshot retained for traceability.
> If this file conflicts with `docs/dev/0.9.530/final-architect-review-clarifications.md`, `docs/specs/`, `docs/architecture/`, `docs/adr/`, or `docs/plans/2026-05-20-0530-clean-workroot-domain-reset-plan.md`, the later clarified documents win.
> In particular: build replacement architecture first, then quarantine the old Public Seed active root.

## 1. Purpose

0.9.530 is a major architecture reset. The project is moving from the retired Public Seed / Portable Seed layout into the Clean Workroot architecture.

The work has three simultaneous goals:

1. Retire the old active source-tree shape: `space/`, `.workroot/`, and committed root `AGENTS.md` / `CLAUDE.md`.
2. Preserve valuable legacy capabilities: tasks, runs, actions, checkpoints, retrieval cards, invalidations, artifacts, decisions, mind/release/tombstone concepts, link registry, global indexes, capability registry, doctor, migrations, Context Guide behavior, and bootstrap-dev.
3. Implement a simpler open-source-friendly engineering layout: `core / contracts / runtime / storage / indexing / agent / cli`.

The project uses DDD only as strategic modeling. The implementation must not become a heavy DDD tree.

## 2. Final engineering structure

```text
src/ai_workroot/
  core/
  contracts/
  runtime/
  storage/
  indexing/
  agent/
  cli/
  resources/
```

The rest of the repository:

```text
install/
  unix/install.sh
  windows/install.ps1
scripts/dev/
docs/architecture/
docs/specs/
docs/adr/
docs/releases/
docs/dev/
docs/history/
tests/unit/
tests/integration/
tests/smoke/
tests/fixtures/
templates/native-agent-entry/
.github/workflows/
```

## 3. Final core concepts

The final conceptual model has 10 core areas:

1. Workroot Management
2. Work
3. Asset
4. Release Control
5. Relationship Network
6. Retrieval & Index Control
7. Context Control
8. Agent Interface
9. System Health
10. Extensions

These names must be used in docs and new code. Old terms must be retired from active architecture:

```text
Public Seed active profile
space/ as active product root
.workroot/ as active runtime root
Memory as formal term
Mind as formal term
Knowledge as top-level domain
Graph as business domain name
Context Gate
TombstoneMarker / ReleaseMarker / DeletionMarker
```

## 4. Implementation rule

Codex must implement in dependency order:

1. Branch and baseline.
2. Documentation source of truth.
3. Source layout scaffold.
4. Legacy active-tree quarantine.
5. WorkrootEnvironment and managed state.
6. Native Agent Entry templates.
7. Storage/schema alignment.
8. Core models.
9. Runtime orchestration.
10. Indexing and retrieval providers.
11. Context Control.
12. Release Control propagation.
13. Relationship Network.
14. System Health / Doctor.
15. CLI and install scripts.
16. Tests.
17. As-built documentation and release validation.

## 5. No silent capability loss

Before deleting or moving any old file or behavior, Codex must map it in the Legacy Capability Preservation Matrix.

Old active source structures may be quarantined into `docs/history/` or `tests/fixtures/legacy-public-seed-history/`, but must not remain active root architecture.

## 6. Release principle

This release may make major source tree changes. It must not automatically migrate real user directories because current usage is limited and the old Public Seed product shape is retired. However, it must preserve old project files in history/fixtures to avoid losing design knowledge or test evidence.
