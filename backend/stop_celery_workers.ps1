# 🔧 Stop Celery Workers Script
# PowerShell script to stop all Celery workers

Write-Host "Stopping InzightedG Celery Workers..." -ForegroundColor Yellow

# Get all celery processes
$celeryProcesses = Get-Process -Name celery -ErrorAction SilentlyContinue

if ($celeryProcesses) {
    $count = $celeryProcesses.Count
    Write-Host "Found $count Celery worker process(es)" -ForegroundColor Cyan
    
    foreach ($process in $celeryProcesses) {
        Write-Host "Stopping worker (PID: $($process.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $process.Id -Force
    }
    
    Write-Host "✓ All Celery workers stopped" -ForegroundColor Green
} else {
    Write-Host "No Celery workers found running" -ForegroundColor Yellow
}

# Also check for Python processes running celery
$pythonCeleryProcesses = Get-WmiObject Win32_Process -Filter "name = 'python.exe'" | 
    Where-Object { $_.CommandLine -like "*celery*worker*" }

if ($pythonCeleryProcesses) {
    Write-Host "Found Python celery processes, stopping..." -ForegroundColor Yellow
    foreach ($process in $pythonCeleryProcesses) {
        Stop-Process -Id $process.ProcessId -Force
    }
    Write-Host "✓ Python celery processes stopped" -ForegroundColor Green
}

Write-Host "`nAll workers have been stopped." -ForegroundColor Green
