#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: scripts/dev/export-review-zip.sh <output.zip>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_PATH="$1"

mkdir -p "$(dirname "$OUTPUT_PATH")"
cd "$PROJECT_ROOT"

git archive --format=zip --output="$OUTPUT_PATH" HEAD
echo "Review source archive written: $OUTPUT_PATH"
