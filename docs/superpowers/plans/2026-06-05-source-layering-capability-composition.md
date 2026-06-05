# Source Layering and Capability Composition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Move AI Workroot to the approved entrypoints/protocol/capabilities/state/shared package layout and move protocol projections into capability composition.

**Architecture:** Use direct package moves with no compatibility wrappers. Keep `commands/` as the use-case adapter layer, keep `protocol/` as Agent Protocol control, move cross-capability projection logic into `capabilities/composition/projections.py`, and keep each capability's `model.py` and `operations.py` split.

**Tech Stack:** Python 3.9+, argparse, sqlite3, importlib.resources, unittest, shell validation scripts.

**Execution Status:** Completed on local `main`. Verified with `ruff format`, `scripts/dev/validate-release.sh`, and full `python3 -m unittest discover -s tests -v`.

---

## File Structure

- Create: `src/ai_workroot/entrypoints/`
- Move: `src/ai_workroot/cli/` to `src/ai_workroot/entrypoints/cli/`
- Move: `src/ai_workroot/agent_entry/` to `src/ai_workroot/entrypoints/native_agent/`
- Move: `src/ai_workroot/templates/native_agent_entry/` to `src/ai_workroot/entrypoints/native_agent/templates/`
- Create: `src/ai_workroot/capabilities/`
- Move capability packages under `src/ai_workroot/capabilities/`
- Rename: `src/ai_workroot/diagnostics/` to `src/ai_workroot/capabilities/system_health/`
- Move: `src/ai_workroot/protocol/projections.py` to `src/ai_workroot/capabilities/composition/projections.py`
- Modify imports across `src/` and `tests/`
- Modify source layout contract tests and public docs
- Modify `pyproject.toml` script entrypoint and package-data path

### Task 1: Move Packages

**Files:**
- Move source package directories under `src/ai_workroot/`

- [x] **Step 1: Create new layer directories**

Run:

```bash
mkdir -p src/ai_workroot/entrypoints src/ai_workroot/capabilities/composition
```

Expected: directories exist.

- [x] **Step 2: Move entrypoint packages**

Run:

```bash
git mv src/ai_workroot/cli src/ai_workroot/entrypoints/cli
git mv src/ai_workroot/agent_entry src/ai_workroot/entrypoints/native_agent
mkdir -p src/ai_workroot/entrypoints/native_agent/templates
git mv src/ai_workroot/templates/native_agent_entry/* src/ai_workroot/entrypoints/native_agent/templates/
git rm src/ai_workroot/templates/__init__.py
rmdir src/ai_workroot/templates/native_agent_entry src/ai_workroot/templates
```

Expected: old `cli/`, `agent_entry/`, and `templates/` directories no longer exist.

- [x] **Step 3: Move capability packages**

Run:

```bash
git mv src/ai_workroot/work src/ai_workroot/capabilities/work
git mv src/ai_workroot/assets src/ai_workroot/capabilities/assets
git mv src/ai_workroot/handoff src/ai_workroot/capabilities/handoff
git mv src/ai_workroot/relationships src/ai_workroot/capabilities/relationships
git mv src/ai_workroot/retrieval src/ai_workroot/capabilities/retrieval
git mv src/ai_workroot/context src/ai_workroot/capabilities/context
git mv src/ai_workroot/release src/ai_workroot/capabilities/release
git mv src/ai_workroot/diagnostics src/ai_workroot/capabilities/system_health
```

Expected: capabilities live under `src/ai_workroot/capabilities/`.

- [x] **Step 4: Move protocol projection implementation**

Run:

```bash
git mv src/ai_workroot/protocol/projections.py src/ai_workroot/capabilities/composition/projections.py
touch src/ai_workroot/capabilities/__init__.py
touch src/ai_workroot/capabilities/composition/__init__.py
```

Expected: projection implementation lives under composition.

### Task 2: Update Imports and Entrypoints

**Files:**
- Modify: `src/ai_workroot/**/*.py`
- Modify: `tests/**/*.py`
- Modify: `pyproject.toml`

- [x] **Step 1: Mechanically rewrite package imports**

Run import rewrites for these package prefixes:

```text
ai_workroot.cli -> ai_workroot.entrypoints.cli
ai_workroot.agent_entry -> ai_workroot.entrypoints.native_agent
ai_workroot.templates.native_agent_entry -> ai_workroot.entrypoints.native_agent.templates
ai_workroot.work -> ai_workroot.capabilities.work
ai_workroot.assets -> ai_workroot.capabilities.assets
ai_workroot.handoff -> ai_workroot.capabilities.handoff
ai_workroot.relationships -> ai_workroot.capabilities.relationships
ai_workroot.retrieval -> ai_workroot.capabilities.retrieval
ai_workroot.context -> ai_workroot.capabilities.context
ai_workroot.release -> ai_workroot.capabilities.release
ai_workroot.diagnostics -> ai_workroot.capabilities.system_health
ai_workroot.protocol.projections -> ai_workroot.capabilities.composition.projections
```

