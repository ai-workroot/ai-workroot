#!/usr/bin/env bash
set -euo pipefail
python3 "$(dirname "$0")/workroot_cli.py" bootstrap-dev "$@"
