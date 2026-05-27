# Start Redis and Qdrant containers for Migration Copilot
# Simplified PowerShell script for Windows

Write-Host "Starting Migration Copilot containers..." -ForegroundColor Green

# Function to check if container exists
function ContainerExists {
    param($name)
    $result = podman ps -a --filter "name=$name" --format "{{.Names}}" 2>$null
    return $result -eq $name
}

# Function to check if container is running
function ContainerRunning {
    param($name)
    $result = podman ps --filter "name=$name" --format "{{.Names}}" 2>$null
    return $result -eq $name
}

# Create network if it doesn't exist
Write-Host ""
Write-Host "Checking network..." -ForegroundColor Yellow
$networkExists = podman network ls --format "{{.Name}}" | Select-String -Pattern "mig26-network" -Quiet
if (-not $networkExists) {
    Write-Host "Creating network mig26-network..." -ForegroundColor Yellow
    podman network create mig26-network 2>$null
} else {
    Write-Host "Network mig26-network already exists" -ForegroundColor Gray
}

# Create volumes if they don't exist
Write-Host "Checking volumes..." -ForegroundColor Yellow
$redisVolumeExists = podman volume ls --format "{{.Name}}" | Select-String -Pattern "redis-data" -Quiet
if (-not $redisVolumeExists) {
    Write-Host "Creating volume redis-data..." -ForegroundColor Yellow
    podman volume create redis-data 2>$null
} else {
    Write-Host "Volume redis-data already exists" -ForegroundColor Gray
}

$qdrantVolumeExists = podman volume ls --format "{{.Name}}" | Select-String -Pattern "qdrant-data" -Quiet
if (-not $qdrantVolumeExists) {
    Write-Host "Creating volume qdrant-data..." -ForegroundColor Yellow
    podman volume create qdrant-data 2>$null
} else {
    Write-Host "Volume qdrant-data already exists" -ForegroundColor Gray
}

# Handle Redis container
Write-Host ""
Write-Host "Checking Redis container..." -ForegroundColor Yellow
if (ContainerExists "mig26-redis") {
    if (ContainerRunning "mig26-redis") {
        Write-Host "Redis container is already running" -ForegroundColor Green
    } else {
        Write-Host "Starting existing Redis container..." -ForegroundColor Yellow
        podman start mig26-redis 2>$null
    }
} else {
    Write-Host "Creating and starting Redis container..." -ForegroundColor Yellow
    podman run -d `
        --name mig26-redis `
        --network mig26-network `
        -p 6379:6379 `
        -v redis-data:/data `
        docker.io/redis:7-alpine `
        redis-server --appendonly yes 2>$null
}

# Handle Qdrant container
Write-Host "Checking Qdrant container..." -ForegroundColor Yellow
if (ContainerExists "mig26-qdrant") {
    if (ContainerRunning "mig26-qdrant") {
        Write-Host "Qdrant container is already running" -ForegroundColor Green
    } else {
        Write-Host "Starting existing Qdrant container..." -ForegroundColor Yellow
        podman start mig26-qdrant 2>$null
    }
} else {
    Write-Host "Creating and starting Qdrant container..." -ForegroundColor Yellow
    podman run -d `
        --name mig26-qdrant `
        --network mig26-network `
        -p 6333:6333 `
        -p 6334:6334 `
        -v qdrant-data:/qdrant/storage `
        -e QDRANT__SERVICE__GRPC_PORT=6334 `
        docker.io/qdrant/qdrant:latest 2>$null
}

# Wait for containers to be ready
Write-Host ""
Write-Host "Waiting for containers to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check status
Write-Host ""
Write-Host "Container Status:" -ForegroundColor Cyan
Write-Host "=================" -ForegroundColor Cyan
podman ps --filter "name=mig26-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Test connectivity
Write-Host ""
Write-Host "Testing connectivity..." -ForegroundColor Yellow

# Test Redis
try {
    $redisTest = Test-NetConnection -ComputerName localhost -Port 6379 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    if ($redisTest.TcpTestSucceeded) {
        Write-Host "✓ Redis is accessible on port 6379" -ForegroundColor Green
    } else {
        Write-Host "✗ Redis is not accessible on port 6379" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ Could not test Redis connectivity" -ForegroundColor Red
}

# Test Qdrant
try {
    $qdrantTest = Test-NetConnection -ComputerName localhost -Port 6333 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    if ($qdrantTest.TcpTestSucceeded) {
        Write-Host "✓ Qdrant is accessible on port 6333" -ForegroundColor Green
    } else {
        Write-Host "✗ Qdrant is not accessible on port 6333" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ Could not test Qdrant connectivity" -ForegroundColor Red
}

Write-Host ""
Write-Host "Service URLs:" -ForegroundColor Cyan
Write-Host "=============" -ForegroundColor Cyan
Write-Host "Redis:            redis://localhost:6379" -ForegroundColor White
Write-Host "Qdrant API:       http://localhost:6333" -ForegroundColor White
Write-Host "Qdrant Dashboard: http://localhost:6333/dashboard" -ForegroundColor White

Write-Host ""
Write-Host "Useful Commands:" -ForegroundColor Cyan
Write-Host "================" -ForegroundColor Cyan
Write-Host "View logs:    podman logs mig26-redis" -ForegroundColor Gray
Write-Host "              podman logs mig26-qdrant" -ForegroundColor Gray
Write-Host "Stop all:     podman stop mig26-redis mig26-qdrant" -ForegroundColor Gray
Write-Host "Remove all:   podman rm mig26-redis mig26-qdrant" -ForegroundColor Gray
Write-Host "Restart:      podman restart mig26-redis mig26-qdrant" -ForegroundColor Gray

Write-Host ""
Write-Host "Done! Containers are ready." -ForegroundColor Green

# Made with Bob
