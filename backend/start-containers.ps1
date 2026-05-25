# Start Redis and Qdrant containers for Migration Copilot
# PowerShell script for Windows

Write-Host "Starting Migration Copilot containers..." -ForegroundColor Green

# Create network if it doesn't exist
Write-Host ""
Write-Host "Creating network..." -ForegroundColor Yellow
podman network create mig26-network 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Network created successfully" -ForegroundColor Green
} else {
    Write-Host "Network already exists or created" -ForegroundColor Cyan
}

# Create volumes if they don't exist
Write-Host ""
Write-Host "Creating volumes..." -ForegroundColor Yellow
podman volume create redis-data 2>$null
podman volume create qdrant-data 2>$null
Write-Host "Volumes ready" -ForegroundColor Green

# Start Redis
Write-Host ""
Write-Host "Starting Redis..." -ForegroundColor Yellow
podman run -d --name mig26-redis --network mig26-network -p 6379:6379 -v redis-data:/data docker.io/redis:7-alpine redis-server --appendonly yes

if ($LASTEXITCODE -eq 0) {
    Write-Host "Redis started successfully" -ForegroundColor Green
} else {
    Write-Host "Redis may already be running" -ForegroundColor Cyan
}

# Start Qdrant
Write-Host ""
Write-Host "Starting Qdrant..." -ForegroundColor Yellow
podman run -d --name mig26-qdrant --network mig26-network -p 6333:6333 -p 6334:6334 -v qdrant-data:/qdrant/storage -e QDRANT__SERVICE__GRPC_PORT=6334 docker.io/qdrant/qdrant:latest

if ($LASTEXITCODE -eq 0) {
    Write-Host "Qdrant started successfully" -ForegroundColor Green
} else {
    Write-Host "Qdrant may already be running" -ForegroundColor Cyan
}

# Wait for containers to be healthy
Write-Host ""
Write-Host "Waiting for containers to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check Redis
Write-Host ""
Write-Host "Checking Redis..." -ForegroundColor Yellow
$redisStatus = podman exec mig26-redis redis-cli ping 2>$null
if ($redisStatus -eq "PONG") {
    Write-Host "Redis is healthy" -ForegroundColor Green
} else {
    Write-Host "Redis is not responding" -ForegroundColor Red
}

# Check Qdrant
Write-Host ""
Write-Host "Checking Qdrant..." -ForegroundColor Yellow
$qdrantHealthy = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:6333/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        $qdrantHealthy = $true
    }
} catch {
    $qdrantHealthy = $false
}

if ($qdrantHealthy) {
    Write-Host "Qdrant is healthy" -ForegroundColor Green
} else {
    Write-Host "Qdrant is not responding yet (may need more time)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Containers Status:" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
podman ps --filter "name=mig26-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Service URLs:" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Redis:   redis://localhost:6379" -ForegroundColor White
Write-Host "Qdrant:  http://localhost:6333" -ForegroundColor White
Write-Host "Qdrant Dashboard: http://localhost:6333/dashboard" -ForegroundColor White

Write-Host ""
Write-Host "Containers started successfully!" -ForegroundColor Green
Write-Host "Use 'podman logs mig26-redis' or 'podman logs mig26-qdrant' to view logs" -ForegroundColor Cyan

# Made with Bob
