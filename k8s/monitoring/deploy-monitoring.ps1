# Скрипт для развертывания мониторинга (PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "=== Deploying Monitoring Stack ===" -ForegroundColor Cyan
Write-Host ""

# Проверка секретов Grafana
if (-Not (Test-Path "k8s/monitoring/grafana-secrets.yaml")) {
    Write-Host "WARNING: grafana-secrets.yaml not found" -ForegroundColor Yellow
    Write-Host "Copy k8s/monitoring/grafana-secrets.yaml.example to k8s/monitoring/grafana-secrets.yaml" -ForegroundColor Yellow
    Write-Host "and set admin password" -ForegroundColor Yellow
    exit 1
}

# Применение манифестов
Write-Host "[1/9] Creating Prometheus storage..." -ForegroundColor Green
kubectl apply -f k8s/monitoring/prometheus-storage.yaml

Write-Host "[2/9] Creating Prometheus config..." -ForegroundColor Green
kubectl apply -f k8s/monitoring/prometheus-config.yaml

Write-Host "[3/9] Deploying Prometheus..." -ForegroundColor Green
kubectl apply -f k8s/monitoring/prometheus-deployment.yaml

Write-Host "[4/9] Creating Grafana storage..." -ForegroundColor Green
kubectl apply -f k8s/monitoring/grafana-storage.yaml

Write-Host "[5/9] Creating Grafana datasources..." -ForegroundColor Green
kubectl apply -f k8s/monitoring/grafana-datasources.yaml

Write-Host "[6/9] Creating Grafana dashboards..." -ForegroundColor Green
kubectl apply -f k8s/monitoring/grafana-dashboards.yaml

Write-Host "[7/9] Applying Grafana secrets..." -ForegroundColor Green
kubectl apply -f k8s/monitoring/grafana-secrets.yaml

Write-Host "[8/9] Deploying Grafana..." -ForegroundColor Green
kubectl apply -f k8s/monitoring/grafana-deployment.yaml

Write-Host "[9/9] Deploying exporters..." -ForegroundColor Green
kubectl apply -f k8s/monitoring/postgres-exporter.yaml
kubectl apply -f k8s/monitoring/redis-exporter.yaml

Write-Host ""
Write-Host "=== Monitoring deployed! ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access Grafana:" -ForegroundColor Yellow
Write-Host "  kubectl port-forward svc/grafana-service 3000:3000 -n medaudit" -ForegroundColor Gray
Write-Host "  Then open: http://localhost:3000" -ForegroundColor Gray
Write-Host "  Default credentials: admin / (your password)" -ForegroundColor Gray
Write-Host ""
Write-Host "Access Prometheus:" -ForegroundColor Yellow
Write-Host "  kubectl port-forward svc/prometheus-service 9090:9090 -n medaudit" -ForegroundColor Gray
Write-Host "  Then open: http://localhost:9090" -ForegroundColor Gray



