# Agent Protocol v1.1 Discovery Shorthand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Agent-friendly commit shorthand and stronger protocol guidance so models can discover the Workroot `sync -> commit` loop from Agent Entry and Control Capsule.

**Architecture:** Keep the domain and protocol controller unchanged. The shorthand lives only in the existing CLI/command adapter boundary, where it builds canonical CommitRequest dictionaries and passes them to `protocol.controller.commit`. Agent Entry and Control Capsule remain model-facing guidance, not persisted facts.

**Tech Stack:** Python argparse, unittest, SQLite-backed Workroot protocol projections, existing E2E harness.

---

## File Structure

- Modify `src/ai_workroot/cli/main.py`: allow `agent commit` to accept either `--request` or shorthand fields.
- Modify `src/ai_workroot/commands/agent_exchange.py`: build canonical commit requests from shorthand input.
- Modify `src/ai_workroot/context/control.py`: include explicit shorthand command guidance in Control Capsule.
- Modify `src/ai_workroot/templates/native_agent_entry/AGENTS.md.template` and `CLAUDE.md.template`: keep short but mention private control guidance and non-blocking behavior.
- Modify `tests/unit/test_agent_exchange_command.py`: shorthand request construction and CLI behavior.
- Modify `tests/unit/test_protocol_controller.py` or integration tests: shorthand commits project task/run/summary/handoff facts.
- Modify `tests/contracts/test_e2e_opt_in_policy.py` and `tests/e2e/harness.py` only if Native Agent Entry line-count expectations need to change.
- Modify `tests/e2e/live_protocol.py` and `tests/e2e/live_protocol_cases.py`: live report aggregation and discovery classification.

## Task 1: Shorthand Commit Request Builder

- [x] Write unit tests showing intent/progress/handoff shorthand produces canonical commit requests with deterministic event IDs and idempotency keys.
- [x] Implement `build_commit_request_from_shorthand` in `src/ai_workroot/commands/agent_exchange.py`.
- [x] Verify focused tests pass.

## Task 2: CLI Wiring

- [x] Write CLI tests showing `workroot agent commit --kind intent ...` returns JSON and creates task/run facts.
- [x] Update `src/ai_workroot/cli/main.py` parser and dispatch.
- [x] Keep `--request` behavior unchanged.

## Task 3: Control Capsule and Agent Entry

- [x] Add tests for Control Capsule containing sync and shorthand commit examples.
- [x] Add tests that Native Agent Entry remains short, safe, and includes the context launcher command.
- [x] Update templates and control text.

## Task 4: Live E2E Report and Discovery

- [x] Write tests that live protocol summary aggregation preserves multiple case results.
- [x] Add `discovered_sync` classification when command log includes `agent sync` but not `agent commit`.
- [x] Update discovery prompt/control guidance to avoid explicit JSON examples but allow shorthand command discovery.
- [x] Preserve usable paths for quarantined live protocol report artifacts.

## Task 5: Verification

- [x] Run `PYTHONPATH=src python3 -m unittest tests.unit.test_agent_exchange_command -v`.
- [x] Run `PYTHONPATH=src python3 -m unittest tests.e2e.live_protocol_cases -v`.
- [x] Run `PYTHONPATH=src python3 -m unittest discover -s tests -q`.
- [x] Run `PATH="$PWD/.venv/bin:$PATH" scripts/dev/validate-release.sh`.
- [x] Run live protocol E2E with explicit opt-in.
