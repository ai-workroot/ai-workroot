#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

python3 -m py_compile $(find src -name "*.py")
python3 -m py_compile scripts/*.py
bash -n install/unix/install.sh scripts/install.sh scripts/bootstrap-dev.sh
PYTHONPATH="$PROJECT_ROOT/src${PYTHONPATH:+:${PYTHONPATH}}" python3 -m ai_workroot doctor --release
git diff --check

echo "Clean Workroot release validation passed"
