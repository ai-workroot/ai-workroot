# P0 E2E Safety Incident: Empty Run Root Deleted Real Repository

## Status

Recorded

## Date

2026-05-21

## Summary

An end-to-end harness command accidentally deleted the local AI Workroot repository directory. The command passed an empty run-root argument after shell expansion, the harness interpreted the empty path as the current directory, and recursive cleanup removed the real repository checkout.

## What Happened

The unsafe command form was equivalent to:

```bash
RUN_ROOT=/some/path PYTHONPATH=src python3 -m tests.e2e.longrun --run-root "$RUN_ROOT"
```

In shell evaluation, `"$RUN_ROOT"` expanded before the same-line temporary assignment took effect. The E2E harness received an empty `--run-root` value. Python path handling treated the empty value as the current directory. The harness then performed recursive cleanup against the current repository directory.

## Why It Happened

- The harness accepted an empty run-root value.
- The harness allowed the current directory as an effective run root.
- The harness used recursive deletion without sentinel-based ownership checks.
- E2E destructive operations did not go through a shared safe cleanup API.
- The workflow did not require a dedicated sandbox root before cleanup.

## What Guard Failed

Missing guards:

- Reject empty path.
- Reject `.` and current working directory.
- Reject real repository path.
- Reject repository parent and shared project parent.
- Require `.ai-workroot-e2e-sandbox` before run execution.
- Require `.ai-workroot-owned` before recursive cleanup.
- Quarantine before deletion.
- Detect dangerous same-line shell variable assignment patterns.

## Data Affected

The local AI Workroot repository checkout was deleted. The repository was later restored from a local backup archive.

## Recovery

The repository was restored from:

```text
<local-backup-archive>
```

Uncommitted implementation and test changes were rebuilt after restoration.

## Required Prevention

This incident is now governed by:

```text
docs/specs/036-e2e-sandbox-and-destructive-operation-safety.spec.md
```

All future E2E harnesses must:

- Use a dedicated visible sandbox base, preferably `$HOME/tmp/ai-workroot-e2e-sandboxes`.
- Reject empty and ambiguous paths.
- Require sandbox and ownership sentinels.
- Use safe cleanup helpers instead of direct recursive deletion.
- Preserve E2E sandboxes by default for human review.
- Prove that the real repository, real home, and real managed state were untouched.

## Regression Tests Required

- Empty run-root is rejected before any file operation.
- `.` is rejected before any file operation.
- Real repository root is rejected.
- Real repository parent is rejected.
- Shared project parent is rejected.
- Missing sandbox sentinel is rejected.
- Missing owned sentinel is rejected for cleanup.
- Same-line environment variable assignment command pattern is rejected.
- Valid run root under the dedicated sandbox base is accepted.

## Follow-up Status

Spec added. Implementation and regression tests must be completed before running any further live-agent E2E or destructive E2E cleanup.
