# 0.9.530 Clean Workroot Domain Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` for independent implementation packets or `superpowers:executing-plans` for inline execution with checkpoints. Execute task-by-task. Do not tag, release, or merge without explicit human approval.

**Goal:** Reset AI Workroot from Public Seed active layout to Clean Workroot architecture while preserving legacy capabilities and keeping each checkpoint reviewable.

**Architecture:** The target source tree is `src/ai_workroot/{core,contracts,runtime,storage,indexing,agent,cli,resources}`. Replacement architecture is built before root Public Seed artifacts are quarantined. Public Seed capabilities are preserved through explicit model, storage, runtime, indexing, context, health, and test mappings.

**Tech Stack:** Python standard library, SQLite, shell/PowerShell wrappers, local filesystem state, `unittest`, Git.

---

## Baseline

Already verified before this plan was written:

```text
python3 -m py_compile scripts/*.py
python3 scripts/validate_kernel.py --release
python3 -m unittest discover -s tests -v
```

Result:

```text
231 tests passed.
AI Workroot release kernel validation passed.
```

## Execution Invariants

- Build replacement architecture first, then quarantine Public Seed active root.
- Keep `contracts/` standard-library-only.
- Keep `core/` free of storage, indexing, agent, and CLI imports.
- Keep CLI thin; CLI calls runtime, not storage/indexing adapters directly.
- Use Relationship Network as business language; `graph` may appear only as technical implementation terminology.
- Use `ReleaseRecord`, `ReleaseTargetRef`, `ReleaseLevel`, `Tombstone`, `Redaction`, `DeletionRecord`, `RecallRule`, `ReleasePolicy`, and `ReleasePropagationEvent`.
- Do not introduce real vector database, remote embedding, or remote LLM dependencies.
- Do not make global indexes a global knowledge body store.
- Do not commit generated root `AGENTS.md`, generated root `CLAUDE.md`, or `.ai-workroot-local/`.

## Checkpoint 1: Source-Of-Truth Docs

**Purpose:** Make 0.9.530 architecture docs, specs, ADRs, validation, final review clarifications, and preservation matrix the committed source of truth.

**Inputs:**

- `/Users/zeer/ai_workroot_0_9_530_final_codex_package`
- `/Users/zeer/codex_readiness_review_final_response.md`
- Current repository docs/specs from 0.9.529

**Outputs:**

- `docs/specs/*.spec.md` for 0.9.530.
- `docs/specs/README.md`.
- `docs/architecture/*.md`.
- `docs/adr/*.md`.
- `docs/validation/*.md`.
- `docs/dev/0.9.530/**`.
- Historical 0.9.529 specs under `docs/history/0.9.529/specs/`.

**Risks:**

- Old 0.9.529 validation may still expect active specs under `docs/specs/`.
- Imported execution docs may conflict with final architect clarifications unless edited.

**Verification:**

```bash
find docs/specs docs/architecture docs/adr docs/validation docs/dev/0.9.530 -type f | sort
rg -n "Phase 3 . Legacy active-tree quarantine" docs/specs docs/dev/0.9.530 || true
rg -n "validate_kernel.py --release" docs/specs docs/dev/0.9.530
git diff --check
```

## Checkpoint 2: Project Skeleton And Packaging

**Purpose:** Create importable package structure without moving product logic yet.

**Files:**

- Create `pyproject.toml`.
- Create `src/ai_workroot/__init__.py`.
- Create `src/ai_workroot/__main__.py`.
- Create `src/ai_workroot/cli/main.py`.
- Create `src/ai_workroot/{core,contracts,runtime,storage,indexing,agent,resources}/__init__.py`.
- Add initial tests under `tests/unit/test_import_boundaries.py` and `tests/smoke/test_package_entrypoint.py`.

**Approach:**

- `python3 -m ai_workroot --help` must work before logic migration.
- The first CLI can be a thin wrapper that reports available Clean Workroot commands and delegates legacy commands only through explicit compatibility paths later.

**Verification:**

```bash
python3 -m py_compile $(find src -name "*.py")
PYTHONPATH=src python3 -m ai_workroot --help
python3 -m unittest tests.unit.test_import_boundaries tests.smoke.test_package_entrypoint -v
```

## Checkpoint 3: Contracts And Core Model

**Purpose:** Establish stable DTO/protocol boundaries and rich lightweight core models.

**Files:**

- Create `src/ai_workroot/contracts/{clock.py,events.py,filesystem.py,git.py,retrieval.py,storage.py,templates.py}`.
- Create `src/ai_workroot/core/{common.py,environment.py,work.py,assets.py,release.py,relationships.py,retrieval.py,context.py,agent.py,health.py,extensions.py}`.
- Add tests under `tests/unit/core/` and `tests/unit/contracts/`.

**Required behaviors:**

