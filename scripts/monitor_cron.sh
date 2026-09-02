#!/bin/bash
# Daily standing-watch cycle (see helio_agent/monitor.py).
# Installed as a macOS LaunchAgent: com.helio-agent.monitor
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
LOG=workspace/logs/monitor_cron.log
mkdir -p workspace/logs
{
  echo "=== monitor cycle $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  uv run helio-agent monitor
} >> "$LOG" 2>&1
