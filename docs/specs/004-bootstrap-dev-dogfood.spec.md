# Spec 004 — bootstrap-dev Dogfood

Status: accepted  
Target: 0.9.530

## Purpose

Define AI Workroot self-management through Clean Workroot dogfood.

## Rules

- bootstrap-dev treats the AI Workroot source repo as a Clean Workroot user directory.
- It does not use Public Seed assumptions.
- It does not require root `AGENTS.md`.
- It does not require `.workroot/kernel/VERSION`.
- It must not commit, tag, push, or create release.
- It must be idempotent.
- It must be safe under concurrent runs.

## Project marker

Use:

```text
workroot.project.json
```

Required fields:

```json
{
  "project": "ai-workroot",
  "bootstrapDevSupported": true,
  "architecture": "clean-workroot",
  "version": "0.9.530"
}
```

## Local generated files

bootstrap-dev creates:

```text
AGENTS.md
CLAUDE.md
.ai-workroot-local/
```

These must be ignored:

```text
/AGENTS.md
/CLAUDE.md
/.ai-workroot-local/
```

## `.ai-workroot-local/`

Use for:

- drafts
- reviews
- patches
- smoke output
- context package samples
- temporary analysis

Do not use for:

- managed state
- canonical assets
- formal architecture docs
- formal specs
- source code
- tests
- release notes

## bootstrap-dev publication policy

bootstrap-dev uses project-native asset publication:

```text
architecture doc -> docs/architecture/
spec -> docs/specs/
ADR -> docs/adr/
release note -> docs/releases/
history -> docs/history/
source code -> src/ai_workroot/
test -> tests/
template -> templates/
CI -> .github/workflows/
process draft -> .ai-workroot-local/
```

## Acceptance

- bootstrap-dev succeeds without root AGENTS.md and without `.workroot/`.
- second bootstrap-dev run reuses existing Workroot registration.
- generated entry files are ignored.
- `.ai-workroot-local/` is ignored.
- no commit/tag/push command is executed.
