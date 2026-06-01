$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "Starting backend with uvicorn. This script does not stop existing processes."
Write-Host "Live execution remains disabled by environment policy."
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
