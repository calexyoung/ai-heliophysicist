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

# Log next to the state, in whichever workspace the profile resolved to, so
# the two never live in different trees. Falls back to the shared workspace
# if that import fails, because a cycle with nowhere to log is worse than a
# cycle logged in the wrong place; launchd's own stdout file catches the
# failure either way.
WORKSPACE_DIR="$(uv run python -c 'from helio_agent.workspace import WORKSPACE; print(WORKSPACE)' \
                 2>/dev/null || echo workspace)"
LOG="$WORKSPACE_DIR/logs/monitor_cron.log"
mkdir -p "$(dirname "$LOG")"
{
  echo "=== monitor cycle $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo "profile: ${HELIO_AGENT_USER:-<none, shared workspace>}"
  echo "workspace: $WORKSPACE_DIR"
  uv run helio-agent monitor
} >> "$LOG" 2>&1
