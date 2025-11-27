# Скрипт для удаления MediAudit Backend из Kubernetes (PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "=== Удаление MediAudit Backend из Kubernetes ===" -ForegroundColor Yellow
Write-Host ""

# Подтверждение
$response = Read-Host "Вы уверены, что хотите удалить все ресурсы? (y/N)"
if ($response -ne "y" -and $response -ne "Y") {
    Write-Host "Отменено" -ForegroundColor Green
    exit 0
}

# Удаление ресурсов в обратном порядке
Write-Host "Удаление ресурсов..." -ForegroundColor Green

# Удаление Ingress
try {
    kubectl get ingress medaudit-ingress -n medaudit | Out-Null
    Write-Host "Удаление Ingress..." -ForegroundColor Green
    kubectl delete -f k8s/ingress.yaml
} catch {
    # Ingress не существует, пропускаем
}

# Удаление HPA
Write-Host "Удаление HPA..." -ForegroundColor Green
try { kubectl delete -f k8s/backend-hpa.yaml } catch {}
try { kubectl delete -f k8s/celery-hpa.yaml } catch {}

# Удаление Deployments
Write-Host "Удаление Deployments..." -ForegroundColor Green
try { kubectl delete -f k8s/backend-deployment.yaml } catch {}
try { kubectl delete -f k8s/celery-deployment.yaml } catch {}

# Удаление StatefulSets
Write-Host "Удаление StatefulSets..." -ForegroundColor Green
try { kubectl delete -f k8s/postgres-statefulset.yaml } catch {}
try { kubectl delete -f k8s/redis-statefulset.yaml } catch {}

# Удаление PVC (опционально)
$response = Read-Host "Удалить PersistentVolumeClaims (данные будут потеряны)? (y/N)"
if ($response -eq "y" -or $response -eq "Y") {
    Write-Host "Удаление PVC..." -ForegroundColor Green
    try { kubectl delete -f k8s/storage-pvc.yaml } catch {}
}

# Удаление ConfigMap и Secrets
Write-Host "Удаление ConfigMap и Secrets..." -ForegroundColor Green
try { kubectl delete -f k8s/configmap.yaml } catch {}
try { kubectl delete -f k8s/secrets.yaml } catch {}

# Удаление Namespace (удалит все ресурсы в namespace)
$response = Read-Host "Удалить namespace medaudit (удалит все ресурсы)? (y/N)"
if ($response -eq "y" -or $response -eq "Y") {
    Write-Host "Удаление namespace..." -ForegroundColor Green
    try { kubectl delete namespace medaudit } catch {}
}

Write-Host ""
Write-Host "=== Удаление завершено! ===" -ForegroundColor Green
Write-Host ""





