#!/bin/bash
#
# Install git hooks for RolloForge
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "🔧 Installing git hooks..."

# Create hooks directory if needed
mkdir -p "$HOOKS_DIR"

# Install pre-commit hook
if [ -f "$SCRIPT_DIR/pre-commit.sh" ]; then
    cp "$SCRIPT_DIR/pre-commit.sh" "$HOOKS_DIR/pre-commit"
    chmod +x "$HOOKS_DIR/pre-commit"
    echo "✅ Installed: pre-commit"
else
    echo "❌ pre-commit.sh not found"
    exit 1
fi

# Install pre-push hook (deploy check)
if [ -f "$SCRIPT_DIR/deploy-check.sh" ]; then
    cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash
# Run deploy check before push
echo "🔍 Running pre-push checks..."
./scripts/deploy-check.sh
EOF
    chmod +x "$HOOKS_DIR/pre-push"
    echo "✅ Installed: pre-push"
fi

echo ""
echo "Git hooks installed successfully!"
echo ""
echo "Hooks active:"
ls -la "$HOOKS_DIR/" | grep -E "(pre-commit|pre-push)" || true