- Work: `TaskKind`, `TaskProcessLevel`, `TaskDecompositionPolicy`, `Task`, `AgentRun`, `WorkAction`, `WorkCheckpoint`, `RetrievalCard`, `InvalidationRecord`, `OperationTransaction`.
- Assets: `Asset`, `AssetSurface`, `AssetPublication`, path history, fingerprint update, publication state transitions.
- Release: `ReleaseRecord`, `Tombstone`, `Redaction`, `DeletionRecord`, recall/release policy, protected-content behavior.
- Relationships: `RelationshipNode`, `RelationshipEdge`, `RelationshipType`, `RelationshipEvidence`, relation-backed edge validation.
- Retrieval/context: `IndexManifest`, `ContextBudget`, request/result/package/trace DTOs.
- Agent/health/extensions: Native Agent Entry policy, doctor check result types, reserved extension capability types.

**Verification:**

```bash
python3 -m unittest discover -s tests/unit -v
python3 -m py_compile $(find src/ai_workroot/contracts src/ai_workroot/core -name "*.py")
```

## Checkpoint 4: Storage, Environment, And Migrations

**Purpose:** Move managed state and SQLite schema control into storage/runtime without leaking into user directories.

**Files:**

- Create `src/ai_workroot/storage/{filesystem.py,jsonl_registry.py,locks.py,sqlite.py,migrations.py}`.
- Create `src/ai_workroot/runtime/environment.py`.
- Add tests under `tests/integration/storage/` and `tests/integration/runtime/`.

**Required behaviors:**

- `AI_WORKROOT_HOME/config.json`.
- `registry/workroots.jsonl`, `directory-bindings.jsonl`, `aliases.jsonl`, `relationships.jsonl`, and registry lock.
- `global-index/` as management/navigation read model only.
- `global-cache/global.sqlite` as cache, not knowledge.
- Per-Workroot `workroot.json` and managed directories.
- SQLite `schema_migrations`, assets, release, relationship, retrieval/index, context, health, and work tables.
- Backup before old DB migration.

**Verification:**

```bash
python3 -m unittest discover -s tests/integration -p "test_storage*.py" -v
python3 -m unittest discover -s tests/integration -p "test_environment*.py" -v
```

## Checkpoint 5: Agent Interface And bootstrap-dev Replacement

**Purpose:** Replace root committed agent files with packaged templates and local generated entries.

**Files:**

- Create `src/ai_workroot/resources/templates/native-agent-entry/AGENTS.md.template`.
- Create `src/ai_workroot/resources/templates/native-agent-entry/CLAUDE.md.template`.
- Create `src/ai_workroot/agent/native_entry.py`.
- Create `src/ai_workroot/runtime/bootstrap.py`.
- Create `workroot.project.json`.
- Update `.gitignore`.
- Add or update `scripts/bootstrap-dev.sh` and `scripts/bootstrap-dev.ps1` wrappers.

**Required behaviors:**

- bootstrap-dev identifies the repo by `workroot.project.json`.
- bootstrap-dev does not require root `AGENTS.md`.
- bootstrap-dev does not require `.workroot/kernel/VERSION`.
- bootstrap-dev creates local ignored `AGENTS.md`, `CLAUDE.md`, and `.ai-workroot-local/` only when appropriate.
- bootstrap-dev is idempotent and does not commit, tag, push, or release.

**Verification:**

```bash
python3 -m unittest discover -s tests/integration -p "test_bootstrap*.py" -v
bash -n scripts/bootstrap-dev.sh
git check-ignore AGENTS.md CLAUDE.md .ai-workroot-local/
```

## Checkpoint 6: Runtime Flows And CLI

**Purpose:** Route user-visible commands through runtime orchestration and keep legacy seed commands isolated.

**Files:**

- Create `src/ai_workroot/runtime/{init.py,context.py,doctor.py,indexing.py,release.py,assets.py}`.
- Update `src/ai_workroot/cli/main.py`.
- Move or wrap install scripts into `install/unix/install.sh` and `install/windows/install.ps1`.
- Keep root `scripts/` as compatibility wrappers or `scripts/dev/` utilities.

**Required commands:**

- `workroot init`
- `workroot list`
- `workroot status`
- `workroot context`
- `workroot doctor`
- `workroot bootstrap-dev`
- `workroot legacy ...` for old seed commands if retained

**Verification:**

```bash
PYTHONPATH=src python3 -m ai_workroot --help
PYTHONPATH=src python3 -m ai_workroot init --help
PYTHONPATH=src python3 -m ai_workroot context --help
python3 -m unittest discover -s tests/smoke -v
```

## Checkpoint 7: Retrieval, Index Control, Relationship Network, And Context Control

**Purpose:** Preserve retrieval capabilities under the new domain boundaries.

**Files:**

- Create `src/ai_workroot/indexing/providers/{sqlite_fts.py,candidate_provider.py,relationship_provider.py,metadata_provider.py,vector_provider.py,search_provider.py}`.
- Create `src/ai_workroot/indexing/{manifest.py,pipeline.py,global_indexes.py,workroot_indexes.py}`.
- Add context/runtime integration tests.

**Required behaviors:**

