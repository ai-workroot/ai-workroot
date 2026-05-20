# Negative Test Checklist

Codex must add or update tests for these negative cases.

## Retired Public Seed

- [ ] bootstrap-dev must not require root `AGENTS.md`.
- [ ] bootstrap-dev must not require `.workroot/kernel/VERSION`.
- [ ] root tracked `AGENTS.md` fails Git hygiene check.
- [ ] root tracked `CLAUDE.md` fails Git hygiene check.
- [ ] active root tracked `space/` fails architecture check unless fixture/history.
- [ ] active root tracked `.workroot/` fails architecture check unless fixture/history.

## User directory

- [ ] user-created `logs/` must not be treated as managed state.
- [ ] user-created `cache/` must not be treated as managed state.
- [ ] ContextPackage must not write user directory.
- [ ] ContextTrace must not write user directory.
- [ ] Candidate/FTS rows must not write user directory.

## Native Agent Entry

- [ ] entry file containing state path fails validation.
- [ ] entry file containing Workroot ID fails validation.
- [ ] entry file containing debug trace path fails validation.
- [ ] entry update must preserve user content outside managed block.

## Release Control

- [ ] Redacted content cannot enter ContextPackage.
- [ ] Deleted content cannot enter ContextPackage.
- [ ] Deleted content cannot remain in FTS/candidate indexes.
- [ ] Tombstone does not mutate Task.status.
- [ ] Tombstone can target Task through ReleaseTargetRef.
- [ ] Tombstone is visible/traceable.
- [ ] Deletion cannot be auto-converted to Tombstone.

## Retrieval & Index Control

- [ ] Index provider must not bypass release/deletion filtering.
- [ ] Context Control must not call SQLite/FTS adapter directly if provider contract exists.
- [ ] Graph/relationship traversal projection loss does not delete canonical RelationshipEdge.
- [ ] Redacted/deleted entries cannot remain in global indexes.

## Relationship Network

- [ ] invalid relationship type rejected.
- [ ] relationship edge without valid nodes rejected or flagged.
- [ ] cross-Workroot relationship not allowed without explicit WorkrootRelationship/global policy.

## Contracts and imports

- [ ] `contracts` importing `core` fails import-boundary test.
- [ ] `core` importing `storage` fails import-boundary test.
- [ ] `cli` importing `storage` directly fails import-boundary test.

## Asset model

- [ ] `knowledge_items` as active top-level domain rejected.
- [ ] Decision not modeled as top-level separate domain.
- [ ] ContextPackage cannot be published as user asset unless explicit asset publication flow is used.
- [ ] Missing asset path does not delete asset identity.

## bootstrap-dev

- [ ] bootstrap-dev must not commit/tag/push.
- [ ] second bootstrap-dev run must not duplicate registry records.
- [ ] concurrent bootstrap-dev must not duplicate registry records.
- [ ] generated AGENTS/CLAUDE must be ignored.
