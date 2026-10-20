[CmdletBinding()]
param(
    [switch]$Start
)

$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$envPath = Join-Path $projectDir '.env'

function New-LabSecret {
    $bytes = New-Object byte[] 24
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker CLI is missing. Install or open Docker Desktop first.'
}

if (-not (Test-Path -LiteralPath $envPath)) {
    $content = @(
        "ZABBIX_DB_PASSWORD=$(New-LabSecret)"
        "SNMP_COMMUNITY=$(New-LabSecret)"
        'LAB_SUBNET=172.30.250.0/24'
        'LAB_ENDPOINT_IP=172.30.250.50'
        ''
    ) -join "`n"
    [System.IO.File]::WriteAllText($envPath, $content, [System.Text.UTF8Encoding]::new($false))
    Write-Host 'Created .env with random lab secrets.'
} else {
    Write-Host 'Using existing .env; secrets were not replaced.'
}

Push-Location $projectDir
try {
    & docker compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose configuration is invalid.' }

    if ($Start) {
        & docker info --format '{{.ServerVersion}}' | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop is not running. Open it and wait for the engine to start.' }
        & docker compose up -d --build
        if ($LASTEXITCODE -ne 0) { throw 'Container startup failed. Check docker compose ps and docker compose logs.' }
        Write-Host 'Zabbix: http://127.0.0.1:8080'
        Write-Host 'Lab mailbox: http://127.0.0.1:8025'
        Write-Host 'Wait for the Zabbix login page, then change the default Admin password.'
    } else {
        Write-Host 'Compose configuration is valid. Run .\setup.ps1 -Start after Docker Desktop is running.'
    }
} finally {
    Pop-Location
}

