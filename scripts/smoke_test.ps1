# Project Fortify - Docker stack smoke test
# Run from project root after: docker compose up --build -d

$ErrorActionPreference = "Stop"
$api  = "http://localhost:8000"
$dash = "http://localhost:8501"
$pass = 0
$fail = 0

function Test-Step($label, $block) {
    try {
        & $block
        Write-Host "[PASS] $label" -ForegroundColor Green
        $script:pass++
    } catch {
        Write-Host "[FAIL] $label - $_" -ForegroundColor Red
        $script:fail++
    }
}

Test-Step "API health endpoint returns healthy" {
    $r = Invoke-RestMethod "$api/health"
    if ($r.status -ne "healthy") { throw "status=$($r.status)" }
}

Test-Step "Unauthenticated /api/v1/vms returns 401" {
    try { Invoke-RestMethod "$api/api/v1/vms" }
    catch {
        if ($_.Exception.Response.StatusCode.value__ -ne 401) {
            throw "expected 401, got $($_.Exception.Response.StatusCode.value__)"
        }
    }
}

Test-Step "POST /auth/token returns a JWT" {
    $body = "username=admin&password=admin123"
    $script:token = (Invoke-RestMethod -Method POST "$api/auth/token" `
        -ContentType "application/x-www-form-urlencoded" `
        -Body $body).access_token
    if (-not $script:token) { throw "empty token" }
}

Test-Step "Authenticated /api/v1/vms/summary returns data" {
    $r = Invoke-RestMethod "$api/api/v1/vms/summary" `
        -Headers @{ Authorization = "Bearer $($script:token)" }
    if (-not $r) { throw "empty response" }
}

Test-Step "Streamlit frontend responds on port 8501" {
    $r = Invoke-WebRequest "$dash/_stcore/health" -UseBasicParsing
    if ($r.StatusCode -ne 200) { throw "status $($r.StatusCode)" }
}

Write-Host ""
$color = if ($fail -eq 0) { "Green" } else { "Red" }
Write-Host "Results: $pass passed, $fail failed" -ForegroundColor $color
if ($fail -gt 0) { exit 1 }
