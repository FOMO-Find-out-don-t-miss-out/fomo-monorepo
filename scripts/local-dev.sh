#!/usr/bin/env bash
# scripts/local-dev.sh - One-command local development helper for FOMO (bash).
#
# Windows primary: use scripts/local-dev.ps1 instead.
# This script is for Linux/macOS or Git Bash on Windows.
#
# Usage:
#   bash scripts/local-dev.sh <command>
#
# Commands:
#   infra   Start postgres, redis, and local-portal
#   up      Build and start the full local stack
#   app     Alias for 'up'
#   n8n     Start n8n optional profile
#   smoke   Run smoke tests
#   down    Stop all local services
#   reset   Wipe volumes and restart infra
#   urls    Print all local service URLs
#   help    Show this message (default)

set -euo pipefail

COMPOSE_FILE="docker-compose.local.yml"
CMD="${1:-help}"

# -- helpers ------------------------------------------------------------------

header() { echo ""; echo "==> $1"; }
step()   { echo "    $1"; }

check_http() {
  local label="$1"
  local url="$2"
  local expected="${3:-200}"
  local status
  status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000")
  if [ "$status" = "$expected" ]; then
    printf "  PASS  %-35s -> HTTP %s\n" "$label" "$status"
    return 0
  else
    printf "  FAIL  %-35s -> HTTP %s (expected %s)\n" "$label" "$status" "$expected"
    return 1
  fi
}

# -- commands -----------------------------------------------------------------

cmd_infra() {
  header "Starting infrastructure (postgres, redis, local-portal)"
  docker compose -f "$COMPOSE_FILE" up -d postgres redis local-portal
  echo ""
  step "Waiting for healthchecks..."
  sleep 3
  docker compose -f "$COMPOSE_FILE" ps postgres redis local-portal
  echo ""
  echo "  Infra ready. Run migrations if this is a fresh volume:"
  step "  uv run alembic -c apps/api/alembic.ini upgrade head"
  cmd_urls_infra
}

cmd_up() {
  header "Building and starting full local stack"
  echo ""
  echo "  NOTE: The API builder uses ghcr.io/astral-sh/uv:python3.12-bookworm-slim."
  echo "  If build fails with 'denied', run:"
  step "  docker logout ghcr.io"
  step "  docker pull ghcr.io/astral-sh/uv:python3.12-bookworm-slim"
  echo "  Then retry: bash scripts/local-dev.sh up"
  echo ""
  docker compose -f "$COMPOSE_FILE" up -d --build
  echo ""
  docker compose -f "$COMPOSE_FILE" ps
  cmd_urls
}

cmd_n8n() {
  header "Starting n8n (optional profile)"
  step "postgres must already be running (run 'infra' first if not)"
  docker compose -f "$COMPOSE_FILE" --profile n8n up -d
  echo ""
  echo "  n8n: http://localhost:5678"
}

cmd_smoke() {
  header "Running smoke tests"
  echo ""
  pass=0; fail=0
  checks=(
    "API docs (Swagger)|http://localhost:8000/docs"
    "API health|http://localhost:8000/api/v1/health"
    "Dashboard|http://localhost:3000"
    "Local portal|http://localhost:8088"
  )
  for entry in "${checks[@]}"; do
    label="${entry%%|*}"
    url="${entry##*|}"
    if check_http "$label" "$url"; then
      pass=$((pass + 1))
    else
      fail=$((fail + 1))
    fi
  done
  echo ""
  header "Container status"
  docker compose -f "$COMPOSE_FILE" ps
  echo ""
  if [ "$fail" -gt 0 ]; then
    echo "  $pass passed, $fail failed"
    echo ""
    echo "  Tip: start infra first:  bash scripts/local-dev.sh infra"
    echo "  For full stack:          bash scripts/local-dev.sh up"
    exit 1
  fi
  echo "  $pass passed, $fail failed - all checks OK"
}

cmd_down() {
  header "Stopping all local services"
  docker compose -f "$COMPOSE_FILE" --profile n8n down
  echo "  Done."
}

cmd_reset() {
  header "Resetting local stack (down -v + start infra)"
  echo ""
  echo "  WARNING: This deletes all local postgres data."
  read -r -p "  Type 'yes' to confirm: " confirm
  if [ "$confirm" != "yes" ]; then
    echo "  Aborted."
    return
  fi
  docker compose -f "$COMPOSE_FILE" --profile n8n down -v
  echo ""
  cmd_infra
  echo ""
  echo "  Volume wiped. Re-run migrations:"
  step "  uv run alembic -c apps/api/alembic.ini upgrade head"
}

cmd_urls() {
  echo ""
  echo "  FOMO Local Service URLs"
  echo "  ---------------------------------------------------------"
  printf "  %-30s %s\n" "Local Portal"       "http://localhost:8088"
  printf "  %-30s %s\n" "API Docs (Swagger)" "http://localhost:8000/docs"
  printf "  %-30s %s\n" "API Health"         "http://localhost:8000/api/v1/health"
  printf "  %-30s %s\n" "API Metrics"        "http://localhost:8000/metrics"
  printf "  %-30s %s\n" "Dashboard"          "http://localhost:3000"
  printf "  %-30s %s\n" "Postgres"           "localhost:5432  (user: fomo / db: fomo)"
  printf "  %-30s %s\n" "Redis"              "localhost:6379"
  printf "  %-30s %s\n" "n8n (optional)"     "http://localhost:5678  [bash scripts/local-dev.sh n8n]"
  echo "  ---------------------------------------------------------"
  printf "  %-30s %s\n" "AI extraction"      "disabled by default (AI_PROVIDER=disabled)"
  echo ""
}

cmd_urls_infra() {
  echo ""
  echo "  FOMO Local Service URLs (infra)"
  echo "  ---------------------------------------------------------"
  printf "  %-30s %s\n" "Local Portal"   "http://localhost:8088"
  printf "  %-30s %s\n" "Postgres"       "localhost:5432  (user: fomo / db: fomo)"
  printf "  %-30s %s\n" "Redis"          "localhost:6379"
  echo ""
}

cmd_help() {
  echo ""
  echo "  FOMO local-dev.sh"
  echo ""
  echo "  Usage: bash scripts/local-dev.sh <command>"
  echo ""
  echo "  Commands:"
  printf "  %-10s %s\n" "infra"  "Start postgres, redis, local-portal (no build)"
  printf "  %-10s %s\n" "up"     "Build + start full stack (infra + api + dashboard)"
  printf "  %-10s %s\n" "app"    "Alias for 'up'"
  printf "  %-10s %s\n" "n8n"    "Start n8n optional profile"
  printf "  %-10s %s\n" "smoke"  "Run smoke tests against the running stack"
  printf "  %-10s %s\n" "down"   "Stop all local services"
  printf "  %-10s %s\n" "reset"  "Wipe volumes and restart infra"
  printf "  %-10s %s\n" "urls"   "Print all local service URLs"
  printf "  %-10s %s\n" "help"   "Show this message"
  echo ""
}

# -- dispatch -----------------------------------------------------------------

case "$CMD" in
  infra)  cmd_infra  ;;
  up)     cmd_up     ;;
  app)    cmd_up     ;;
  n8n)    cmd_n8n    ;;
  smoke)  cmd_smoke  ;;
  down)   cmd_down   ;;
  reset)  cmd_reset  ;;
  urls)   cmd_urls   ;;
  help)   cmd_help   ;;
  *)
    echo "  Unknown command: $CMD"
    cmd_help
    exit 1
    ;;
esac
