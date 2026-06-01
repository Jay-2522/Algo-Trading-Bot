$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "Starting backend on http://127.0.0.1:8000"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
