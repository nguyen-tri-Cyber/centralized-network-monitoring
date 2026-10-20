[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$BackupDir,
    [switch]$ConfirmRestore
)

$ErrorActionPreference = 'Stop'
if (-not $ConfirmRestore) { throw 'Restore replaces the current lab database. Re-run with -ConfirmRestore.' }
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$folder = (Resolve-Path -LiteralPath $BackupDir).Path
$dumpPath = Join-Path $folder 'zabbix.dump'
$manifestPath = Join-Path $folder 'manifest.json'
if (-not (Test-Path -LiteralPath $dumpPath) -or -not (Test-Path -LiteralPath $manifestPath)) {
    throw 'Backup folder is incomplete.'
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath $dumpPath -Algorithm SHA256).Hash -ne $manifest.dump_sha256) {
    throw 'Backup hash does not match manifest.'
}
$containerPath = '/tmp/a1-restore.dump'
Push-Location $projectDir
try {
    $containerId = (& docker compose ps -q db).Trim()
    if (-not $containerId) { throw 'Database container is not running.' }
    & docker cp $dumpPath "${containerId}:$containerPath"
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy dump into database container.' }
    & docker compose stop web zabbix-server lab-agent
    if ($LASTEXITCODE -ne 0) { throw 'Could not stop monitoring services.' }
    & docker compose exec -T db pg_restore -U zabbix -d zabbix --clean --if-exists --no-owner $containerPath
    if ($LASTEXITCODE -ne 0) { throw 'Database restore failed. Services will be started for diagnosis.' }
    Write-Host 'Database restored. Run .\setup.ps1 -Start, then py -3.12 .\a1.py verify.'
} finally {
    & docker compose exec -T db rm -f $containerPath 2>$null | Out-Null
    & docker compose start zabbix-server web lab-agent | Out-Null
    Pop-Location
}
