# Spec 020 — Documentation Rewrite

Status: accepted for 0.9.530; amended by 0.9.531 source layout
Applies to: 0.9.530 base documentation rewrite

## Purpose

All public docs must describe the current Clean Workroot architecture. Public Seed must be historical only.

## Required rewrites

- README.md
- ROADMAP.md
- START_HERE_FOR_HUMANS.md if retained
- CHANGELOG.md
- docs/architecture-map.md
- docs/workroot-system-design.md
- docs/kernel-implementation-specification.md
- docs/specs/README.md
- docs/releases/0.9.530.md

## Required additions

```text
docs/architecture/clean-workroot-architecture.md
docs/architecture/final-core-concepts.md
docs/architecture/lightweight-core-runtime-architecture.md
docs/architecture/runtime-layout.md
docs/architecture/relationship-network.md
docs/architecture/retrieval-index-control.md
docs/architecture/release-control.md
docs/architecture/workroot-environment.md
docs/history/public-seed.md
```

## Language rules

Forbidden active-architecture language:

```text
Current Public Seed
space/ + .workroot as current layout
Memory as formal domain
Mind as formal domain
Graph as business domain
Context Gate
TombstoneMarker
```

Required active-architecture language for the 0.9.530 rewrite:

```text
Clean Workroot
WorkrootEnvironment
Relationship Network
Retrieval & Index Control
Release Control
Tombstone
Agent Interface
```

0.9.531 source layout amendment:

```text
entrypoints / commands / protocol / capabilities / state / shared
```

## Acceptance

Run textual audit:

```bash
grep -R "Current Public Seed" README.md docs || true
grep -R "Context Gate" README.md docs src || true
grep -R "TombstoneMarker" README.md docs src || true
grep -R "Memory" README.md docs/src || true
```

Mentions inside `docs/history/` are allowed if clearly historical.
