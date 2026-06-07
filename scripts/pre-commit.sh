#!/bin/bash
#
# Pre-commit hook for RolloForge
# Validates data files before allowing commits
#

set -e

echo "🔍 Running pre-commit checks..."

DATA_DIR="data"
ERRORS=0
WARNINGS=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_json_syntax() {
    local file=$1
    if ! python3 -m json.tool "$file" > /dev/null 2>&1; then
        echo -e "${RED}✗ Invalid JSON: $file${NC}"
        return 1
    fi
    return 0
}

# Check bookmarks.json
if [ -f "$DATA_DIR/bookmarks_raw.json" ]; then
    if ! check_json_syntax "$DATA_DIR/bookmarks_raw.json"; then
        ERRORS=$((ERRORS + 1))
    else
        # Check for duplicate IDs
        DUPS=$(python3 -c "
import json
with open('$DATA_DIR/bookmarks_raw.json') as f:
    data = json.load(f)
ids = [b['id'] for b in data]
dups = [id for id in ids if ids.count(id) > 1]
if dups:
    print('Duplicate IDs:', set(dups))
" 2>&1)
        if [ -n "$DUPS" ]; then
            echo -e "${RED}✗ $DUPS${NC}"
            ERRORS=$((ERRORS + 1))
        fi
        
        # Check required fields
        MISSING=$(python3 -c "
import json
with open('$DATA_DIR/bookmarks_raw.json') as f:
    data = json.load(f)
required = ['id', 'url', 'title', 'source', 'created_at']
bad = [b for b in data if not all(f in b and b[f] for f in required)]
if bad:
    print(f'Missing required fields in {len(bad)} bookmarks')
" 2>&1)
        if [ -n "$MISSING" ]; then
            echo -e "${YELLOW}⚠ $MISSING${NC}"
            WARNINGS=$((WARNINGS + 1))
        fi
    fi
fi

# Check analysis_results.json
if [ -f "$DATA_DIR/analysis_results.json" ]; then
    if ! check_json_syntax "$DATA_DIR/analysis_results.json"; then
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check file sizes (warn if >10MB)
for file in "$DATA_DIR"/*.json; do
    if [ -f "$file" ]; then
        SIZE=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
        if [ "$SIZE" -gt 10485760 ]; then
            echo -e "${YELLOW}⚠ Large file: $(basename $file) ($((SIZE/1048576))MB)${NC}"
            WARNINGS=$((WARNINGS + 1))
        fi
    fi
done

# Summary
echo ""
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️ $WARNINGS warning(s), but committing anyway${NC}"
    exit 0
else
    echo -e "${RED}❌ $ERRORS error(s), $WARNINGS warning(s)${NC}"
    echo "Fix errors before committing."
    exit 1
fi
