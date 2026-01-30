#!/bin/bash
# run_daily_selection.sh - Wrapper for daily_news_selector.py
# Usage: run_daily_selection.sh [cron|anacron]
# Prevents duplicate runs via flock, logs to separate files per caller.

set -euo pipefail

PROJECT_DIR="/home/jeozeohan/vibe_temp/China Economy News Analysis"
LOG_DIR="/home/jeozeohan/logs"
LOCK_FILE="/tmp/china_news_selector.lock"
PYTHON="/usr/bin/python3"
SCRIPT="src/agents/daily_news_selector.py"

# Determine caller for log separation
CALLER="${1:-manual}"
LOG_FILE="${LOG_DIR}/daily_news_${CALLER}.log"

mkdir -p "$LOG_DIR"

# flock-based duplicate execution prevention (fd 200)
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$CALLER] Another instance is already running. Exiting." >> "$LOG_FILE"
    exit 0
fi

{
    echo "=========================================="
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$CALLER] Starting daily news selection"
    echo "=========================================="

    cd "$PROJECT_DIR"
    "$PYTHON" "$SCRIPT"

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$CALLER] Completed successfully"
    echo ""
} >> "$LOG_FILE" 2>&1
