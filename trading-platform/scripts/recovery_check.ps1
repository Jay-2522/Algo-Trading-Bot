param(
    [string]$BaseUrl = $(if ($env:NEXT_PUBLIC_API_BASE_URL) { $env:NEXT_PUBLIC_API_BASE_URL } else { "http://127.0.0.1:8000" })
)

$ErrorActionPreference = "Stop"

Write-Host "Recovery readiness check"
Write-Host "Base URL: $BaseUrl"

$checks = @(
    "/backup/recovery",
    "/backup/rollback",
    "/backup/incident-response",
    "/monitoring/health"
)

foreach ($path in $checks) {
    $url = "$BaseUrl$path"
    Write-Host ""
    Write-Host "GET $url"
    try {
        $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 10
        $response | ConvertTo-Json -Depth 8
    }
    catch {
        Write-Error "Recovery check failed for $path`: $($_.Exception.Message)"
    }
}
