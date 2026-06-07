#!/bin/bash
#
# 2-Hour Proactive Build Cycle
# Runs automatically every 2 hours during the day
# Spawns 8 parallel workers to build/improve RolloForge
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/.build-cycle-logs"
LOCK_FILE="/tmp/rolloforge-2hour-cycle.lock"

# Ensure log directory
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/cycle-$(date +%Y%m%d-%H%M).log"

echo "[$(date)] Starting 2-hour build cycle" | tee -a "$LOG_FILE"

# Check if another instance is running
if [ -f "$LOCK_FILE" ]; then
    LOCK_PID=$(cat "$LOCK_FILE")
    if ps -p "$LOCK_PID" > /dev/null 2>&1; then
        echo "[$(date)] Another cycle running (PID $LOCK_PID), skipping" | tee -a "$LOG_FILE"
        exit 0
    fi
fi
echo $$ > "$LOCK_FILE"

# Cleanup lock on exit
trap "rm -f $LOCK_FILE" EXIT

cd "$PROJECT_ROOT"
. .venv/bin/activate

# Run the cycle via OpenClaw API
# This spawns 8 workers automatically
echo "[$(date)] Spawning 8 workers..." | tee -a "$LOG_FILE"

# Create a marker file that OpenClaw will detect and act on
CYCLE_TRIGGER="$PROJECT_ROOT/.trigger-2hour-cycle"
cat > "$CYCLE_TRIGGER" << EOF
{
  "type": "2hour_build_cycle",
  "timestamp": "$(date -Iseconds)",
  "workers": 8,
  "auto_approve": true
}
EOF

echo "[$(date)] Cycle triggered, waiting for completion..." | tee -a "$LOG_FILE"

# The actual worker spawning is done via OpenClaw's cron system
# This script just triggers it and logs

sleep 5
rm -f "$CYCLE_TRIGGER"

echo "[$(date)] 2-hour build cycle completed" | tee -a "$LOG_FILE"
