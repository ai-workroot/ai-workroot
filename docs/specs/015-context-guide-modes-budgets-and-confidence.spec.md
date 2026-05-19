# Spec: Context Guide Modes, Budgets, and Confidence

## Status

Draft

## Priority

P0

## Background

AI Workroot 0.9.529 originally treated the Context Guide hot path as a strict sub-second feature. That remains the default target, but it must not become a hard rule that causes missing, inaccurate, or low-quality context. Context Guide should be fast by default, accurate when needed, and deep only when explicitly requested.

This Spec defines mode-aware Context Guide behavior, runtime-configured latency and token budgets, agent-aware output limits, context confidence, and mode-switch observability.

## Goals

- Treat 1 second as the normal hot-path target, not an absolute correctness limit.
- Make Context Guide mode, latency, and token budgets configurable.
- Keep Standard Mode as the default for normal agent use.
- Provide conservative agent-specific budgets for Codex, Claude Code, and default agents.
- Include mode, confidence, latency, token usage, and fallback metadata in every Context Package.
- Reserve Quality and Deep behavior without introducing remote calls, vector dependency, full scans, or maintenance jobs in the hot path.

## Non-goals

- This Spec does not introduce a vector database.
- This Spec does not allow remote LLM or remote embedding calls in P0 Context Guide hot paths.
- This Spec does not make Deep Mode automatic.
- This Spec does not require full Quality or Deep retrieval expansion in the first implementation if the configurable architecture is present.
- This Spec does not turn `AGENTS.md` or `CLAUDE.md` into full context packages.

## Scope

### Included

- Context Guide modes: `fast`, `standard`, `quality`, and `deep`.
- Runtime hints configuration for latency and token budgets.
- Agent-aware budget selection.
- Context confidence calculation and package metadata.
- Quality escalation rules and Deep explicit-request rule.
- Hot-path allowed and forbidden operations.
- Debug trace fields for mode, confidence, budget, and mode switching.

### Excluded

- Candidate lifecycle details, covered by `008-materialized-context-candidates.spec.md`.
- FTS indexing details, covered by `009-fts-indexing-and-retrieval.spec.md`.
- Debug trace storage and retention details, covered by `010-debug-trace-and-observability.spec.md`.
- Native Agent Entry file generation details, covered by `012-native-agent-entry.spec.md`.
- Release gate execution, covered by `014-release-and-test-gates.spec.md`.

## Dependencies

- Core project decisions: Clean Mode; managed state outside the user directory; controlled bootstrap; high-quality Context Guide; Materialized Context Candidates; local-first explainable retrieval without a P0 vector dependency; debug traces; branch-and-review Git workflow; English-first docs and comments.
- `003-managed-state-layout.spec.md`
- `007-context-guide-builder.spec.md`
- `008-materialized-context-candidates.spec.md`
- `009-fts-indexing-and-retrieval.spec.md`
- `010-debug-trace-and-observability.spec.md`
- `011-cli-user-flows.spec.md`
- `012-native-agent-entry.spec.md`

## Requirements

### Functional Requirements

FR-001: Context Guide must read latency and token budgets from runtime hints or built-in defaults rather than scattering hardcoded limits across the codebase.

FR-002: Runtime hints must support `fast`, `standard`, `quality`, and `deep` mode definitions.

FR-003: `standard` must be the default Context Guide mode unless runtime hints or CLI options explicitly choose another mode.

FR-004: `deep` must require an explicit `workroot context --deep` request and must never be selected silently during normal agent startup.

FR-005: Agent-specific budgets must exist for `codex`, `claude`, and `default`.

FR-006: Codex must use a conservative default Workroot Context Package hard limit no greater than 6000 tokens unless an explicit mode or budget override raises it within configured limits.

FR-007: Claude Code must be allowed a larger configured budget than Codex, while still avoiding unnecessary context noise.

FR-008: Every Context Package must include context mode, confidence, latency, token usage, fallback status, and low-confidence reasons when applicable.

