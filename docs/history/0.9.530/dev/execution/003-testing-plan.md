# Testing Plan

## 1. Test structure

Target structure:

```text
tests/unit/
tests/integration/
tests/smoke/
tests/fixtures/
```

## 2. Unit tests

### Core model

Test core files:

- environment.py
- work.py
- assets.py
- release.py
- relationships.py
- retrieval.py
- context.py
- agent.py
- health.py
- extensions.py

Required unit cases:

- Task status transitions.
- TaskKind and TaskProcessLevel behavior.
- Task decomposition policy decisions.
- Asset publication state transitions.
- Asset fingerprint/path history behavior.
- ReleaseRecord and Tombstone behavior.
- Redaction/deletion protection rules.
- RelationshipEdge validation.
- IndexManifest stale/refresh decisions.
- ContextBudget trim decisions.
- Native Agent Entry managed block validation.

## 3. Contracts tests

Contracts must be importable without core/runtime/storage/indexing/agent/cli.

Test:

```python
import ai_workroot.contracts.storage
import ai_workroot.contracts.retrieval
import ai_workroot.contracts.filesystem
```

and verify contracts do not import `ai_workroot.core`.

## 4. Storage integration tests

Required:

- SQLite schema initialization.
- schema_migrations table.
- relationship tables.
- release tables.
- asset tables.
- index tables.
- backup before migration.
- JSONL registry lock behavior.
- duplicate user directory rejection.
- WorkrootEnvironment config creation.

## 5. Indexing integration tests

Required:

- global workroot index creation.
- workroot task/asset index creation.
- FTS index refresh.
- ContextCandidate generation.
- Relationship traversal projection.
- release-aware index annotation.
- redacted/deleted content not exposed by index result.
- tombstone result is traceable/annotated.

## 6. Context Control tests

Required:

- context package generated from Clean Workroot.
- Context Control uses retrieval providers, not direct SQLite.
- Context Trace records selected/dropped candidates.
- hard token limit fallback.
- relationship signal inclusion.
- release/tombstone/redaction/deletion handling.
- no user-directory writes.

## 7. Agent Interface tests

Required:

- templates exist.
- templates are short launchers.
- generated AGENTS.md / CLAUDE.md are local and ignored.
- no absolute state path.
- no Workroot ID leak.
- managed block replacement preserves user content.

## 8. bootstrap-dev tests

Required:

- identifies repo by workroot.project.json.
- does not require root AGENTS.md.
- does not require .workroot/kernel/VERSION.
- initializes Clean Workroot state.
- creates .ai-workroot-local/.
- generated files are ignored.
- second run is idempotent.
- concurrent run does not duplicate registry records.
- no commit/tag/push.

## 9. System Health tests

Required doctor checks:

- environment exists.
- config schema correct.
- registry valid.
- no duplicate active binding.
- state path under AI_WORKROOT_HOME.
- SQLite schema valid.
- relationship tables valid.
- release records valid.
- index health valid.
- agent entry safe.
- legacy active root absent.
- .idea not tracked.

## 10. Smoke tests

Smoke scripts should cover:

- clean init with temporary user directory.
- init with Native Agent Entry authorized.
- context command output.
- bootstrap-dev first run.
- bootstrap-dev second run.
- doctor after init.
- release/tombstone creation if CLI exists; otherwise runtime test.
- index refresh.

## 11. Full validation commands

```bash
python3 -m py_compile $(find src scripts -name "*.py")
python3 -m unittest discover -s tests -v
python3 scripts/compat/validate_kernel.py --release  # baseline only until replaced or rewritten
git diff --check
git status --short
```

If `validate_kernel.py` is retired or replaced, create a new release validation script and document it.
If it remains, add tests proving it validates Clean Workroot and no longer depends on tracked root `AGENTS.md`, `CLAUDE.md`, `space/`, or `.workroot/`.
