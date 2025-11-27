# Полное развертывание MediAudit Backend в Kubernetes
# Этот скрипт проверяет окружение и разворачивает все компоненты

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MediAudit Backend - Full Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка Docker
Write-Host "[1/12] Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK Docker installed: $dockerVersion" -ForegroundColor Green
    } else {
        throw "Docker not found"
    }
} catch {
    Write-Host "  ERROR: Docker not installed or not running!" -ForegroundColor Red
    Write-Host "  Install Docker Desktop: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Проверка kubectl
Write-Host "[2/12] Checking kubectl..." -ForegroundColor Yellow
try {
    $kubectlVersion = kubectl version --client 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK kubectl installed" -ForegroundColor Green
    } else {
        throw "kubectl not found"
    }
} catch {
    Write-Host "  ERROR: kubectl not installed!" -ForegroundColor Red
    Write-Host "  Install kubectl: https://kubernetes.io/docs/tasks/tools/" -ForegroundColor Yellow
    exit 1
}

# Проверка Kubernetes кластера
Write-Host "[3/12] Checking Kubernetes cluster..." -ForegroundColor Yellow
$clusterAvailable = $false
try {
    $clusterCheckResult = kubectl cluster-info 2>&1
    if ($LASTEXITCODE -eq 0) {
        $clusterAvailable = $true
        Write-Host "  OK Kubernetes cluster available" -ForegroundColor Green
        $nodes = kubectl get nodes 2>&1
        Write-Host "  Cluster nodes:" -ForegroundColor Cyan
        $nodes | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
    }
} catch {
    Write-Host "  WARNING: Could not check cluster status" -ForegroundColor Yellow
}

if (-not $clusterAvailable) {
    Write-Host "  ERROR: Kubernetes cluster not running!" -ForegroundColor Red
    Write-Host "  Enable Kubernetes in Docker Desktop:" -ForegroundColor Yellow
    Write-Host "    Settings -> Kubernetes -> Enable Kubernetes" -ForegroundColor Yellow
    Write-Host ""
    $launchDocker = Read-Host "  Launch Docker Desktop now? (Y/N)"
    if ($launchDocker -eq "Y" -or $launchDocker -eq "y") {
        Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        Write-Host "  Waiting for Docker Desktop to start..." -ForegroundColor Yellow
        Start-Sleep -Seconds 30
    } else {
        exit 1
    }
}

# Проверка Metrics Server
Write-Host "[4/12] Checking Metrics Server..." -ForegroundColor Yellow
$metricsServer = kubectl get deployment metrics-server -n kube-system 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  WARNING: Metrics Server not found. HPA may not work." -ForegroundColor Yellow
    Write-Host "  Install Metrics Server for HPA to work properly." -ForegroundColor Yellow
} else {
    Write-Host "  OK Metrics Server available" -ForegroundColor Green
}

# Сборка Docker образа
Write-Host "[5/12] Building Docker image..." -ForegroundColor Yellow
Write-Host "  Building medaudit-backend:latest..." -ForegroundColor Gray
$ErrorActionPreference = "SilentlyContinue"
$buildOutput = docker build -f Dockerfile.prod -t medaudit-backend:latest . 2>&1 | Out-String
$buildExitCode = $LASTEXITCODE
$ErrorActionPreference = "Stop"

if ($buildExitCode -eq 0) {
    Write-Host "  OK Docker image built successfully" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Docker build failed with exit code: $buildExitCode" -ForegroundColor Red
    Write-Host "  Build output (last 30 lines):" -ForegroundColor Yellow
    $buildOutput -split "`n" | Select-Object -Last 30 | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "  Full build output saved. Check Docker Desktop logs for details." -ForegroundColor Yellow
    exit 1
}

# Создание namespace
Write-Host "[6/12] Creating namespace..." -ForegroundColor Yellow
kubectl apply -f k8s/namespace.yaml
Write-Host "  OK Namespace created" -ForegroundColor Green

# Применение секретов
Write-Host "[7/12] Applying secrets..." -ForegroundColor Yellow
if (-Not (Test-Path "k8s/secrets.yaml")) {
    Write-Host "  ERROR: k8s/secrets.yaml not found!" -ForegroundColor Red
    Write-Host "  Copy k8s/secrets.yaml.example to k8s/secrets.yaml and configure it" -ForegroundColor Yellow
    exit 1
}
kubectl apply -f k8s/secrets.yaml
Write-Host "  OK Secrets applied" -ForegroundColor Green

# Применение ConfigMap
Write-Host "[8/12] Applying ConfigMap..." -ForegroundColor Yellow
kubectl apply -f k8s/configmap.yaml
Write-Host "  OK ConfigMap applied" -ForegroundColor Green

# Развертывание хранилища
Write-Host "[9/12] Creating storage..." -ForegroundColor Yellow
kubectl apply -f k8s/storage-pvc.yaml
Write-Host "  OK Storage created" -ForegroundColor Green

# Развертывание PostgreSQL
Write-Host "[10/12] Deploying PostgreSQL..." -ForegroundColor Yellow
kubectl apply -f k8s/postgres-statefulset.yaml
Write-Host "  Waiting for PostgreSQL to be ready..." -ForegroundColor Gray
Start-Sleep -Seconds 15
Write-Host "  OK PostgreSQL deployed" -ForegroundColor Green

