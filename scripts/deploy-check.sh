#!/bin/bash
#
# Deployment readiness check for RolloForge
# Usage: ./scripts/deploy-check.sh [--verbose]
#

VERBOSE=0
if [ "$1" = "--verbose" ] || [ "$1" = "-v" ]; then
    VERBOSE=1
fi

echo "🚀 Deployment Readiness Check"
echo "=============================="

PASSED=0
FAILED=0
WARNINGS=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

pass() {
    echo -e "${GREEN}✓${NC} $1"
    PASSED=$((PASSED + 1))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    FAILED=$((FAILED + 1))
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    WARNINGS=$((WARNINGS + 1))
}

info() {
    if [ $VERBOSE -eq 1 ]; then
        echo -e "${BLUE}→${NC} $1"
    fi
}

# 1. Environment Variables
echo ""
echo "📋 Environment Variables"
if [ -f ".env" ]; then
    if grep -q "DEEPSEEK_API_KEY" .env; then
        pass ".env exists with DEEPSEEK_API_KEY"
    else
        fail ".env missing DEEPSEEK_API_KEY"
    fi
else
    fail ".env file not found"
fi

# 2. Git Status
echo ""
echo "📁 Git Status"
BRANCH=$(git branch --show-current)
if [ "$BRANCH" = "main" ]; then
    pass "On main branch"
else
    warn "Not on main branch (currently: $BRANCH)"
fi

if [ -z "$(git status --porcelain)" ]; then
    pass "Working directory clean"
else
    warn "Uncommitted changes:"
    git status --short
fi

AHEAD=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo 0)
if [ "$AHEAD" -eq 0 ]; then
    pass "In sync with origin/main"
else
    warn "$AHEAD commit(s) ahead of origin/main"
fi

# 3. Data Files
echo ""
echo "💾 Data Files"
if [ -f "data/bookmarks_raw.json" ]; then
    BM_COUNT=$(python3 -c "import json; print(len(json.load(open('data/bookmarks_raw.json'))))" 2>/dev/null || echo 0)
    pass "bookmarks_raw.json exists ($BM_COUNT bookmarks)"
else
    fail "bookmarks_raw.json not found"
fi

if [ -f "data/analysis_results.json" ]; then
    AN_COUNT=$(python3 -c "import json; print(len(json.load(open('data/analysis_results.json'))))" 2>/dev/null || echo 0)
    pass "analysis_results.json exists ($AN_COUNT analyses)"
else
    fail "analysis_results.json not found"
fi

# 4. JSON Validity
echo ""
echo "✅ JSON Validity"
if python3 -m json.tool data/bookmarks_raw.json > /dev/null 2>&1; then
    pass "bookmarks_raw.json is valid JSON"
else
    fail "bookmarks_raw.json has JSON errors"
fi

if python3 -m json.tool data/analysis_results.json > /dev/null 2>&1; then
    pass "analysis_results.json is valid JSON"
else
    fail "analysis_results.json has JSON errors"
fi

# 5. Data Sync
echo ""
echo "🔄 Data Sync"
if [ -f "web/lib/data.json" ] && [ -f "web/lib/analysis.json" ]; then
    pass "Web data files exist"
    
    # Check if synced
    DATA_HASH=$(md5sum data/bookmarks_raw.json 2>/dev/null | cut -d' ' -f1)
    WEB_HASH=$(md5sum web/lib/data.json 2>/dev/null | cut -d' ' -f1)
    
    if [ "$DATA_HASH" = "$WEB_HASH" ]; then
        pass "Data is synced to web/lib/"
    else
        warn "Data not synced (run: npm run data)"
    fi
else
    warn "Web data files missing (run: npm run data)"
fi

# 6. Build Test
echo ""
echo "🔨 Build Test"
if [ -d "web" ]; then
    pass "web/ directory exists"
    
    cd web
    if npm run build > /tmp/build.log 2>&1; then
        pass "Build successful"
    else
        fail "Build failed (see /tmp/build.log)"
        if [ $VERBOSE -eq 1 ]; then
            tail -20 /tmp/build.log
        fi
    fi
    cd ..
else
    fail "web/ directory not found"
fi

# 7. Critical Files
echo ""
echo "📄 Critical Files"
for file in "package.json" "next.config.js" "tsconfig.json"; do
    if [ -f "web/$file" ]; then
        pass "$file exists"
    else
        fail "$file missing"
    fi
done

# 8. Vercel Config
echo ""
echo "🌐 Vercel Configuration"
if [ -f "web/vercel.json" ]; then
    pass "vercel.json exists"
else
    warn "vercel.json not found (optional)"
fi

# Summary
echo ""
echo "=============================="
echo "Summary: $PASSED passed, $FAILED failed, $WARNINGS warnings"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Ready for deployment!${NC}"
    exit 0
else
    echo -e "${RED}❌ Fix failures before deploying${NC}"
    exit 1
fi
