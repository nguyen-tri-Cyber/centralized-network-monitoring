# PowerShell helper to start the monitoring stack
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$deployDir = Join-Path $repoRoot "deploy"

Set-Location $deployDir

if (-not (Test-Path ".env")) {
    Write-Host "[INFO] No .env found in deploy/. Copying from .env.example..." -ForegroundColor Cyan
    Copy-Item ".env.example" ".env"
}

Write-Host "[INFO] Starting Centralized Network Monitoring stack..." -ForegroundColor Green
docker compose up -d --build

Write-Host "`n=== Stack Services Status ===" -ForegroundColor Cyan
docker compose ps

Write-Host "`nAccess URLs:" -ForegroundColor Yellow
Write-Host "  - Prometheus:    http://localhost:9090"
Write-Host "  - Grafana:       http://localhost:3000 (default: admin / admin_lab_change_me)"
Write-Host "  - Alertmanager:  http://localhost:9093"
Write-Host "  - SNMP Exporter: http://localhost:9116"
