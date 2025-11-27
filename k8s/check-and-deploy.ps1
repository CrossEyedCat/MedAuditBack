# Environment check and deployment script for Windows

$ErrorActionPreference = "Continue"

Write-Host "=== MediAudit Kubernetes Environment Check ===" -ForegroundColor Cyan
Write-Host ""

# Check Docker
Write-Host "[1/6] Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "  OK Docker installed: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Docker not installed!" -ForegroundColor Red
    exit 1
}

# Check kubectl
Write-Host "[2/6] Checking kubectl..." -ForegroundColor Yellow
try {
    $kubectlVersion = kubectl version --client 2>&1 | Select-Object -First 1
    Write-Host "  OK kubectl installed: $kubectlVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: kubectl not installed!" -ForegroundColor Red
    exit 1
}

# Check Kubernetes cluster
Write-Host "[3/6] Checking Kubernetes cluster..." -ForegroundColor Yellow
$null = kubectl cluster-info 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK Kubernetes cluster available" -ForegroundColor Green
    $nodes = kubectl get nodes 2>&1
    Write-Host "  Cluster nodes:" -ForegroundColor Cyan
    $nodes | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
} else {
    Write-Host "  ERROR: Kubernetes cluster not running!" -ForegroundColor Red
    Write-Host "  Enable Kubernetes in Docker Desktop: Settings -> Kubernetes -> Enable Kubernetes" -ForegroundColor Yellow
    exit 1
}

# Check Metrics Server
Write-Host "[4/6] Checking Metrics Server..." -ForegroundColor Yellow
$null = kubectl get deployment metrics-server -n kube-system 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK Metrics Server installed" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Metrics Server not installed (required for HPA)" -ForegroundColor Yellow
    $response = Read-Host "  Install Metrics Server now? (y/N)"
    if ($response -eq "y" -or $response -eq "Y") {
        Write-Host "  Installing Metrics Server..." -ForegroundColor Cyan
        kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    }
}

# Check secrets
Write-Host "[5/6] Checking secrets..." -ForegroundColor Yellow
if (Test-Path "k8s/secrets.yaml") {
    Write-Host "  OK secrets.yaml file found" -ForegroundColor Green
    $secretsContent = Get-Content "k8s/secrets.yaml" -Raw
    if ($secretsContent -match "CHANGE_ME") {
        Write-Host "  WARNING: secrets.yaml contains CHANGE_ME values" -ForegroundColor Yellow
        Write-Host "  Edit k8s/secrets.yaml before deployment" -ForegroundColor Yellow
    } else {
        Write-Host "  OK Secrets configured" -ForegroundColor Green
    }
} else {
    Write-Host "  WARNING: secrets.yaml file not found" -ForegroundColor Yellow
    Write-Host "  Creating from template..." -ForegroundColor Cyan
    Copy-Item "k8s/secrets.yaml.example" "k8s/secrets.yaml"
    Write-Host "  OK File created. Edit k8s/secrets.yaml before deployment" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  To generate SECRET_KEY run:" -ForegroundColor Cyan
    Write-Host "    python -c `"import secrets; print(secrets.token_urlsafe(32))`"" -ForegroundColor Gray
}

# Check Docker image
Write-Host "[6/6] Checking Docker image..." -ForegroundColor Yellow
$imageExists = docker images medaudit-backend:latest --format "{{.Repository}}:{{.Tag}}" 2>&1
if ($imageExists -match "medaudit-backend:latest") {
    Write-Host "  OK Docker image medaudit-backend:latest found" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Docker image medaudit-backend:latest not found" -ForegroundColor Yellow
    $response = Read-Host "  Build image now? (y/N)"
    if ($response -eq "y" -or $response -eq "Y") {
        Write-Host "  Building image..." -ForegroundColor Cyan
        docker build -f Dockerfile.prod -t medaudit-backend:latest .
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  OK Image built successfully" -ForegroundColor Green
        } else {
            Write-Host "  ERROR: Failed to build image" -ForegroundColor Red
            exit 1
        }
    }
}

Write-Host ""
Write-Host "=== Check completed ===" -ForegroundColor Cyan
Write-Host ""

$response = Read-Host "Deploy application to Kubernetes? (y/N)"
if ($response -eq "y" -or $response -eq "Y") {
    Write-Host ""
    Write-Host "Starting deployment..." -ForegroundColor Cyan
    Write-Host ""
    & ".\k8s\deploy.ps1"
} else {
    Write-Host ""
    Write-Host "To deploy manually run:" -ForegroundColor Cyan
    Write-Host "  .\k8s\deploy.ps1" -ForegroundColor Gray
}
