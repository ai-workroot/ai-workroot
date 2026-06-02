#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

check_active_source_ascii() {
  python3 - <<'PY'
from pathlib import Path
import sys

root = Path.cwd()
violations = []
for base in (root / "src", root / "scripts"):
    for path in base.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if any(ord(char) > 127 for char in line):
                violations.append(f"{path.relative_to(root)}:{line_number}")

if violations:
    sys.stderr.write("Active Python source must be ASCII-only:\n")
    sys.stderr.write("\n".join(violations) + "\n")
    raise SystemExit(1)
PY
}

check_active_source_fixture_leakage() {
  python3 - <<'PY'
from pathlib import Path
import re
import sys

root = Path.cwd()
markers_path = root / "tests" / "fixtures" / "active_source_fixture_markers.txt"


def marker_pattern(marker):
    words = [word for word in re.split(r"[\s_-]+", marker.lower().strip()) if word]
    return re.compile(r"(?<![a-z])" + r"[ _-]+".join(re.escape(word) for word in words) + r"(?![a-z])")


blocked_patterns = [
    (marker, marker_pattern(marker))
    for marker in markers_path.read_text(encoding="utf-8").splitlines()
    if marker.strip() and not marker.lstrip().startswith("#")
]
violations = []
for base in (root / "src", root / "scripts"):
    for path in base.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            lowered = line.lower()
            for term, pattern in blocked_patterns:
                if pattern.search(lowered):
                    violations.append(f"{path.relative_to(root)}:{line_number}: {term}")

if violations:
    sys.stderr.write("E2E fixture or business scenario text leaked into active source:\n")
    sys.stderr.write("\n".join(violations) + "\n")
    raise SystemExit(1)
PY
}

run_ruff() {
  if command -v ruff >/dev/null 2>&1; then
    ruff "$@"
  elif python3 -m ruff --version >/dev/null 2>&1; then
    python3 -m ruff "$@"
  else
    echo "ruff is required for release validation." >&2
    echo "Run scripts/dev/setup-dev.sh, then re-run this command from the activated development environment." >&2
    return 1
  fi
}

check_active_source_ascii
check_active_source_fixture_leakage
python3 -m py_compile $(find src scripts -name "*.py")
run_ruff format --check src scripts tests
run_ruff check src scripts tests
bash -n install/unix/install.sh scripts/dev/bootstrap-dev.sh scripts/dev/export-review-zip.sh scripts/dev/validate-release.sh
PYTHONPATH="$PROJECT_ROOT/src${PYTHONPATH:+:${PYTHONPATH}}" python3 -m ai_workroot doctor --release
git diff --check

echo "Clean Workroot release validation passed"
