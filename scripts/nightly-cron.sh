#!/bin/bash
#
# Nightly Build Cron Wrapper
# 
# This script wraps nightly-build.py for reliable cron execution
# Handles: logging, locking, error notifications, environment setup
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON="$PROJECT_ROOT/.venv/bin/python"
BUILD_SCRIPT="$SCRIPT_DIR/nightly-build.py"
LOG_DIR="$PROJECT_ROOT/.nightly-logs"
LOCK_FILE="/tmp/rolloforge-nightly.lock"
NOTIFY_ON_ERROR=true

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/cron-wrapper.log"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_DIR/cron-wrapper.log"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_DIR/cron-wrapper.log"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_DIR/cron-wrapper.log"
}

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Check if another instance is running
check_lock() {
    if [ -f "$LOCK_FILE" ]; then
        LOCK_PID=$(cat "$LOCK_FILE")
        if ps -p "$LOCK_PID" > /dev/null 2>&1; then
            log_error "Another nightly build is already running (PID: $LOCK_PID)"
            exit 1
        else
            log_warn "Stale lock file found, removing"
            rm -f "$LOCK_FILE"
        fi
    fi
    echo $$ > "$LOCK_FILE"
}

# Clean up lock on exit
cleanup() {
    rm -f "$LOCK_FILE"
}
trap cleanup EXIT

# Setup Python environment
setup_env() {
    cd "$PROJECT_ROOT"
    
    # Activate virtual environment if it exists
    if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
        source "$PROJECT_ROOT/.venv/bin/activate"
    fi
    
    # Ensure Python is available
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 not found"
        exit 1
    fi
}

# Send notification on error
notify_error() {
    local exit_code=$1
    local log_file=$2
    
    if [ "$NOTIFY_ON_ERROR" = true ]; then
        # Create error summary
        local error_summary="Nightly build failed with exit code $exit_code\n\nLast 20 lines of log:\n$(tail -20 "$log_file")"
        
        # Log to file for pickup by notification system
        echo "$error_summary" > "$LOG_DIR/last-error.txt"
        
        # If telegram-send is available, use it
        if command -v telegram-send &> /dev/null; then
            telegram-send "🚨 RolloForge Nightly Build Failed\n\n$error_summary" 2>/dev/null || true
        fi
        
        log_error "Error notification sent"
    fi
}

# Send success notification
notify_success() {
    local report_file=$1
    
    if [ -f "$report_file" ]; then
        local summary=$(head -20 "$report_file")
        
        # Log success
        log_success "Nightly build completed successfully"
        
        # If telegram-send is available, send brief summary
        if command -v telegram-send &> /dev/null; then
            local bookmark_count=$(grep -o "[0-9]\+ bookmarks" "$report_file" | head -1 || echo "N/A")
            telegram-send "✅ RolloForge Nightly Build Complete\n\n$bookmark_count\n\nFull report: $report_file" 2>/dev/null || true
        fi
    fi
}

# Main execution
main() {
    log "=== Nightly Build Cron Job Starting ==="
    
    # Check lock
    check_lock
    
    # Setup environment
    setup_env
    
    # Run the build
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local build_log="$LOG_DIR/build-$timestamp.log"
    
    log "Running nightly build..."
    
    if "$PYTHON" "$BUILD_SCRIPT" "$@" 2>&1 | tee "$build_log"; then
        local exit_code=$?
        log_success "Build completed with exit code: $exit_code"
        
        # Find the latest report
        local latest_report=$(ls -t "$PROJECT_ROOT/reports/nightly-report-"*.txt 2>/dev/null | head -1)
        
        if [ -n "$latest_report" ]; then
            notify_success "$latest_report"
        fi
        
        exit $exit_code
    else
        local exit_code=$?
        log_error "Build failed with exit code: $exit_code"
        notify_error "$exit_code" "$build_log"
        exit $exit_code
    fi
}

# Handle arguments
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Nightly Build Cron Wrapper"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options (passed to nightly-build.py):"
    echo "  --dry-run          Show what would be done without making changes"
    echo "  --skip-auto-fix    Skip applying auto-fixes (health checks only)"
    echo "  --report-only      Generate report from last run"
    echo "  --rollback ID      Rollback to specific backup"
    echo "  --list-backups     List available backups"
    echo ""
    echo "Cron example:"
    echo "  0 2 * * * /home/ubuntu/RolloForge/scripts/nightly-cron.sh"
    exit 0
fi

main "$@"
