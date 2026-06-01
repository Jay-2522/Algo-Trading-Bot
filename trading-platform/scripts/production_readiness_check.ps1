param(
    [string]$BaseUrl = $(if ($env:NEXT_PUBLIC_API_BASE_URL) { $env:NEXT_PUBLIC_API_BASE_URL } else { "http://127.0.0.1:8000" })
)

$ErrorActionPreference = "Stop"

Write-Host "Production readiness certification check"
Write-Host "Base URL: $BaseUrl"

$checks = @(
    "/production-readiness/status",
    "/production-readiness/report",
    "/deployment/readiness",
    "/security/status",
    "/monitoring/health",
    "/backup/status"
)

foreach ($path in $checks) {
    $url = "$BaseUrl$path"
    Write-Host ""
    Write-Host "GET $url"
    try {
        $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 10
        $response | ConvertTo-Json -Depth 10
    }
    catch {
        Write-Error "Production readiness check failed for $path`: $($_.Exception.Message)"
    }
}
