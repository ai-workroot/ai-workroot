# Spec 017 — Release Validation

Status: accepted
Target: 0.9.530

## Required validation before tag

```text
python3 -m py_compile $(find src -name "*.py")
python3 -m py_compile scripts/*.py  # if remaining scripts exist
python3 -m unittest discover -s tests -v
python3 scripts/validate_kernel.py --release  # Phase 0 baseline only until replaced or rewritten
python3 -m ai_workroot --help
git diff --check
```

`scripts/validate_kernel.py --release` is tied to the old Public Seed/kernel architecture. It may be used for baseline comparison, but final 0.9.530 release readiness must not rely on it alone unless it is rewritten to validate Clean Workroot.

Final validation must provide a Clean Workroot release entry point, for example:

```text
python3 -m ai_workroot.cli.main doctor --release
python3 -m ai_workroot.runtime.doctor --release
scripts/dev/validate-release.sh
```

## Smoke tests

- Clean Workroot init.
- Native Agent Entry authorization.
- Native Agent Entry local ignored under bootstrap-dev.
- bootstrap-dev first run.
- bootstrap-dev second run idempotency.
- Context Control package generation.
- Context Trace generation.
- Asset publication staging/publish.
- Release Control redaction/deletion protection.
- Tombstone visible/traceable.
- Relationship Network relationship creation/traversal.
- Retrieval & Index Control global/workroot index status.
- Doctor check.
- Migration check.
- Import-boundary check.
- Public Seed retirement check.
- Redaction/deletion leakage negative checks.
- Relationship Network canonical table checks.

## Git hygiene

These must be empty unless fixture/history paths are explicitly allowed:

```text
git ls-files | grep '^AGENTS.md$'
git ls-files | grep '^CLAUDE.md$'
git ls-files | grep '^space/'
git ls-files | grep '^.workroot/'
git ls-files | grep '^.idea/'
```

## Docs validation

- README reflects Clean Workroot.
- ROADMAP reflects 0.9.530 reset.
- specs have statuses.
- ADRs exist.
- Public Seed only appears in history/retired context.
- Core terms are consistent.

## Final report

Codex must produce final report with:

- commit hash;
- changed file summary;
- validation command outputs;
- smoke outputs;
- known limitations;
- items deferred intentionally.
- replacement release validation command and output.
