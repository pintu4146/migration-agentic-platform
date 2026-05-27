# Setup Podman Machine for Windows
# This script initializes and starts the Podman Linux VM

Write-Host "Podman Machine Setup for Migration Copilot" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# Check if Podman is installed
Write-Host "Checking Podman installation..." -ForegroundColor Yellow
try {
    $podmanVersion = podman --version
    Write-Host "OK Podman is installed: $podmanVersion" -ForegroundColor Green
} catch {
    Write-Host "X Podman is not installed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Podman first:" -ForegroundColor Yellow
    Write-Host "  Option 1: winget install RedHat.Podman" -ForegroundColor White
    Write-Host "  Option 2: Download from https://podman.io/getting-started/installation" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "Checking Podman machine status..." -ForegroundColor Yellow

# Check if machine exists
$machineList = podman machine list --format "{{.Name}}" 2>$null
if ($machineList -match "podman-machine-default") {
    Write-Host "OK Podman machine exists" -ForegroundColor Green
    
    # Check if it's running
    $machineStatus = podman machine list --format "{{.Running}}" 2>$null
    if ($machineStatus -match "true") {
        Write-Host "OK Podman machine is already running" -ForegroundColor Green
        Write-Host ""
        Write-Host "Podman is ready to use!" -ForegroundColor Green
        Write-Host ""
        Write-Host "You can now run: .\start-containers-simple.ps1" -ForegroundColor Cyan
        exit 0
    } else {
        Write-Host "WARNING Podman machine exists but is not running" -ForegroundColor Yellow
        Write-Host "Starting Podman machine..." -ForegroundColor Yellow
        podman machine start
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "OK Podman machine started successfully" -ForegroundColor Green
        } else {
            Write-Host "X Failed to start Podman machine" -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "WARNING Podman machine does not exist" -ForegroundColor Yellow
    Write-Host "Initializing Podman machine..." -ForegroundColor Yellow
    Write-Host "(This may take a few minutes on first run)" -ForegroundColor Gray
    Write-Host ""
    
    # Initialize with recommended settings
    podman machine init --cpus 2 --memory 4096 --disk-size 50
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK Podman machine initialized" -ForegroundColor Green
        Write-Host ""
        Write-Host "Starting Podman machine..." -ForegroundColor Yellow
        podman machine start
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "OK Podman machine started successfully" -ForegroundColor Green
        } else {
            Write-Host "X Failed to start Podman machine" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "X Failed to initialize Podman machine" -ForegroundColor Red
        exit 1
    }
}

# Verify connection
Write-Host ""
Write-Host "Verifying Podman connection..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

$connectionTest = podman ps 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "OK Podman is working correctly" -ForegroundColor Green
} else {
    Write-Host "X Podman connection test failed" -ForegroundColor Red
    Write-Host "Error: $connectionTest" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Podman Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Run: .\start-containers-simple.ps1" -ForegroundColor White
Write-Host "2. Verify containers: podman ps" -ForegroundColor White
Write-Host "3. Start backend: python -m uvicorn app.main:app --reload" -ForegroundColor White
Write-Host ""
Write-Host "Useful Podman commands:" -ForegroundColor Cyan
Write-Host "  podman machine list    - Show machine status" -ForegroundColor Gray
Write-Host "  podman machine stop    - Stop the machine" -ForegroundColor Gray
Write-Host "  podman machine start   - Start the machine" -ForegroundColor Gray
Write-Host "  podman ps              - List running containers" -ForegroundColor Gray
Write-Host "  podman ps -a           - List all containers" -ForegroundColor Gray
Write-Host ""

# Made with Bob