Expected: `rg "ai_workroot\\.(cli|agent_entry|templates|work|assets|handoff|relationships|retrieval|context|release|diagnostics)" src tests` finds no active import paths.

- [x] **Step 2: Update script and template package config**

Change `pyproject.toml`:

```toml
[project.scripts]
workroot = "ai_workroot.entrypoints.cli.main:main"

[tool.setuptools.package-data]
"ai_workroot.entrypoints.native_agent.templates" = ["*.template"]
```

Expected: console script points at the new CLI path and native templates are packaged from the new location.

- [x] **Step 3: Update Native Agent template package constant**

Change `src/ai_workroot/entrypoints/native_agent/native.py`:

```python
TEMPLATE_PACKAGE = "ai_workroot.entrypoints.native_agent.templates"
```

Expected: `render_native_agent_entry("codex")` reads templates from the new package path.

- [x] **Step 4: Update module launcher**

Change `src/ai_workroot/__main__.py`:

```python
from ai_workroot.entrypoints.cli.main import main
```

Expected: `python3 -m ai_workroot --version` can load the new CLI module.

### Task 3: Remove Context-To-Protocol Dependency

**Files:**
- Modify: `src/ai_workroot/capabilities/context/builder.py`
- Modify: `src/ai_workroot/commands/build_context.py`

- [x] **Step 1: Add optional startup guidance input to ContextRequest**

In `ContextRequest`, add:

```python
startup_guidance: str = ""
```

Expected: context builder can receive protocol guidance instead of importing protocol.

- [x] **Step 2: Remove protocol imports from context builder**

Remove imports of:

```python
from ai_workroot.protocol.controller import startup_context
from ai_workroot.protocol.model import PROTOCOL_VERSION
from ai_workroot.protocol.packet import render_private_packet_markdown
```

Use `request.startup_guidance` where builder currently constructs protocol startup guidance.

Expected: `capabilities/context` has no `ai_workroot.protocol` imports.

- [x] **Step 3: Build startup guidance in the command layer**

In `commands/build_context.py`, import protocol helpers and pass rendered startup guidance into `ContextRequest`.

Expected: protocol guidance remains in `workroot context`, but context capability no longer depends on protocol.

### Task 4: Update Architecture Contract Tests

**Files:**
- Modify: `tests/unit/test_import_boundaries.py`
- Modify: `tests/unit/test_source_layout_imports.py`
- Modify: `tests/contracts/test_current_docs_contract.py`
- Modify: `tests/contracts/test_release_surface_contract.py`
- Modify: `tests/contracts/test_dependency_policy_contract.py`
- Modify: `tests/smoke/test_clean_release_validator.py`

- [x] **Step 1: Update required package directories**

Expected required source packages:

```python
required = [
    "capabilities",
    "commands",
    "entrypoints",
    "protocol",
    "shared",
    "state",
]
```

Expected capability subpackages:

```python
required_capabilities = [
    "assets",
    "composition",
    "context",
    "handoff",
    "relationships",
    "release",
    "retrieval",
    "system_health",
    "work",
]
```

- [x] **Step 2: Update dependency graph policy**

Expected primary graph:

```text
entrypoints -> commands
commands -> protocol / capabilities / state
protocol -> capabilities / state
capabilities -> state / shared
state -> shared
shared -> stdlib only
```

Expected no capability imports `ai_workroot.protocol`.

- [x] **Step 3: Update source import smoke tests**

Replace old imports with new paths such as:

```python
from ai_workroot.entrypoints.native_agent import native
from ai_workroot.capabilities.system_health import doctor
from ai_workroot.capabilities.work import operations as work_operations
```

Expected: source layout import tests verify new public module paths only.

### Task 5: Update Docs

**Files:**
- Modify current public docs and release docs that describe source structure

- [x] **Step 1: Update public architecture docs**

Update source tree references to show:

```text
entrypoints/
commands/
protocol/
capabilities/
state/
shared/
```

Expected: no public current doc still presents `agent_entry/`, `diagnostics/`, or capability packages as top-level source packages.

- [x] **Step 2: Update release and validation docs**

Update release checklist and acceptance checklist references to `capabilities/system_health` and `entrypoints/native_agent`.

Expected: current docs contract passes.

### Task 6: Validate

**Files:**
- No production file changes.

- [x] **Step 1: Run focused boundary tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_import_boundaries tests.unit.test_source_layout_imports -v
```

Expected: all tests pass.

- [x] **Step 2: Run contract tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.contracts.test_current_docs_contract tests.contracts.test_release_surface_contract tests.contracts.test_dependency_policy_contract -v
```

Expected: all tests pass.

- [x] **Step 3: Run release validation**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" PYTHONPATH=src scripts/dev/validate-release.sh
```

Expected: release validation passes.

- [x] **Step 4: Run full unittest suite**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: full suite passes.