# Развертывание Redis
Write-Host "[11/12] Deploying Redis..." -ForegroundColor Yellow
kubectl apply -f k8s/redis-statefulset.yaml
Write-Host "  Waiting for Redis to be ready..." -ForegroundColor Gray
Start-Sleep -Seconds 10
Write-Host "  OK Redis deployed" -ForegroundColor Green

# Развертывание Backend и Celery
Write-Host "[12/12] Deploying Backend and Celery..." -ForegroundColor Yellow
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/celery-deployment.yaml
kubectl apply -f k8s/backend-hpa.yaml
kubectl apply -f k8s/celery-hpa.yaml
Write-Host "  Waiting for Backend and Celery to be ready..." -ForegroundColor Gray
Start-Sleep -Seconds 30
Write-Host "  OK Backend and Celery deployed" -ForegroundColor Green

# Выполнение миграций
Write-Host "[Bonus] Running database migrations..." -ForegroundColor Yellow
$ErrorActionPreference = "SilentlyContinue"
$backendPod = kubectl get pods -n medaudit -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>&1 | Out-String
$backendPod = $backendPod.Trim()
$podCheckExitCode = $LASTEXITCODE
$ErrorActionPreference = "Stop"

if ($backendPod -and $podCheckExitCode -eq 0 -and $backendPod -ne "") {
    Write-Host "  Running migrations on pod: $backendPod" -ForegroundColor Gray
    $ErrorActionPreference = "SilentlyContinue"
    $migrationOutput = kubectl exec $backendPod -n medaudit -- alembic upgrade head 2>&1 | Out-String
    $migrationExitCode = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    
    if ($migrationExitCode -eq 0) {
        Write-Host "  OK Migrations completed" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: Migrations may have failed. Check logs." -ForegroundColor Yellow
        Write-Host "  Migration output:" -ForegroundColor Gray
        $migrationOutput -split "`n" | Select-Object -First 10 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
    }
} else {
    Write-Host "  WARNING: Backend pod not ready. Migrations will run on next pod start." -ForegroundColor Yellow
}

# Развертывание мониторинга (опционально)
Write-Host ""
$deployMonitoring = Read-Host "Deploy monitoring stack (Prometheus + Grafana)? (Y/N)"
if ($deployMonitoring -eq "Y" -or $deployMonitoring -eq "y") {
    Write-Host "Deploying monitoring..." -ForegroundColor Yellow
    
    # Подготовка секретов Grafana
    if (-Not (Test-Path "k8s/monitoring/grafana-secrets.yaml")) {
        Copy-Item "k8s/monitoring/grafana-secrets.yaml.example" "k8s/monitoring/grafana-secrets.yaml"
        Write-Host "  Created grafana-secrets.yaml from example" -ForegroundColor Green
    }
    
    # Развертывание мониторинга
    kubectl apply -f k8s/monitoring/prometheus-storage.yaml
    kubectl apply -f k8s/monitoring/prometheus-config.yaml
    kubectl apply -f k8s/monitoring/prometheus-deployment.yaml
    kubectl apply -f k8s/monitoring/grafana-storage.yaml
    kubectl apply -f k8s/monitoring/grafana-datasources.yaml
    kubectl apply -f k8s/monitoring/grafana-dashboards.yaml
    kubectl apply -f k8s/monitoring/grafana-secrets.yaml
    kubectl apply -f k8s/monitoring/grafana-deployment.yaml
    kubectl apply -f k8s/monitoring/postgres-exporter.yaml
    kubectl apply -f k8s/monitoring/redis-exporter.yaml
    
    Write-Host "  OK Monitoring stack deployed" -ForegroundColor Green
}

# Финальный статус
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Checking deployment status..." -ForegroundColor Yellow
Start-Sleep -Seconds 10
kubectl get pods -n medaudit

Write-Host ""
Write-Host "=== Access Information ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend API:" -ForegroundColor Yellow
Write-Host "  kubectl port-forward svc/backend-service 8000:8000 -n medaudit" -ForegroundColor Gray
Write-Host "  URL: http://localhost:8000" -ForegroundColor Gray
Write-Host "  Docs: http://localhost:8000/api/docs" -ForegroundColor Gray
Write-Host ""

if ($deployMonitoring -eq "Y" -or $deployMonitoring -eq "y") {
    Write-Host "Grafana:" -ForegroundColor Yellow
    Write-Host "  kubectl port-forward svc/grafana-service 3000:3000 -n medaudit" -ForegroundColor Gray
    Write-Host "  URL: http://localhost:3000" -ForegroundColor Gray
    Write-Host "  Username: admin" -ForegroundColor Gray
    Write-Host "  Password: MedAudit2024!Grafana" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "Prometheus:" -ForegroundColor Yellow
    Write-Host "  kubectl port-forward svc/prometheus-service 9090:9090 -n medaudit" -ForegroundColor Gray
    Write-Host "  URL: http://localhost:9090" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  kubectl get all -n medaudit" -ForegroundColor Gray
Write-Host "  kubectl logs -f deployment/backend -n medaudit" -ForegroundColor Gray
Write-Host "  kubectl get pods -n medaudit" -ForegroundColor Gray
Write-Host ""

