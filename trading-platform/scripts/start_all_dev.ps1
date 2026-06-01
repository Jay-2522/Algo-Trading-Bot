$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendScript = Join-Path $PSScriptRoot "start_backend.ps1"
$FrontendScript = Join-Path $PSScriptRoot "start_frontend.ps1"

Write-Host "Starting backend and frontend in separate PowerShell windows."
Write-Host "Project root: $ProjectRoot"

Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$BackendScript`""
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$FrontendScript`""
