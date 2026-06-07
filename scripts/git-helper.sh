#!/bin/bash
#
# Git Helper Script for RolloForge
# Usage: ./scripts/git-helper.sh [command] [args]
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Config
REPO_URL="https://github.com/aungminnkhant9400/RolloForge"

# Helper functions
print_status() {
    echo -e "${BLUE}→ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

cmd_status() {
    echo ""
    print_status "Git Status"
    echo "──────────"
    
    # Branch info
    local branch=$(git branch --show-current)
    echo -e "Branch: ${GREEN}$branch${NC}"
    
    # Check if main
    if [ "$branch" = "main" ]; then
        echo -e "Status: ${YELLOW}On main branch${NC}"
    fi
    
    # Ahead/behind
    local ahead_behind=$(git rev-list --left-right --count origin/main...HEAD 2>/dev/null || echo "? ?")
    local ahead=$(echo $ahead_behind | cut -d' ' -f1)
    local behind=$(echo $ahead_behind | cut -d' ' -f2)
    
    if [ "$ahead" -gt 0 ]; then
        echo -e "Ahead of origin/main: ${GREEN}$ahead commits${NC}"
    fi
    if [ "$behind" -gt 0 ]; then
        echo -e "Behind origin/main: ${YELLOW}$behind commits${NC}"
    fi
    
    # Uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        echo ""
        print_warning "Uncommitted changes:"
        git status --short
    else
        echo -e "Working directory: ${GREEN}clean${NC}"
    fi
    
    # Recent commits
    echo ""
    echo "Recent commits:"
    git log --oneline -3
}

cmd_commit() {
    local msg="$1"
    
    if [ -z "$msg" ]; then
        print_error "Commit message required"
        echo "Usage: git-helper.sh commit \"<message>\""
        exit 1
    fi
    
    local branch=$(git branch --show-current)
    
    # Warn if on main
    if [ "$branch" = "main" ]; then
        print_warning "You are committing directly to main!"
        read -p "Continue? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Aborted"
            exit 0
        fi
    fi
    
    print_status "Staging changes..."
    git add -A
    
    print_status "Committing..."
    git commit -m "$msg"
    
    print_success "Committed: $msg"
}

cmd_pr() {
    local branch_name="$1"
    
    if [ -z "$branch_name" ]; then
        print_error "Branch name required"
        echo "Usage: git-helper.sh pr <branch-name>"
        exit 1
    fi
    
    # Validate branch name
    if [[ ! $branch_name =~ ^[a-z0-9-]+$ ]]; then
        print_error "Branch name must be lowercase letters, numbers, and hyphens only"
        exit 1
    fi
    
    print_status "Creating feature branch: $branch_name"
    
    # Ensure we're on main and up to date
    git checkout main
    git pull origin main
    
    # Create and checkout branch
    git checkout -b "$branch_name"
    
    print_success "Created branch: $branch_name"
    echo ""
    echo "Make your changes, then:"
    echo "  ./scripts/git-helper.sh commit \"Your message\""
    echo "  git push -u origin $branch_name"
    echo ""
    
    # Try to open PR URL
    if command -v xdg-open &> /dev/null; then
        xdg-open "$REPO_URL/compare/main...$branch_name" 2>/dev/null || true
    elif command -v open &> /dev/null; then
        open "$REPO_URL/compare/main...$branch_name" 2>/dev/null || true
    fi
    
    echo "PR URL: $REPO_URL/compare/main...$branch_name"
}

cmd_clean() {
    print_status "Checking for merged branches..."
    
    # Update remote
    git fetch origin --prune
    
    # Find merged branches (excluding main)
    local merged=$(git branch --merged main | grep -v "main" | grep -v "\*" | sed 's/^[[:space:]]*//')
    
    if [ -z "$$merged" ]; then
        print_success "No merged branches to clean up"
        return 0
    fi
    
    echo "Merged branches found:"
    echo "$merged" | while read branch; do
        echo "  - $branch"
    done
    
    echo ""
    read -p "Delete these branches? (y/N) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "$merged" | while read branch; do
            if [ -n "$branch" ]; then
                git branch -d "$branch" && print_success "Deleted: $branch"
            fi
        done
    else
        print_status "Aborted"
    fi
}

cmd_help() {
    echo "Git Helper for RolloForge"
    echo ""
    echo "Usage:"
    echo "  ./scripts/git-helper.sh status              Show git status"
    echo "  ./scripts/git-helper.sh commit \"<msg>\"    Stage and commit"
    echo "  ./scripts/git-helper.sh pr <branch>        Create feature branch"
    echo "  ./scripts/git-helper.sh clean              Remove merged branches"
    echo "  ./scripts/git-helper.sh help               Show this help"
    echo ""
    echo "Examples:"
    echo "  ./scripts/git-helper.sh pr fix-login-bug"
    echo "  ./scripts/git-helper.sh commit \"Fix login redirect\""
    echo "  ./scripts/git-helper.sh clean"
}

# Main
main() {
    local cmd="${1:-status}"
    
    case "$cmd" in
        status|s)
            cmd_status
            ;;
        commit|c)
            shift
            cmd_commit "$*"
            ;;
        pr)
            shift
            cmd_pr "$1"
            ;;
        clean)
            cmd_clean
            ;;
        help|h|-h|--help)
            cmd_help
            ;;
        *)
            print_error "Unknown command: $cmd"
            cmd_help
            exit 1
            ;;
    esac
}

main "$@"
