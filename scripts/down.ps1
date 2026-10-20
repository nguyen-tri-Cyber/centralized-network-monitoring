# PowerShell helper to stop the monitoring stack
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$deployDir = Join-Path $repoRoot "deploy"

Set-Location $deployDir
Write-Host "[INFO] Stopping monitoring stack..." -ForegroundColor Yellow
docker compose down $args
Write-Host "[INFO] Monitoring stack stopped." -ForegroundColor Green
