[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$folder = Join-Path $projectDir "backups\$stamp"
New-Item -ItemType Directory -Path $folder -Force | Out-Null
$dumpPath = Join-Path $folder 'zabbix.dump'
$containerPath = "/tmp/a1-$stamp.dump"

Push-Location $projectDir
try {
    $containerId = (& docker compose ps -q db).Trim()
    if (-not $containerId) { throw 'Database container is not running.' }
    & docker compose exec -T db pg_dump -U zabbix -d zabbix -Fc -f $containerPath
    if ($LASTEXITCODE -ne 0) { throw 'pg_dump failed.' }
    & docker cp "${containerId}:$containerPath" $dumpPath
    if ($LASTEXITCODE -ne 0) { throw 'docker cp failed.' }
    if ((Get-Item -LiteralPath $dumpPath).Length -lt 100000) { throw 'Backup dump is unexpectedly small.' }
    Copy-Item -LiteralPath (Join-Path $projectDir '.env') -Destination (Join-Path $folder '.env')
    $accounts = Join-Path $projectDir 'local-accounts.json'
    if (Test-Path -LiteralPath $accounts) {
        Copy-Item -LiteralPath $accounts -Destination (Join-Path $folder 'local-accounts.json')
    }
    $manifest = @{
        created_at_utc = [DateTime]::UtcNow.ToString('o')
        dump_sha256 = (Get-FileHash -LiteralPath $dumpPath -Algorithm SHA256).Hash
        dump_bytes = (Get-Item -LiteralPath $dumpPath).Length
        note = 'Contains database and local lab secrets; keep private.'
    }
    $manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $folder 'manifest.json') -Encoding UTF8
    Write-Host "Backup created: $folder"
    Write-Host 'Run .\verify-backup.ps1 -BackupDir <folder> to validate a scratch restore.'
} finally {
    & docker compose exec -T db rm -f $containerPath 2>$null | Out-Null
    Pop-Location
}
