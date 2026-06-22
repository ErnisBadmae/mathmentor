Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

function Invoke-Native {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
  )
  & $FilePath @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
  }
}

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example. Review API_SHARED_TOKEN and LLM settings."
}

Invoke-Native docker compose up -d --build postgres api web
Invoke-Native docker compose exec -T api alembic upgrade head
Invoke-Native docker compose exec -T api python scripts/seed.py

$python = Join-Path $root "backend\.venv312\Scripts\python.exe"
if (Test-Path $python) {
  Invoke-Native $python "scripts\preview_tracker.py" --write
} else {
  Write-Host "Skipped tracker import: backend\.venv312\Scripts\python.exe was not found."
}

try {
  $lanIp = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
    Select-Object -First 1 -ExpandProperty IPAddress
} catch {
  $lanIp = "127.0.0.1"
  Write-Host "Could not determine LAN IP automatically; using 127.0.0.1."
}

Write-Host "EGE Mentor LAN URL: http://$lanIp:8088"
Write-Host "Health: http://$lanIp:8088/api/health"
