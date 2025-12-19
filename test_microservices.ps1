# ============================================================================
# COMPREHENSIVE MICROSERVICES INTEGRATION TEST
# Tests: Gateway, Auth, Video, Search, Analytics, and Developer Dashboard
# ============================================================================

$ErrorActionPreference = "Stop"
$GATEWAY_URL = "http://localhost:5000"

# Test Results Tracking
$tests = @{
    passed = 0
    failed = 0
    results = @()
}

function Test-Assertion {
    param($name, $condition, $details = "")
    
    if ($condition) {
        Write-Host "   $name" -ForegroundColor Green
        $tests.passed++
        $tests.results += @{ name=$name; passed=$true; details=$details }
    } else {
        Write-Host "   $name" -ForegroundColor Red
        if ($details) { Write-Host "     $details" -ForegroundColor Gray }
        $tests.failed++
        $tests.results += @{ name=$name; passed=$false; details=$details }
    }
}

function Write-Section {
    param($title)
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host " $title" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

function Write-SubSection {
    param($title)
    Write-Host "`n[$title]" -ForegroundColor Yellow
}

# ============================================================================
# TEST 1: SERVICE HEALTH CHECKS
# ============================================================================
Write-Section "TEST 1: Service Health Checks"

Write-SubSection "Gateway Health"
try {
    $health = Invoke-RestMethod "$GATEWAY_URL/health" -TimeoutSec 5
    Test-Assertion "Gateway is online" ($health.status -eq "healthy")
} catch {
    Test-Assertion "Gateway is online" $false "Cannot connect to $GATEWAY_URL"
    Write-Host "` Gateway is down. Cannot continue tests." -ForegroundColor Red
    exit 1
}

Write-SubSection "Individual Services (via Gateway)"
$services = @(
    @{name="Auth Service"; url="http://localhost:5002/health"},
    @{name="Search Service"; url="http://localhost:5001/health"},
    @{name="Video Service"; url="http://localhost:5003/health"},
    @{name="Analytics Service"; url="http://localhost:5004/health"}
)

foreach ($service in $services) {
    try {
        $sHealth = Invoke-RestMethod $service.url -TimeoutSec 3
        Test-Assertion "$($service.name) is healthy" ($sHealth.status -eq "healthy")
    } catch {
        Test-Assertion "$($service.name) is healthy" $false "Service may be down"
    }
}

# ============================================================================
# TEST 2: AUTHENTICATION & AUTHORIZATION
# ============================================================================
Write-Section "TEST 2: Authentication & Authorization"

$randomId = Get-Random -Minimum 1000 -Maximum 9999
$testEmail = "test$randomId@example.com"
$testPassword = "SecurePass123!"

Write-SubSection "User Registration"
try {
    $regBody = @{
        email = $testEmail
        password = $testPassword
        name = "Test User $randomId"
    } | ConvertTo-Json

    $regResponse = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/auth/register" `
        -Method POST `
        -ContentType "application/json" `
        -Body $regBody

    Test-Assertion "User can register" ($regResponse.token -ne $null)
    Test-Assertion "Registration returns user ID" ($regResponse.user.id -ne $null)
    Test-Assertion "Registration returns JWT token" ($regResponse.token.StartsWith("eyJ"))
    
    $token = $regResponse.token
    $userId = $regResponse.user.id
} catch {
    Test-Assertion "User can register" $false $_.Exception.Message
    Write-Host "`Cannot continue without authentication" -ForegroundColor Red
    exit 1
}

Write-SubSection "User Login"
try {
    $loginBody = @{
        email = $testEmail
        password = $testPassword
    } | ConvertTo-Json

    $loginResponse = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/auth/login" `
        -Method POST `
        -ContentType "application/json" `
        -Body $loginBody

    Test-Assertion "User can login" ($loginResponse.token -ne $null)
    Test-Assertion "Login returns same user ID" ($loginResponse.user.id -eq $userId)
    Test-Assertion "Login token is valid JWT" ($loginResponse.token.StartsWith("eyJ"))
} catch {
    Test-Assertion "User can login" $false $_.Exception.Message
}

Write-SubSection "Invalid Credentials"
try {
    $badLoginBody = @{
        email = $testEmail
        password = "WrongPassword"
    } | ConvertTo-Json

    $badLogin = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/auth/login" `
        -Method POST `
        -ContentType "application/json" `
        -Body $badLoginBody `
        -ErrorAction Stop

    Test-Assertion "Rejects invalid credentials" $false "Should have returned 401"
} catch {
    Test-Assertion "Rejects invalid credentials" ($_.Exception.Response.StatusCode.value__ -eq 401)
}

Write-SubSection "Protected Endpoint Access"
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

try {
    $videosResponse = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/users/$userId/videos" `
        -Method GET `
        -Headers $headers

    Test-Assertion "Can access protected endpoints with token" $true
} catch {
    Test-Assertion "Can access protected endpoints with token" $false
}

# ============================================================================
# TEST 3: API KEY MANAGEMENT
# ============================================================================
Write-Section "TEST 3: API Key Management"

Write-SubSection "Create API Key"
try {
    $keyBody = @{
        name = "Test API Key $randomId"
    } | ConvertTo-Json

    $keyResponse = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/auth/api-keys" `
        -Method POST `
        -Headers $headers `
        -Body $keyBody

    Test-Assertion "Can create API key" ($keyResponse.api_key -ne $null)
    Test-Assertion "API key starts with prefix" ($keyResponse.api_key.StartsWith("imaginario_live_"))
    
    $apiKey = $keyResponse.api_key
    $apiKeyId = $keyResponse.api_key_id
} catch {
    Test-Assertion "Can create API key" $false $_.Exception.Message
}

Write-SubSection "List API Keys"
try {
    $keysList = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/auth/api-keys" `
        -Method GET `
        -Headers $headers

    Test-Assertion "Can list API keys" ($keysList.api_keys -ne $null)
    Test-Assertion "Created key appears in list" ($keysList.api_keys.Count -gt 0)
} catch {
    Test-Assertion "Can list API keys" $false
}

Write-SubSection "Delete API Key"
try {
    $deleteResponse = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/auth/api-keys/$apiKeyId" `
        -Method DELETE `
        -Headers $headers

    Test-Assertion "Can delete API key" ($deleteResponse.message -ne $null)
} catch {
    Test-Assertion "Can delete API key" $false
}

# ============================================================================
# TEST 4: VIDEO SERVICE (CRUD OPERATIONS)
# ============================================================================
Write-Section "TEST 4: Video Service CRUD Operations"

Write-SubSection "Create Videos"
$testVideos = @(
    @{title="PowerShell Automation"; description="Learn PowerShell scripting"; duration=450},
    @{title="Microservices Architecture"; description="Building scalable systems"; duration=720},
    @{title="Docker Tutorial"; description="Containerization basics"; duration=600}
)

$videoIds = @()
foreach ($videoData in $testVideos) {
    try {
        $videoBody = $videoData | ConvertTo-Json
        $videoResponse = Invoke-RestMethod `
            -Uri "$GATEWAY_URL/api/v1/users/$userId/videos" `
            -Method POST `
            -Headers $headers `
            -Body $videoBody

        Test-Assertion "Create video: $($videoData.title)" ($videoResponse.id -ne $null)
        $videoIds += $videoResponse.id
    } catch {
        Test-Assertion "Create video: $($videoData.title)" $false
    }
}

Write-SubSection "List Videos"
try {
    $videosList = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/users/$userId/videos" `
        -Method GET `
        -Headers $headers

    Test-Assertion "Can list videos" ($videosList -ne $null)
    Test-Assertion "All created videos appear" ($videosList.Count -ge 3)
} catch {
    Test-Assertion "Can list videos" $false
}

Write-SubSection "Get Single Video"
if ($videoIds.Count -gt 0) {
    try {
        $singleVideo = Invoke-RestMethod `
            -Uri "$GATEWAY_URL/api/v1/users/$userId/videos/$($videoIds[0])" `
            -Method GET `
            -Headers $headers

        Test-Assertion "Can get single video" ($singleVideo.id -eq $videoIds[0])
        Test-Assertion "Video has correct fields" ($singleVideo.title -ne $null)
    } catch {
        Test-Assertion "Can get single video" $false
    }
}

