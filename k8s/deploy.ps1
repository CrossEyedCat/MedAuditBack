# Deployment script for MediAudit Backend in Kubernetes (PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "=== Deploying MediAudit Backend to Kubernetes ===" -ForegroundColor Green
Write-Host ""

# Check kubectl
try {
    kubectl version --client | Out-Null
} catch {
    Write-Host "ERROR: kubectl not installed" -ForegroundColor Red
    exit 1
}

# Check cluster connection
try {
    kubectl cluster-info | Out-Null
} catch {
    Write-Host "ERROR: Cannot connect to Kubernetes cluster" -ForegroundColor Red
    exit 1
}

# Check secrets.yaml
if (-Not (Test-Path "k8s/secrets.yaml")) {
    Write-Host "WARNING: k8s/secrets.yaml not found" -ForegroundColor Yellow
    Write-Host "Copy k8s/secrets.yaml.example to k8s/secrets.yaml and configure secrets" -ForegroundColor Yellow
    $response = Read-Host "Continue without secrets? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        exit 1
    }
}

# Create namespace
Write-Host "[1/10] Creating namespace..." -ForegroundColor Green
kubectl apply -f k8s/namespace.yaml

# Apply ConfigMap
Write-Host "[2/10] Applying ConfigMap..." -ForegroundColor Green
kubectl apply -f k8s/configmap.yaml

# Apply Secrets (if exists)
if (Test-Path "k8s/secrets.yaml") {
    Write-Host "[3/10] Applying Secrets..." -ForegroundColor Green
    kubectl apply -f k8s/secrets.yaml
} else {
    Write-Host "[3/10] Skipping Secrets (file not found)" -ForegroundColor Yellow
}

# Create PVC
Write-Host "[4/10] Creating PersistentVolumeClaim..." -ForegroundColor Green
kubectl apply -f k8s/storage-pvc.yaml

# Deploy PostgreSQL
Write-Host "[5/10] Deploying PostgreSQL..." -ForegroundColor Green
kubectl apply -f k8s/postgres-statefulset.yaml

# Deploy Redis
Write-Host "[6/10] Deploying Redis..." -ForegroundColor Green
kubectl apply -f k8s/redis-statefulset.yaml

# Wait for PostgreSQL and Redis
Write-Host "[7/10] Waiting for PostgreSQL and Redis..." -ForegroundColor Green
Write-Host "This may take a few minutes..." -ForegroundColor Yellow
try {
    kubectl wait --for=condition=ready pod -l app=postgres -n medaudit --timeout=300s
} catch {
    Write-Host "PostgreSQL not ready" -ForegroundColor Red
}
try {
    kubectl wait --for=condition=ready pod -l app=redis -n medaudit --timeout=300s
} catch {
    Write-Host "Redis not ready" -ForegroundColor Red
}

# Deploy Backend
Write-Host "[8/10] Deploying Backend..." -ForegroundColor Green
kubectl apply -f k8s/backend-deployment.yaml

# Apply HPA for Backend
Write-Host "[9/10] Applying HorizontalPodAutoscaler for Backend..." -ForegroundColor Green
kubectl apply -f k8s/backend-hpa.yaml

# Deploy Celery Worker
Write-Host "[10/10] Deploying Celery Worker..." -ForegroundColor Green
kubectl apply -f k8s/celery-deployment.yaml

# Apply HPA for Celery
Write-Host "[11/11] Applying HorizontalPodAutoscaler for Celery..." -ForegroundColor Green
kubectl apply -f k8s/celery-hpa.yaml

# Apply Ingress (optional)
$response = Read-Host "Apply Ingress? (y/N)"
if ($response -eq "y" -or $response -eq "Y") {
    Write-Host "Applying Ingress..." -ForegroundColor Green
    kubectl apply -f k8s/ingress.yaml
}

Write-Host ""
Write-Host "=== Deployment completed! ===" -ForegroundColor Green
Write-Host ""

# Show status
Write-Host "Pod status:" -ForegroundColor Green
kubectl get pods -n medaudit

Write-Host ""
Write-Host "Service status:" -ForegroundColor Green
kubectl get svc -n medaudit

Write-Host ""
Write-Host "HPA status:" -ForegroundColor Green
kubectl get hpa -n medaudit

Write-Host ""
Write-Host "To view logs use:" -ForegroundColor Green
Write-Host "  kubectl logs -f deployment/backend -n medaudit"
Write-Host "  kubectl logs -f deployment/celery-worker -n medaudit"
