# Complete startup script for Migration Copilot
# Starts containers, activates venv, and runs the FastAPI server
# PowerShell script for Windows

param(
    [switch]$SkipContainers,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Migration Copilot - Complete Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Step 1: Start containers (unless skipped)
if (-not $SkipContainers) {
    Write-Host "`n[1/4] Starting Redis and Qdrant containers..." -ForegroundColor Green
    & "$PSScriptRoot\start-containers.ps1"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to start containers" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "`n[1/4] Skipping container startup" -ForegroundColor Yellow
}

# Step 2: Activate virtual environment
Write-Host "`n[2/4] Activating virtual environment..." -ForegroundColor Green
if (Test-Path "$PSScriptRoot\venv\Scripts\Activate.ps1") {
    & "$PSScriptRoot\venv\Scripts\Activate.ps1"
    Write-Host "Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv venv
    & "$PSScriptRoot\venv\Scripts\Activate.ps1"
    Write-Host "Virtual environment created and activated" -ForegroundColor Green
}

# Step 3: Install/update dependencies (unless skipped)
if (-not $SkipInstall) {
    Write-Host "`n[3/4] Installing/updating dependencies..." -ForegroundColor Green
    pip install --upgrade pip
    pip install -r requirements.txt
    Write-Host "Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "`n[3/4] Skipping dependency installation" -ForegroundColor Yellow
}

# Step 4: Check .env file
Write-Host "`n[4/4] Checking configuration..." -ForegroundColor Green
if (-not (Test-Path "$PSScriptRoot\.env")) {
    Write-Host "Warning: .env file not found. Copying from .env.example..." -ForegroundColor Yellow
    Copy-Item "$PSScriptRoot\.env.example" "$PSScriptRoot\.env"
    Write-Host "Please update .env with your API keys before running the server" -ForegroundColor Yellow
    Write-Host "Press any key to continue or Ctrl+C to exit..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# Display service status
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Service Status" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check Redis
try {
    $redisStatus = podman exec mig26-redis redis-cli ping 2>$null
    if ($redisStatus -eq "PONG") {
        Write-Host "✓ Redis:   Running on localhost:6379" -ForegroundColor Green
    } else {
        Write-Host "✗ Redis:   Not responding" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ Redis:   Not running" -ForegroundColor Red
}

# Check Qdrant
try {
    $qdrantStatus = Invoke-RestMethod -Uri "http://localhost:6333/health" -Method Get -ErrorAction SilentlyContinue -TimeoutSec 2
    if ($qdrantStatus) {
        Write-Host "✓ Qdrant:  Running on localhost:6333" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Qdrant:  Not responding" -ForegroundColor Red
}

# Display URLs
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Service URLs" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Redis:            redis://localhost:6379" -ForegroundColor White
Write-Host "Qdrant API:       http://localhost:6333" -ForegroundColor White
Write-Host "Qdrant Dashboard: http://localhost:6333/dashboard" -ForegroundColor White
Write-Host "FastAPI (soon):   http://localhost:8000" -ForegroundColor White
Write-Host "API Docs (soon):  http://localhost:8000/docs" -ForegroundColor White

# Start FastAPI server
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Starting FastAPI Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Run uvicorn
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Made with Bob
