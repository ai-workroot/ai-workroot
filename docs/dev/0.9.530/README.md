# AI Workroot 0.9.530 Development Notes

This directory preserves the external architecture package and final review clarifications used to plan the 0.9.530 Clean Workroot Domain Reset.

## Authority Order

When documents conflict, use this order:

1. `docs/dev/0.9.530/final-architect-review-clarifications.md`
2. `docs/specs/`
3. `docs/architecture/`
4. `docs/adr/`
5. `docs/plans/2026-05-20-0530-clean-workroot-domain-reset-plan.md`
6. `docs/dev/0.9.530/execution/`
7. Raw package snapshots: `00-final-master-plan.md`, `final-all-in-one.md`, `package-readme.md`

The raw package snapshots are retained for traceability. They may contain pre-clarification execution order or terminology examples. Do not treat them as higher authority than the final clarifications, current specs, architecture docs, ADRs, or implementation plan.

## Scripts-to-Source Migration Checkpoint

The next 0.9.530 implementation stage is documented in:

- `scripts-to-src-migration-architecture.md`
- `scripts-to-src-migration-detailed-design.md`
- `docs/specs/023-active-package-cli-and-legacy-isolation.spec.md`
- `docs/specs/024-work-and-asset-runtime-migration.spec.md`
- `docs/specs/025-storage-and-migrations-migration.spec.md`
- `docs/specs/026-retrieval-indexing-and-context-control-migration.spec.md`
- `docs/specs/027-release-relationship-and-safety-migration.spec.md`
- `docs/specs/028-system-health-validation-and-checkbot.spec.md`
- `docs/specs/029-install-dev-scripts-and-wrappers.spec.md`
- `docs/specs/030-test-suite-and-public-seed-quarantine.spec.md`

These documents make the remaining migration explicit: active Clean Workroot product logic moves into `src/ai_workroot/`, while `scripts/` narrows to wrappers, developer tooling, release validation, and legacy compatibility.

## Mandatory Execution Correction

Build the replacement architecture first, then quarantine the old Public Seed active root.

Do not begin implementation by deleting or moving root `space/`, `.workroot/`, `AGENTS.md`, or `CLAUDE.md`.

## Baseline

Before source-of-truth docs were imported, the branch passed:

```text
python3 -m py_compile scripts/*.py
python3 scripts/validate_kernel.py --release
python3 -m unittest discover -s tests -v
```

Result:

```text
231 tests passed.
AI Workroot release kernel validation passed.
```
