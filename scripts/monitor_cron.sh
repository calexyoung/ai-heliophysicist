#!/bin/bash
# Daily standing-watch cycle (see helio_agent/monitor.py, docs/MONITOR.md).
# Installed as a macOS LaunchAgent: com.helio-agent.monitor
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# The monitor writes its state to the ACTIVE USER's workspace
# (users/<name>/workspace/monitor_state.json), not the shared tree. That
# currently resolves inside Python — workspace.load_env() reads .env before
# the path constants are built — which works but is invisible from here, and
# a scheduler inherits none of your shell profile. Resolve it explicitly so
# the dependency is visible and the log can state where state went.
#
# Precedence, matching load_env(): an already-set environment wins, then
# .env, then unset. No profile is hardcoded — this script is shared, and an
# empty value means the shared workspace, which active_user() treats as None.
if [ -z "${HELIO_AGENT_USER:-}" ] && [ -f .env ]; then
  HELIO_AGENT_USER="$(sed -n 's/^[[:space:]]*HELIO_AGENT_USER[[:space:]]*=//p' .env \
                      | head -1 | tr -d '"'"'"' ' || true)"
fi
export HELIO_AGENT_USER="${HELIO_AGENT_USER:-}"

LOG=workspace/logs/monitor_cron.log
mkdir -p workspace/logs
{
  echo "=== monitor cycle $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo "profile: ${HELIO_AGENT_USER:-<none, shared workspace>}"
  uv run python -c 'from helio_agent.workspace import WORKSPACE; print("workspace:", WORKSPACE)'
  uv run helio-agent monitor
} >> "$LOG" 2>&1
