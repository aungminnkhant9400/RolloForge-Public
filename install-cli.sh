#!/bin/bash
# Install Forge CLI to system PATH

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${HOME}/.local/bin"

# Create install directory if needed
mkdir -p "$INSTALL_DIR"

# Create symlink
if [ -L "$INSTALL_DIR/forge" ]; then
    rm "$INSTALL_DIR/forge"
fi

ln -sf "$SCRIPT_DIR/forge" "$INSTALL_DIR/forge"

echo "✓ Forge CLI installed to $INSTALL_DIR/forge"

# Check if install dir is in PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo ""
    echo "⚠️  $INSTALL_DIR is not in your PATH"
    echo "   Add this to your shell profile:"
    echo "   export PATH=\"$INSTALL_DIR:\$PATH\""
fi

echo ""
echo "Test with: forge --help"
