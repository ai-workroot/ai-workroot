# Spec: E2E Sandbox and Destructive Operation Safety

## Status

Draft

## Priority

P0

## Background

AI Workroot end-to-end validation needs realistic deterministic and live-agent runs, but an E2E harness must never damage the real source checkout, real user directories, real home directory, or real managed state. A P0 incident showed that an empty run-root argument can resolve to the current directory and cause recursive deletion of the repository.

This Spec makes E2E safety a hard architecture boundary. All E2E harnesses that create, modify, clean, or delete directories must use explicit sandbox roots, canonical path validation, sentinel files, and controlled cleanup APIs.

## Goals

- Prevent E2E harnesses from deleting or modifying the real AI Workroot repository.
- Prevent E2E harnesses from reading or writing real user state by default.
- Allow visible, reviewable sandbox runs under a standard per-user directory.
- Reject empty, ambiguous, parent, home, repository, and symlink-escaped paths.
- Require sentinel files before recursive cleanup.
- Preserve artifacts and sandboxes for human review by default.
- Apply the same safety baseline to deterministic E2E and live-agent E2E.

## Non-goals

- Do not implement full OS-level container sandboxing.
- Do not ban deterministic E2E.
- Do not ban live-agent E2E once safety guards are implemented.
- Do not require remote LLMs for E2E.
- Do not make E2E the only release gate.
- Do not permit any path guard bypass through user or agent approval.

## Scope

### Included

- E2E sandbox root requirements.
- Safe path validation rules.
- Sentinel-file ownership rules.
- Safe deletion and quarantine requirements.
- Environment variable requirements for live-agent E2E.
- Command construction and destructive command classification rules.
- Real repository protection evidence.
- Artifact preservation requirements.
- Regression test requirements for destructive-operation safety.

### Excluded

- Detailed live-agent scenario content beyond safety boundaries.
- Remote LLM provider implementation.
- UI automation.
- Release creation or tagging.

## Dependencies

- `034-end-to-end-persona-smoke-testing.spec.md`
- `017-release-validation.spec.md`
- `022-ci-and-release-gates.spec.md`
- `tests/e2e/`
- Future safe path and safe cleanup helper modules.

## Requirements

### Functional Requirements

FR-001: All E2E harnesses that write or delete files must require an explicit run root.

FR-002: The run root must be a non-empty absolute path after canonical resolution.

FR-003: The run root must not equal `.`, `..`, `/`, the user's home directory, the real AI Workroot repository, the real repository parent, `AI_WORKROOT_HOME`, or any shared project parent.

FR-004: The default sandbox base must be `$HOME/tmp/ai-workroot-e2e-sandboxes`, resolved with the current user's home directory at runtime.

FR-005: Each run root must contain `.ai-workroot-e2e-sandbox` before the harness may run agent steps or cleanup steps.

FR-006: Any recursively deletable directory must contain `.ai-workroot-owned` and must be inside the current run root.

FR-007: Direct calls to `shutil.rmtree`, `rm -rf`, `find -delete`, `git clean -fdx`, recursive `unlink`, or recursive `rmdir` must not appear in E2E harness code except inside a reviewed safe cleanup helper.

FR-008: Cleanup must quarantine owned paths by default. Permanent deletion is allowed only for current-run owned paths with sentinels and explicit cleanup mode.

FR-009: Live-agent E2E must require `AI_WORKROOT_E2E_LIVE=1`, `AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1`, and a valid sandbox run root under the default sandbox base or an explicitly approved sandbox base.

FR-010: Deterministic E2E must not require live-agent remote LLM flags, but it must still use the same safe run-root and cleanup guards.

FR-011: The harness must reject missing, unset, or empty environment variables used for path construction.

FR-012: The harness must reject shell command patterns where a same-line temporary assignment is referenced by another argument in the same command, such as `RUN_ROOT=/x command "$RUN_ROOT"`.

