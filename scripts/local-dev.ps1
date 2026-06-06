# scripts/local-dev.ps1 - One-command local development helper for FOMO.
#
# Usage:
#   .\scripts\local-dev.ps1 <command>
#
# Commands:
#   infra   Start postgres, redis, and local-portal (no app build required)
#   up      Build and start the full local stack (infra + api + dashboard)
#   app     Alias for 'up'
#   n8n     Start n8n (optional; requires infra to be running)
#   smoke   Run smoke tests against the running stack
#   down    Stop all local services
#   reset   Wipe all local volumes and restart infra from scratch
#   urls    Print all local service URLs
#   help    Show this help message (default)

param(
    [Parameter(Position = 0)]
    [string]$Command = "help"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ComposeFile = "docker-compose.local.yml"
$ComposeFArgs = "-f", $ComposeFile

# -- helpers ------------------------------------------------------------------

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "==> $Text" -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Text)
    Write-Host "    $Text" -ForegroundColor White
}

function Test-Http {
    param(
        [string]$Label,
        [string]$Url,
        [int]$ExpectedStatus = 200,
        [int]$TimeoutSec = 10
    )
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec -ErrorAction Stop
        if ($response.StatusCode -eq $ExpectedStatus) {
            Write-Host ("  PASS  {0,-35} -> HTTP {1}" -f $Label, $response.StatusCode) -ForegroundColor Green
            return $true
        }
        Write-Host ("  FAIL  {0,-35} -> HTTP {1} (expected {2})" -f $Label, $response.StatusCode, $ExpectedStatus) -ForegroundColor Red
        return $false
    } catch {
        $msg = $_.Exception.Message -replace "`n", " "
        Write-Host ("  FAIL  {0,-35} -> {1}" -f $Label, $msg) -ForegroundColor Red
        return $false
    }
}

# -- commands -----------------------------------------------------------------

function Invoke-Infra {
    Write-Header "Starting infrastructure (postgres, redis, local-portal)"
    docker compose @ComposeFArgs up -d postgres redis local-portal
    Write-Host ""
    Write-Step "Waiting for healthchecks..."
    Start-Sleep -Seconds 3
    docker compose @ComposeFArgs ps postgres redis local-portal
    Write-Host ""
    Write-Host "  Infra ready. Run migrations if this is a fresh volume:" -ForegroundColor Yellow
    Write-Step "  uv run alembic -c apps/api/alembic.ini upgrade head"
    Write-Host ""
    Show-Urls -InfraOnly
}

function Invoke-Up {
    Write-Header "Building and starting full local stack"
    Write-Host ""
    Write-Host "  NOTE: The API builder stage uses ghcr.io/astral-sh/uv:python3.12-bookworm-slim." -ForegroundColor Yellow
    Write-Host "  If the build fails with 'denied', run:" -ForegroundColor Yellow
    Write-Step "  docker logout ghcr.io"
    Write-Step "  docker pull ghcr.io/astral-sh/uv:python3.12-bookworm-slim"
    Write-Host "  Then retry: .\scripts\local-dev.ps1 up" -ForegroundColor Yellow
    Write-Host ""
    docker compose @ComposeFArgs up -d --build
    Write-Host ""
    docker compose @ComposeFArgs ps
    Write-Host ""
    Show-Urls
}

function Invoke-N8n {
    Write-Header "Starting n8n (optional profile)"
    Write-Step "postgres must already be running (run 'infra' first if not)"
    docker compose @ComposeFArgs --profile n8n up -d
    Write-Host ""
    Write-Host "  n8n: http://localhost:5678" -ForegroundColor Cyan
    Write-Host "  DB:  n8n__harvester (created automatically on first postgres start)" -ForegroundColor White
}

function Invoke-Smoke {
    Write-Header "Running smoke tests"
    Write-Host ""

    $pass = 0
    $fail = 0

    $checks = @(
        @{ Label = "API docs (Swagger)"; Url = "http://localhost:8000/docs" },
        @{ Label = "API health";         Url = "http://localhost:8000/api/v1/health" },
        @{ Label = "Dashboard";          Url = "http://localhost:3000" },
        @{ Label = "Local portal";       Url = "http://localhost:8088" }
    )

    foreach ($c in $checks) {
        $ok = Test-Http -Label $c.Label -Url $c.Url
        if ($ok) { $pass++ } else { $fail++ }
    }

    Write-Host ""
    Write-Header "Container status"
    docker compose @ComposeFArgs ps
    Write-Host ""

    if ($fail -gt 0) {
        Write-Host ("  {0} passed, {1} failed" -f $pass, $fail) -ForegroundColor Red
        Write-Host ""
        Write-Host "  Tip: start infra first with: .\scripts\local-dev.ps1 infra" -ForegroundColor Yellow
        Write-Host "  For full stack:              .\scripts\local-dev.ps1 up" -ForegroundColor Yellow
        exit 1
    }

    Write-Host ("  {0} passed, {1} failed - all checks OK" -f $pass, $fail) -ForegroundColor Green
}

