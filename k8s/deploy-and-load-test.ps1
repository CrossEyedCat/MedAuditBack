# Полное развертывание и запуск нагрузки для тестирования Kubernetes
# Этот скрипт разворачивает все компоненты и запускает нагрузку

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MediAudit - Full Deployment & Load Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Шаг 1: Проверка окружения
Write-Host "[1/8] Checking environment..." -ForegroundColor Yellow
try {
    $dockerVersion = docker version --format '{{.Server.Version}}' 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker not running"
    }
    Write-Host "  OK Docker is running" -ForegroundColor Green
    
    $kubectlVersion = kubectl version --client --output json 2>&1 | ConvertFrom-Json
    Write-Host "  OK kubectl installed: $($kubectlVersion.clientVersion.gitVersion)" -ForegroundColor Green
    
    $clusterInfo = kubectl cluster-info 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Kubernetes cluster not available"
    }
    Write-Host "  OK Kubernetes cluster available" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: $_" -ForegroundColor Red
    Write-Host "  Please start Docker Desktop and enable Kubernetes" -ForegroundColor Yellow
    exit 1
}

# Шаг 2: Создание namespace
Write-Host "`n[2/8] Creating namespace..." -ForegroundColor Yellow
kubectl apply -f k8s/namespace.yaml 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK Namespace created" -ForegroundColor Green
} else {
    Write-Host "  Namespace may already exist" -ForegroundColor Yellow
}

# Шаг 3: Применение секретов и конфигов
Write-Host "`n[3/8] Applying secrets and configs..." -ForegroundColor Yellow
if (Test-Path "k8s/secrets.yaml") {
    kubectl apply -f k8s/secrets.yaml 2>&1 | Out-Null
    Write-Host "  OK Secrets applied" -ForegroundColor Green
} else {
    Write-Host "  WARNING: secrets.yaml not found. Using example..." -ForegroundColor Yellow
    if (Test-Path "k8s/secrets.yaml.example") {
        Copy-Item "k8s/secrets.yaml.example" "k8s/secrets.yaml"
        Write-Host "  Please edit k8s/secrets.yaml and run again" -ForegroundColor Yellow
        exit 1
    }
}

kubectl apply -f k8s/configmap.yaml 2>&1 | Out-Null
Write-Host "  OK ConfigMap applied" -ForegroundColor Green

# Шаг 4: Развертывание базовых компонентов
Write-Host "`n[4/8] Deploying base components..." -ForegroundColor Yellow
$components = @(
    "k8s/storage-pvc.yaml",
    "k8s/postgres-statefulset.yaml",
    "k8s/redis-statefulset.yaml"
)

foreach ($component in $components) {
    if (Test-Path $component) {
        kubectl apply -f $component 2>&1 | Out-Null
        Write-Host "  Applied: $(Split-Path $component -Leaf)" -ForegroundColor Gray
    }
}

