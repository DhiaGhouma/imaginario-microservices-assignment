# Integration test for API Gateway + Search Service (PowerShell)
# Verifies inter-service communication through the gateway

Write-Host "Testing Microservices Integration..."
Write-Host "==================================="

$GATEWAY_URL = "http://localhost:5000"

$email = "test@example.com"
$password = "test123"
$name = "Test User"

# -------------------------------
# 1. Health check
# -------------------------------
Write-Host "`n1. Testing API Gateway health..."
try {
    $health = Invoke-RestMethod "$GATEWAY_URL/health"
    $health | ConvertTo-Json -Depth 5
}
catch {
    Write-Host "❌ Gateway health failed"
    exit 1
}

# -------------------------------
# 2. Register / Login
# -------------------------------
Write-Host "`n2. Registering user..."
$token = $null
$userId = $null

$registerBody = @{
    email    = $email
    password = $password
    name     = $name
} | ConvertTo-Json

try {
    $registerResponse = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/auth/register" `
        -Method POST `
        -ContentType "application/json" `
        -Body $registerBody

    $token = $registerResponse.token
    $userId = $registerResponse.user.id
}
catch {
    Write-Host "User probably exists, attempting login..."
    $loginBody = @{
        email    = $email
        password = $password
    } | ConvertTo-Json

    try {
        $loginResponse = Invoke-RestMethod `
            -Uri "$GATEWAY_URL/api/v1/auth/login" `
            -Method POST `
            -ContentType "application/json" `
            -Body $loginBody

        $token = $loginResponse.token
        $userId = $loginResponse.user.id
    }
    catch {
        Write-Host "❌ Login failed"
        exit 1
    }
}

Write-Host "User ID: $userId"
Write-Host "Token acquired"

# -------------------------------
# 3. Create video
# -------------------------------
Write-Host "`n3. Creating video..."
$videoBody = @{
    title       = "Microservices Test"
    description = "Search integration test"
    duration    = 90
} | ConvertTo-Json

$videoResponse = Invoke-RestMethod `
    -Uri "$GATEWAY_URL/api/v1/users/$userId/videos" `
    -Method POST `
    -Headers @{ Authorization = "Bearer $token" } `
    -ContentType "application/json" `
    -Body $videoBody

$videoResponse | ConvertTo-Json -Depth 5

# -------------------------------
# 4. Submit search job
# -------------------------------
Write-Host "`n4. Submitting search job..."
$searchBody = @{
    query = "microservices"
} | ConvertTo-Json

$searchResponse = Invoke-RestMethod `
    -Uri "$GATEWAY_URL/api/v1/users/$userId/search" `
    -Method POST `
    -Headers @{ Authorization = "Bearer $token" } `
    -ContentType "application/json" `
    -Body $searchBody

$searchResponse | ConvertTo-Json -Depth 5

$jobId = $searchResponse.job_id

if (-not $jobId) {
    Write-Host "❌ Search job creation failed"
    exit 1
}

# -------------------------------
# 5. Fetch search results
# -------------------------------
Write-Host "`n5. Waiting for job completion..."
Start-Sleep -Seconds 2

try {
    $result = Invoke-RestMethod `
        -Uri "$GATEWAY_URL/api/v1/users/$userId/search/$jobId" `
        -Method GET `
        -Headers @{ Authorization = "Bearer $token" }

    $result | ConvertTo-Json -Depth 5
}
catch {
    Write-Host "❌ Failed to fetch search results"
    exit 1
}

# -------------------------------
# 6. Final status
# -------------------------------
Write-Host ""
Write-Host "==================================="

if ($result.status -eq "completed") {
    Write-Host "✅ SUCCESS: Gateway <-> Search Service communication verified"
}
else {
    Write-Host "⚠ WARNING: Job not completed yet (async behavior)"
}

Write-Host "==================================="
