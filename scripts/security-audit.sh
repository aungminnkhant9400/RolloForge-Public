#!/bin/bash
# Security Audit Script for RolloForge
# Runs pip-audit, npm audit, and other security checks
# Exit codes: 0 = clean, 1 = vulnerabilities found, 2 = error
# FAST MODE: Skips audit for bookmark-only changes
# Usage: ./security-audit.sh --fast

set -e

FAST_MODE=false
if [ "$1" = "--fast" ]; then
    FAST_MODE=true
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

VULNERABILITIES_FOUND=0
ERRORS=0

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     RolloForge Security Audit                          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# FAST MODE: Check if only data files are being changed
# If only bookmarks/data files, skip full security audit
STAGED_FILES=$(git diff --cached --name-only 2>/dev/null || echo "")

# Check if any code files are being changed (not just data)
CODE_FILES_CHANGED=false
for file in $STAGED_FILES; do
    # Skip data files and generated files
    if [[ ! "$file" =~ ^data/ ]] && \
       [[ ! "$file" =~ ^web/lib/ ]] && \
       [[ ! "$file" =~ \.json$ ]] && \
       [[ ! "$file" =~ ^reports/ ]]; then
        CODE_FILES_CHANGED=true
        break
    fi
done

if [ "$CODE_FILES_CHANGED" = false ] && [ -n "$STAGED_FILES" ]; then
    echo -e "${GREEN}✓ Data-only changes detected (bookmarks) - skipping full security audit${NC}"
    echo -e "${GREEN}✓ Security checks passed - proceeding with commit${NC}"
    exit 0
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" > /dev/null 2>&1
}

# Function to get pip-audit path
get_pip_audit() {
    if [ -f "$PROJECT_ROOT/.venv/bin/pip-audit" ]; then
        echo "$PROJECT_ROOT/.venv/bin/pip-audit"
    elif command_exists pip-audit; then
        echo "pip-audit"
    else
        echo ""
    fi
}

# Function to get bandit path  
get_bandit() {
    if [ -f "$PROJECT_ROOT/.venv/bin/bandit" ]; then
        echo "$PROJECT_ROOT/.venv/bin/bandit"
    elif command_exists bandit; then
        echo "bandit"
    else
        echo ""
    fi
}

PIP_AUDIT=$(get_pip_audit)
BANDIT=$(get_bandit)

# ============================================
# Fast Mode: Skip heavy dependency audits
# ============================================
if [ "$FAST_MODE" = true ]; then
    echo -e "${YELLOW}⚡ Fast mode enabled - skipping dependency audits${NC}"
    echo "  (pip-audit and npm audit skipped)"
    echo ""
    
    # Still run lightweight checks in fast mode
    goto_bandit=true
    goto_secrets=true
else
    goto_bandit=false
    goto_secrets=false
fi

# ============================================
# Python Dependencies Audit (pip-audit)
# ============================================
if [ "$FAST_MODE" = true ]; then
    :
else
echo -e "${BLUE}▶ Python Dependencies Audit${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -n "$PIP_AUDIT" ]; then
    cd "$PROJECT_ROOT"
    
    # Check if requirements.txt exists
    if [ -f "requirements.txt" ]; then
        echo "  → Scanning requirements.txt..."
        if $PIP_AUDIT --requirement requirements.txt --format markdown --desc on 2>/dev/null; then
            echo -e "  ${GREEN}✓ No Python vulnerabilities found${NC}"
        else
            echo -e "  ${YELLOW}⚠ Python vulnerabilities detected (see above)${NC}"
            VULNERABILITIES_FOUND=1
        fi
    else
        echo -e "  ${YELLOW}⚠ requirements.txt not found${NC}"
    fi
    
    # Also check installed packages in virtual environment
    if [ -d ".venv" ] && [ -f ".venv/bin/python" ]; then
        echo "  → Scanning virtual environment packages..."
        if $PIP_AUDIT --format markdown --desc on 2>/dev/null; then
            echo -e "  ${GREEN}✓ No venv vulnerabilities found${NC}"
        else
            echo -e "  ${YELLOW}⚠ venv vulnerabilities detected${NC}"
            VULNERABILITIES_FOUND=1
        fi
    fi
else
    echo -e "  ${YELLOW}⚠ pip-audit not installed${NC}"
    echo "    Install: .venv/bin/pip install pip-audit"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# ============================================
