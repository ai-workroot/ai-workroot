# Spec: Publication Authoring Index Doctor Hardening

## Status

Draft

## Priority

P1

## Background

0.9.530 added active runtime modules for Work, Asset, Release, Relationship, and global indexes. Several behaviors remain too ambiguous for a milestone: asset publication is metadata-only while named as publish, active authoring surfaces are runtime-only, index invalidation is minimal, Doctor integrity checks are shallow, and clean review export is not standardized.

This Spec hardens these surfaces without removing legacy compatibility.

## Goals

- Split metadata-only asset publication from actual file publication semantics.
- Make active Work/Asset/Release/Relationship authoring surfaces reachable or explicitly documented.
- Add minimal index invalidation and index health checks.
- Add logic-level SQLite integrity Doctor checks.
- Add a clean review export helper.

## Non-goals

- Do not build a full product CLI.
- Do not remove legacy scripts or compatibility paths.
- Do not add GUI, MCP implementation, vector DB, remote embeddings, or remote LLMs.
- Do not add broad database foreign-key constraints in this pass.

## Scope

### Included

- Active asset publication runtime.
- Active authoring API/CLI documentation or minimal CLI exposure.
- Index invalidation rows for active runtime writes.
- Doctor integrity checks.
- Release validation script split or documentation.
- Clean review export helper.

### Excluded

- Full import/export product feature.
- Compatibility removal.
- Heavy DDD directory restructuring.

## Dependencies

- `024-work-and-asset-runtime-migration.spec.md`
- `027-release-relationship-and-safety-migration.spec.md`
- `028-system-health-validation-and-checkbot.spec.md`
- `029-install-dev-scripts-and-wrappers.spec.md`
- `031-compatibility-preserving-script-migration.spec.md`
- `037-release-derived-index-safety-hardening.spec.md`

## Requirements

### Functional Requirements

FR-001: Metadata-only publication must be named explicitly as metadata-only.

FR-002: Actual file publication must require explicit target path or surface, content or source file, and publication authorization.

FR-003: Actual file publication must not write outside the authorized surface.

FR-004: Active runtime authoring paths for Task, Internal Asset, Tombstone, Redaction, DeletionRecord, RelationshipEdge, and Index refresh must be documented as runtime APIs or exposed through minimal CLI.

FR-005: Active writes must record index invalidations where derived indexes can become stale.

FR-006: Doctor must detect orphan relationship edges, orphan relationship evidence, release targets pointing to missing known objects, candidate sources pointing to missing known objects, and context packages without traces.

FR-007: Release doctor must keep failing tracked root `AGENTS.md`, `CLAUDE.md`, `space/`, and `.workroot/`, while allowing ignored local root entries.

FR-008: A clean export helper must produce a review bundle from Git-tracked source and exclude local ignored artifacts.

### Non-functional Requirements

NFR-001: Keep filesystem writes explicit and Clean Mode compatible.

NFR-002: Logic integrity checks are preferred over broad DB foreign keys in this phase.

NFR-003: The implementation must remain standard-library-only.

NFR-004: Review export must not include ignored local state.

## Proposed Design

### Concepts

Metadata-only publication:
A durable record that an asset is considered published to a named surface, without writing a user-visible file.

Publish-to-surface:
An explicit write of content or a source file into an authorized surface path.

Logic integrity check:
A Doctor query that detects broken references without relying on SQLite foreign keys.

### Data Model

Use existing tables:

```text
asset_surfaces
asset_publications
assets
index_invalidations
relationship_nodes
relationship_edges
relationship_evidence
release_records
context_candidates
context_packages
context_traces
```

No broad foreign-key migration is required.

### File Layout

Likely changed files:

```text
src/ai_workroot/runtime/assets.py
src/ai_workroot/runtime/work.py
src/ai_workroot/runtime/release.py
src/ai_workroot/runtime/relationships.py
src/ai_workroot/indexing/global_indexes.py
src/ai_workroot/storage/sqlite.py
src/ai_workroot/runtime/doctor.py
scripts/dev/export-review-zip.sh
scripts/dev/validate-release.sh
docs/dev/0.9.530/active-authoring-surfaces.md
tests/unit/test_runtime_assets.py
tests/unit/test_runtime_work.py
tests/unit/test_runtime_release.py
tests/unit/test_runtime_relationships.py
tests/unit/test_global_indexes.py
tests/smoke/test_clean_release_validator.py
```