Write-Host "  Waiting for PostgreSQL and Redis..." -ForegroundColor Yellow
$maxWait = 120
$waited = 0
while ($waited -lt $maxWait) {
    $postgresStatus = kubectl get pod postgres-0 -n medaudit --no-headers 2>&1
    $redisStatus = kubectl get pod redis-0 -n medaudit --no-headers 2>&1
    
    $postgresReady = $postgresStatus -match "Running" -and $postgresStatus -match "1/1"
    $redisReady = $redisStatus -match "Running" -and $redisStatus -match "1/1"
    
    if ($postgresReady -and $redisReady) {
        Write-Host "  OK PostgreSQL and Redis are ready" -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 5
    $waited += 5
    Write-Host "  Waiting... ($waited/$maxWait seconds)" -ForegroundColor Gray
}

# Шаг 5: Развертывание backend и celery
Write-Host "`n[5/8] Deploying backend and celery..." -ForegroundColor Yellow
kubectl apply -f k8s/backend-deployment.yaml 2>&1 | Out-Null
kubectl apply -f k8s/celery-deployment.yaml 2>&1 | Out-Null
kubectl apply -f k8s/backend-hpa.yaml 2>&1 | Out-Null
kubectl apply -f k8s/celery-hpa.yaml 2>&1 | Out-Null

Write-Host "  Waiting for backend pods..." -ForegroundColor Yellow
$maxWait = 120
$waited = 0
while ($waited -lt $maxWait) {
    $backendPods = kubectl get pods -n medaudit -l app=backend --no-headers 2>&1
    $readyCount = ($backendPods | Where-Object { $_ -match "Running" -and $_ -match "1/1" }).Count
    
    if ($readyCount -ge 1) {
        Write-Host "  OK Backend pods are ready ($readyCount)" -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 5
    $waited += 5
    Write-Host "  Waiting... ($waited/$maxWait seconds)" -ForegroundColor Gray
}

# Шаг 6: Развертывание мониторинга
Write-Host "`n[6/8] Deploying monitoring stack..." -ForegroundColor Yellow
$monitoringFiles = @(
    "k8s/monitoring/prometheus-storage.yaml",
    "k8s/monitoring/prometheus-config.yaml",
    "k8s/monitoring/prometheus-deployment.yaml",
    "k8s/monitoring/postgres-exporter.yaml",
    "k8s/monitoring/redis-exporter.yaml",
    "k8s/monitoring/grafana-storage.yaml",
    "k8s/monitoring/grafana-secrets.yaml",
    "k8s/monitoring/grafana-datasources.yaml",
    "k8s/monitoring/grafana-dashboards.yaml",
    "k8s/monitoring/grafana-deployment.yaml"
)

foreach ($file in $monitoringFiles) {
    if (Test-Path $file) {
        kubectl apply -f $file 2>&1 | Out-Null
    }
}

Write-Host "  Waiting for Prometheus and Grafana..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Шаг 7: Запуск port-forwards
Write-Host "`n[7/8] Starting port-forwards..." -ForegroundColor Yellow
Write-Host "  Starting backend port-forward..." -ForegroundColor Gray
Start-Process powershell -ArgumentList "-NoExit", "-Command", "kubectl port-forward svc/backend-service 8000:8000 -n medaudit" -WindowStyle Minimized
Start-Sleep -Seconds 3

Write-Host "  Starting Prometheus port-forward..." -ForegroundColor Gray
Start-Process powershell -ArgumentList "-NoExit", "-Command", "kubectl port-forward svc/prometheus-service 9090:9090 -n medaudit" -WindowStyle Minimized
Start-Sleep -Seconds 3

Write-Host "  Starting Grafana port-forward..." -ForegroundColor Gray
Start-Process powershell -ArgumentList "-NoExit", "-Command", "kubectl port-forward svc/grafana-service 3000:3000 -n medaudit" -WindowStyle Minimized
Start-Sleep -Seconds 5

# Проверка доступности backend
Write-Host "  Checking backend availability..." -ForegroundColor Gray
$maxRetries = 10
$retry = 0
while ($retry -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        Write-Host "  OK Backend is accessible" -ForegroundColor Green
        break
    } catch {
        $retry++
        if ($retry -ge $maxRetries) {
            Write-Host "  WARNING: Backend not accessible yet. Port-forward may need more time." -ForegroundColor Yellow
        } else {
            Start-Sleep -Seconds 2
        }
    }
}

# Шаг 8: Запуск генератора нагрузки
Write-Host "`n[8/8] Starting load generator..." -ForegroundColor Yellow
Write-Host "  Configuration:" -ForegroundColor Gray
Write-Host "    Duration: 120 seconds" -ForegroundColor Gray
Write-Host "    Rate: 150 requests/second (10x increased)" -ForegroundColor Gray
Write-Host "    Concurrent: 80 requests (10x increased)" -ForegroundColor Gray
Write-Host ""

# Запуск генератора нагрузки в отдельном окне
$loadScript = @'
$ErrorActionPreference = "SilentlyContinue"
$baseUrl = "http://localhost:8000"
$endpoints = @("/health", "/", "/api/docs", "/metrics")
$duration = 120
$requestsPerSecond = 150
$concurrent = 80
$startTime = Get-Date
$requestCount = 0
$successCount = 0
$errorCount = 0

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Load Generator Started" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Target: $baseUrl" -ForegroundColor Gray
Write-Host "Duration: $duration seconds" -ForegroundColor Gray
Write-Host "Rate: $requestsPerSecond req/s" -ForegroundColor Gray
Write-Host ""

while (((Get-Date) - $startTime).TotalSeconds -lt $duration) {
    $jobs = @()
    for ($i = 0; $i -lt $concurrent; $i++) {
        $endpoint = $endpoints | Get-Random
        $job = Start-Job -ScriptBlock {
            param($url)
            try {
                $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
                return @{Success=$true; StatusCode=$response.StatusCode}
            } catch {
                return @{Success=$false}
            }
        } -ArgumentList "$baseUrl$endpoint"
        $jobs += $job
    }
    
    Start-Sleep -Milliseconds ([math]::Round(1000 / $requestsPerSecond * $concurrent))
    
    foreach ($job in $jobs) {
        $result = Receive-Job -Job $job -Wait -ErrorAction SilentlyContinue
        Remove-Job -Job $job -ErrorAction SilentlyContinue
        $requestCount++
        if ($result -and $result.Success) {
            $successCount++
        } else {
            $errorCount++
        }
    }
    
    if ($requestCount % 50 -eq 0) {
        $elapsed = ((Get-Date) - $startTime).TotalSeconds
        $rate = [math]::Round($requestCount / $elapsed, 2)
        Write-Host "[$([math]::Round($elapsed))s] Requests: $requestCount | Success: $successCount | Errors: $errorCount | Rate: $rate req/s" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Load Generation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Total requests: $requestCount" -ForegroundColor Cyan
Write-Host "Successful: $successCount" -ForegroundColor Green
Write-Host "Errors: $errorCount" -ForegroundColor $(if ($errorCount -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Check metrics in:" -ForegroundColor Yellow
Write-Host "  Prometheus: http://localhost:9090" -ForegroundColor Cyan
Write-Host "  Grafana: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
'@

$loadScript | Out-File -FilePath "$env:TEMP\load-test.ps1" -Encoding UTF8
Start-Process powershell -ArgumentList "-NoExit", "-File", "$env:TEMP\load-test.ps1" -WindowStyle Normal
Write-Host "  OK Load generator started" -ForegroundColor Green

# Финальный статус
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Component Status:" -ForegroundColor Cyan
kubectl get pods -n medaudit | Format-Table -AutoSize
Write-Host ""
Write-Host "Access URLs:" -ForegroundColor Yellow
Write-Host "  Backend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Prometheus: http://localhost:9090" -ForegroundColor Cyan
Write-Host "  Grafana: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Grafana Credentials:" -ForegroundColor Yellow
Write-Host "  Username: admin" -ForegroundColor Gray
Write-Host "  Password: MedAudit2024!Grafana" -ForegroundColor Gray
Write-Host ""
Write-Host "View Metrics in Grafana:" -ForegroundColor Yellow
Write-Host "  1. Login to Grafana" -ForegroundColor Gray
Write-Host "  2. Create new dashboard" -ForegroundColor Gray
Write-Host "  3. Add panel with query: rate(http_requests_total[5m])" -ForegroundColor Gray
Write-Host "  4. Add panel with query: sum(http_requests_total)" -ForegroundColor Gray
Write-Host "  5. Add panel with query: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))" -ForegroundColor Gray
Write-Host ""
Write-Host "Load generator is running for 120 seconds..." -ForegroundColor Green
Write-Host "Metrics will appear in Grafana within 15-30 seconds" -ForegroundColor Yellow
Write-Host ""

