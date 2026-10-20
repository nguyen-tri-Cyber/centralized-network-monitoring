[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://127.0.0.1:8080',
    [string]$Username = 'Admin'
)

$ErrorActionPreference = 'Stop'
if ($Username -ne 'Admin') { throw 'The complete A1 lab provisioner uses the Admin account.' }
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $projectDir
try {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        throw 'Python 3.12 launcher (py) is missing.'
    }
    & py -3.12 .\a1.py --url $BaseUrl provision
    if ($LASTEXITCODE -ne 0) { throw 'A1 lab provisioning failed.' }
} finally {
    Pop-Location
}
