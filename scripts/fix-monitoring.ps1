# Скрипт для исправления проблем с Prometheus и Grafana

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Monitoring Fix Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка статуса подов
Write-Host "[1/5] Checking pod status..." -ForegroundColor Yellow
$prometheusPods = kubectl get pods -n medaudit -l app=prometheus --no-headers 2>&1
$grafanaPods = kubectl get pods -n medaudit -l app=grafana --no-headers 2>&1

if ($prometheusPods -match "Running" -and $prometheusPods -match "1/1") {
    Write-Host "  OK Prometheus pods are running" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Prometheus pods may have issues" -ForegroundColor Yellow
    Write-Host "  Pods:" -ForegroundColor Gray
    $prometheusPods | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
}

if ($grafanaPods -match "Running" -and $grafanaPods -match "1/1") {
    Write-Host "  OK Grafana pods are running" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Grafana pods may have issues" -ForegroundColor Yellow
    Write-Host "  Pods:" -ForegroundColor Gray
    $grafanaPods | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
}

# Проверка сервисов
Write-Host "`n[2/5] Checking services..." -ForegroundColor Yellow
$prometheusSvc = kubectl get svc prometheus-service -n medaudit --no-headers 2>&1
$grafanaSvc = kubectl get svc grafana-service -n medaudit --no-headers 2>&1

if ($prometheusSvc) {
    Write-Host "  OK Prometheus service exists" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Prometheus service not found!" -ForegroundColor Red
    Write-Host "  Reapplying Prometheus manifests..." -ForegroundColor Yellow
    kubectl apply -f k8s/monitoring/prometheus-deployment.yaml 2>&1 | Out-Null
}

if ($grafanaSvc) {
    Write-Host "  OK Grafana service exists" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Grafana service not found!" -ForegroundColor Red
    Write-Host "  Reapplying Grafana manifests..." -ForegroundColor Yellow
    kubectl apply -f k8s/monitoring/grafana-deployment.yaml 2>&1 | Out-Null
}

# Проверка port-forwards
Write-Host "`n[3/5] Checking port-forwards..." -ForegroundColor Yellow
$prometheusPort = Get-NetTCPConnection -LocalPort 9090 -ErrorAction SilentlyContinue
$grafanaPort = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue

if ($prometheusPort) {
    Write-Host "  OK Prometheus port-forward is running" -ForegroundColor Green
} else {
    Write-Host "  Starting Prometheus port-forward..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "kubectl port-forward svc/prometheus-service 9090:9090 -n medaudit" -WindowStyle Minimized
    Start-Sleep -Seconds 3
}

if ($grafanaPort) {
    Write-Host "  OK Grafana port-forward is running" -ForegroundColor Green
} else {
    Write-Host "  Starting Grafana port-forward..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "kubectl port-forward svc/grafana-service 3000:3000 -n medaudit" -WindowStyle Minimized
    Start-Sleep -Seconds 3
}

# Проверка доступности
Write-Host "`n[4/5] Testing accessibility..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

try {
    $prometheusTest = Invoke-WebRequest -Uri "http://localhost:9090/-/healthy" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  OK Prometheus is accessible at http://localhost:9090" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Prometheus not accessible" -ForegroundColor Red
    Write-Host "  Check logs: kubectl logs -n medaudit -l app=prometheus --tail=50" -ForegroundColor Yellow
}

try {
    $grafanaTest = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  OK Grafana is accessible at http://localhost:3000" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Grafana not accessible" -ForegroundColor Red
    Write-Host "  Check logs: kubectl logs -n medaudit -l app=grafana --tail=50" -ForegroundColor Yellow
}

# Перезапуск подов если нужно
Write-Host "`n[5/5] Checking if restart is needed..." -ForegroundColor Yellow
$restartNeeded = $false

if (-not $prometheusPort -or -not (Test-Path "http://localhost:9090/-/healthy")) {
    Write-Host "  Restarting Prometheus deployment..." -ForegroundColor Yellow
    kubectl rollout restart deployment/prometheus -n medaudit 2>&1 | Out-Null
    $restartNeeded = $true
}

if (-not $grafanaPort -or -not (Test-Path "http://localhost:3000/api/health")) {
    Write-Host "  Restarting Grafana deployment..." -ForegroundColor Yellow
    kubectl rollout restart deployment/grafana -n medaudit 2>&1 | Out-Null
    $restartNeeded = $true
}

if ($restartNeeded) {
    Write-Host "  Waiting for pods to restart..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Fix Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Access URLs:" -ForegroundColor Cyan
Write-Host "  Prometheus: http://localhost:9090" -ForegroundColor White
Write-Host "  Grafana: http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "If still not working, check:" -ForegroundColor Yellow
Write-Host "  1. Pod logs: kubectl logs -n medaudit -l app=prometheus" -ForegroundColor Gray
Write-Host "  2. Pod logs: kubectl logs -n medaudit -l app=grafana" -ForegroundColor Gray
Write-Host "  3. Pod status: kubectl get pods -n medaudit" -ForegroundColor Gray
Write-Host "  4. Describe pods: kubectl describe pod <pod-name> -n medaudit" -ForegroundColor Gray
Write-Host ""

