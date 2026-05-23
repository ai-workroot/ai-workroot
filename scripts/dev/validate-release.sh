#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

run_ruff() {
  if python3 -m ruff --version >/dev/null 2>&1; then
    python3 -m ruff "$@"
  else
    echo "ruff is required for release validation." >&2
    echo "Run scripts/dev/setup-dev.sh, then re-run this command from the activated development environment." >&2
    return 1
  fi
}

python3 -m py_compile $(find src scripts -name "*.py")
run_ruff format --check src scripts tests
run_ruff check src scripts tests
bash -n install/unix/install.sh scripts/dev/bootstrap-dev.sh scripts/dev/export-review-zip.sh scripts/dev/validate-release.sh
PYTHONPATH="$PROJECT_ROOT/src${PYTHONPATH:+:${PYTHONPATH}}" python3 -m ai_workroot doctor --release
git diff --check

echo "Clean Workroot release validation passed"
