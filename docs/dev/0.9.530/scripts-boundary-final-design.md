# 0.9.530 Scripts Boundary Final Design

## Status

Historical 0.9.530 transition checkpoint.

This document is superseded for current active behavior by
`docs/specs/041-runnable-legacy-compat-removal.spec.md`. The compatibility
CLI namespace and compatibility wrappers described below were intentionally
removed in the runnable legacy compatibility cleanup branch. Keep this file only as historical design
context for why the compatibility layer existed during the 0.9.530 migration.

## Problem

The previous scripts-to-source migration moved active implementation into
`src/ai_workroot/` and reorganized `scripts/` into support directories. One
boundary problem remained: package-owned legacy operation output still presented
`scripts/compat/workroot_cli.py` as the canonical command path.

That is not a runtime reverse dependency, but it keeps the product protocol
centered on scripts. The architecture boundary should be stronger:

- `src/ai_workroot/` owns active and compatibility behavior.
- `scripts/` may call package code.
- package code must not import, execute, or recommend scripts as canonical
  product commands.

## Historical Target Design

### Canonical CLI Surface

Clean Workroot commands remain:

```text
workroot init
workroot list
workroot status
workroot context
workroot doctor
workroot bootstrap-dev
```

During the 0.9.530 transition, Legacy Public Seed operation commands were
planned as package-owned compatibility commands under a hidden legacy namespace:

```text
workroot <removed-legacy-namespace> ...
```

That compatibility namespace is no longer available after Spec 041. Current
Clean Workroot users should use only the active commands listed above.

### Compatibility Wrappers

During the 0.9.530 transition, compatibility wrappers remained callable for old
automation and legacy Public Seed entry points stayed in a runnable quarantine
area. Spec 041 removes those runnable surfaces. Historical source snapshots now
live under `docs/history/public-seed/code-archive/` as non-runnable `.txt`
files.

### Package Boundary

Package modules must not:

- import `scripts` modules;
- execute any `scripts/...` path through subprocess or equivalent;
- expose `scripts/...` paths as canonical package command guidance.

Package modules may mention legacy concepts, but command examples emitted by
package code should use current Clean Workroot commands, not script paths or
removed compatibility commands.

### Agent Operation Manifest

During the 0.9.530 transition, the legacy operation manifest stayed package
owned under a temporary legacy module. That module has been archived as
non-runnable history after Spec 041. Historical examples used the removed
legacy namespace:

```text
workroot <removed-legacy-namespace> manifest --format json
workroot <removed-legacy-namespace> schema --format json
workroot <removed-legacy-namespace> recipe batch-12-tasks --format json
workroot <removed-legacy-namespace> batch apply --file plan.json
```

Implementation source modules remain non-startup implementation details and are
not normal agent reading requirements.

## Implementation Plan

1. Add regression tests proving package source no longer contains canonical
   `scripts/...` command guidance.
2. Add package CLI tests for the temporary compatibility namespace.
3. Refactor `ai_workroot.cli.legacy_seed.main` to accept `argv` so package CLI
   can call it directly without subprocess.
4. Add hidden `legacy` dispatch to `ai_workroot.cli.main`.
5. Update legacy quickstart, recipes, and operation manifest output to use
   `workroot legacy ...`.
6. Update historical Public Seed fast-start docs and architecture tests to use
   package-owned legacy commands.
7. Re-run unit, integration, negative, smoke, package doctor, release
   validation, py_compile, and diff checks.

## Historical Acceptance Criteria

These criteria applied only to the 0.9.530 compatibility-preserving checkpoint.
They are superseded by Spec 041:

- Package source has no `scripts/` string constants.
- `python -m ai_workroot --help` remains Clean Mode focused.
- The removed compatibility namespace fails as an invalid command.
- `scripts/compat/` and `scripts/legacy/` do not exist as runnable surfaces.
- No package module imports or executes scripts.

## Non-goals

- Do not remove compatibility wrappers during the historical 0.9.530 transition.
- Do not remove legacy Public Seed capability during that transition.
- Do not make legacy commands a primary Clean Mode user surface.
- Do not introduce new architecture concepts.
- Do not merge, tag, or release.
