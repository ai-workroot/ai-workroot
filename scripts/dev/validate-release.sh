#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

python3 -m py_compile $(find src scripts -name "*.py")
bash -n install/unix/install.sh scripts/compat/install.sh scripts/dev/bootstrap-dev.sh scripts/dev/export-review-zip.sh
PYTHONPATH="$PROJECT_ROOT/src${PYTHONPATH:+:${PYTHONPATH}}" python3 -m ai_workroot doctor --release
git diff --check

echo "Clean Workroot release validation passed"
