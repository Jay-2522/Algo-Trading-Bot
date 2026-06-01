$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $ProjectRoot "frontend")

Write-Host "Starting frontend dev server. This script does not stop existing processes."
npm run dev
