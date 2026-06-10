# Documentation Policy

This repository publishes result-oriented documentation, not agent execution
transcripts or detailed process scratchpads.

## Goals

AI Workroot documentation should help readers answer:

- what the product does;
- how to use it;
- how the current architecture works;
- which interfaces are stable;
- how to contribute safely;
- what changed in a release.

It should not require readers to reconstruct the project from old plans,
failed design paths, intermediate review packages, or Agent-specific execution
logs.

## Public Documentation Types

### Current Product Docs

Examples:

- `README.md`
- `START_HERE_FOR_HUMANS.md`
- `ROADMAP.md`
- `docs/workroot-system-design.md`
- `docs/workroot-operating-protocol.md`

These documents should describe the current product. They must not rely on
historical implementation plans as their source of truth.

### Architecture Docs

Examples:

- `docs/architecture.md`
- `docs/architecture/*`
- `docs/adr/*`

Architecture docs describe stable boundaries, responsibilities, dependency
rules, and durable decisions.

They may mention history only when it explains a current boundary.

### Specs

Specs under `docs/specs/` are stable implementation contracts. A spec should be
committed only when it describes behavior that is accepted, implemented, or
intentionally planned as a public contract.

Specs should not contain:

- step-by-step Agent execution plans;
- old failing attempts;
- temporary checklists;
- chat review packages;
- local E2E transcripts;
- stale command examples.

### Developer Docs

Docs under `docs/dev/` are for maintainers and contributors. They may include
quality gates, release procedures, testing notes, and short active TODOs.

They should stay concise. Long process artifacts should move to local
workspace storage or historical archive only when they have long-term value.

### History

Docs under `docs/history/` are non-current historical material. Historical
documents must not be cited as active implementation guidance unless the caller
explicitly asks for historical context.

## Local-Only Documentation

The following are local-only by default and should not be committed:

- detailed Agent execution plans;
- scratch design drafts;
- ChatGPT/Codex/Claude review bundles;
- E2E raw run packages;
- temporary report bundles;
- process-heavy implementation checklists;
- obsolete design paths that have been superseded.

Use ignored local paths such as:

```text
docs/local/
reports/
*_docs_bundle/
*_review_package/
workroot_*_package/
```

## Retired Process Docs

The repository no longer uses `docs/superpowers/` as a public documentation
surface.

Agent workflow plans and intermediate design specs may still be useful during a
local implementation session, but they should be summarized into current
architecture docs or stable specs before code is published.

## Current Source Of Truth

For current architecture, read:

1. `README.md`
2. `docs/workroot-system-design.md`
3. `docs/architecture.md`
4. `docs/architecture/010-runtime-layering.md`
5. `docs/specs/README.md`
6. `docs/releases/`

When documents conflict, the more current result-oriented document wins over
older plans or historical migration material.
