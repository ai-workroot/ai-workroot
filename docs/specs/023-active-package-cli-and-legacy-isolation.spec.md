# Spec 023: Active Package CLI and Legacy Isolation

## Status

Superseded by `041-runnable-legacy-compat-removal.spec.md`

## Priority

P0

## Background

This Spec records the earlier 0.9.530 transition where AI Workroot introduced the package CLI while temporarily isolating older Public Seed commands behind an explicit legacy boundary.

That transitional compatibility boundary is no longer active. Spec 041 is authoritative for current behavior: the active package CLI exposes only Clean Workroot commands, and runnable legacy compatibility is removed from active paths.

## Current Rule

The active CLI command set is:

```text
workroot init
workroot list
workroot status
workroot context
workroot doctor
workroot bootstrap-dev
```

Removed legacy command namespaces must fail as invalid active commands.

## Replacement

Use `041-runnable-legacy-compat-removal.spec.md` for:

- active CLI boundaries;
- removed legacy command behavior;
- package import boundaries;
- script compatibility removal;
- historical non-runnable archive requirements.

## Historical Note

The 0.9.530 compatibility-preserving design is retained in `docs/history/0.9.530/dev/` and historical plans. It is not the current active implementation contract.
