#!/bin/bash
# Test script for security automation
# Validates that all security tools are installed and configured

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Security Automation Test Suite                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: Check security files exist
echo -e "${BLUE}Test 1: Security Files Exist${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
FILES=(
    "SECURITY.md"
    "requirements-security.txt"
    "scripts/security-audit.sh"
    "scripts/install-security.sh"
    ".githooks/pre-commit"
    ".github/workflows/security-audit.yml"
)

for file in "${FILES[@]}"; do
    if [ -f "$PROJECT_ROOT/$file" ]; then
        echo -e "  ${GREEN}✓ $file${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${RED}✗ $file missing${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
done

echo ""

# Test 2: Check executable permissions
echo -e "${BLUE}Test 2: Executable Scripts${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
SCRIPTS=(
    "scripts/security-audit.sh"
    "scripts/install-security.sh"
    ".githooks/pre-commit"
)

for script in "${SCRIPTS[@]}"; do
    if [ -x "$PROJECT_ROOT/$script" ]; then
        echo -e "  ${GREEN}✓ $script is executable${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${YELLOW}⚠ $script not executable${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
done

echo ""

# Test 3: Check Python security tools
echo -e "${BLUE}Test 3: Python Security Tools${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "$PROJECT_ROOT/.venv/bin/pip-audit" ]; then
    VERSION=$($PROJECT_ROOT/.venv/bin/pip-audit --version 2>/dev/null)
    echo -e "  ${GREEN}✓ pip-audit installed ($VERSION)${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "  ${YELLOW}⚠ pip-audit not in .venv${NC}"
    echo "    Install with: .venv/bin/pip install pip-audit"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

if [ -f "$PROJECT_ROOT/.venv/bin/bandit" ]; then
    VERSION=$($PROJECT_ROOT/.venv/bin/bandit --version 2>&1 | head -1)
    echo -e "  ${GREEN}✓ bandit installed ($VERSION)${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "  ${YELLOW}⚠ bandit not in .venv${NC}"
    echo "    Install with: .venv/bin/pip install bandit"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

echo ""

# Test 4: Check Node.js tools
echo -e "${BLUE}Test 4: Node.js Tools${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v npm > /dev/null 2>&1; then
    VERSION=$(npm --version)
    echo -e "  ${GREEN}✓ npm installed (v$VERSION)${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    
    if [ -f "$PROJECT_ROOT/web/package.json" ]; then
        echo -e "  ${GREEN}✓ web/package.json exists${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${YELLOW}⚠ web/package.json not found${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
else
    echo -e "  ${YELLOW}⚠ npm not found${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

echo ""

# Test 5: Check GitHub Actions workflow
echo -e "${BLUE}Test 5: GitHub Actions Workflow${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "$PROJECT_ROOT/.github/workflows/security-audit.yml" ]; then
    if grep -q "pip-audit" "$PROJECT_ROOT/.github/workflows/security-audit.yml"; then
        echo -e "  ${GREEN}✓ Workflow includes pip-audit${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${RED}✗ Workflow missing pip-audit${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    
    if grep -q "npm audit" "$PROJECT_ROOT/.github/workflows/security-audit.yml"; then
        echo -e "  ${GREEN}✓ Workflow includes npm audit${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${RED}✗ Workflow missing npm audit${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    
    if grep -q "bandit" "$PROJECT_ROOT/.github/workflows/security-audit.yml"; then
        echo -e "  ${GREEN}✓ Workflow includes bandit${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${RED}✗ Workflow missing bandit${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
else
    echo -e "  ${RED}✗ Security workflow not found${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 3))
fi

echo ""

# Test 6: Check pre-commit hook
echo -e "${BLUE}Test 6: Pre-commit Hook${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "$PROJECT_ROOT/.githooks/pre-commit" ]; then
    if grep -q "security-audit.sh" "$PROJECT_ROOT/.githooks/pre-commit"; then
        echo -e "  ${GREEN}✓ Pre-commit calls security-audit.sh${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${RED}✗ Pre-commit doesn't call security-audit.sh${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
else
    echo -e "  ${RED}✗ Pre-commit hook not found${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

echo ""

# Test 7: Documentation check
echo -e "${BLUE}Test 7: Security Documentation${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "$PROJECT_ROOT/SECURITY.md" ]; then
    echo -e "  ${GREEN}✓ SECURITY.md exists${NC}"
    
    CHECKS=(
        "pip-audit"
        "npm audit"
        "bandit"
        "pre-commit"
        "supply chain"
    )
    
    for check in "${CHECKS[@]}"; do
        if grep -qi "$check" "$PROJECT_ROOT/SECURITY.md"; then
            echo -e "    ${GREEN}✓ Documents: $check${NC}"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo -e "    ${YELLOW}⚠ Missing: $check${NC}"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    done
else
    echo -e "  ${RED}✗ SECURITY.md not found${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 6))
fi

echo ""

# Test 8: Run a quick security scan
echo -e "${BLUE}Test 8: Quick Security Scan${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "  → Running quick pip-audit check..."
if [ -f "$PROJECT_ROOT/.venv/bin/pip-audit" ] && [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    # Run in background and capture output
    if timeout 60 "$PROJECT_ROOT/.venv/bin/pip-audit" --requirement "$PROJECT_ROOT/requirements.txt" --format=json > /tmp/pip-audit-test.json 2>/dev/null; then
        VULN_COUNT=$(jq length /tmp/pip-audit-test.json 2>/dev/null || echo "0")
        if [ "$VULN_COUNT" = "0" ]; then
            echo -e "    ${GREEN}✓ No vulnerabilities in requirements.txt${NC}"
        else
            echo -e "    ${YELLOW}⚠ $VULN_COUNT vulnerabilities found${NC}"
        fi
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "    ${YELLOW}⚠ pip-audit scan incomplete (timeout or error)${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
else
    echo -e "    ${YELLOW}⚠ Cannot run pip-audit (missing tools)${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

echo ""

# ============================================
# Summary
# ============================================
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Test Summary                                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Tests passed: $TESTS_PASSED"
echo "Tests failed: $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed! Security automation is ready.${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ Some tests failed. Review the output above.${NC}"
    exit 1
fi