Write-SubSection "Update Video"
if ($videoIds.Count -gt 0) {
    try {
        $updateBody = @{
            title = "Updated Title"
            description = "Updated Description"
        } | ConvertTo-Json

        $updatedVideo = Invoke-RestMethod `
            -Uri "$GATEWAY_URL/api/v1/users/$userId/videos/$($videoIds[0])" `
            -Method PUT `
            -Headers $headers `
            -Body $updateBody

        Test-Assertion "Can update video" ($updatedVideo.title -eq "Updated Title")
    } catch {
        Test-Assertion "Can update video" $false
    }
}

Write-SubSection "Delete Video"
if ($videoIds.Count -gt 2) {
    try {
        $deleteResponse = Invoke-RestMethod `
            -Uri "$GATEWAY_URL/api/v1/users/$userId/videos/$($videoIds[2])" `
            -Method DELETE `
            -Headers $headers

        Test-Assertion "Can delete video" ($deleteResponse.message -ne $null)
    } catch {
        Test-Assertion "Can delete video" $false
    }
}

# ============================================================================
# TEST 5: SEARCH SERVICE (ASYNC PROCESSING)
# ============================================================================
Write-Section "TEST 5: Search Service & Async Processing"

# Around line 400
Write-SubSection "Submit Search Job"
try {
    $searchBody = @{
        query = "Microservices"  
    } | ConvertTo-Json

    $searchResponse = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/users/$userId/search" `
        -Method POST `
        -Headers $headers `
        -Body $searchBody

    Test-Assertion "Search job created" ($searchResponse.job_id -ne $null)
    Test-Assertion "Job status is pending/queued" ($searchResponse.status -in @("pending", "queued"))
    
    $jobId = $searchResponse.job_id
} catch {
    Test-Assertion "Search job created" $false $_.Exception.Message
}

Write-SubSection "Poll for Search Results"
$maxAttempts = 10
$attempt = 0
$jobCompleted = $false
$searchResults = $null

while ($attempt -lt $maxAttempts -and -not $jobCompleted) {
    try {
        $jobStatus = Invoke-RestMethod `
            -Uri "$GATEWAY_URL/api/v1/users/$userId/search/$jobId" `
            -Method GET `
            -Headers $headers

        if ($jobStatus.status -eq "completed") {
            $jobCompleted = $true
            $searchResults = $jobStatus.results
            Write-Host "  Job completed in attempt $($attempt + 1)" -ForegroundColor Gray
        } elseif ($jobStatus.status -eq "failed") {
            break
        } else {
            Write-Host "  Polling... Status: $($jobStatus.status) (Attempt $($attempt + 1))" -ForegroundColor Gray
            Start-Sleep -Seconds 1
        }
        $attempt++
    } catch {
        break
    }
}
# Add this debug code to your test script right after "Poll for Search Results" section (around line 440)

Write-Host "`n=== DEBUG INFORMATION ===" -ForegroundColor Magenta

# 1. Show the job status details
Write-Host "`nSearch Job Details:" -ForegroundColor Yellow
Write-Host "Job ID: $jobId" -ForegroundColor Gray
Write-Host "Job Completed: $jobCompleted" -ForegroundColor Gray
Write-Host "Full Job Status:" -ForegroundColor Gray
Write-Host ($jobStatus | ConvertTo-Json -Depth 5) -ForegroundColor Gray

# 2. Check how many videos exist
Write-Host "`nChecking Videos in Database:" -ForegroundColor Yellow
try {
    $allVideos = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/users/$userId/videos" `
        -Method GET `
        -Headers $headers
    
    Write-Host "Total videos for this user: $($allVideos.Count)" -ForegroundColor Gray
    foreach ($v in $allVideos) {
        Write-Host "  - Video ID: $($v.id), Title: '$($v.title)', User: $($v.user_id)" -ForegroundColor Gray
    }
} catch {
    Write-Host "Could not fetch videos: $($_.Exception.Message)" -ForegroundColor Red
}

# 3. Try a direct search (without user_id in URL)
Write-Host "`nTrying Direct Search (no user_id filter):" -ForegroundColor Yellow
try {
    $directSearch = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/search" `
        -Method POST `
        -Headers $headers `
        -Body (@{query="Automation"} | ConvertTo-Json)
    
    Start-Sleep -Seconds 2
    
    $directResults = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/search/$($directSearch.job_id)" `
        -Method GET `
        -Headers $headers
    
    Write-Host "Direct search results count: $($directResults.results.Count)" -ForegroundColor Gray
    Write-Host ($directResults | ConvertTo-Json -Depth 5) -ForegroundColor Gray
} catch {
    Write-Host "Direct search failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== END DEBUG ===" -ForegroundColor Magenta

Test-Assertion "Search job completes" $jobCompleted
Test-Assertion "Search returns results" ($searchResults.Count -gt 0)
if ($searchResults.Count -gt 0) {
    Test-Assertion "Results have relevance scores" ($searchResults[0].relevance_score -ne $null)
    Test-Assertion "Results have video IDs" ($searchResults[0].video_id -ne $null)
}

Write-SubSection "Search Different Query"
try {
    $searchBody2 = @{
        query = "Microservices"
    } | ConvertTo-Json

    $searchResponse2 = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/users/$userId/search" `
        -Method POST `
        -Headers $headers `
        -Body $searchBody2

    $jobId2 = $searchResponse2.job_id
    
    Start-Sleep -Seconds 2
    
    $jobStatus2 = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/users/$userId/search/$jobId2" `
        -Method GET `
        -Headers $headers

    Test-Assertion "Multiple searches work independently" ($jobStatus2.job_id -eq $jobId2)
} catch {
    Test-Assertion "Multiple searches work independently" $false
}

# ============================================================================
# TEST 6: ANALYTICS & DEVELOPER DASHBOARD
# ============================================================================
Write-Section "TEST 6: Analytics & Developer Dashboard"

Write-SubSection "Analytics Overview"
try {
    $analytics = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/analytics/overview" `
        -Method GET `
        -Headers $headers

    Test-Assertion "Can get analytics overview" ($analytics -ne $null)
    Test-Assertion "Analytics has total_requests" ($analytics.total_requests -ne $null)
    Test-Assertion "Analytics has success_rate" ($analytics.success_rate -ne $null)
    Test-Assertion "Analytics has endpoint breakdown" ($analytics.requests_by_endpoint -ne $null)
} catch {
    Test-Assertion "Can get analytics overview" $false $_.Exception.Message
}

Write-SubSection "Search Jobs List (Dashboard)"
try {
    $jobsList = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/search/jobs?per_page=20" `
        -Method GET `
        -Headers $headers

    Test-Assertion "Can list search jobs" ($jobsList -ne $null)
    Test-Assertion "Jobs list has correct structure" ($jobsList.jobs -ne $null)
    Test-Assertion "Jobs list shows created searches" ($jobsList.jobs.Count -ge 2)
} catch {
    Test-Assertion "Can list search jobs" $false $_.Exception.Message
}

# ============================================================================
# TEST 7: ERROR HANDLING & EDGE CASES
# ============================================================================
Write-Section "TEST 7: Error Handling & Edge Cases"

Write-SubSection "Invalid Requests"

# Missing required fields
try {
    $badVideoBody = @{description="No title"} | ConvertTo-Json
    $badVideo = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/users/$userId/videos" `
        -Method POST `
        -Headers $headers `
        -Body $badVideoBody `
        -ErrorAction Stop
    Test-Assertion "Rejects invalid video (missing title)" $false
} catch {
    Test-Assertion "Rejects invalid video (missing title)" ($_.Exception.Response.StatusCode.value__ -eq 400)
}

# Invalid user ID
try {
    $wrongUserVideos = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/users/99999/videos" `
        -Method GET `
        -Headers $headers `
        -ErrorAction Stop
    Test-Assertion "Rejects access to other user's data" $false
} catch {
    Test-Assertion "Rejects access to other user's data" ($_.Exception.Response.StatusCode.value__ -eq 403)
}

# Non-existent job
try {
    $fakeJob = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/users/$userId/search/fake-job-id" `
        -Method GET `
        -Headers $headers `
        -ErrorAction Stop
    Test-Assertion "Returns 404 for non-existent job" $false
} catch {
    Test-Assertion "Returns 404 for non-existent job" ($_.Exception.Response.StatusCode.value__ -eq 404)
}

Write-SubSection "Unauthorized Access"
try {
    $noAuthVideos = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/users/$userId/videos" `
        -Method GET `
        -ErrorAction Stop
    Test-Assertion "Requires authentication" $false
} catch {
    Test-Assertion "Requires authentication" ($_.Exception.Response.StatusCode.value__ -eq 401)
}

# ============================================================================
# TEST 8: CONCURRENT OPERATIONS
# ============================================================================
Write-Section "TEST 8: Concurrent Operations"

Write-SubSection "Parallel Search Jobs"
$parallelJobs = @()

for ($i = 1; $i -le 3; $i++) {
    try {
        $searchBody = @{query="Test Query $i"} | ConvertTo-Json
        $job = Invoke-RestMethod `
            -Uri "$GATEWAY_URL/api/v1/users/$userId/search" `
            -Method POST `
            -Headers $headers `
            -Body $searchBody
        $parallelJobs += $job.job_id
    } catch {
        # Continue
    }
}

Test-Assertion "Can submit multiple concurrent searches" ($parallelJobs.Count -eq 3)

Start-Sleep -Seconds 3

$completedJobs = 0
foreach ($jobId in $parallelJobs) {
    try {
        $status = Invoke-RestMethod `
            -Uri "$GATEWAY_URL/api/v1/users/$userId/search/$jobId" `
            -Method GET `
            -Headers $headers
        if ($status.status -eq "completed") {
            $completedJobs++
        }
    } catch {
    }
}

Test-Assertion "All concurrent jobs complete" ($completedJobs -eq 3)

# ============================================================================
# FINAL REPORT
# ============================================================================
Write-Section "TEST RESULTS SUMMARY"

Write-Host "`nTotal Tests Run: $($tests.passed + $tests.failed)" -ForegroundColor White
Write-Host "Passed: $($tests.passed)" -ForegroundColor Green
Write-Host "Failed: $($tests.failed)" -ForegroundColor Red

if ($tests.failed -eq 0) {
    Write-Host " ALL TESTS PASSED! " -ForegroundColor Green
    Write-Host "Your microservices architecture is working perfectly!" -ForegroundColor Green
} else {
    Write-Host "`  Some tests failed. Review the output above." -ForegroundColor Yellow
    
    Write-Host "`Failed Tests:" -ForegroundColor Red
    foreach ($result in $tests.results) {
        if (-not $result.passed) {
            Write-Host "  • $($result.name)" -ForegroundColor Red
            if ($result.details) {
                Write-Host "    $($result.details)" -ForegroundColor Gray
            }
        }
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan

# Calculate success rate
$successRate = [math]::Round(($tests.passed / ($tests.passed + $tests.failed)) * 100, 2)
Write-Host "Success Rate: $successRate%" -ForegroundColor $(if ($successRate -gt 90) {"Green"} elseif ($successRate -gt 70) {"Yellow"} else {"Red"})

Write-Host "========================================`n" -ForegroundColor Cyan

# Exit code
exit $(if ($tests.failed -eq 0) {0} else {1})