- Local FTS and metadata retrieval.
- Candidate pool from explicit rules, active task, FTS, relationship one-hop signals, recent/high-importance candidates.
- Relationship signals must be relation-backed.
- Query failures degrade gracefully and record trace errors.
- Reserved vector/search providers do not import external packages.
- Context output includes mode, confidence, latency, token usage, selected candidates, retrieval metadata, and debug trace.
- Token estimate is conservative for English, CJK, code, and all-content-trimmed cases.

**Verification:**

```bash
python3 -m unittest discover -s tests/integration -p "test_indexing*.py" -v
python3 -m unittest discover -s tests/integration -p "test_context*.py" -v
```

## Checkpoint 8: Release Control Protection

**Purpose:** Ensure redacted/deleted content cannot leak while Tombstone remains visible and traceable.

**Files:**

- Extend `src/ai_workroot/core/release.py`.
- Extend `src/ai_workroot/storage/sqlite.py`.
- Extend `src/ai_workroot/indexing/`.
- Extend `src/ai_workroot/runtime/context.py`.
- Add negative tests under `tests/negative/`.

**Required behaviors:**

- `Tombstone` overlays a target without mutating target status.
- Tombstone/quiet/archive are annotated and traceable, not hard-excluded by default.
- Redaction/deletion/safety-sensitive content is excluded from ordinary context, FTS, candidates, and global indexes.
- DeletionRecord leaves only minimal trace.

**Verification:**

```bash
python3 -m unittest discover -s tests/negative -v
```

## Checkpoint 9: System Health And Release Validator

**Purpose:** Replace old Public Seed release validation with Clean Workroot health/release validation.

**Files:**

- Create or update `src/ai_workroot/runtime/doctor.py`.
- Create `scripts/dev/validate-release.sh` or equivalent Python entry point.
- Update `scripts/validate_kernel.py` only if it becomes a compatibility wrapper or is rewritten for Clean Workroot.
- Add release validation tests.

**Required checks:**

- Environment config.
- Registry integrity and duplicate bindings.
- State directory boundaries.
- SQLite schema and migrations.
- Relationship canonical tables.
- Release propagation and leakage protection.
- Index health.
- Agent entry safety.
- bootstrap-dev ignored files.
- Public Seed active root retired.
- Import boundaries.

**Verification:**

```bash
PYTHONPATH=src python3 -m ai_workroot doctor --release
scripts/dev/validate-release.sh
python3 -m unittest discover -s tests -p "*release*" -v
```

## Checkpoint 10: Public Seed Quarantine

**Purpose:** Retire tracked active root Public Seed only after replacement flows work.

**Files:**

- Move `space/` to `docs/history/public-seed/` or `tests/fixtures/legacy-public-seed-history/`.
- Move `.workroot/` to `docs/history/public-seed/` or `tests/fixtures/legacy-public-seed-history/`.
- Remove tracked root `AGENTS.md` and `CLAUDE.md`.
- Ensure `.idea/` is untracked and ignored.

**Verification:**

```bash
git ls-files | grep '^AGENTS.md$' && exit 1 || true
git ls-files | grep '^CLAUDE.md$' && exit 1 || true
git ls-files | grep '^space/' && exit 1 || true
git ls-files | grep '^.workroot/' && exit 1 || true
git ls-files | grep '^.idea/' && exit 1 || true
git check-ignore AGENTS.md CLAUDE.md .ai-workroot-local/
```

## Checkpoint 11: Public Docs And Release Notes

**Purpose:** Make user-facing docs match Clean Workroot and mark Public Seed as historical only.

**Files:**

- `README.md`
- `START_HERE_FOR_HUMANS.md`
- `ROADMAP.md`
- `CHANGELOG.md`
- `docs/releases/0.9.530.md`
- `docs/architecture-map.md`
- `docs/workroot-system-design.md`
- `docs/kernel-implementation-specification.md`
- `docs/history/public-seed.md`

**Verification:**

```bash
rg -n "Current Public Seed|Context Gate|TombstoneMarker|ReleaseMarker" README.md docs src || true
rg -n "space/ \\+ \\.workroot as current layout" README.md docs || true
```

Mentions under `docs/history/` are allowed when explicitly historical.

## Checkpoint 12: Final Validation And Handoff

**Purpose:** Produce review-ready branch without merging, tagging, or releasing.

**Verification commands:**

```bash
python3 -m py_compile $(find src scripts -name "*.py")
python3 -m unittest discover -s tests -v
git diff --check origin/main...HEAD
PYTHONPATH=src python3 -m ai_workroot --help
PYTHONPATH=src python3 -m ai_workroot doctor --release
scripts/dev/validate-release.sh
```

**Handoff must include:**

- Branch and commit.
- Base SHA.
- Changed files summary.
- Legacy capability preservation status.
- SQLite schema summary.
- CLI command summary.
- Smoke outputs.
- Negative test outputs.
- Known limitations.
- Explicit confirmation: no merge, no tag, no release.
