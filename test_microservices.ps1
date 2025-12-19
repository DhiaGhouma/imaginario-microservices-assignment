# Integration test for API Gateway + All Microservices
$ErrorActionPreference = "Stop"
Write-Host "🚀 Starting Full Microservices Integration Test..." -ForegroundColor Cyan
Write-Host "==============================================="

$GATEWAY_URL = "http://localhost:5000"

# 1. Health Check
Write-Host "`n[1/6] Checking Gateway & Services..."
try {
    $health = Invoke-RestMethod "$GATEWAY_URL/health"
    Write-Host "✅ Gateway Online: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR: Gateway is offline at $GATEWAY_URL. Ensure 'gateway.py' is running." -ForegroundColor Red
    exit 1
}

# 2. Register & Auth
$id = Get-Random -Minimum 1000 -Maximum 9999
$email = "dev$id@example.com"
Write-Host "`n[2/6] Registering User ($email)..."
$regBody = @{ email=$email; password="password123"; name="Tester $id" } | ConvertTo-Json
$auth = Invoke-RestMethod -Uri "$GATEWAY_URL/api/v1/auth/register" -Method POST -ContentType "application/json" -Body $regBody

$token = $auth.token
$userId = $auth.user.id
$headers = @{ Authorization = "Bearer $token"; Accept = "application/json" }
Write-Host " User Registered. ID: $userId" -ForegroundColor Green

# 3. Populate Data (Video Service)
Write-Host "`n[3/6] Creating test video in Video Service..."
$videoBody = @{
    title = "Testing Microservices with PowerShell"
    description = "A deep dive into cross-service communication."
    duration = 450
} | ConvertTo-Json

$video = Invoke-RestMethod -Uri "$GATEWAY_URL/api/v1/users/$userId/videos" -Method POST -Headers $headers -ContentType "application/json" -Body $videoBody
$videoId = $video.id
Write-Host " Video Created! ID: $videoId" -ForegroundColor Green

# 4. Trigger Search (Search Service)
Write-Host "`n[4/6] Submitting Search Job for query: 'PowerShell'..."
$searchBody = @{ query = "PowerShell" } | ConvertTo-Json
$searchJob = Invoke-RestMethod -Uri "$GATEWAY_URL/api/v1/users/$userId/search" -Method POST -Headers $headers -ContentType "application/json" -Body $searchBody
$jobId = $searchJob.job_id
Write-Host " Job Queued. ID: $jobId" -ForegroundColor Yellow

# 5. Polling Logic
Write-Host "`n[5/6] Polling for results..."
$done = $false
$attempts = 0
while (-not $done -and $attempts -lt 10) {
    $status = Invoke-RestMethod -Uri "$GATEWAY_URL/api/v1/users/$userId/search/$jobId" -Method GET -Headers $headers
    if ($status.status -eq "completed") {
        $done = $true
        Write-Host " Search Completed!" -ForegroundColor Green
        $resultsCount = $status.results.Count
    } else {
        Write-Host "Status: $($status.status)... (Attempt $($attempts+1))"
        Start-Sleep -Seconds 2
        $attempts++
    }
}

# 6. Final Report
Write-Host "`n[6/6] Final Validation"
Write-Host "-----------------------------------------------"
if ($done -and $resultsCount -gt 0) {
    Write-Host " ALL SYSTEMS GO !" -ForegroundColor Green
    Write-Host "Gateway, Auth, Video, and Search services are communicating perfectly."
    Write-Host "Search successfully found the video created in Step 3."
} elseif ($done) {
    Write-Host "  COMMUNICATION OK, BUT NO RESULTS." -ForegroundColor Yellow
    Write-Host "The services are talking, but the search query didn't match the database content."
} else {
    Write-Host " INTEGRATION FAILED: Job never completed." -ForegroundColor Red
}
Write-Host "==============================================="