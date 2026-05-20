#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${AI_WORKROOT_INSTALL_DIR:-$HOME/.local/bin}"
SOURCE_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
COMMAND_PATH="$INSTALL_DIR/workroot"

usage() {
  cat <<'EOF'
AI Workroot CLI wrapper installer

Usage:
  install/unix/install.sh [--dry-run]
  install/unix/install.sh --help

Installs a user-level `workroot` wrapper for the Clean Workroot package entrypoint.
This installer does not run first-use setup and does not initialize a Workroot.
EOF
}

case "${1:-}" in
  -h|--help)
    usage
    exit 0
    ;;
  --dry-run)
    echo "AI Workroot CLI wrapper installer"
    echo "installs the Clean Workroot package entrypoint"
    echo "would install workroot CLI wrapper to $COMMAND_PATH"
    echo "would run: workroot init --name <name> --directory <directory> --no-native-agent-entry"
    exit 0
    ;;
  "")
    ;;
  *)
    echo "unknown option: $1" >&2
    usage >&2
    exit 2
    ;;
esac

mkdir -p "$INSTALL_DIR"
cat > "$COMMAND_PATH" <<EOF
#!/usr/bin/env bash
PYTHONPATH="$SOURCE_DIR/src\${PYTHONPATH:+:\${PYTHONPATH}}" python3 -m ai_workroot "\$@"
EOF
chmod +x "$COMMAND_PATH"

echo "Installed workroot CLI to $COMMAND_PATH"
echo "Run: workroot init --name <name> --directory <directory> --no-native-agent-entry"
