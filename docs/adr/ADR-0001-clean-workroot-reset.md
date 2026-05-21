# ADR-0001 — Clean Workroot Reset

Status: accepted

## Decision

Public Seed is retired as active architecture. Clean Workroot and bootstrap-dev dogfood are the only active scenarios.

## Rationale

The original seed structure mixed user space, system runtime, agent entry, kernel contracts, and project development files. Clean Workroot separates user assets from managed state and supports product usage and self-dogfood through the same architecture.

## Consequences

- `space/` and `.workroot/` leave active root.
- Root `AGENTS.md` / `CLAUDE.md` are local generated and ignored.
- Public Seed lives only in history or fixtures.
