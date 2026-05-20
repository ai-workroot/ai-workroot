# Implementation Order and Checkpoints

This plan is mandatory for Codex. The work is large and must not be done in random order.

## Phase 0 — Branch and baseline

Branch:

```text
feat/0.9.530-clean-workroot-domain-reset
```

Baseline commands:

```bash
python3 -m py_compile scripts/*.py
python3 scripts/validate_kernel.py --release
python3 -m unittest discover -s tests -v
```

If baseline tests fail because old Public Seed contracts conflict with new architecture, record them in the implementation report before modifying them.

Checkpoint output:

- branch name
- current commit
- baseline test result
- known baseline failures

## Phase 1 — Documentation source of truth

Create/update:

```text
docs/architecture/
docs/specs/
docs/adr/
docs/history/
docs/dev/
```

Required docs:

- Architecture overview.
- Final core concepts and boundaries.
- Engineering structure.
- Runtime layout.
- Legacy capability preservation matrix.
- Dependency rules.
- Clean Workroot installation spec.
- WorkrootEnvironment managed state spec.
- Bootstrap-dev dogfood spec.
- Core model spec.
- Storage/schema spec.
- Testing plan.
- Release validation plan.

Checkpoint:

- docs exist
- old Public Seed active language removed or marked retired
- spec statuses updated

## Phase 2 — Source scaffold

Create target structure:

```text
src/ai_workroot/core/
src/ai_workroot/contracts/
src/ai_workroot/runtime/
src/ai_workroot/storage/
src/ai_workroot/indexing/
src/ai_workroot/agent/
src/ai_workroot/cli/
src/ai_workroot/resources/
```

Add `pyproject.toml` entry points if missing.

Checkpoint:

```bash
python3 -m py_compile $(find src -name "*.py")
python3 -m ai_workroot --help
```

## Phase 3 — Contracts and core model

Create:

```text
src/ai_workroot/contracts/
src/ai_workroot/core/
```

Rules:

- `contracts/` uses only the standard library.
- `contracts/` must not import `ai_workroot.core`, `runtime`, `storage`, `indexing`, `agent`, or `cli`.
- `core/` may import `contracts` only when necessary.
- `core/` must not import storage, indexing, agent, or CLI.
- Core objects include local behavior and invariants; they are not passive DTOs.

Checkpoint:

- contracts import-boundary tests exist
- core import-boundary tests exist
- core behavior unit tests exist

## Phase 4 — WorkrootEnvironment and runtime state

Implement WorkrootEnvironment and managed state layout.

Required changes:

- Global `user/profile.md` retired.
- Operator preferences and policy defaults introduced.
- Registry remains canonical global state.
- Global index remains derived read model.
- Global cache is not knowledge.

Checkpoint:

- init creates correct AI_WORKROOT_HOME layout
- duplicate binding rejected
- registry lock works
- doctor validates environment

## Phase 5 — Agent Interface

Implement packaged templates and local generation:

```text
src/ai_workroot/resources/templates/native-agent-entry/AGENTS.md.template
src/ai_workroot/resources/templates/native-agent-entry/CLAUDE.md.template
```

`.gitignore` must contain:

```text
/AGENTS.md
/CLAUDE.md
/.ai-workroot-local/
```

Checkpoint:

- bootstrap-dev generates local root AGENTS/CLAUDE
- generated files ignored
- templates contain only launcher instructions
- no state path or Workroot ID leaks

## Phase 6 — bootstrap-dev replacement path

Implement:

- `workroot.project.json`
- bootstrap-dev repo identity from project marker
- no dependency on root `AGENTS.md`
- no dependency on `.workroot/kernel/VERSION`
- idempotent first and second run
- no commit/tag/push

Checkpoint:

- bootstrap-dev succeeds after temporarily moving root AGENTS/CLAUDE aside in a temp copy
- bootstrap-dev succeeds after temporarily moving `.workroot/` aside in a temp copy
- second run does not duplicate registry records

## Phase 7 — Storage and schema

Implement schema aligned with:

- WorkrootEnvironment
- Asset unified model
- Release Control
- Relationship Network
- Retrieval & Index Control
- Context Control
- System Health

Checkpoint:

- `schema_migrations` present
- no top-level `knowledge_items` as canonical domain table
- `relationship_nodes`, `relationship_edges`, and `relationship_evidence` exist as canonical relationship tables
- release tables exist
- index tables exist
- redaction/deletion protection fields present

