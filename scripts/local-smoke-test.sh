#!/usr/bin/env bash
# scripts/local-smoke-test.sh — Basic smoke test for the local development stack.
#
# Requires bash (Git Bash on Windows, or WSL). For PowerShell equivalents see
# docs/local-development.md.
#
# Usage:
#   bash scripts/local-smoke-test.sh
#
# Expects API on localhost:8000 and dashboard on localhost:3000.
# Services must already be running (docker compose up or host-mode).

set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
DASHBOARD_URL="${DASHBOARD_URL:-http://localhost:3000}"
PASS=0
FAIL=0

check() {
  local label="$1"
  local url="$2"
  local expected_status="${3:-200}"

  status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000")
  if [ "$status" = "$expected_status" ]; then
    echo "  PASS  $label ($url) -> HTTP $status"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $label ($url) -> HTTP $status (expected $expected_status)"
    FAIL=$((FAIL + 1))
  fi
}

echo ""
echo "FOMO local smoke test"
echo "====================="
echo "API:       $API_URL"
echo "Dashboard: $DASHBOARD_URL"
echo ""

check "API docs (Swagger)"   "$API_URL/docs"
check "API health endpoint"  "$API_URL/api/v1/health"
check "Dashboard root"       "$DASHBOARD_URL"

echo ""
echo "Docker Compose status:"
docker compose -f docker-compose.local.yml ps 2>/dev/null || echo "  (docker compose not available or stack not running)"

echo ""
echo "Results: $PASS passed, $FAIL failed"
echo ""

if [ "$FAIL" -gt 0 ]; then
  echo "Some checks failed. Ensure services are running:"
  echo "  docker compose -f docker-compose.local.yml up --build"
  echo "  # or for infra only: docker compose -f docker-compose.local.yml up -d postgres redis"
  exit 1
fi

echo "All checks passed."
