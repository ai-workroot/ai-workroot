# Orthogonal Capability Dependencies Design

## Goal

Make the 0.9.530 command-first source tree strictly acyclic at the package level, with each capability owning its canonical behavior and upper layers composing lower capabilities through explicit public entrypoints.

## Dependency Direction

The active package dependency direction is:

```text
cli -> commands -> orchestration/capabilities -> state/shared
context -> retrieval + relationships + release + state
retrieval -> state
release -> release model/evaluation/filter only
relationships -> state + shared
work/assets -> state
diagnostics -> state + agent_entry
state/shared/agent_entry -> no capability imports
```

`shared` and `state` are bottom packages. `commands` may coordinate application use cases. Peer capability packages must not form cycles.

## Capability Ownership

Release Control owns release records, tombstones, redactions, deletion records, release level ranking, target evaluation, target resolution, and filtering. Context Control asks Release Control whether a candidate, FTS match, or relationship signal is allowed; Retrieval must not define or import release policy.

Relationship Network owns relationship node/edge/evidence writes and relationship traversal signals. Retrieval must not expose canonical relationship write APIs. Context Control consumes relationship signals as part of context assembly.

Retrieval owns candidate and FTS read models. It does not contain adapters that map retrieval objects to Release Control targets; those adapters live in Release Control filtering.

## Test Contract

Add a static package graph contract that:

- fails on any package-level cycle;
- fails on unlisted package edges;
- specifically prevents `release -> retrieval`;
- specifically prevents `relationships -> retrieval`.

Keep existing runtime and release validation tests as behavior guards.

## Migration Scope

This is still an internal 0.9.530 structure correction. It does not change CLI commands, SQLite schema, release semantics, context package semantics, or user-facing behavior.