FR-013: Agent-generated shell commands must be classified as `safe`, `write`, `destructive`, `forbidden`, or `unknown` before execution.

FR-014: `destructive`, `forbidden`, and `unknown` commands must be blocked in automated runs. Human approval may permit only scenario-level safe operations inside the sandbox and must never override path guards.

FR-015: Live-agent E2E must run only inside a disposable repository clone or copy under the run root, never in the real source checkout.

FR-016: Repository copies must not use hardlinks to the real checkout.

FR-017: Every E2E run must write preflight and post-run artifacts showing source repository path, branch, commit, git status, run root, managed state path, and safety guard decisions.

FR-018: The final E2E report must state whether the real repository, real home, and real `~/.ai-workroot` were untouched.

### Non-functional Requirements

NFR-001: Path validation must use canonical absolute paths, resolving symlinks and `..` components.

NFR-002: On macOS, path validation must account for case-insensitive aliases.

NFR-003: Safety checks must fail closed when a path cannot be resolved, a sentinel is missing, or command intent is unknown.

NFR-004: E2E sandboxes must be preserved by default for human inspection.

NFR-005: Safety regression tests must be deterministic and CI-safe.

NFR-006: E2E safety code must be small, auditable, and shared by all harnesses.

## Proposed Design

### Concepts

E2E sandbox base:
The dedicated parent directory that may contain E2E run directories. The default base is:

```text
$HOME/tmp/ai-workroot-e2e-sandboxes
```

The harness resolves this to the current user's home directory at runtime. The resolved value must never be written into committed docs or fixtures.

E2E run root:
A unique run directory under the sandbox base, such as:

```text
$HOME/tmp/ai-workroot-e2e-sandboxes/run-20260521-153000-a1b2c3
```

Sandbox sentinel:
The file `.ai-workroot-e2e-sandbox`, created inside the run root by the harness before any scenario runs.

Owned-path sentinel:
The file `.ai-workroot-owned`, created inside any directory that the harness may recursively clean.

Quarantine:
The default cleanup behavior that moves owned paths into `artifacts/quarantine/` instead of deleting them permanently.

### Data Model

Preflight artifacts must include:

```json
{
  "runId": "run-20260521-153000-a1b2c3",
  "createdAt": "2026-05-21T15:30:00Z",
  "sandboxBase": "$HOME/tmp/ai-workroot-e2e-sandboxes",
  "runRoot": "$HOME/tmp/ai-workroot-e2e-sandboxes/run-20260521-153000-a1b2c3",
  "repoPath": ".../repo",
  "aiWorkrootHome": ".../ai-workroot-home",
  "home": ".../home",
  "userWorkroots": ".../user-workroots",
  "artifacts": ".../artifacts",
  "sourceRepoPath": "<local-ai-workroot-repo>",
  "sourceBranch": "feat/0.9.530-clean-workroot-domain-reset",
  "sourceCommit": "...",
  "sourceGitStatusBefore": "...",
  "remoteLlmAllowed": false,
  "safetyGuardVersion": "0.9.530"
}
```

Post-run artifacts must include:

- `artifacts/preflight.json`
- `artifacts/safety-decisions.jsonl`
- `artifacts/commands.jsonl`
- `artifacts/git-status-before.txt`
- `artifacts/git-status-after.txt`
- `artifacts/source-git-status-before.txt`
- `artifacts/source-git-status-after.txt`
- `artifacts/git-diff.patch`
- `artifacts/final-report.md`

### File Layout

Allowed visible local sandbox layout:

```text
$HOME/tmp/ai-workroot-e2e-sandboxes/
  run-<createdAt>-<short-id>/
    .ai-workroot-e2e-sandbox
    repo/
      .ai-workroot-owned
    ai-workroot-home/
      .ai-workroot-owned
    home/
      .ai-workroot-owned
    user-workroots/
      .ai-workroot-owned
    artifacts/
      .ai-workroot-owned
      quarantine/
      preflight.json
      final-report.md
```