function Invoke-Down {
    Write-Header "Stopping all local services"
    docker compose @ComposeFArgs --profile n8n down
    Write-Host "  Done." -ForegroundColor Green
}

function Invoke-Reset {
    Write-Header "Resetting local stack (down -v + start infra)"
    Write-Host ""
    Write-Host "  WARNING: This deletes all local postgres data (fomo_postgres_data volume)." -ForegroundColor Yellow
    $confirm = Read-Host "  Type 'yes' to confirm"
    if ($confirm -ne "yes") {
        Write-Host "  Aborted." -ForegroundColor Yellow
        return
    }
    docker compose @ComposeFArgs --profile n8n down -v
    Write-Host ""
    Invoke-Infra
    Write-Host ""
    Write-Host "  Volume wiped. Re-run migrations:" -ForegroundColor Yellow
    Write-Step "  uv run alembic -c apps/api/alembic.ini upgrade head"
}

function Show-Urls {
    param([switch]$InfraOnly)

    Write-Host ""
    Write-Host "  FOMO Local Service URLs" -ForegroundColor Cyan
    Write-Host "  ---------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host ("  {0,-30} {1}" -f "Local Portal",        "http://localhost:8088") -ForegroundColor White
    if (-not $InfraOnly) {
        Write-Host ("  {0,-30} {1}" -f "API Docs (Swagger)",  "http://localhost:8000/docs") -ForegroundColor White
        Write-Host ("  {0,-30} {1}" -f "API Health",          "http://localhost:8000/api/v1/health") -ForegroundColor White
        Write-Host ("  {0,-30} {1}" -f "API Metrics",         "http://localhost:8000/metrics") -ForegroundColor White
        Write-Host ("  {0,-30} {1}" -f "Dashboard",           "http://localhost:3000") -ForegroundColor White
    }
    Write-Host ("  {0,-30} {1}" -f "Postgres",            "localhost:5432  (user: fomo / db: fomo)") -ForegroundColor DarkGray
    Write-Host ("  {0,-30} {1}" -f "Redis",               "localhost:6379") -ForegroundColor DarkGray
    Write-Host ("  {0,-30} {1}" -f "n8n (optional)",      "http://localhost:5678  [start: .\scripts\local-dev.ps1 n8n]") -ForegroundColor DarkGray
    Write-Host "  ---------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host ("  {0,-30} {1}" -f "AI extraction",       "disabled by default (AI_PROVIDER=disabled)") -ForegroundColor DarkGray
    Write-Host ""
}

function Show-Help {
    Write-Host ""
    Write-Host "  FOMO local-dev.ps1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Usage: .\scripts\local-dev.ps1 [command]" -ForegroundColor White
    Write-Host ""
    Write-Host "  Commands:" -ForegroundColor White
    Write-Host ("  {0,-10} {1}" -f "infra",  "Start postgres, redis, local-portal (no build)")
    Write-Host ("  {0,-10} {1}" -f "up",     "Build + start full stack (infra + api + dashboard)")
    Write-Host ("  {0,-10} {1}" -f "app",    "Alias for 'up'")
    Write-Host ("  {0,-10} {1}" -f "n8n",    "Start n8n optional profile (requires infra)")
    Write-Host ("  {0,-10} {1}" -f "smoke",  "Run smoke tests against the running stack")
    Write-Host ("  {0,-10} {1}" -f "down",   "Stop all local services")
    Write-Host ("  {0,-10} {1}" -f "reset",  "Wipe volumes and restart infra from scratch")
    Write-Host ("  {0,-10} {1}" -f "urls",   "Print all local service URLs")
    Write-Host ("  {0,-10} {1}" -f "help",   "Show this message")
    Write-Host ""
}

# -- dispatch -----------------------------------------------------------------

switch ($Command.ToLower()) {
    "infra"  { Invoke-Infra }
    "up"     { Invoke-Up }
    "app"    { Invoke-Up }
    "n8n"    { Invoke-N8n }
    "smoke"  { Invoke-Smoke }
    "down"   { Invoke-Down }
    "reset"  { Invoke-Reset }
    "urls"   { Show-Urls }
    "help"   { Show-Help }
    default  {
        Write-Host "  Unknown command: $Command" -ForegroundColor Red
        Show-Help
        exit 1
    }
}
