# PowerShell скрипт для генерации нагрузки на API
# Использует Invoke-WebRequest для создания метрик

param(
    [string]$Url = "http://localhost:8000",
    [int]$Duration = 60,
    [int]$RequestsPerSecond = 100,
    [int]$Concurrent = 50
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MediAudit API Load Generator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  URL: $Url" -ForegroundColor Gray
Write-Host "  Duration: $Duration seconds" -ForegroundColor Gray
Write-Host "  Requests per second: $RequestsPerSecond" -ForegroundColor Gray
Write-Host "  Concurrent requests: $Concurrent" -ForegroundColor Gray
Write-Host ""

# Проверка доступности API
Write-Host "Checking API availability..." -ForegroundColor Yellow
try {
    $healthCheck = Invoke-WebRequest -Uri "$Url/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    if ($healthCheck.StatusCode -eq 200) {
        Write-Host "  OK API is available" -ForegroundColor Green
    } else {
        Write-Host "  ERROR: API returned status $($healthCheck.StatusCode)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ERROR: API is not available!" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host ""
    
    # Проверка подов
    Write-Host "1. Checking backend pods..." -ForegroundColor Cyan
    $pods = kubectl get pods -n medaudit -l app=backend --no-headers 2>&1
    if ($LASTEXITCODE -eq 0 -and $pods) {
        Write-Host "   Backend pods found:" -ForegroundColor Gray
        $pods | ForEach-Object { Write-Host "     $_" -ForegroundColor Gray }
        
        # Проверка статуса подов
        $readyPods = kubectl get pods -n medaudit -l app=backend -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}' 2>&1
        if ($readyPods -match "True") {
            Write-Host "   Pods are ready" -ForegroundColor Green
        } else {
            Write-Host "   WARNING: Some pods may not be ready" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   No backend pods found!" -ForegroundColor Red
        Write-Host "   Deploy backend first: .\k8s\deploy-all.ps1" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "2. Start port-forward in another terminal:" -ForegroundColor Cyan
    Write-Host "   kubectl port-forward svc/backend-service 8000:8000 -n medaudit" -ForegroundColor White
    Write-Host ""
    Write-Host "3. Or check if port-forward is already running:" -ForegroundColor Cyan
    Write-Host "   Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue" -ForegroundColor White
    Write-Host ""
    Write-Host "4. Alternative: Use service IP directly:" -ForegroundColor Cyan
    try {
        $serviceIp = kubectl get svc backend-service -n medaudit -o jsonpath='{.spec.clusterIP}' 2>&1
        if ($serviceIp -and $LASTEXITCODE -eq 0) {
            Write-Host "   Service IP: $serviceIp" -ForegroundColor Gray
            Write-Host "   Try: .\scripts\load-generator.ps1 -Url `"http://$serviceIp:8000`"" -ForegroundColor White
            Write-Host "   (Requires access to cluster network)" -ForegroundColor Yellow
        }
    } catch {
        # Ignore
    }
    
    exit 1
}

Write-Host ""
Write-Host "Starting load generation..." -ForegroundColor Green
Write-Host ""

# Эндпоинты для тестирования
$endpoints = @(
    "/health",
    "/",
    "/api/docs",
    "/api/v1/auth/me",
    "/metrics"
)

$startTime = Get-Date
$requestCount = 0
$errorCount = 0
$successCount = 0

# Функция для выполнения запроса
function Invoke-LoadRequest {
    param([string]$Endpoint, [string]$Method = "GET")
    
    $fullUrl = "$Url$Endpoint"
    try {
        $response = Invoke-WebRequest -Uri $fullUrl -Method $Method -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        return @{
            Status = $response.StatusCode
            Success = $true
        }
    } catch {
        $statusCode = 0
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode.value__
        }
        return @{
            Status = $statusCode
            Success = $false
            Error = $_.Exception.Message
        }
    }
}

# Основной цикл генерации нагрузки
$endTime = $startTime.AddSeconds($Duration)
$delay = 1000 / $RequestsPerSecond  # миллисекунды между запросами

Write-Host "Generating load..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop early" -ForegroundColor Yellow
Write-Host ""

$jobsList = New-Object System.Collections.ArrayList

while ((Get-Date) -lt $endTime) {
    # Запуск параллельных запросов
    for ($i = 0; $i -lt $Concurrent; $i++) {
        $endpoint = $endpoints | Get-Random
        $job = Start-Job -ScriptBlock {
            param($Url, $Endpoint)
            try {
                $response = Invoke-WebRequest -Uri "$Url$Endpoint" -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
                return @{ Status = $response.StatusCode; Success = $true }
            } catch {
                $statusCode = 0
                if ($_.Exception.Response) {
                    $statusCode = [int]$_.Exception.Response.StatusCode.value__
                }
                return @{ Status = $statusCode; Success = $false }
            }
        } -ArgumentList $Url, $endpoint
        
        [void]$jobsList.Add($job)
    }
    
    # Обработка завершенных задач
    $completed = $jobsList | Where-Object { $_.State -eq "Completed" }
    foreach ($job in $completed) {
        $result = Receive-Job -Job $job -ErrorAction SilentlyContinue
        Remove-Job -Job $job -ErrorAction SilentlyContinue
        [void]$jobsList.Remove($job)
        
        if ($result) {
            $requestCount++
            if ($result.Success -and $result.Status -lt 400) {
                $successCount++
            } else {
                $errorCount++
            }
        }
    }
    
    # Удаление старых задач (на случай зависания)
    $oldJobs = $jobsList | Where-Object { (Get-Date) - $_.PSBeginTime -gt [TimeSpan]::FromSeconds(30) }
    foreach ($job in $oldJobs) {
        Stop-Job -Job $job -ErrorAction SilentlyContinue
        Remove-Job -Job $job -ErrorAction SilentlyContinue
        [void]$jobsList.Remove($job)
    }
    
    # Прогресс
    $elapsed = ((Get-Date) - $startTime).TotalSeconds
    $remaining = $Duration - $elapsed
    if ($requestCount % 10 -eq 0) {
        Write-Host "  Requests: $requestCount | Success: $successCount | Errors: $errorCount | Remaining: $([math]::Round($remaining))s" -ForegroundColor Gray
    }
    
    Start-Sleep -Milliseconds $delay
}

# Ожидание завершения всех задач
Write-Host ""
Write-Host "Waiting for remaining requests to complete..." -ForegroundColor Yellow
$jobsList | Wait-Job -Timeout 30 | Out-Null
foreach ($job in $jobsList) {
    $result = Receive-Job -Job $job -ErrorAction SilentlyContinue
    Remove-Job -Job $job -ErrorAction SilentlyContinue
    
    if ($result) {
        $requestCount++
        if ($result.Success -and $result.Status -lt 400) {
            $successCount++
        } else {
            $errorCount++
        }
    }
}

$elapsed = ((Get-Date) - $startTime).TotalSeconds

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Load Generation Completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Statistics:" -ForegroundColor Yellow
Write-Host "  Duration: $([math]::Round($elapsed, 2)) seconds" -ForegroundColor Gray
Write-Host "  Total requests: $requestCount" -ForegroundColor Gray
Write-Host "  Successful: $successCount" -ForegroundColor Green
Write-Host "  Errors: $errorCount" -ForegroundColor $(if ($errorCount -gt 0) { "Red" } else { "Gray" })
if ($requestCount -gt 0) {
    $successRate = ($successCount / $requestCount) * 100
    Write-Host "  Success rate: $([math]::Round($successRate, 2))%" -ForegroundColor Gray
    Write-Host "  Requests/sec: $([math]::Round($requestCount / $elapsed, 2))" -ForegroundColor Gray
}
Write-Host ""
Write-Host "Check metrics in Grafana:" -ForegroundColor Cyan
Write-Host "  kubectl port-forward svc/grafana-service 3000:3000 -n medaudit" -ForegroundColor Gray
Write-Host ""

