# Spec 018 — Codex Execution Plan

Status: accepted
Target: 0.9.530

## Branch

Use:

```text
feat/0.9.530-clean-workroot-domain-reset
```

## Execution order

Codex must follow this order.

### Phase 0 — Baseline

- Create branch.
- Record current status.
- Run current tests if feasible.
- Do not tag.

### Phase 1 — Source of truth docs

- Add architecture docs.
- Add ADRs.
- Add specs with statuses.
- Add legacy preservation matrix.

### Phase 2 — New package scaffold

- Add `pyproject.toml` if missing.
- Create `src/ai_workroot/` structure.
- Add module placeholders with minimal importable code.
- Add `python -m ai_workroot --help` path.

### Phase 3 — Contracts

- Add `contracts/` protocols/DTOs.
- Ensure contracts do not import core.

### Phase 4 — Core models

- Add core files.
- Implement minimal rich models and policies.
- Do not over-split files.

### Phase 5 — Storage and environment

- Move environment/state path logic.
- Add WorkrootEnvironment model support.
- Add registry lock and registry store implementation.
- Update SQLite schema/migrations.

### Phase 6 — Agent Interface

- Move templates.
- Add local generated entry behavior.
- Update `.gitignore`.

### Phase 7 — bootstrap-dev

- Add `workroot.project.json`.
- Rewrite bootstrap-dev identity.
- Remove dependency on root AGENTS and `.workroot/kernel/VERSION`.
- Ensure idempotency.

### Phase 8 — Retrieval & Index Control

- Implement index manifests/build/health basics.
- Implement FTS/candidate provider integration.
- Implement global index projections.
- Implement release-aware filtering for redacted/deleted.

### Phase 9 — Relationship Network

- Rename business docs/code to relationships.
- Add/modify schema for relationship nodes/edges/evidence.
- Maintain compatibility if required.

### Phase 10 — Context Control

- Rename Context Guide docs to Context Control.
- Keep CLI `workroot context`.
- Ensure hard token limit conservative.
- Ensure trace includes release/relationship/index details.

### Phase 11 — Asset and Release Control

- Implement Asset unified model.
- Merge knowledge/decision/result into Asset types.
- Implement ReleaseRecord/Tombstone/Redaction/DeletionRecord basics.
- Enforce redaction/deletion strict protection.

### Phase 12 — System Health

- Update doctor checks.
- Add import-boundary checks.
- Add Public Seed retirement checks.
- Add release/index/schema checks.

### Phase 13 — Public Seed quarantine

- Remove tracked root `AGENTS.md` and `CLAUDE.md` only after packaged templates and bootstrap-dev local generation are working.
- Move tracked active root `space/` and `.workroot/` only after replacement runtime, CLI, docs, templates, tests, and doctor checks are working.
- Remove tracked `.idea/` if tracked.
- Preserve history/fixtures if useful.

Quarantine is intentionally late. Do not start implementation by deleting or moving `space/`, `.workroot/`, root `AGENTS.md`, or root `CLAUDE.md`.

### Phase 14 — Tests

- Add/modify unit, integration, smoke, negative tests.
- Ensure no old tests enforce Public Seed active structure.

### Phase 15 — Final docs sweep

- README
- START_HERE_FOR_HUMANS
- ROADMAP
- CHANGELOG
- release note
- docs/specs/README
- docs/history/public-seed.md

### Phase 16 — Validation and report

- Run all validations.
- Produce final report.
- Do not tag until user approves.

## Codex rules

- Build replacement architecture first, then quarantine the old Public Seed active root.
- Do not invent new domain names.
- Do not delete legacy capability without matrix entry.
- Do not add remote LLM/embedding/vector dependencies.
- Do not commit generated root AGENTS/CLAUDE.
- Do not reintroduce Public Seed as active architecture.
- Keep implementation lightweight.
