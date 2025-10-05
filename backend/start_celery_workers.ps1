# PowerShell script to start 4 Celery workers on Windows
# Usage: .\start_celery_workers.ps1

Write-Host "Starting InzightedG Celery Workers..." -ForegroundColor Green

# Check if Redis is running
Write-Host "Checking Redis connection..." -ForegroundColor Yellow
$redisTest = Test-NetConnection -ComputerName localhost -Port 6379 -InformationLevel Quiet

if (-not $redisTest) {
    Write-Host "ERROR: Redis is not running on localhost:6379" -ForegroundColor Red
    Write-Host "Please start Redis first:" -ForegroundColor Yellow
    Write-Host "  - Using Docker: docker run -d -p 6379:6379 redis:7-alpine" -ForegroundColor Cyan
    Write-Host "  - Or install Redis for Windows" -ForegroundColor Cyan
    exit 1
}

Write-Host "Redis connection OK" -ForegroundColor Green

# Set environment variables
$env:CELERY_BROKER_URL = "redis://localhost:6379/0"
$env:CELERY_RESULT_BACKEND = "redis://localhost:6379/1"

# Navigate to backend directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "`nStarting 4 Celery Workers..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop all workers`n" -ForegroundColor Yellow

# Start 4 worker processes in background (robustly)
try {
    # Use python -m celery to ensure the current Python/venv is used, and use the 'solo' pool on Windows
    $worker1 = Start-Process -FilePath "python" -ArgumentList "-m celery -A hellotutor worker --loglevel=info -P solo --concurrency=1 -n worker1@%h" -PassThru -WindowStyle Normal -ErrorAction Stop
} catch {
    Write-Host "Worker 1 failed to start: $($_.Exception.Message)" -ForegroundColor Red
    $worker1 = $null
}

try {
    $worker2 = Start-Process -FilePath "python" -ArgumentList "-m celery -A hellotutor worker --loglevel=info -P solo --concurrency=1 -n worker2@%h" -PassThru -WindowStyle Normal -ErrorAction Stop
} catch {
    Write-Host "Worker 2 failed to start: $($_.Exception.Message)" -ForegroundColor Red
    $worker2 = $null
}

try {
    $worker3 = Start-Process -FilePath "python" -ArgumentList "-m celery -A hellotutor worker --loglevel=info -P solo --concurrency=1 -n worker3@%h" -PassThru -WindowStyle Normal -ErrorAction Stop
} catch {
    Write-Host "Worker 3 failed to start: $($_.Exception.Message)" -ForegroundColor Red
    $worker3 = $null
}

try {
    $worker4 = Start-Process -FilePath "python" -ArgumentList "-m celery -A hellotutor worker --loglevel=info -P solo --concurrency=1 -n worker4@%h" -PassThru -WindowStyle Normal -ErrorAction Stop
} catch {
    Write-Host "Worker 4 failed to start: $($_.Exception.Message)" -ForegroundColor Red
    $worker4 = $null
}

if ($worker1) { Write-Host "Worker 1 started (PID: $($worker1.Id))" -ForegroundColor Green } else { Write-Host "Worker 1 not running" -ForegroundColor Yellow }
if ($worker2) { Write-Host "Worker 2 started (PID: $($worker2.Id))" -ForegroundColor Green } else { Write-Host "Worker 2 not running" -ForegroundColor Yellow }
if ($worker3) { Write-Host "Worker 3 started (PID: $($worker3.Id))" -ForegroundColor Green } else { Write-Host "Worker 3 not running" -ForegroundColor Yellow }
if ($worker4) { Write-Host "Worker 4 started (PID: $($worker4.Id))" -ForegroundColor Green } else { Write-Host "Worker 4 not running" -ForegroundColor Yellow }

Write-Host "`nAll workers are running!" -ForegroundColor Green
Write-Host "Monitor workers: http://localhost:5555 (if Flower is installed)" -ForegroundColor Cyan
Write-Host "`nTo stop workers, run: .\stop_celery_workers.ps1" -ForegroundColor Yellow

# Keep script running
try {
    while ($true) {
        Start-Sleep -Seconds 10
        
        # Check if workers are still running
        if ($worker1.HasExited -or $worker2.HasExited -or $worker3.HasExited -or $worker4.HasExited) {
            Write-Host "`nWARNING: One or more workers have stopped!" -ForegroundColor Red
            break
        }
    }
}
finally {
    Write-Host "`nStopping workers..." -ForegroundColor Yellow
    if ($worker1) { Stop-Process -Id $worker1.Id -Force -ErrorAction SilentlyContinue }
    if ($worker2) { Stop-Process -Id $worker2.Id -Force -ErrorAction SilentlyContinue }
    if ($worker3) { Stop-Process -Id $worker3.Id -Force -ErrorAction SilentlyContinue }
    if ($worker4) { Stop-Process -Id $worker4.Id -Force -ErrorAction SilentlyContinue }
    Write-Host "Workers stopped." -ForegroundColor Green
}
