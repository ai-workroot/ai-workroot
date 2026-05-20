# Migration and Quarantine Plan

## 1. Principles

- Do not silently delete old capability evidence.
- Do not keep old Public Seed as active architecture.
- Preserve old files in history/fixtures when useful.
- Treat 0.9.530 as an architecture reset with minimal real-user migration obligations.
- Rebuild derived data when safe; back up canonical relationship/release/asset/work records before destructive migration.

## 2. Active source tree migration

### Root files/directories

| Old path | Action | New location |
|---|---|---|
| `space/` | Quarantine | `docs/history/public-seed/space/` or `tests/fixtures/legacy-public-seed-history/space/` |
| `.workroot/` | Quarantine | `docs/history/public-seed/.workroot/` or fixture |
| `AGENTS.md` | Remove from tracked root | `templates/native-agent-entry/AGENTS.md.template` |
| `CLAUDE.md` | Remove from tracked root | `templates/native-agent-entry/CLAUDE.md.template` |
| `.idea/` | Remove from Git | none |
| `scripts/install.sh` | Move/wrap | `install/unix/install.sh` |
| `scripts/install.ps1` | Move/wrap | `install/windows/install.ps1` |
| product logic in `scripts/*.py` | Migrate | `src/ai_workroot/*` |
| dev helper scripts | Move | `scripts/dev/` |

## 3. Documentation migration

Old docs must be rewritten or retired:

| Old doc | Action |
|---|---|
| README Public Seed sections | Rewrite to Clean Workroot |
| ROADMAP Public Seed P0 | Rewrite |
| docs/workroot-system-design.md | Rewrite or replace |
| docs/architecture-map.md | Rewrite |
| docs/kernel-implementation-specification.md | Mark retired or replace with release validation spec |
| old specs with Draft status | Update status and content |
| old handoffs/review notes | Move to `docs/dev/` or remove if obsolete |

## 4. Managed state migration

### Environment-level

Current global layout contains `user/profile.md`, `preferences.md`, and `global-principles.md`. New model should not create global user profile.

Action:

- Replace with `preferences/operator-preferences.json` and `preferences/policy-defaults.json`.
- If old files exist, preserve as `docs/history` in source or as environment backup in runtime, but do not treat as active global profile.

### Per-Workroot

New per-Workroot layout should include:

```text
workroot.json
charter/
state/
tasks/
handoffs/
assets/
release/
relationships/
indexes/
context/
diagnostics/
maintenance/
cache/
logs/
```

If old `knowledge/` exists, migrate conceptually to `assets/` with `asset_type=knowledge` or keep as legacy directory only until runtime migration.

## 5. SQLite migration

### Required precondition

Before schema migration, run backup where old DB exists:

```text
cache/workroot.sqlite -> cache/backups/workroot.sqlite.<timestamp>.bak
```

### New canonical/derived split

Canonical:

- workroots / registrations
- tasks / runs / actions / checkpoints / handoffs
- assets
- release records / tombstones / redactions / deletion records
- relationship nodes / edges / evidence
- migrations

Derived:

- indexed files / chunks
- FTS rows
- context candidates
- global navigation indexes
- relationship traversal projections
- context package history unless explicitly retained as diagnostics

### Table direction

Old top-level `knowledge_items` must not remain the canonical knowledge table. Knowledge becomes:

```text
assets.asset_type = 'knowledge'
```

Old `graph_nodes` / `graph_edges` should become:

```text
relationship_nodes
relationship_edges
relationship_evidence
```

If implementation risk is high, compatibility views may be created temporarily, but docs must use Relationship Network.

## 6. CLI migration

Old main commands:

```text
init
list
status
context
doctor
bootstrap-dev
```

Legacy seed commands must not appear as Clean Workroot primary flow. They may be moved under:

```text
workroot legacy ...
```

or kept as hidden/compat wrappers with clear warning.

## 7. Test migration

Tests that assert active Public Seed layout must be rewritten or moved to legacy fixture tests. No current architecture test may require root `space/`, `.workroot/`, `AGENTS.md`, or `CLAUDE.md`.

## 8. Rollback approach

Because source tree migration is large, Codex must commit/checkpoint per phase. If a phase fails, revert that phase rather than rolling back the whole branch.

Do not tag until final validation passes.