FR-009: Confidence values must be `high`, `medium`, or `low`.

FR-010: Standard Mode may escalate to Quality Mode only when local confidence is insufficient and only using allowed local operations.

FR-011: Quality Mode must use a soft latency limit from configuration and return the best current context if the soft limit is exceeded.

FR-012: Fast, Standard, and Quality hot paths must not perform remote LLM calls, remote embedding calls, vector database searches, full user directory scans, full graph traversal, index rebuilds, or maintenance jobs.

FR-013: Debug trace must record context mode, mode switch reason, confidence, latency, token budget, used tokens, selected candidates, filtered candidates, filter reasons, and fallback details.

FR-014: CLI budget overrides such as `--target-tokens` and `--max-latency-ms` must be bounded by configured hard limits.

FR-015: If runtime hints are missing, Context Guide must use sensible built-in defaults that match this Spec.

### Non-functional Requirements

NFR-001: Context Guide must remain local-first and work offline.

NFR-002: The normal Standard Mode hot path should target under 1 second on healthy small Workroots.

NFR-003: Quality Mode should target a 2-3 second soft limit when local expansion is needed.

NFR-004: Context output must remain compact enough for agents that also read system instructions, user prompts, tool results, file contents, and repository instructions.

NFR-005: Mode and budget behavior must be deterministic enough for automated tests with fixture Workroots.

NFR-006: Runtime hints must be inspectable JSON stored in managed state only.

## Proposed Design

### Concepts

- Context mode: Retrieval depth and package budget profile for a Context Guide run.
- Fast Mode: Minimal startup context when the active task is clear and high-confidence candidates are available.
- Standard Mode: Default mode for normal Workroot agent use.
- Quality Mode: Local-only expansion when Standard Mode is low-confidence or incomplete.
- Deep Mode: Explicit deep context generation for architecture review, release review, major refactor, deep research, or cross-Workroot analysis.
- Agent budget: Target and hard token limits selected for a specific agent.
- Context confidence: Package-level signal that tells the agent how safe it is to act on the returned context.

### Data Model

Runtime hints file:

```json
{
  "contextGuide": {
    "defaultMode": "standard",
    "latency": {
      "targetMs": 1000,
      "standardSoftLimitMs": 2000,
      "qualitySoftLimitMs": 3000
    },
    "agentBudgets": {
      "codex": {
        "targetTokens": 4000,
        "hardTokenLimit": 6000
      },
      "claude": {
        "targetTokens": 5000,
        "hardTokenLimit": 8000
      },
      "default": {
        "targetTokens": 4000,
        "hardTokenLimit": 6000
      }
    },
    "modes": {
      "fast": {
        "targetTokens": 2500,
        "hardTokenLimit": 4000,
        "maxLatencyMs": 1000
      },
      "standard": {
        "targetTokens": 4000,
        "hardTokenLimit": 6000,
        "targetLatencyMs": 1000,
        "softLatencyMs": 2000
      },
      "quality": {
        "targetTokens": 8000,
        "hardTokenLimit": 12000,
        "softLatencyMs": 3000
      },
      "deep": {
        "requiresExplicitRequest": true,
        "targetTokens": 12000,
        "hardTokenLimit": 20000
      }
    },
    "hotPath": {
      "allowRemoteLlm": false,
      "allowRemoteEmbedding": false,
      "allowVectorSearch": false,
      "allowFullDirectoryScan": false,
      "allowIndexRebuild": false,
      "allowMaintenanceJob": false
    }
  }
}
```

Context metadata block:

```md
## Context Metadata

Mode: standard
Confidence: medium
Latency: 842ms
Tokens: 3820 / 6000
Fallback: no

Reason:
The active task was resolved, but some related asset summaries are stale.
```

Mode switch trace field:

```json
{
  "contextMode": "quality",
  "modeSwitchReason": "standard candidate set had low confidence and missing related decisions",
  "latencyMs": 2180
}
```

### File Layout

Runtime hints live in managed state:

