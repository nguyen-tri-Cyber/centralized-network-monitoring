[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$BackupDir)

$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$folder = (Resolve-Path -LiteralPath $BackupDir).Path
$dumpPath = Join-Path $folder 'zabbix.dump'
if (-not (Test-Path -LiteralPath $dumpPath)) { throw 'zabbix.dump is missing.' }
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddHHmmss')
$scratch = "a1_restore_check_$stamp"
$containerPath = "/tmp/$scratch.dump"
$created = $false

Push-Location $projectDir
try {
    $containerId = (& docker compose ps -q db).Trim()
    if (-not $containerId) { throw 'Database container is not running.' }
    & docker cp $dumpPath "${containerId}:$containerPath"
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy dump into database container.' }
    & docker compose exec -T db pg_restore --list $containerPath | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'pg_restore cannot read the dump.' }
    & docker compose exec -T db createdb -U zabbix -T template0 $scratch
    if ($LASTEXITCODE -ne 0) { throw 'Could not create scratch database.' }
    $created = $true
    & docker compose exec -T db pg_restore -U zabbix --no-owner -d $scratch $containerPath
    if ($LASTEXITCODE -ne 0) { throw 'Scratch restore failed.' }
    $hostCount = (& docker compose exec -T db psql -U zabbix -d $scratch -Atc "select count(*) from hosts where host in ('A1-LAB-ENDPOINT','lab-linux-agent','A1-LAB-SNMP');").Trim()
    if ($LASTEXITCODE -ne 0 -or [int]$hostCount -ne 3) { throw 'Scratch restore is missing A1 lab hosts.' }
    Write-Host 'Backup restore check passed: all 3 A1 lab hosts are present.'
} finally {
    if ($created) { & docker compose exec -T db dropdb -U zabbix --if-exists --force $scratch | Out-Null }
    & docker compose exec -T db rm -f $containerPath 2>$null | Out-Null
    Pop-Location
}
