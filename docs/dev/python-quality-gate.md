# Python Quality Gate

AI Workroot uses a thin Python quality gate for active source files.

The goal is not to enforce a heavy style system. The goal is to keep source
readable on GitHub, make reviews stable, and catch high-signal Python mistakes
before release.

## Scope

The active gate covers:

- `src/`
- `scripts/`
- `tests/`

Historical archives under `docs/history/` are intentionally outside the active
gate.

## Commands

Prepare the development environment explicitly:

```bash
scripts/dev/setup-dev.sh
. .venv/bin/activate
```

Format check:

```bash
python3 -m ruff format --check src scripts tests
```

Lint check:

```bash
python3 -m ruff check src scripts tests
```

`ruff format --check` verifies that files already match the formatter. It does
not modify files. To apply formatting locally, run:

```bash
python3 -m ruff format src scripts tests
```

## Rules

The first gate intentionally enables only:

- `E9`: syntax-level Python errors.
- `F`: Pyflakes checks such as undefined names and unused imports.

This keeps the gate useful without turning the early Clean Workroot phase into a
large style cleanup.

## References

This follows the same general direction as mature Python projects that use Ruff
as a fast quality gate. Hermes uses Ruff in development and CI, but keeps its
blocking rule set narrow. AI Workroot starts with the same conservative posture:
establish the gate first, then expand rules only when the project benefits from
the added strictness.

Ruff is a development dependency only. It is not required by ordinary Clean
Workroot users and is not part of the product runtime dependency set.

Release validation checks for Ruff but does not install it implicitly. If the
tool is missing, run `scripts/dev/setup-dev.sh` and re-run validation from the
activated development environment.
