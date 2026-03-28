Write-Host "CHECK: Running Quality Gates (2026 Standards)..." -ForegroundColor Cyan

Write-Host "TASK: Running Ruff (Linting & Formatting)..." -ForegroundColor Yellow
uv run ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

uv run ruff format --check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "TASK: Running Tests (95% Coverage Mandatory)..." -ForegroundColor Yellow
# Run pytest specifically for the api package to ensure coverage and logic check
uv run pytest apps/api/tests --cov=apps/api/app --cov-fail-under=95
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "TASK: Checking for Database Schema Drift..." -ForegroundColor Yellow
uv run python tooling/verify-schema-sync.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "SUCCESS: Quality check passed!" -ForegroundColor Green