```text
<stateDirectory>/state/runtime-hints.json
```

Context packages and traces continue to live in managed state:

```text
<stateDirectory>/context/
  packages/
  debug/
```

No mode configuration, context package, trace, cache, or runtime state is written to the user-selected directory by default.

### CLI / API

Required CLI:

```bash
workroot context --agent codex --cwd .
workroot context --agent claude --cwd .
workroot context --agent codex --cwd . --debug
```

Mode and budget CLI:

```bash
workroot context --mode fast
workroot context --mode standard
workroot context --mode quality
workroot context --deep
workroot context --target-tokens 4000
workroot context --max-latency-ms 3000
```

Implementation may treat Quality and Deep as reserved local modes in 0.9.529 if full expansion is not yet implemented, but it must preserve the explicit mode contract and trace the effective behavior. If Quality Mode only expands the local candidate budget, debug trace must label the behavior as `quality-budget-expansion`.

### Runtime Behavior

Mode selection flow:

1. Load runtime hints from managed state.
2. Fall back to built-in defaults if hints are missing.
3. Select agent budget from `agentBudgets`.
4. Select mode from CLI, `--deep`, runtime default, or built-in default.
5. Apply explicit token or latency overrides only within configured hard limits.
6. Build the Standard Mode candidate set from required rules, active task state, Materialized Context Candidates, candidate FTS matches, file FTS matches, and related one-hop graph signals.
7. Compute confidence from active task resolution, candidate count, candidate confidence, stale source state, FTS quality, and graph conflict/supersession signals.
8. Escalate to Quality Mode only when Standard confidence is insufficient and local time budget remains.
9. Build the Context Package with metadata.
10. Write debug trace showing mode, budget, confidence, and any fallback.

Quality escalation triggers include:

```text
active task is unclear
candidate confidence is low
important source candidates are stale
FTS results are too sparse or too noisy
graph indicates superseded or conflicting knowledge
task is architecture-heavy or review-heavy
user question asks why, source, relationship, architecture, or tradeoff
```

Hot-path allowed operations:

```text
read current state
read active task
query SQLite context_candidates
query SQLite FTS
query SQLite one-hop graph relations
query local time, domain, and task indexes
score and filter candidates
build context package
write debug trace
```

### Error Handling

- If runtime hints JSON is malformed, use built-in defaults and trace a configuration fallback.
- If an invalid mode is requested, fail with supported modes.
- If `--deep` is requested but Deep Mode is not fully implemented, return an actionable message or a reserved local Deep package; do not silently run Standard Mode without trace.
- If Quality Mode exceeds its soft limit, return the best current context, set confidence to `medium` or `low`, and suggest `workroot context --deep`.
- If a token override exceeds the configured hard limit, cap or reject it consistently and record the decision in debug trace.

### Security / Privacy

Mode expansion must not bypass safety policy. Fast, Standard, and Quality modes remain local-only and must not send data to remote services. Debug trace must not include full file bodies, secrets, credentials, or unbounded snippets.

### Compatibility

Existing 0.9.529 Workroots without `runtime-hints.json` must continue to work with built-in defaults. Migrations may create the runtime hints file, but Context Guide must not require it to exist before producing a safe package.

## Acceptance Criteria

AC-001:
Given no `runtime-hints.json`
When `workroot context --agent codex --cwd .` runs
Then Context Guide uses built-in Standard Mode defaults and returns a Context Package.

AC-002:
Given runtime hints with Codex and Claude budgets
When Context Guide runs for each agent
Then the selected target and hard token limits differ according to configuration.

AC-003:
Given Standard Mode has low-confidence candidates
When local Quality escalation is allowed within the configured soft limit
Then the debug trace records Quality Mode and the mode switch reason.

AC-004:
Given normal agent startup
When Context Guide runs without `--deep`
Then Deep Mode is not used.

AC-005:
Given `workroot context --deep`
When Deep Mode is requested
Then the explicit request is recorded and Standard Mode is not silently substituted without trace.

