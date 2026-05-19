#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${AI_WORKROOT_INSTALL_DIR:-$HOME/.local/bin}"
SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

mkdir -p "$INSTALL_DIR"
cat > "$INSTALL_DIR/workroot" <<EOF
#!/usr/bin/env bash
python3 "$SOURCE_DIR/scripts/workroot_cli.py" "\$@"
EOF
chmod +x "$INSTALL_DIR/workroot"

echo "Installed workroot CLI to $INSTALL_DIR/workroot"
echo "Run: workroot init --name <name> --directory <directory> --no-native-agent-entry"
