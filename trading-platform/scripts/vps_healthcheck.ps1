$ErrorActionPreference = "Stop"

$BaseUrl = if ($env:NEXT_PUBLIC_API_BASE_URL) { $env:NEXT_PUBLIC_API_BASE_URL } else { "http://127.0.0.1:8000" }
$Endpoints = @(
    "/health",
    "/deployment/status",
    "/deployment/runtime/status",
    "/monitoring/health",
    "/strategy-execution-bridge/operations/status"
)

foreach ($Endpoint in $Endpoints) {
    $Url = "$BaseUrl$Endpoint"
    Write-Host "Checking $Url"
    Invoke-RestMethod -Uri $Url -Method Get
}
