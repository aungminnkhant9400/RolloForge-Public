#!/bin/bash
#
# Digest Scheduler Cron Wrapper
#
# Checks the digest schedule and sends any due digests.
# Designed to run hourly via cron.
#
# Cron example:
#   0 * * * * /home/ubuntu/RolloForge/scripts/digest-cron.sh >> /home/ubuntu/RolloForge/.nightly-logs/digest-cron.log 2>&1
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/.nightly-logs"
STATUS_FILE="$PROJECT_ROOT/data/digest_scheduler_state.json"

mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "=== Digest Scheduler Starting ==="

cd "$PROJECT_ROOT"

# Prefer venv python if available
PYTHON="${PROJECT_ROOT}/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
    PYTHON="python3"
fi

# Run scheduler
if "$PYTHON" "$SCRIPT_DIR/digest_scheduler.py" "$@"; then
    log "=== Digest Scheduler Completed ==="
    exit 0
else
    EXIT_CODE=$?
    log "=== Digest Scheduler Failed (exit $EXIT_CODE) ==="
    exit $EXIT_CODE
fi
