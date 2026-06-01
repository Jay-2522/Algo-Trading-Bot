$ErrorActionPreference = "Continue"

$BaseUrl = if ($env:NEXT_PUBLIC_API_BASE_URL) { $env:NEXT_PUBLIC_API_BASE_URL } else { "http://127.0.0.1:8000" }
$FrontendUrl = if ($env:FRONTEND_URL) { $env:FRONTEND_URL } else { "http://localhost:3000/dashboard" }

Write-Host "Backend health:"
Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get

Write-Host "Frontend health:"
Invoke-WebRequest -Uri $FrontendUrl -Method Get -UseBasicParsing | Select-Object StatusCode, StatusDescription

Write-Host "Runtime status:"
Invoke-RestMethod -Uri "$BaseUrl/deployment/runtime/status" -Method Get