Forbidden cleanup targets include:

```text
/
.
..
~/
$HOME
$HOME/.ai-workroot
<local-project-parent>
<local-ai-workroot-repo>
<local-ai-workroot-repo-parent>
```

### CLI / API

Recommended future helper APIs:

```python
assert_safe_e2e_run_root(path: Path, *, source_repo: Path, sandbox_base: Path) -> Path
assert_owned_cleanup_target(path: Path, *, run_root: Path) -> Path
prepare_e2e_run_root(run_root: Path) -> None
safe_quarantine_owned_path(path: Path, *, run_root: Path) -> Path
safe_delete_owned_path(path: Path, *, run_root: Path, permanent: bool = False) -> None
classify_shell_command(command: Sequence[str] | str) -> CommandSafetyDecision
```

E2E CLI commands must pass paths through argv or environment variables that are already exported. They must not rely on same-line temporary assignments referenced in the same shell command.

All E2E suites are opt-in only and must be launched through the explicit runner:

```bash
AI_WORKROOT_RUN_E2E=1 python3 -m tests.e2e.runner --suite safety
AI_WORKROOT_RUN_E2E=1 python3 -m tests.e2e.runner --suite persona-smoke
AI_WORKROOT_RUN_E2E=1 python3 -m tests.e2e.runner --suite longrun
```

Bad:

```bash
RUN_ROOT=/tmp/example python3 -m tests.e2e.longrun --run-root "$RUN_ROOT"
```

Good:

```bash
export RUN_ROOT="$HOME/tmp/ai-workroot-e2e-sandboxes/run-20260521-153000-a1b2c3"
AI_WORKROOT_RUN_E2E=1 python3 -m tests.e2e.runner --suite longrun
```

Better:

```bash
AI_WORKROOT_RUN_E2E=1 python3 -m tests.e2e.runner --suite safety --suite persona-smoke
```

### Runtime Behavior

Before any E2E scenario:

1. Resolve and validate the sandbox base.
2. Create a unique run root under the sandbox base.
3. Write `.ai-workroot-e2e-sandbox`.
4. Create child directories and `.ai-workroot-owned` sentinels.
5. Clone or copy the repository into `repo/` without hardlinks.
6. Set `AI_WORKROOT_HOME`, `HOME`, and scenario paths under the run root.
7. Write preflight artifacts.
8. Run deterministic or live-agent steps.
9. Write post-run artifacts.
10. Preserve the run root by default.

### Error Handling

If any guard fails:

- Stop immediately.
- Do not run cleanup.
- Write a failure report if the artifacts directory is already known safe.
- Print the rejected path or command.
- Preserve the run root for review when safe.

### Security / Privacy

E2E harnesses must not read or write real user documents, real managed state, real shell configuration, real agent credentials, or real source checkout files beyond read-only source metadata and safe repository copy operations.

Secrets and API keys must not be written to artifacts.

### Compatibility

Existing deterministic E2E harnesses must be updated to call shared safe path helpers. Existing run-root command forms remain supported only if they pass validation and are non-empty.

## Acceptance Criteria

AC-001:
Given a run root argument that is an empty string
When an E2E harness starts
Then it fails before creating, deleting, or modifying any file.

AC-002:
Given a run root equal to the real AI Workroot repository
When an E2E harness starts
Then it fails before creating, deleting, or modifying any file.

AC-003:
Given a run root equal to a shared project parent directory
When an E2E harness starts
Then it fails because shared project parents are not valid run roots.

AC-004:
Given a run root under `$HOME/tmp/ai-workroot-e2e-sandboxes/run-*`
When the harness prepares it
Then it creates `.ai-workroot-e2e-sandbox` and owned child directories.

AC-005:
Given an owned child directory without `.ai-workroot-owned`
When cleanup is requested
Then cleanup is rejected.

AC-006:
Given an owned child directory inside the run root
When default cleanup is requested
Then the directory is moved to `artifacts/quarantine/` rather than permanently deleted.

