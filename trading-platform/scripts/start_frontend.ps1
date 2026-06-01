$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $ProjectRoot "frontend")

Write-Host "Starting frontend on http://127.0.0.1:3000"
npm run dev
