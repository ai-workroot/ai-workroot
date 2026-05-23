#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="${AI_WORKROOT_DEV_VENV:-$PROJECT_ROOT/.venv}"

cd "$PROJECT_ROOT"

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
. "$VENV_DIR/bin/activate"

python3 -m pip install --upgrade pip
python3 -m pip install -e ".[dev]"

echo "AI Workroot development environment is ready."
echo "Activate it with: . \"$VENV_DIR/bin/activate\""
