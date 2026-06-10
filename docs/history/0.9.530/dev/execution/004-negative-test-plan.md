# Negative Test Plan

Negative tests are mandatory. A green happy path is not enough.

## 1. Retired Public Seed tests

- Root `space/` must not be required.
- Root `.workroot/` must not be required.
- Root committed `AGENTS.md` must not be required.
- Root committed `CLAUDE.md` must not be required.
- bootstrap-dev must fail if it still checks `.workroot/kernel/VERSION`.
- README/ROADMAP must not describe Public Seed as current architecture.

## 2. User directory contamination tests

- `workroot init` must not create `.workroot/` in user directory.
- `workroot init` must not create `.ai-workroot/` in user directory.
- `workroot init` must not treat user-created `logs/`, `cache/`, `state/`, or `context/` as managed state.
- Context Control must not write ContextPackage or ContextTrace to user directory.

## 3. Native Agent Entry negative tests

- Generated entry must not contain AI_WORKROOT_HOME.
- Generated entry must not contain per-Workroot state path.
- Generated entry must not contain Workroot ID.
- Generated entry must not include handoffs/logs/indexes/debug paths.
- Managed block update must not delete user content outside block.
- Entry files must be Git ignored in bootstrap-dev.

## 4. Release Control negative tests

- Redacted content must not appear in normal ContextPackage.
- Deleted content must not appear in indexes or normal ContextPackage.
- Deleted content must not be preserved in hidden FTS rows.
- Tombstone must not be auto-created without explicit decision.
- Tombstone must not mutate TaskStatus or Asset core identity.
- Tombstone must be visible/traceable if explicitly queried.
- Tombstone must not be hard-excluded in 0.9.530 unless explicit policy says so.

## 5. Relationship Network negative tests

- New docs/code must not use Graph as business domain name.
- Relationship traversal projection loss must not delete RelationshipEdge truth.
- RelationshipEdge must require valid RelationshipType.
- Cross-Workroot relationship traversal must not be used for default context recall.

## 6. Retrieval & Index Control negative tests

- Contracts must not import core.
- Indexing must not call CLI.
- Context Control must not directly query SQLite FTS.
- Retrieval provider failure must be recorded and handled.
- Redacted/deleted records must invalidate or suppress affected index entries.
- Vector/search provider must remain reserved; no actual dependency introduced.

## 7. Storage/schema negative tests

- `knowledge_items` must not be canonical knowledge table.
- Graph table names must not be introduced as new business docs. If compatibility tables remain, docs must explain them as technical compatibility.
- schema_migrations missing must cause doctor warning/fail.
- old DB migration must back up before destructive change.

## 8. WorkrootEnvironment negative tests

- Duplicate active directory binding must fail.
- Unsafe Workroot ID must fail.
- State directory escaping AI_WORKROOT_HOME must fail.
- Global preferences must not become global knowledge/profile store.
- Global index must not contain knowledge body.

## 9. Git hygiene negative tests

- `.idea/` must not be tracked.
- `/AGENTS.md` must not be tracked.
- `/CLAUDE.md` must not be tracked.
- `/.ai-workroot-local/` must not be tracked.
- Generated bootstrap-dev files must not appear in `git status --short` except ignored files.
