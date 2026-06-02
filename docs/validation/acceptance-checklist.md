# Acceptance Checklist

## Architecture

- [ ] Public Seed retired as active architecture.
- [ ] Clean Workroot and bootstrap-dev dogfood are the only active scenarios.
- [ ] Core terms are consistent.
- [ ] No `Memory` as formal domain term.
- [ ] No `Graph` as business domain term.
- [ ] `Tombstone` entity named correctly.
- [ ] Relationship Network docs/specs exist.
- [ ] Retrieval & Index Control docs/specs exist.
- [ ] WorkrootEnvironment docs/specs exist.

## Source tree

- [ ] `src/ai_workroot/cli/` exists.
- [ ] `src/ai_workroot/commands/` exists.
- [ ] `src/ai_workroot/protocol/` exists.
- [ ] `src/ai_workroot/state/` exists.
- [ ] `src/ai_workroot/work/` exists.
- [ ] `src/ai_workroot/assets/` exists.
- [ ] `src/ai_workroot/relationships/` exists.
- [ ] `src/ai_workroot/retrieval/` exists.
- [ ] `src/ai_workroot/context/` exists.
- [ ] `src/ai_workroot/release/` exists.
- [ ] `src/ai_workroot/handoff/` exists.
- [ ] `src/ai_workroot/agent_entry/` exists.
- [ ] `src/ai_workroot/diagnostics/` exists.
- [ ] `src/ai_workroot/shared/` exists.
- [ ] `src/ai_workroot/templates/` exists.
- [ ] user install scripts under `install/`.
- [ ] scripts are dev wrappers only.

## Git hygiene

- [ ] root `AGENTS.md` not tracked.
- [ ] root `CLAUDE.md` not tracked.
- [ ] root `space/` not active tracked.
- [ ] root `.workroot/` not active tracked.
- [ ] `.idea/` not tracked.
- [ ] `.gitignore` ignores `/AGENTS.md`, `/CLAUDE.md`, `/.ai-workroot-local/`.

## WorkrootEnvironment

- [ ] `AI_WORKROOT_HOME` maps to WorkrootEnvironment.
- [ ] global config exists.
- [ ] global registry exists.
- [ ] registry lock exists.
- [ ] global preferences are not user profile.
- [ ] global index treated as derived read model.

## bootstrap-dev

- [ ] uses `workroot.project.json`.
- [ ] does not require root AGENTS.
- [ ] does not require `.workroot/kernel/VERSION`.
- [ ] creates local generated entry files.
- [ ] creates `.ai-workroot-local/`.
- [ ] no commit/tag/push.
- [ ] idempotent second run.

## Asset

- [ ] Asset unifies knowledge/decision/result.
- [ ] Asset publication policy exists.
- [ ] Published Asset only writes user directory.
- [ ] ContextPackage/Trace/Candidate/FTS row are not Assets.
- [ ] path history/fingerprint fields exist or are reserved.

## Release Control

- [ ] ReleaseRecord exists.
- [ ] Tombstone exists.
- [ ] Redaction exists.
- [ ] DeletionRecord exists.
- [ ] Tombstone does not mutate target object.
- [ ] redacted/deleted strictly protected.
- [ ] tombstone visible/traceable but not hard excluded by default.

## Relationship Network

- [ ] RelationshipNode/Edge/Evidence exists.
- [ ] docs use Relationship Network.
- [ ] Relationship traversal projection is derived.

## Retrieval & Index Control

- [ ] Index manifest/build/health exists.
- [ ] environment/global index scope exists.
- [ ] workroot index scope exists.
- [ ] candidate/FTS/text providers exist.
- [ ] release-aware filtering prevents redacted/deleted leakage.

## Context Control

- [ ] CLI remains `workroot context`.
- [ ] docs/specs use Context Control.
- [ ] ContextPackage generated.
- [ ] ContextTrace generated.
- [ ] hard token limit conservative.
- [ ] no user directory write by Context Control.

## System Health

- [ ] Doctor checks environment.
- [ ] Doctor checks registry.
- [ ] Doctor checks schema.
- [ ] Doctor checks index health.
- [ ] Doctor checks Native Entry safety.
- [ ] Doctor read-only by default.

## Validation commands

- [ ] `python3 -m py_compile $(find src -name "*.py")`
- [ ] `python3 -m unittest discover -s tests -v`
- [ ] `python3 -m ai_workroot --help`
- [ ] `git diff --check`
- [ ] relevant smoke commands recorded.