AC-007:
Given an agent-generated command classified as destructive
When the run is automated
Then the command is blocked and recorded in `safety-decisions.jsonl`.

AC-008:
Given a same-line temporary variable command such as `RUN_ROOT=/x command "$RUN_ROOT"`
When command validation runs
Then the command is rejected.

AC-009:
Given a completed E2E run
When the final report is inspected
Then it states whether the real repo, real home, and real `~/.ai-workroot` were untouched.

## Test Plan

### Unit Tests

- Reject empty path.
- Reject `.`.
- Reject `..`.
- Reject `/`.
- Reject real user home.
- Reject real repository path.
- Reject real repository parent.
- Reject shared project parent.
- Reject symlink escape.
- Reject missing sandbox sentinel.
- Reject missing owned sentinel.
- Reject same-line environment assignment expansion pattern.
- Classify destructive commands.
- Allow valid run root under the dedicated sandbox base.

### Integration Tests

- Deterministic E2E run uses safe run-root preparation.
- Level 2 persona smoke preserves run root and artifacts.
- Level 3/4 longrun refuses unsafe roots before any cleanup.
- Live-agent E2E preflight refuses to start without live flags.

### Manual Verification

- Inspect a run directory under `$HOME/tmp/ai-workroot-e2e-sandboxes`.
- Confirm the real repository still exists and has unchanged git status.
- Confirm artifacts include preflight, safety decisions, command logs, and final report.

## Migration / Rollback

Existing E2E harnesses must migrate from ad hoc run-root validation and direct cleanup to shared safety helpers.

Rollback is not recommended. If a regression blocks E2E, disable the unsafe E2E entrypoint rather than restoring direct deletion behavior.

## Observability / Debugging

Safety decisions must be logged to `artifacts/safety-decisions.jsonl` with:

- createdAt
- operation
- path or command
- classification
- decision
- reason

Final reports must include safety guard summary and any rejected operations.

## Task Breakdown

T1: Add shared E2E safety helpers
- Change: Implement canonical path validation, sentinel checks, and safe cleanup API.
- Files likely affected: `tests/e2e/safety.py`
- Verification: Unit tests reject unsafe paths and allow only dedicated sandbox run roots.

T2: Migrate deterministic E2E harnesses
- Change: Replace local run-root validation and direct cleanup with shared helpers.
- Files likely affected: `tests/e2e/harness.py`, `tests/e2e/persona_smoke.py`, `tests/e2e/longrun.py`
- Verification: Existing E2E tests pass and unsafe root tests fail closed.

T3: Add command safety classification
- Change: Add command classifier and reject dangerous shell patterns.
- Files likely affected: `tests/e2e/safety.py`, `tests/e2e/safety_cases.py`, `tests/e2e/runner.py`
- Verification: Destructive and same-line variable commands are rejected.

T4: Add artifact safety reporting
- Change: Write preflight, post-run, and safety decision artifacts.
- Files likely affected: `tests/e2e/harness.py`, `tests/e2e/reports.py`
- Verification: E2E reports include safety evidence.

T5: Add live-agent preflight gate
- Change: Add a live-agent entrypoint that refuses to run without live flags and sandbox validation.
- Files likely affected: `tests/e2e/live_agent.py`
- Verification: Live-agent preflight fails without required variables and passes only inside sandbox.

T6: Add release validation check
- Change: Ensure release validation rejects direct destructive operations in E2E harness code.
- Files likely affected: `src/ai_workroot/diagnostics/doctor.py` or release validation scripts
- Verification: `doctor --release` reports E2E safety checks.

## Risks

- Overly strict guards may initially block useful local E2E workflows.
- Hardlink detection can be platform-dependent.
- Command classification can miss shell edge cases if it tries to parse arbitrary shell syntax.
- Preserving sandboxes by default can consume disk space if old runs are not reviewed and cleaned safely.

## Open Questions

None.