## Phase 8 — Runtime orchestration

Implement flows:

- initialize environment
- init Clean Workroot
- bootstrap-dev
- generate context
- publish/stage asset
- create release/tombstone/redaction/deletion
- refresh indexes
- run doctor

Checkpoint:

- CLI calls runtime
- runtime wires contracts/adapters
- old scripts are wrappers only where needed

## Phase 9 — Asset, Release Control, and Relationship Network

Implement:

- Asset unified model
- ReleaseRecord / ReleaseTargetRef / ReleaseLevel / Tombstone / Redaction / DeletionRecord / RecallRule / ReleasePolicy / ReleasePropagationEvent
- RelationshipNode / RelationshipEdge / RelationshipType / RelationshipEvidence / RelationshipPolicy
- redaction/deletion strict protection
- tombstone visible/traceable but not hard-excluded by default

Checkpoint:

- redacted/deleted content cannot enter ordinary context, FTS, candidates, or global indexes
- Tombstone can be annotated/traced without mutating target object status
- RelationshipEdge is canonical and relation-backed

## Phase 10 — Indexing and retrieval

Implement:

- global indexes
- workroot indexes
- FTS
- Context candidates
- relationship traversal projection
- release-aware index entries
- provider contracts/adapters

Checkpoint:

- indexing refresh works
- retrieval result includes source/provider metadata
- redacted/deleted content is not exposed
- tombstone can be annotated/traced
- reserved vector/search providers do not import external packages

## Phase 11 — Context Control

Implement:

- ContextRequest
- ContextBudget
- hard token fallback
- retrieval provider usage
- relationship signal usage
- release state annotation/protection
- ContextPackage
- ContextTrace

Checkpoint:

- context command works
- trace records selection/drop/budget/release information
- context does not write user directory
- management queries do not route through Context Control

## Phase 12 — System Health

Doctor checks:

- Environment config
- registry integrity
- duplicate bindings
- state directory boundary
- SQLite schema
- relationship tables
- release propagation
- index health
- agent entry safety
- bootstrap-dev ignored files
- legacy active root not present

Checkpoint:

- doctor PASS on clean environment
- negative cases produce WARN/FAIL

## Phase 13 — Legacy active-tree quarantine

Quarantine active Public Seed artifacts:

```text
space/      -> docs/history/ or tests/fixtures/legacy-public-seed-history/
.workroot/  -> docs/history/ or tests/fixtures/legacy-public-seed-history/
AGENTS.md   -> remove from tracked root, replace with template
CLAUDE.md   -> remove from tracked root, replace with template
.idea/      -> remove from Git
```

Do not delete historical information without preserving it.

This phase must remain after replacement templates, bootstrap-dev, runtime, CLI, docs, tests, and doctor checks work. Do not start the implementation by moving these paths.

Checkpoint:

```bash
git ls-files | grep '^AGENTS.md$'      # empty
git ls-files | grep '^CLAUDE.md$'      # empty
git ls-files | grep '^space/'          # empty unless fixture/history path
git ls-files | grep '^.workroot/'      # empty unless fixture/history path
git ls-files | grep '^.idea/'          # empty
```

## Phase 14 — Tests and validation

Run full validation and update tests.

Required:

```bash
python3 -m py_compile $(find src scripts -name "*.py")
python3 -m unittest discover -s tests -v
python3 scripts/validate_kernel.py --release  # baseline only until replaced
git diff --check
git status --short
```

Checkpoint:

- acceptance checklist passed
- negative tests passed
- final report produced
- final release validation does not rely only on old Public Seed kernel validation

## Phase 15 — As-built docs and release note

Update:

- README
- START_HERE_FOR_HUMANS if retained
- ROADMAP
- CHANGELOG
- docs/releases/0.9.530.md
- docs/specs statuses
- docs/architecture as-built notes

Checkpoint:

- no active Public Seed language
- release notes mention architecture reset
- validation output included

## Phase 16 — Final release validation and report

Final release validation must either rewrite `scripts/validate_kernel.py --release` for Clean Workroot or replace it with a new validation entry point such as:

```bash
python3 -m ai_workroot.cli.main doctor --release
python3 -m ai_workroot.runtime.doctor --release
scripts/dev/validate-release.sh
```

Checkpoint:

- final validation command is documented
- final report includes exact command output
- no tag/release is created without human approval
