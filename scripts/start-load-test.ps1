# Скрипт для автоматического запуска port-forward и генератора нагрузки
# Упрощает процесс запуска тестирования

param(
    [int]$Duration = 60,
    [int]$RequestsPerSecond = 100,
    [int]$Concurrent = 50,
    [switch]$HighLoad
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MediAudit Load Test Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка доступности API
Write-Host "[1/3] Checking API availability..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host "  OK API is accessible" -ForegroundColor Green
    $apiReady = $true
} catch {
    Write-Host "  API not accessible. Starting port-forward..." -ForegroundColor Yellow
    $apiReady = $false
}

# Запуск port-forward если нужно
if (-not $apiReady) {
    Write-Host "`n[2/3] Starting port-forward..." -ForegroundColor Yellow
    
    # Проверка, не запущен ли уже port-forward
    $existingPortForward = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    if ($existingPortForward) {
        Write-Host "  Port-forward may already be running on port 8000" -ForegroundColor Yellow
        Write-Host "  Checking connection..." -ForegroundColor Gray
        Start-Sleep -Seconds 2
    } else {
        Write-Host "  Starting kubectl port-forward..." -ForegroundColor Gray
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "kubectl port-forward svc/backend-service 8000:8000 -n medaudit" -WindowStyle Minimized
        Write-Host "  Waiting for connection..." -ForegroundColor Gray
        Start-Sleep -Seconds 5
    }
    
    # Ожидание доступности API
    $maxRetries = 15
    $retry = 0
    while ($retry -lt $maxRetries) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            Write-Host "  OK API is now accessible!" -ForegroundColor Green
            $apiReady = $true
            break
        } catch {
            $retry++
            if ($retry -lt $maxRetries) {
                Start-Sleep -Seconds 2
                Write-Host "  Waiting... ($retry/$maxRetries)" -ForegroundColor Gray
            }
        }
    }
    
    if (-not $apiReady) {
        Write-Host "  ERROR: Could not establish connection to API" -ForegroundColor Red
        Write-Host "`nTroubleshooting:" -ForegroundColor Yellow
        Write-Host "  1. Check backend pods: kubectl get pods -n medaudit -l app=backend" -ForegroundColor Gray
        Write-Host "  2. Check backend logs: kubectl logs -n medaudit -l app=backend --tail=20" -ForegroundColor Gray
        Write-Host "  3. Start port-forward manually: kubectl port-forward svc/backend-service 8000:8000 -n medaudit" -ForegroundColor Gray
        exit 1
    }
} else {
    Write-Host "`n[2/3] Port-forward check skipped (API already accessible)" -ForegroundColor Green
}

# Настройка параметров для высокой нагрузки
if ($HighLoad) {
    $Duration = 120
    $RequestsPerSecond = 150
    $Concurrent = 80
    Write-Host "`nHigh load mode enabled:" -ForegroundColor Yellow
    Write-Host "  Duration: $Duration seconds" -ForegroundColor Gray
    Write-Host "  Rate: $RequestsPerSecond req/s" -ForegroundColor Gray
    Write-Host "  Concurrent: $Concurrent" -ForegroundColor Gray
}

# Запуск генератора нагрузки
Write-Host "`n[3/3] Starting load generator..." -ForegroundColor Yellow
Write-Host "  Duration: $Duration seconds" -ForegroundColor Gray
Write-Host "  Rate: $RequestsPerSecond req/s" -ForegroundColor Gray
Write-Host "  Concurrent: $Concurrent" -ForegroundColor Gray
Write-Host ""

& "$PSScriptRoot\load-generator.ps1" `
    -Url "http://localhost:8000" `
    -Duration $Duration `
    -RequestsPerSecond $RequestsPerSecond `
    -Concurrent $Concurrent

