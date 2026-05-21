# 0.9.530 Scripts Boundary Final Design

## Status

Draft implementation checkpoint for `feat/0.9.530-clean-workroot-domain-reset`.

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

## Target Design

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

Legacy Public Seed operation commands become package-owned compatibility
commands under:

```text
workroot legacy manifest
workroot legacy schema
workroot legacy recipe
workroot legacy task
workroot legacy run
workroot legacy action
workroot legacy artifact
workroot legacy retrieval-card
workroot legacy checkpoint
workroot legacy invalidation
workroot legacy mind
workroot legacy session
workroot legacy continue
workroot legacy batch
```

The `legacy` command is intentionally hidden from default Clean Mode help. It is
available for compatibility and documented only where legacy Public Seed
operation compatibility is being discussed.

### Compatibility Wrappers

`scripts/compat/workroot_cli.py` remains callable for old automation. It is a
thin wrapper that imports package code after adding the repository `src/`
directory to `sys.path`.

`scripts/legacy/public_seed/*` remains a quarantine area for historical entry
points. Those files may re-export package behavior, but new Clean Workroot
product behavior must not be added there.

### Package Boundary

Package modules must not:

- import `scripts` modules;
- execute any `scripts/...` path through subprocess or equivalent;
- expose `scripts/...` paths as canonical package command guidance.

Package modules may mention legacy concepts, but command examples emitted by
package code should use `workroot legacy ...` or `python -m ai_workroot legacy
...`, not script paths.

### Agent Operation Manifest

The legacy operation manifest stays package-owned under
`ai_workroot.runtime.legacy_seed.operation_manifest`.

It should describe operation contracts and use package CLI commands:

```text
workroot legacy manifest --format json
workroot legacy schema --format json
workroot legacy recipe batch-12-tasks --format json
workroot legacy batch apply --file plan.json
```

Implementation source modules remain non-startup implementation details and are
not normal agent reading requirements.

## Implementation Plan

1. Add regression tests proving package source no longer contains canonical
   `scripts/...` command guidance.
2. Add package CLI tests for `python -m ai_workroot legacy ...`.
3. Refactor `ai_workroot.cli.legacy_seed.main` to accept `argv` so package CLI
   can call it directly without subprocess.
4. Add hidden `legacy` dispatch to `ai_workroot.cli.main`.
5. Update legacy quickstart, recipes, and operation manifest output to use
   `workroot legacy ...`.
6. Update historical Public Seed fast-start docs and architecture tests to use
   package-owned legacy commands.
7. Re-run unit, integration, negative, smoke, package doctor, release
   validation, py_compile, and diff checks.

## Acceptance Criteria

- Package source has no `scripts/` string constants.
- `python -m ai_workroot --help` remains Clean Mode focused and does not expose
  individual legacy operation commands.
- `python -m ai_workroot legacy manifest --format json` works.
- `python -m ai_workroot legacy recipe task-l2-evidence` renders package-owned
  legacy command examples.
- `scripts/compat/workroot_cli.py` remains callable for compatibility.
- No package module imports or executes scripts.

## Non-goals

- Do not remove compatibility wrappers.
- Do not remove legacy Public Seed capability.
- Do not make legacy commands a primary Clean Mode user surface.
- Do not introduce new architecture concepts.
- Do not merge, tag, or release.
