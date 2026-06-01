$ErrorActionPreference = "Stop"

$BackendScript = Join-Path $PSScriptRoot "restart_backend.ps1"
$FrontendScript = Join-Path $PSScriptRoot "restart_frontend.ps1"

Write-Host "Opening backend and frontend runtime scripts in separate PowerShell windows."
Write-Host "No API-based process killing or autonomous restart is performed."

Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$BackendScript`""
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$FrontendScript`""
