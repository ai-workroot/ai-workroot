# Spec 002 — Clean Workroot Installation

Status: accepted  
Target: 0.9.530

## Purpose

Define user-facing Clean Workroot initialization.

## User directory rules

The selected directory is a user asset directory.

AI Workroot must not:

- create internal managed state folders in the user directory;
- treat same-named folders like `logs/`, `cache/`, `state/`, `context/` as managed state;
- write ContextPackage, ContextTrace, candidates, FTS rows, logs, cache, registry, or indexes into the user directory;
- write Native Agent Entry files without explicit authorization.

AI Workroot may:

- create or update `AGENTS.md` / `CLAUDE.md` only after explicit authorization;
- publish user-visible assets only through Asset Publication Policy;
- leave all other user directory contents untouched unless explicitly requested.

## Init flow

1. Resolve `AI_WORKROOT_HOME`.
2. Initialize or load `WorkrootEnvironment`.
3. Validate selected user directory.
4. Acquire registry lock.
5. Check duplicate active directory binding.
6. Create `WorkrootRegistration` and `WorkrootDirectoryBinding`.
7. Create per-Workroot state directory.
8. Initialize storage schema.
9. Initialize default WorkrootCharter placeholder.
10. Ask for Native Agent Entry authorization.
11. If authorized, write managed block into `AGENTS.md` / `CLAUDE.md`.
12. Run post-init doctor check.

## Native Agent Entry authorization

The prompt must explain:

- files will be created/updated in the user directory;
- contents are short launchers;
- no state path, Workroot ID, logs, indexes, handoffs, or traces will be embedded;
- user content outside managed block is preserved.

## Agent-ready state

A Workroot can be registered without Native Agent Entry for admin/test use.

An agent-ready Workroot requires authorized Native Agent Entry files.

## Acceptance

- Init creates managed state under `AI_WORKROOT_HOME`, not user directory.
- Init rejects duplicate active binding.
- Init can run without Native Agent Entry only as registered/non-agent-ready.
- Native Entry write requires explicit authorization.
- ContextPackage and ContextTrace are not written to user directory.
- User-created `logs/` or `cache/` inside user dir does not cause violation.
