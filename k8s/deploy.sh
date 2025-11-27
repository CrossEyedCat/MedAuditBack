#!/bin/bash

# Скрипт для развертывания MediAudit Backend в Kubernetes

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Развертывание MediAudit Backend в Kubernetes ===${NC}\n"

# Проверка наличия kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Ошибка: kubectl не установлен${NC}"
    exit 1
fi

# Проверка подключения к кластеру
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}Ошибка: Не удается подключиться к Kubernetes кластеру${NC}"
    exit 1
fi

# Проверка наличия secrets.yaml
if [ ! -f "k8s/secrets.yaml" ]; then
    echo -e "${YELLOW}Предупреждение: k8s/secrets.yaml не найден${NC}"
    echo -e "${YELLOW}Скопируйте k8s/secrets.yaml.example в k8s/secrets.yaml и настройте секреты${NC}"
    read -p "Продолжить без секретов? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Создание namespace
echo -e "${GREEN}[1/10] Создание namespace...${NC}"
kubectl apply -f k8s/namespace.yaml

# Применение ConfigMap
echo -e "${GREEN}[2/10] Применение ConfigMap...${NC}"
kubectl apply -f k8s/configmap.yaml

# Применение Secrets (если существует)
if [ -f "k8s/secrets.yaml" ]; then
    echo -e "${GREEN}[3/10] Применение Secrets...${NC}"
    kubectl apply -f k8s/secrets.yaml
else
    echo -e "${YELLOW}[3/10] Пропуск Secrets (файл не найден)${NC}"
fi

# Создание PVC
echo -e "${GREEN}[4/10] Создание PersistentVolumeClaim...${NC}"
kubectl apply -f k8s/storage-pvc.yaml

# Развертывание PostgreSQL
echo -e "${GREEN}[5/10] Развертывание PostgreSQL...${NC}"
kubectl apply -f k8s/postgres-statefulset.yaml

# Развертывание Redis
echo -e "${GREEN}[6/10] Развертывание Redis...${NC}"
kubectl apply -f k8s/redis-statefulset.yaml

# Ожидание готовности PostgreSQL и Redis
echo -e "${GREEN}[7/10] Ожидание готовности PostgreSQL и Redis...${NC}"
echo -e "${YELLOW}Это может занять несколько минут...${NC}"
kubectl wait --for=condition=ready pod -l app=postgres -n medaudit --timeout=300s || echo -e "${RED}PostgreSQL не готов${NC}"
kubectl wait --for=condition=ready pod -l app=redis -n medaudit --timeout=300s || echo -e "${RED}Redis не готов${NC}"

# Развертывание Backend
echo -e "${GREEN}[8/10] Развертывание Backend...${NC}"
kubectl apply -f k8s/backend-deployment.yaml

# Применение HPA для Backend
echo -e "${GREEN}[9/10] Применение HorizontalPodAutoscaler для Backend...${NC}"
kubectl apply -f k8s/backend-hpa.yaml

# Развертывание Celery Worker
echo -e "${GREEN}[10/10] Развертывание Celery Worker...${NC}"
kubectl apply -f k8s/celery-deployment.yaml

# Применение HPA для Celery
echo -e "${GREEN}[11/11] Применение HorizontalPodAutoscaler для Celery...${NC}"
kubectl apply -f k8s/celery-hpa.yaml

# Применение Ingress (опционально)
read -p "Применить Ingress? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Применение Ingress...${NC}"
    kubectl apply -f k8s/ingress.yaml
fi

echo -e "\n${GREEN}=== Развертывание завершено! ===${NC}\n"

# Показ статуса
echo -e "${GREEN}Статус подов:${NC}"
kubectl get pods -n medaudit

echo -e "\n${GREEN}Статус сервисов:${NC}"
kubectl get svc -n medaudit

echo -e "\n${GREEN}Статус HPA:${NC}"
kubectl get hpa -n medaudit

echo -e "\n${GREEN}Для просмотра логов используйте:${NC}"
echo -e "  kubectl logs -f deployment/backend -n medaudit"
echo -e "  kubectl logs -f deployment/celery-worker -n medaudit"



