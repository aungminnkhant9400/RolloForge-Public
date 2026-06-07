#!/bin/bash
# Install security tools and pre-commit hooks for RolloForge

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     RolloForge Security Setup                          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Install Python security tools
echo -e "${BLUE}▶ Installing Python security tools...${NC}"
pip install -q pip-audit bandit safety || {
    echo -e "${YELLOW}⚠ Some Python tools failed to install${NC}"
}

# Install pre-commit hook
echo ""
echo -e "${BLUE}▶ Installing pre-commit hook...${NC}"

if [ -d "$PROJECT_ROOT/.git" ]; then
    if [ -f "$PROJECT_ROOT/.githooks/pre-commit" ]; then
        cp "$PROJECT_ROOT/.githooks/pre-commit" "$PROJECT_ROOT/.git/hooks/pre-commit"
        chmod +x "$PROJECT_ROOT/.git/hooks/pre-commit"
        echo -e "${GREEN}✓ Pre-commit hook installed${NC}"
    else
        echo -e "${YELLOW}⚠ Pre-commit hook not found in .githooks/${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Not a git repository${NC}"
fi

# Configure git to use .githooks directory
echo ""
echo -e "${BLUE}▶ Configuring git hooks path...${NC}"
cd "$PROJECT_ROOT"
git config core.hooksPath .githooks 2>/dev/null || {
    echo -e "${YELLOW}⚠ Could not set hooks path automatically${NC}"
    echo "  Run manually: git config core.hooksPath .githooks"
}

echo ""
echo -e "${GREEN}✓ Security setup complete!${NC}"
echo ""
echo "Available commands:"
echo "  ./scripts/security-audit.sh    Run full security audit"
echo "  pip-audit --help               Python dependency scanner help"
echo "  bandit --help                  Python security linter help"
echo "  npm audit --help               Node.js dependency scanner help"
echo ""
echo "Pre-commit hook will run automatically on each commit."
