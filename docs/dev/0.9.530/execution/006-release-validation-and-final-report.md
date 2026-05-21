# Release Validation and Final Report

## 1. Required final report sections

Codex must provide a final report with:

1. Branch and commit hash.
2. Summary of implemented architecture changes.
3. Files moved/quarantined.
4. Legacy capability preservation matrix status.
5. Schema changes.
6. Test results.
7. Smoke results.
8. Negative test results.
9. Known limitations.
10. Items deferred to next version.
11. Confirmation that no tag/release was created unless explicitly instructed.

## 2. Required command output

Include output for:

```bash
python3 -m py_compile $(find src scripts -name "*.py")
python3 -m unittest discover -s tests -v
python3 scripts/compat/validate_kernel.py --release  # Phase 0 baseline only unless rewritten
git diff --check
git status --short
```

If `scripts/compat/validate_kernel.py` is retired or replaced, provide the replacement command and reason.
If it is not retired, explain how it was rewritten to validate Clean Workroot instead of only old Public Seed/kernel assumptions.

## 3. Smoke scenarios

### Clean Workroot smoke

- Create temp user dir.
- Run init.
- Verify AI_WORKROOT_HOME state created.
- Verify user dir only contains authorized Native Agent Entry if enabled.
- Run context.
- Run doctor.

### bootstrap-dev smoke

- Run bootstrap-dev in repo.
- Verify workroot.project.json used.
- Verify local AGENTS/CLAUDE generated.
- Verify ignored.
- Run bootstrap-dev again.
- Verify idempotent.

### Release Control smoke

- Create Tombstone.
- Verify target object unchanged.
- Verify Tombstone visible/traceable.
- Create Redaction.
- Verify redacted content suppressed.
- Create DeletionRecord.
- Verify deleted content not exposed.

### Retrieval & Index Control smoke

- Refresh indexes.
- Query global workroot index.
- Query workroot task/asset index.
- Query FTS/candidates.
- Verify provider metadata in result.

### Relationship Network smoke

- Create relationship edge.
- Attach evidence.
- Query traversal projection.
- Verify relationship truth remains canonical.

## 4. Known limitations to document

If not fully implemented, document:

- Vector/search providers are reserved only.
- Extensions remain reserved/lightweight.
- Complex Tombstone exclusion policy deferred.
- Full user-file rename/move/delete resolver may be partial.
- Legacy Public Seed automatic migration not supported.

## 5. Tagging

Do not tag until human review approves final report.
