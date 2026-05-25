# Stop and remove Redis and Qdrant containers
# PowerShell script for Windows

Write-Host "Stopping Migration Copilot containers..." -ForegroundColor Yellow

# Stop containers
Write-Host "`nStopping containers..." -ForegroundColor Yellow
podman stop mig26-redis mig26-qdrant 2>$null

# Remove containers
Write-Host "Removing containers..." -ForegroundColor Yellow
podman rm mig26-redis mig26-qdrant 2>$null

Write-Host "`nContainers stopped and removed" -ForegroundColor Green
Write-Host "`nNote: Volumes (redis-data, qdrant-data) and network (mig26-network) are preserved" -ForegroundColor Cyan
Write-Host "To remove volumes: podman volume rm redis-data qdrant-data" -ForegroundColor Cyan
Write-Host "To remove network: podman network rm mig26-network" -ForegroundColor Cyan

# Made with Bob