AC-006:
Given a Context Package
When it is inspected
Then it includes mode, confidence, latency, token usage, fallback status, and low-confidence reasons when applicable.

AC-007:
Given debug mode
When Context Guide runs
Then debug trace includes mode, mode switch reason, confidence, timing, token budget, selected candidates, filtered candidates, and fallbacks.

AC-008:
Given Clean Mode
When runtime hints, packages, and traces are written
Then all writes occur under managed state, not the user directory.

## Test Plan

### Unit Tests

- Test runtime hints loading with valid, missing, and malformed JSON.
- Test built-in default configuration.
- Test mode selection precedence.
- Test agent budget selection for Codex, Claude, and default agents.
- Test override bounds for target tokens and latency.
- Test confidence classification.
- Test Quality escalation trigger decisions.

### Integration Tests

- Run `workroot context --agent codex --cwd .` and verify Standard Mode metadata.
- Run `workroot context --agent claude --cwd .` and verify Claude budget metadata.
- Run `workroot context --mode quality --debug` and verify trace mode fields.
- Run `workroot context --deep` and verify explicit Deep handling.
- Verify Context Guide does not perform remote calls, full directory scans, index rebuilds, or maintenance jobs in Fast, Standard, or Quality modes.

### Manual Verification

- Inspect a generated Context Package for usefulness, compactness, and confidence messaging.
- Inspect `context/debug/latest.json` for mode switch and budget details.
- Confirm `AGENTS.md` and `CLAUDE.md` remain short entry files rather than full context packages.
- Confirm no mode-related files are written to the user directory.

## Migration / Rollback

Migration may add `<stateDirectory>/state/runtime-hints.json` with default values. Rollback may delete the generated runtime hints file if no user customizations exist. If user customizations exist, rollback must preserve or back up the file because it is user-configurable managed state.

## Observability / Debugging

Debug trace must include:

- context mode;
- requested mode;
- effective mode;
- mode switch reason;
- confidence;
- confidence reasons;
- target tokens;
- hard token limit;
- used tokens;
- latency and timing spans;
- agent budget source;
- selected and filtered candidates;
- fallback decisions;
- Quality soft-limit status;
- Deep explicit-request status.

Doctor should validate runtime hints readability and report malformed configuration with an actionable path.

## Task Breakdown

T1: Add runtime hints schema
- Change: Define Context Guide mode, latency, and budget configuration with built-in defaults.
- Files likely affected: context configuration module, state initialization, tests.
- Verification: Unit tests for default and file-backed configuration.

T2: Add mode and budget resolution
- Change: Resolve requested mode, effective mode, agent budget, token override, and latency override.
- Files likely affected: context module, CLI module.
- Verification: Unit tests for mode precedence and budget bounds.

T3: Add package metadata
- Change: Render mode, confidence, latency, token usage, fallback, and low-confidence reasons into every Context Package.
- Files likely affected: context package builder.
- Verification: Snapshot or string tests for metadata block.

T4: Add confidence and Quality escalation
- Change: Compute confidence and optionally expand to local Quality Mode when Standard Mode is insufficient.
- Files likely affected: Context Guide arbiter and scoring logic.
- Verification: Fixture tests for high, medium, low, and escalated contexts.

T5: Add CLI flags
- Change: Support `--mode`, `--deep`, `--target-tokens`, and `--max-latency-ms`.
- Files likely affected: CLI module.
- Verification: CLI integration tests for flags and invalid values.

T6: Extend debug trace and doctor
- Change: Record mode, confidence, budget, mode switch, and runtime hints diagnostics.
- Files likely affected: debug trace module, doctor module.
- Verification: Debug JSON validation and doctor malformed-config fixture.

## Risks

- Quality Mode can become a hidden slow path if escalation is not bounded.
- Token estimates can diverge from actual agent tokenizer behavior.
- Confidence can be over-trusted if reasons are not visible.
- Runtime hints can become too broad if unrelated configuration is added prematurely.

## Open Questions

None.
