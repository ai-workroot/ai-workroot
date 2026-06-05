# Architecture Review Follow-up Design

## Goal

Close the remaining 0.9.530 architecture review gaps without expanding product scope or doing a large Context Control rewrite.

## Decisions

- Keep `context/builder.py` as the current Context Control entrypoint. It may stay large while behavior is cohesive and ownership boundaries are explicit.
- Move Handoff authoring into a dedicated `handoff/` capability. `work/` owns durable work facts; `handoff/` owns derived transfer packages.
- Move release filtering and target resolution into `release/filter.py`. Retrieval owns candidates, FTS, recall hints, and indexes; it does not own release governance.
- Remove active source dependence on `shared/model.py`. `shared/` remains reserved extensions and standard-library-only contracts, not a new `core/`.
- Fix `doctor --release --cwd` so release doctor validates the requested root, not the shell working directory.
- Keep this as an internal 0.9.530 structure correction. No version bump, no tag, and no remote push in this implementation pass.

## Source Layout Delta

Added:

```text
src/ai_workroot/capabilities/handoff/
src/ai_workroot/capabilities/release/filter.py
```

Removed:

```text
src/ai_workroot/capabilities/retrieval/providers/release_provider.py
src/ai_workroot/shared/model.py
```

## Ownership Rules

- `handoff/` may use `state` persistence helpers. It does not own tasks, work actions, checkpoints, or invalidations.
- `work/` no longer exposes `create_handoff()`.
- `release/filter.py` owns release target resolution and filtering for context candidates, FTS matches, and relationship signals.
- `retrieval/` must not import `ai_workroot.capabilities.release` or define release filter classes/functions.
- `context/` coordinates retrieval outputs, relationship signals, and release filters. It may import `release.filter`.
- `shared/` must not contain domain model buckets. Capability-specific value objects stay with the owning capability.

## Context Builder Boundary

`context/builder.py` remains one file in this follow-up. The only code movement is import ownership and small helper routing needed to keep retrieval independent from release.

Future split seams are marked in the file:

- request and budget resolution
- retrieval orchestration
- release filtering
- candidate selection
- rendering
- hard-token-limit enforcement
- persistence
- diagnostic logging

## Verification

The follow-up is accepted when:

- `workroot doctor --release --cwd <path>` respects `<path>`.
- Handoff authoring lives under `ai_workroot.capabilities.handoff.operations`.
- Release filtering lives under `ai_workroot.capabilities.release.filter`.
- Retrieval has no package edge to Release Control.
- `shared/model.py` is absent from active source.
- Package dependency graph remains acyclic.
- Full tests and release validation pass.
