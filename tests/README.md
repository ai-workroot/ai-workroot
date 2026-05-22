# AI Workroot Test Layout

Tests are grouped by execution purpose. Keep test modules inside one of these directories; the `tests/` root should not contain loose `test_*.py` files.

## Directories

- `unit/`: fast single-module tests that do not invoke the real CLI as a subprocess.
- `integration/`: cross-module flows, temporary `AI_WORKROOT_HOME`, state storage, and registry behavior.
- `smoke/`: release/user entrypoint checks that exercise the packaged CLI or validation commands.
- `negative/`: forbidden behavior, safety, leakage, and protection tests.
- `contracts/`: architecture, repository surface, release gate, and opt-in policy tests.
- `e2e/`: explicit opt-in long-form scenarios. These are not included in default unittest discovery.
- `support/`: Python helper code shared by tests. Helpers are not tests.
- `fixtures/`: static sample data only.

## Common Commands

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/unit -v
PYTHONPATH=src python3 -m unittest discover -s tests/integration -v
PYTHONPATH=src python3 -m unittest discover -s tests/smoke -v
PYTHONPATH=src python3 -m unittest discover -s tests/negative -v
PYTHONPATH=src python3 -m unittest discover -s tests/contracts -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

E2E scenarios must be run explicitly:

```bash
AI_WORKROOT_RUN_E2E=1 PYTHONPATH=src python3 -m tests.e2e.runner --list
```

E2E harnesses create preserved sandbox run roots under `~/tmp/ai-workroot-e2e-sandboxes` by default. They enable Context Control diagnostic logging in the sandbox `AI_WORKROOT_HOME/config.json` so each `workroot context` request writes `workroots/<workroot_id>/logs/context-requests.jsonl` with token estimates, budget source, retrieval/trace summaries, and the rendered Context Package.

The current E2E suites exercise the real package CLI, SQLite state, retrieval, release filtering, and Context Control. They do not call remote LLM APIs. Live-agent E2E must remain a separate explicit flow with sandboxed `HOME`, sandboxed `AI_WORKROOT_HOME`, no real repository cwd, and separately provided test credentials.