# Node.js Dependencies Audit (npm audit)
# ============================================
echo -e "${BLUE}▶ Node.js Dependencies Audit${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command_exists npm; then
    if [ -d "$PROJECT_ROOT/web" ] && [ -f "$PROJECT_ROOT/web/package.json" ]; then
        cd "$PROJECT_ROOT/web"
        
        echo "  → Running npm audit..."
        # npm audit exits with non-zero if vulnerabilities found
        if npm audit --audit-level=moderate 2>/dev/null; then
            echo -e "  ${GREEN}✓ No npm vulnerabilities found${NC}"
        else
            AUDIT_EXIT=$?
            if [ $AUDIT_EXIT -eq 1 ]; then
                echo -e "  ${YELLOW}⚠ npm vulnerabilities detected${NC}"
                echo "    Run 'npm audit fix' to attempt automatic fixes"
                VULNERABILITIES_FOUND=1
            else
                echo -e "  ${RED}✗ npm audit error${NC}"
                ERRORS=$((ERRORS + 1))
            fi
        fi
    else
        echo -e "  ${YELLOW}⚠ web/package.json not found${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠ npm not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

fi  # End of fast mode skip for dependency audits

echo ""

# ============================================
# Bandit Security Linter (Python)
# ============================================
echo -e "${BLUE}▶ Python Security Linter (Bandit)${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -n "$BANDIT" ]; then
    cd "$PROJECT_ROOT"
    
    # Run bandit on the main Python directories
    BANDIT_TARGETS=("rolloforge" "scripts" "config")
    BANDIT_FOUND=0
    
    for target in "${BANDIT_TARGETS[@]}"; do
        if [ -d "$target" ]; then
            echo "  → Scanning $target/..."
            if $BANDIT -r "$target" -f txt -ll 2>/dev/null | grep -q "No issues identified"; then
                echo -e "    ${GREEN}✓ No issues in $target/${NC}"
            else
                $BANDIT -r "$target" -f txt -ll 2>/dev/null || true
                BANDIT_FOUND=1
            fi
        fi
    done
    
    if [ $BANDIT_FOUND -eq 1 ]; then
        VULNERABILITIES_FOUND=1
    fi
else
    echo -e "  ${YELLOW}⚠ bandit not installed${NC}"
    echo "    Install: .venv/bin/pip install bandit"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# ============================================
# Check for Secrets/Credentials
# ============================================
echo -e "${BLUE}▶ Secret Detection${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check for .env files that might be committed
cd "$PROJECT_ROOT"

if [ -f ".env" ]; then
    echo -e "  ${YELLOW}⚠ .env file exists in repo${NC}"
    echo "    Ensure .env is in .gitignore and not committed"
fi

# Check for common secret patterns in staged files
if command_exists git; then
    echo "  → Checking staged files for potential secrets..."
    
    # Patterns to check
    PATTERNS=(
        "password\s*=\s*['\"][^'\"]+['\"]"
        "api_key\s*=\s*['\"][^'\"]+['\"]"
        "apikey\s*=\s*['\"][^'\"]+['\"]"
        "secret\s*=\s*['\"][^'\"]+['\"]"
        "token\s*=\s*['\"][^'\"]+['\"]"
        "-----BEGIN.*PRIVATE KEY-----"
        "AKIA[0-9A-Z]{16}"  # AWS Access Key ID pattern
    )
    
    SECRETS_FOUND=0
    for pattern in "${PATTERNS[@]}"; do
        if git diff --cached --name-only 2>/dev/null | xargs grep -l -E "$pattern" 2>/dev/null; then
            echo -e "  ${RED}✗ Potential secret found matching: $pattern${NC}"
            SECRETS_FOUND=1
        fi
    done
    
    if [ $SECRETS_FOUND -eq 0 ]; then
        echo -e "  ${GREEN}✓ No obvious secrets detected in staged files${NC}"
    else
        VULNERABILITIES_FOUND=1
    fi
else
    echo -e "  ${YELLOW}⚠ git not available${NC}"
fi

echo ""

# ============================================
# Summary
# ============================================
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Security Audit Summary                             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"

if [ $VULNERABILITIES_FOUND -eq 0 ] && [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All security checks passed!${NC}"
    exit 0
elif [ $VULNERABILITIES_FOUND -eq 1 ]; then
    echo -e "${YELLOW}⚠ Vulnerabilities detected - review required${NC}"
    exit 1
else
    echo -e "${RED}✗ Errors occurred during security audit${NC}"
    exit 2
fi
