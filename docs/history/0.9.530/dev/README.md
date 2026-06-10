# AI Workroot 0.9.530 Development Notes

This directory preserves the external architecture package and final review clarifications used to plan the 0.9.530 Clean Workroot Domain Reset.

## Authority Order

When documents conflict, use this order:

1. `docs/history/0.9.530/dev/final-architect-review-clarifications.md`
2. `docs/specs/`
3. `docs/architecture/`
4. `docs/adr/`
5. `docs/history/0.9.530/plans/2026-05-20-0530-clean-workroot-domain-reset-plan.md`
6. `docs/history/0.9.530/dev/execution/`
7. Raw package snapshots: `00-final-master-plan.md`, `final-all-in-one.md`, `package-readme.md`

The raw package snapshots are retained for traceability. They may contain pre-clarification execution order or terminology examples. Do not treat them as higher authority than the final clarifications, current specs, architecture docs, ADRs, or implementation plan.

## Scripts-to-Source Migration Checkpoint

The next 0.9.530 implementation stage is documented in:

- `final-compatibility-preserving-script-migration-design.md`
- `scripts-to-src-migration-architecture.md`
- `scripts-to-src-migration-detailed-design.md`
- `docs/specs/031-compatibility-preserving-script-migration.spec.md`
- `docs/specs/023-active-package-cli-and-legacy-isolation.spec.md`
- `docs/specs/024-work-and-asset-runtime-migration.spec.md`
- `docs/specs/025-storage-and-migrations-migration.spec.md`
- `docs/specs/026-retrieval-indexing-and-context-control-migration.spec.md`
- `docs/specs/027-release-relationship-and-safety-migration.spec.md`
- `docs/specs/028-system-health-validation-and-checkbot.spec.md`
- `docs/specs/029-install-dev-scripts-and-wrappers.spec.md`
- `docs/specs/030-test-suite-and-public-seed-quarantine.spec.md`

These documents record the 0.9.530 package-ownership migration. They are historical design inputs after runnable legacy compatibility removal. Current active Clean Workroot product logic lives in `src/ai_workroot/`, while `scripts/` is limited to developer, release validation, and review helpers.

## Historical Compatibility Decision

The scripts-to-source migration had two explicitly named phases.

The package-ownership phase was the 0.9.530 target: finish package ownership while preserving existing script and legacy CLI compatibility. Old script files could become wrappers, and historical implementations could be archived under `docs/history/0.9.530/scripts/`.

The Compatibility Removal phase is implemented by `docs/specs/041-runnable-legacy-compat-removal.spec.md`: runnable legacy compatibility is removed from active paths and preserved as non-runnable archive material under `docs/history/public-seed/code-archive/`.

## Mandatory Execution Correction

Build the replacement architecture first, then quarantine the old Public Seed active root.

Do not begin implementation by deleting or moving root `space/`, `.workroot/`, `AGENTS.md`, or `CLAUDE.md`.

## Baseline

Before source-of-truth docs were imported, the 0.9.530 branch passed:

```text
python3 -m py_compile $(find src scripts -name "*.py")
python3 scripts/compat/validate_kernel.py --release
python3 -m unittest discover -s tests -v
```

Result:

```text
231 tests passed.
AI Workroot release kernel validation passed.
```
