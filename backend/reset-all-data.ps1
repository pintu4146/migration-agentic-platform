# Reset All Data Script
# Clears all stored context, cache, and data for Migration Copilot

Write-Host ""
Write-Host "========================================" -ForegroundColor Red
Write-Host "Migration Copilot - Data Reset" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red
Write-Host ""
Write-Host "WARNING: This will delete ALL stored data!" -ForegroundColor Yellow
Write-Host "  - Redis cache and state" -ForegroundColor Yellow
Write-Host "  - Qdrant vector collections" -ForegroundColor Yellow
Write-Host "  - Uploaded files" -ForegroundColor Yellow
Write-Host "  - Logs" -ForegroundColor Yellow
Write-Host ""

# Confirm
$confirmation = Read-Host "Are you sure you want to continue? (yes/no)"
if ($confirmation -ne "yes") {
    Write-Host "Reset cancelled." -ForegroundColor Cyan
    exit 0
}

Write-Host ""
Write-Host "Starting reset..." -ForegroundColor Green

# Step 1: Clear Redis
Write-Host ""
Write-Host "[1/4] Clearing Redis cache..." -ForegroundColor Cyan
try {
    $redisResult = podman exec mig26-redis redis-cli FLUSHALL 2>$null
    if ($redisResult -eq "OK") {
        Write-Host "  Redis cleared successfully" -ForegroundColor Green
    } else {
        Write-Host "  Redis may not be running" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  Could not clear Redis (container may not be running)" -ForegroundColor Yellow
}

# Step 2: Clear Qdrant collections
Write-Host ""
Write-Host "[2/4] Clearing Qdrant collections..." -ForegroundColor Cyan
try {
    $collections = Invoke-RestMethod -Uri "http://localhost:6333/collections" -Method Get -ErrorAction Stop
    $collectionCount = 0
    
    if ($collections.result.collections) {
        foreach ($collection in $collections.result.collections) {
            Write-Host "  Deleting collection: $($collection.name)" -ForegroundColor Gray
            try {
                Invoke-RestMethod -Uri "http://localhost:6333/collections/$($collection.name)" -Method Delete -ErrorAction Stop
                $collectionCount++
            } catch {
                Write-Host "    Failed to delete $($collection.name)" -ForegroundColor Yellow
            }
        }
        Write-Host "  Deleted $collectionCount collection(s)" -ForegroundColor Green
    } else {
        Write-Host "  No collections to delete" -ForegroundColor Green
    }
} catch {
    Write-Host "  Qdrant not responding (container may not be running)" -ForegroundColor Yellow
}

# Step 3: Clear file system
Write-Host ""
Write-Host "[3/4] Clearing file system..." -ForegroundColor Cyan

$dirsToClean = @("uploads", "logs", ".cache", "temp")
$filesDeleted = 0

foreach ($dir in $dirsToClean) {
    if (Test-Path $dir) {
        try {
            $items = Get-ChildItem -Path $dir -Recurse -ErrorAction SilentlyContinue
            $count = ($items | Measure-Object).Count
            if ($count -gt 0) {
                Remove-Item -Path "$dir/*" -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "  Cleared $dir/ ($count items)" -ForegroundColor Gray
                $filesDeleted += $count
            }
        } catch {
            Write-Host "  Could not clear $dir/" -ForegroundColor Yellow
        }
    }
}

if ($filesDeleted -gt 0) {
    Write-Host "  Deleted $filesDeleted file(s)" -ForegroundColor Green
} else {
    Write-Host "  No files to delete" -ForegroundColor Green
}

# Step 4: Verification
Write-Host ""
Write-Host "[4/4] Verifying reset..." -ForegroundColor Cyan

# Check Redis
try {
    $redisSize = podman exec mig26-redis redis-cli DBSIZE 2>$null
    if ($redisSize -match "\d+") {
        $keyCount = [int]($redisSize -replace '\D','')
        if ($keyCount -eq 0) {
            Write-Host "  Redis: Clean (0 keys)" -ForegroundColor Green
        } else {
            Write-Host "  Redis: $keyCount keys remaining" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "  Redis: Not verified" -ForegroundColor Yellow
}

# Check Qdrant
try {
    $collections = Invoke-RestMethod -Uri "http://localhost:6333/collections" -Method Get -ErrorAction Stop
    $collCount = ($collections.result.collections | Measure-Object).Count
    if ($collCount -eq 0) {
        Write-Host "  Qdrant: Clean (0 collections)" -ForegroundColor Green
    } else {
        Write-Host "  Qdrant: $collCount collection(s) remaining" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  Qdrant: Not verified" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Reset Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "All data has been cleared." -ForegroundColor White
Write-Host "You can now start a new analysis with a different application." -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Update .env with new context ID (if needed)" -ForegroundColor White
Write-Host "  2. Start FastAPI server" -ForegroundColor White
Write-Host "  3. Begin new workflow with new project_id" -ForegroundColor White
Write-Host ""

# Made with Bob