### CLI / API

Preferred for this pass:

- Keep runtime APIs as the active authoring surface.
- Document them in `docs/dev/0.9.530/active-authoring-surfaces.md`.
- Defer broad CLI groups unless product need is confirmed.

### Runtime Behavior

Asset publication:

1. `record_asset_publication()` records metadata only.
2. `publish_asset_to_surface()` validates a target path under the surface and writes content or copies source file.
3. Both record index invalidation for asset/global asset indexes.

Authoring:

1. Active runtime authoring functions remain package-owned.
2. Each active write records relevant index invalidation.
3. Documentation points maintainers to active APIs and marks legacy scripts as compatibility.

Doctor:

1. Verify schema tables.
2. Run logic integrity queries.
3. Report actionable findings.

### Error Handling

- Publish-to-surface rejects missing content/source file.
- Publish-to-surface rejects path traversal outside the authorized surface.
- Doctor integrity SQL errors become findings.
- Export helper exits non-zero if git archive fails.

### Security / Privacy

- No implicit writes to user directories.
- Publication writes require explicit authorization and path.
- Export helper uses Git-tracked content and excludes local runtime state.

### Compatibility

- Existing `publish_asset()` may remain as compatibility wrapper but must be documented or aliased to metadata-only behavior.
- Legacy scripts remain callable.

## Acceptance Criteria

AC-001:
Given an internal asset
When metadata-only publication is recorded
Then no user-visible file is written and the function name clearly indicates metadata-only behavior.

AC-002:
Given authorized content and an asset surface
When publish-to-surface runs
Then the file is written under the surface and asset publication metadata is recorded.

AC-003:
Given a target path with `..`
When publish-to-surface runs
Then it fails without writing.

AC-004:
Given orphan relationship edges
When Doctor runs
Then Doctor reports relationship integrity failure.

AC-005:
Given a context package without a trace
When Doctor runs
Then Doctor reports context trace integrity failure.

AC-006:
Given local ignored runtime files
When clean export helper runs
Then the output archive excludes ignored local artifacts.

## Test Plan

### Unit Tests

- Metadata-only asset publication.
- Publish-to-surface writes and path traversal rejection.
- Runtime authoring invalidation records.
- Global index refresh and invalidation behavior.

### Integration Tests

- Doctor integrity checks with deliberately broken rows.

### Manual Verification

- Run clean export helper and inspect archive file list.
- Run segmented validation commands.

## Migration / Rollback

No required schema migration beyond using existing tables. Rollback is a normal Git revert. Published files written during tests must use temp directories only.

## Observability / Debugging

- `index_invalidations` records stale derived surfaces.
- Doctor emits actionable integrity findings.
- Export helper prints archive path and excluded patterns.

## Task Breakdown

T1: Asset publication semantic split
- Change: Add tests and API for metadata-only vs file-writing publication.
- Files likely affected: `src/ai_workroot/runtime/assets.py`, `tests/unit/test_runtime_assets.py`
- Verification: Asset tests pass.

T2: Active authoring surface documentation
- Change: Document runtime APIs and compatibility status.
- Files likely affected: `docs/dev/0.9.530/active-authoring-surfaces.md`
- Verification: Release surface/docs tests pass.

T3: Index invalidation on active writes
- Change: Add small invalidation helper and call from active runtime writes.
- Files likely affected: runtime modules and tests.
- Verification: Runtime unit tests pass.

T4: Doctor integrity checks
- Change: Add logic integrity queries and tests.
- Files likely affected: `src/ai_workroot/storage/sqlite.py`, `src/ai_workroot/runtime/doctor.py`
- Verification: Doctor smoke tests pass.

T5: Clean export helper
- Change: Add `scripts/dev/export-review-zip.sh`.
- Files likely affected: script and release validation tests.
- Verification: Helper smoke test passes and archive excludes local artifacts.

## Risks

- Publish-to-surface can accidentally violate Clean Mode if target validation is weak.
- Too many integrity checks can create noisy Doctor output before migration catches up.
- Export helper must not depend on platform-specific zip behavior without fallback.

## Open Questions

None.
