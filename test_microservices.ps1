# Integration test for API Gateway + Search Service (PowerShell)
# Verifies inter-service communication through the gateway

$ErrorActionPreference = "Stop" # Stop on errors
Write-Host "Testing Microservices Integration..." -ForegroundColor Cyan
Write-Host "==================================="

$GATEWAY_URL = "http://localhost:5000"

# Randomize email to avoid "user exists" errors during rapid testing
$id = Get-Random -Minimum 1000 -Maximum 9999
$email = "test$id@example.com"
$password = "test123"
$name = "Test User $id"

# -------------------------------
# 1. Health check
# -------------------------------
Write-Host "`n1. Testing API Gateway health..."
try {
    $health = Invoke-RestMethod "$GATEWAY_URL/health"
    Write-Host "Gateway Status: $($health.status)" -ForegroundColor Green
}
catch {
    Write-Host "❌ Gateway is offline at $GATEWAY_URL" -ForegroundColor Red
    exit 1
}

# -------------------------------
# 2. Register User
# -------------------------------
Write-Host "`n2. Registering user..."
$registerBody = @{
    email    = $email
    password = $password
    name     = $name
} | ConvertTo-Json

$authResponse = Invoke-RestMethod -Uri "$GATEWAY_URL/api/v1/auth/register" -Method POST -ContentType "application/json" -Body $registerBody
$token = $authResponse.token
$userId = $authResponse.user.id

Write-Host "User registered with ID: $userId"
$headers = @{ 
    Authorization = "Bearer $token" 
    Accept        = "application/json"
}

# -------------------------------
# 3. Create video (to populate search)
# -------------------------------
Write-Host "`n3. Creating video for search indexing..."
$videoBody = @{
    title       = "Microservices Test Video"
    description = "Content about building microservices architecture"
    duration    = 120
} | ConvertTo-Json

$video = Invoke-RestMethod -Uri "$GATEWAY_URL/api/v1/users/$userId/videos" -Method POST -Headers $headers -ContentType "application/json" -Body $videoBody
Write-Host "Video Created: $($video.title) (ID: $($video.id))"

# -------------------------------
# 4. Submit search job
# -------------------------------
Write-Host "`n4. Submitting search job via Gateway..."
$searchBody = @{
    query = "microservices"
} | ConvertTo-Json

$searchResponse = Invoke-RestMethod -Uri "$GATEWAY_URL/api/v1/users/$userId/search" -Method POST -Headers $headers -ContentType "application/json" -Body $searchBody

$jobId = $searchResponse.job_id
Write-Host "Job Submitted. JobID: $jobId" -ForegroundColor Yellow

# -------------------------------
# 5. Fetch search results (with Polling)
# -------------------------------
Write-Host "`n5. Polling for job completion..."
$retries = 0
$maxRetries = 5
$jobDone = $false

while ($retries -lt $maxRetries -and -not $jobDone) {
    $result = Invoke-RestMethod -Uri "$GATEWAY_URL/api/v1/users/$userId/search/$jobId" -Method GET -Headers $headers
    
    if ($result.status -eq "completed") {
        $jobDone = $true
        Write-Host "Job Completed!" -ForegroundColor Green
        $result | ConvertTo-Json -Depth 5
    }
    else {
        Write-Host "Status: $($result.status)... waiting 2s"
        Start-Sleep -Seconds 2
        $retries++
    }
}

# -------------------------------
# 6. Final Validation
# -------------------------------
Write-Host ""
Write-Host "==================================="
if ($jobDone) {
    if ($result.results.Count -gt 0) {
        Write-Host "✅ SUCCESS: Gateway <-> Search Service logic verified" -ForegroundColor Green
        Write-Host "Found $($result.results.Count) matches."
    }
    else {
        Write-Host "⚠ SUCCESS: Connection works, but no results found." -ForegroundColor Yellow
    }
}
else {
    Write-Host "❌ FAILED: Job timed out or failed to complete." -ForegroundColor Red
}
Write-Host "==================================="