# Spec 001 — Project Structure and Naming

Status: accepted
Target: 0.9.530 base, amended for 0.9.531 protocol runtime

## Purpose

Reset the source tree from Public Seed to Clean Workroot architecture and establish stable naming rules.

## Required source structure

Create or migrate toward:

```text
src/ai_workroot/cli/
src/ai_workroot/commands/
src/ai_workroot/protocol/
src/ai_workroot/state/
src/ai_workroot/work/
src/ai_workroot/assets/
src/ai_workroot/relationships/
src/ai_workroot/retrieval/
src/ai_workroot/context/
src/ai_workroot/release/
src/ai_workroot/handoff/
src/ai_workroot/agent_entry/
src/ai_workroot/diagnostics/
src/ai_workroot/shared/
src/ai_workroot/templates/
install/unix/install.sh
install/windows/install.ps1
scripts/dev/
docs/architecture/
docs/specs/
docs/adr/
docs/dev/
docs/history/
```

## Active root must not contain tracked retired seed files

These must not be tracked in active repo root:

```text
AGENTS.md
CLAUDE.md
space/
.workroot/
.idea/
```

If historical content is needed, move it to:

```text
docs/history/public-seed.md
tests/fixtures/legacy-public-seed-history/
```

## Naming rules

Use:

```text
Clean Workroot
bootstrap-dev dogfood
Workroot Management
WorkrootEnvironment
Asset
Release Control
Tombstone
Relationship Network
Retrieval & Index Control
Context Control
Agent Interface
System Health
```

Do not use as active domain names:

```text
Public Seed
Portable Seed
Mind
Memory
Graph
Context Gate
TombstoneMarker
ReleaseMarker
DeletionMarker
RedactionMarker
```

## Template and local entry rules

The repo may contain templates:

```text
templates/native-agent-entry/AGENTS.md.template
templates/native-agent-entry/CLAUDE.md.template
src/ai_workroot/templates/native_agent_entry/...
```

The repo must not track generated root:

```text
/AGENTS.md
/CLAUDE.md
```

`.gitignore` must include:

```text
/AGENTS.md
/CLAUDE.md
/.ai-workroot-local/
```

## Acceptance

- `git ls-files AGENTS.md CLAUDE.md` returns no active root files.
- `git ls-files | grep '^space/'` returns no active root files except explicit fixtures/history.
- `git ls-files | grep '^.workroot/'` returns no active root files except explicit fixtures/history.
- `README.md` no longer says current architecture is Public Seed.
- `ROADMAP.md` no longer has Public Seed stabilization as current P0.
- `docs/specs/README.md` lists new specs and statuses.
