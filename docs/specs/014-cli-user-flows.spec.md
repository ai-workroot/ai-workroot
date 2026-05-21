# Spec 014 — CLI User Flows

Status: accepted
Target: 0.9.530

## Primary commands

```text
workroot init
workroot list
workroot status
workroot context
workroot doctor
workroot bootstrap-dev
```

## Optional/future commands

These can be introduced when implementation is ready:

```text
workroot task ...
workroot asset ...
workroot release ...
workroot index ...
workroot relationship ...
```

## Legacy commands

Old seed commands must not appear as current Clean Workroot primary flow. If retained temporarily, put under:

```text
workroot legacy ...
```

## CLI rules

- CLI is thin.
- CLI calls runtime.
- CLI does not import storage directly.
- CLI help must not describe Public Seed as active architecture.
- CLI should use Clean Workroot wording.

## `workroot init`

Creates registered Workroot and optionally agent-ready entry.

## `workroot context`

Calls Context Control.

Required options:

```text
--agent
--cwd
--query
--mode
--target-tokens
--hard-token-limit
--debug
```

## `workroot bootstrap-dev`

Dogfood only. No commit/tag/push.

## Acceptance

- `python -m ai_workroot --help` works.
- `workroot --help` shows Clean Workroot primary commands.
- legacy commands hidden or namespaced.
- context exposes hard token limit.
- bootstrap-dev output confirms generated local entries are ignored.
