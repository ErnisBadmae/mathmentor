Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

$backupDir = Join-Path $root "backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$target = Join-Path $backupDir "ege_mentor_$stamp.sql"

docker compose exec -T postgres pg_dump -U ege -d ege_mentor | Out-File -FilePath $target -Encoding utf8
Write-Host "Backup written: $target"
