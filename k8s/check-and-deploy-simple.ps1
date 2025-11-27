# Скрипт проверки окружения и развертывания на Windows

$ErrorActionPreference = "Continue"

Write-Host "=== Проверка окружения для MediAudit Kubernetes ===" -ForegroundColor Cyan
Write-Host ""

# Проверка Docker
Write-Host "[1/6] Проверка Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "  ✓ Docker установлен: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Docker не установлен!" -ForegroundColor Red
    exit 1
}

# Проверка kubectl
Write-Host "[2/6] Проверка kubectl..." -ForegroundColor Yellow
try {
    $kubectlVersion = kubectl version --client --short 2>&1 | Select-Object -First 1
    Write-Host "  ✓ kubectl установлен: $kubectlVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ kubectl не установлен!" -ForegroundColor Red
    exit 1
}

# Проверка подключения к кластеру
Write-Host "[3/6] Проверка Kubernetes кластера..." -ForegroundColor Yellow
$null = kubectl cluster-info 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Kubernetes кластер доступен" -ForegroundColor Green
    $nodes = kubectl get nodes 2>&1
    Write-Host "  Узлы кластера:" -ForegroundColor Cyan
    $nodes | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
} else {
    Write-Host "  ✗ Kubernetes кластер не запущен!" -ForegroundColor Red
    Write-Host "  Включите Kubernetes в Docker Desktop: Settings → Kubernetes → Enable Kubernetes" -ForegroundColor Yellow
    exit 1
}

# Проверка Metrics Server
Write-Host "[4/6] Проверка Metrics Server..." -ForegroundColor Yellow
$null = kubectl get deployment metrics-server -n kube-system 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Metrics Server установлен" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Metrics Server не установлен" -ForegroundColor Yellow
    $response = Read-Host "  Установить Metrics Server? (y/N)"
    if ($response -eq "y") {
        kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    }
}

# Проверка секретов
Write-Host "[5/6] Проверка секретов..." -ForegroundColor Yellow
if (Test-Path "k8s/secrets.yaml") {
    Write-Host "  ✓ Файл secrets.yaml найден" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Файл secrets.yaml не найден" -ForegroundColor Yellow
    Copy-Item "k8s/secrets.yaml.example" "k8s/secrets.yaml"
    Write-Host "  ✓ Файл создан. Отредактируйте k8s/secrets.yaml" -ForegroundColor Yellow
}

# Проверка Docker образа
Write-Host "[6/6] Проверка Docker образа..." -ForegroundColor Yellow
$imageExists = docker images medaudit-backend:latest --format "{{.Repository}}:{{.Tag}}" 2>&1
if ($imageExists -match "medaudit-backend:latest") {
    Write-Host "  ✓ Docker образ найден" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Docker образ не найден" -ForegroundColor Yellow
    $response = Read-Host "  Собрать образ? (y/N)"
    if ($response -eq "y") {
        docker build -f Dockerfile.prod -t medaudit-backend:latest .
    }
}

Write-Host ""
Write-Host "=== Проверка завершена ===" -ForegroundColor Cyan
Write-Host ""

$response = Read-Host "Развернуть приложение? (y/N)"
if ($response -eq "y") {
    Write-Host "Запуск развертывания..." -ForegroundColor Cyan
    & ".\k8s\deploy.ps1"
}





