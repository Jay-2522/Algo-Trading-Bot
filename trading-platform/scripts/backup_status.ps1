param(
    [string]$BaseUrl = $(if ($env:NEXT_PUBLIC_API_BASE_URL) { $env:NEXT_PUBLIC_API_BASE_URL } else { "http://127.0.0.1:8000" })
)

$ErrorActionPreference = "Stop"

Write-Host "Backup and recovery readiness status"
Write-Host "Base URL: $BaseUrl"

$checks = @(
    "/backup/status",
    "/backup/strategy",
    "/deployment/readiness"
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
        Write-Error "Backup status check failed for $path`: $($_.Exception.Message)"
    }
}
