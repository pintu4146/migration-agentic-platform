# Start Redis and Qdrant containers for Migration Copilot
# Simplified PowerShell script for Windows

Write-Host "Starting Migration Copilot containers..." -ForegroundColor Green

# Create network
Write-Host ""
Write-Host "Creating network..." -ForegroundColor Yellow
podman network create mig26-network 2>$null

# Create volumes
Write-Host "Creating volumes..." -ForegroundColor Yellow
podman volume create redis-data 2>$null
podman volume create qdrant-data 2>$null

# Start Redis
Write-Host ""
Write-Host "Starting Redis..." -ForegroundColor Yellow
podman run -d --name mig26-redis --network mig26-network -p 6379:6379 -v redis-data:/data docker.io/redis:7-alpine redis-server --appendonly yes 2>$null

# Start Qdrant
Write-Host "Starting Qdrant..." -ForegroundColor Yellow
podman run -d --name mig26-qdrant --network mig26-network -p 6333:6333 -p 6334:6334 -v qdrant-data:/qdrant/storage -e QDRANT__SERVICE__GRPC_PORT=6334 docker.io/qdrant/qdrant:latest 2>$null

# Wait
Write-Host ""
Write-Host "Waiting for containers to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check status
Write-Host ""
Write-Host "Container Status:" -ForegroundColor Cyan
podman ps --filter "name=mig26-"

Write-Host ""
Write-Host "Service URLs:" -ForegroundColor Cyan
Write-Host "Redis:   redis://localhost:6379"
Write-Host "Qdrant:  http://localhost:6333"
Write-Host "Qdrant Dashboard: http://localhost:6333/dashboard"

Write-Host ""
Write-Host "Done! Use 'podman logs mig26-redis' or 'podman logs mig26-qdrant' to view logs" -ForegroundColor Green

# Made with Bob
