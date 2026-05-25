# Phase 1 Command Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add application command entrypoints and make the CLI delegate through them while preserving CLI output and exit behavior.

**Architecture:** `cli/main.py` keeps argparse and terminal formatting. `commands/*` owns application command functions and initially delegates to existing implementation modules.

**Tech Stack:** Python 3.9 standard library, `argparse`, `unittest`.

---

## Files

- Create: `src/ai_workroot/commands/__init__.py`
- Create: `src/ai_workroot/commands/init_workroot.py`
- Create: `src/ai_workroot/commands/list_workroots.py`
- Create: `src/ai_workroot/commands/show_status.py`
- Create: `src/ai_workroot/commands/build_context.py`
- Create: `src/ai_workroot/commands/run_doctor.py`
- Create: `src/ai_workroot/commands/bootstrap_dev.py`
- Modify: `src/ai_workroot/cli/main.py`
- Modify: `tests/unit/test_import_boundaries.py`
- Create: `tests/unit/test_commands.py`

## Tasks

### Task 1: Command Package Contract

- [x] Write `tests/unit/test_commands.py` asserting each command module exposes the expected callable.
- [x] Run `PYTHONPATH=src python3 -m unittest tests.unit.test_commands` and verify it fails because `ai_workroot.commands` does not exist.
- [x] Add command modules as thin wrappers.
- [x] Re-run the command test and verify it passes.

### Task 2: CLI Delegation

- [x] Change `src/ai_workroot/cli/main.py` imports from `runtime.*` to `commands.*`.
- [x] Preserve existing argparse options, stdout/stderr text, and return codes.
- [x] Run:

```bash
PYTHONPATH=src python3 -m unittest tests.smoke.test_cli_discovery tests.smoke.test_package_entrypoint
PYTHONPATH=src python3 -m ai_workroot --help
PYTHONPATH=src python3 -m ai_workroot --version
```

Expected: pass, help command list unchanged, version unchanged.

### Task 3: Import Boundary Update

- [x] Update `tests/unit/test_import_boundaries.py` required package list to include `commands`.
- [x] Add a rule that `cli/` may import `ai_workroot.commands` but must not import `ai_workroot.storage`, `ai_workroot.indexing`, `ai_workroot.state`, or `ai_workroot.retrieval`.
- [x] Run `PYTHONPATH=src python3 -m unittest tests.unit.test_import_boundaries`.

Expected: pass.

