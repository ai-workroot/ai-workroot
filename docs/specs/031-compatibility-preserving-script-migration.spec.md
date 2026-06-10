# Spec 031: Compatibility-Preserving Script Migration

## Status

Superseded by `041-runnable-legacy-compat-removal.spec.md`

## Priority

P0

## Background

This Spec records the 0.9.530 package-ownership phase. During that phase, implementation ownership moved toward `src/ai_workroot/` while older script and Public Seed command surfaces remained callable for compatibility.

That compatibility-preserving phase is complete and superseded. Spec 041 removes runnable legacy compatibility from active paths and preserves old source only as non-runnable historical archive material.

## Current Rule

The active product path is:

```text
src/ai_workroot/
python -m ai_workroot
scripts/dev/
install/
```

The active product path must not depend on:

```text
scripts/compat/
scripts/legacy/
runtime legacy packages
legacy command namespaces
```

## Replacement

Use `041-runnable-legacy-compat-removal.spec.md` for:

- package legacy module removal;
- script compatibility removal;
- historical code archive rules;
- test migration and retirement rules;
- release validation without legacy validators.

## Historical Note

The 0.9.530 compatibility-preserving design is retained in `docs/history/0.9.530/dev/` and historical plans for traceability. It is not the current active implementation contract.

Compatibility Removal phase complete for active paths: no runnable legacy compatibility remains.
