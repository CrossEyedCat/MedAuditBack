#!/bin/bash

# Скрипт для удаления MediAudit Backend из Kubernetes

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Удаление MediAudit Backend из Kubernetes ===${NC}\n"

# Подтверждение
read -p "Вы уверены, что хотите удалить все ресурсы? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Отменено${NC}"
    exit 0
fi

# Удаление ресурсов в обратном порядке
echo -e "${GREEN}Удаление ресурсов...${NC}"

# Удаление Ingress
if kubectl get ingress medaudit-ingress -n medaudit &> /dev/null; then
    echo -e "${GREEN}Удаление Ingress...${NC}"
    kubectl delete -f k8s/ingress.yaml || true
fi

# Удаление HPA
echo -e "${GREEN}Удаление HPA...${NC}"
kubectl delete -f k8s/backend-hpa.yaml || true
kubectl delete -f k8s/celery-hpa.yaml || true

# Удаление Deployments
echo -e "${GREEN}Удаление Deployments...${NC}"
kubectl delete -f k8s/backend-deployment.yaml || true
kubectl delete -f k8s/celery-deployment.yaml || true

# Удаление StatefulSets
echo -e "${GREEN}Удаление StatefulSets...${NC}"
kubectl delete -f k8s/postgres-statefulset.yaml || true
kubectl delete -f k8s/redis-statefulset.yaml || true

# Удаление PVC (опционально)
read -p "Удалить PersistentVolumeClaims (данные будут потеряны)? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Удаление PVC...${NC}"
    kubectl delete -f k8s/storage-pvc.yaml || true
fi

# Удаление ConfigMap и Secrets
echo -e "${GREEN}Удаление ConfigMap и Secrets...${NC}"
kubectl delete -f k8s/configmap.yaml || true
kubectl delete -f k8s/secrets.yaml || true

# Удаление Namespace (удалит все ресурсы в namespace)
read -p "Удалить namespace medaudit (удалит все ресурсы)? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Удаление namespace...${NC}"
    kubectl delete namespace medaudit || true
fi

echo -e "\n${GREEN}=== Удаление завершено! ===${NC}\n"



