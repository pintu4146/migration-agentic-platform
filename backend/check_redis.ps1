# Redis Connection Diagnostic Script
# Checks if Redis is accessible at redis://localhost:6379

Write-Host "=== Redis Connection Diagnostic ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Container running
Write-Host "1. Checking if Redis container is running..." -ForegroundColor Yellow
$container = podman ps --filter "name=mig26-redis" --format "{{.Names}}" 2>$null
if ($container -eq "mig26-redis") {
    Write-Host "   ✓ Redis container is running" -ForegroundColor Green
} else {
    Write-Host "   ✗ Redis container is NOT running" -ForegroundColor Red
    Write-Host "   Run: .\start-containers-simple.ps1" -ForegroundColor Yellow
    exit
}

# Test 2: Ping from inside container
Write-Host ""
Write-Host "2. Testing Redis from inside container..." -ForegroundColor Yellow
$ping = podman exec mig26-redis redis-cli ping 2>$null
if ($ping -eq "PONG") {
    Write-Host "   ✓ Redis responds to PING" -ForegroundColor Green
} else {
    Write-Host "   ✗ Redis not responding" -ForegroundColor Red
    Write-Host "   Check logs: podman logs mig26-redis" -ForegroundColor Yellow
}

# Test 3: Port mapping
Write-Host ""
Write-Host "3. Checking container port mapping..." -ForegroundColor Yellow
$ports = podman port mig26-redis 2>$null
if ($ports) {
    Write-Host "   ✓ Port mapping: $ports" -ForegroundColor Green
} else {
    Write-Host "   ✗ No port mapping found" -ForegroundColor Red
}

# Test 4: Test with Python - simple version
Write-Host ""
Write-Host "4. Testing with Python redis client..." -ForegroundColor Yellow
$result = python -c "import redis; r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=2); print('OK' if r.ping() else 'FAIL')" 2>$null
if ($result -eq "OK") {
    Write-Host "   ✓ Python can connect to Redis" -ForegroundColor Green
} else {
    Write-Host "   ✗ Python cannot connect to Redis" -ForegroundColor Red
}

# Test 5: Test redis:// URL
Write-Host ""
Write-Host "5. Testing redis://localhost:6379 URL..." -ForegroundColor Yellow
$urlResult = python -c "import redis; r = redis.from_url('redis://localhost:6379', socket_connect_timeout=2); print('OK' if r.ping() else 'FAIL')" 2>$null
if ($urlResult -eq "OK") {
    Write-Host "   ✓ redis://localhost:6379 is accessible" -ForegroundColor Green
} else {
    Write-Host "   ✗ redis://localhost:6379 is NOT accessible" -ForegroundColor Red
}

# Test 6: Check Redis info
Write-Host ""
Write-Host "6. Getting Redis info..." -ForegroundColor Yellow
$info = podman exec mig26-redis redis-cli INFO server 2>$null | Select-String "redis_version"
if ($info) {
    Write-Host "   ✓ $info" -ForegroundColor Green
} else {
    Write-Host "   ✗ Could not get Redis info" -ForegroundColor Red
}

# Test 7: Test SET/GET
Write-Host ""
Write-Host "7. Testing SET/GET operations..." -ForegroundColor Yellow
podman exec mig26-redis redis-cli SET test_key "test_value" 2>$null | Out-Null
$getValue = podman exec mig26-redis redis-cli GET test_key 2>$null
if ($getValue -eq "test_value") {
    Write-Host "   ✓ SET/GET operations work" -ForegroundColor Green
    podman exec mig26-redis redis-cli DEL test_key 2>$null | Out-Null
} else {
    Write-Host "   ✗ SET/GET operations failed" -ForegroundColor Red
}

# Summary
Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Redis URL: redis://localhost:6379" -ForegroundColor Cyan
Write-Host ""
Write-Host "If all tests passed:" -ForegroundColor Green
Write-Host "  ✓ Redis is fully accessible and working" -ForegroundColor Green
Write-Host ""
Write-Host "If tests failed:" -ForegroundColor Yellow
Write-Host "  1. Restart containers: .\start-containers-simple.ps1" -ForegroundColor Gray
Write-Host "  2. Check logs: podman logs mig26-redis" -ForegroundColor Gray
Write-Host "  3. Check port: netstat -ano | Select-String ':6379'" -ForegroundColor Gray
Write-Host ""

# Made with Bob
