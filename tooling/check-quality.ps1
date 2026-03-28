Write-Host "CHECK: Running Quality Gates (2026 Standards with Turbo acceleration)..." -ForegroundColor Cyan

npx turbo check-quality

if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILURE: Quality check failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "SUCCESS: Quality check passed!" -ForegroundColor Green
