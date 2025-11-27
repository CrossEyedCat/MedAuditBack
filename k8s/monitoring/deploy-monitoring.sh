#!/bin/bash

# Скрипт для развертывания мониторинга

set -e

echo "=== Deploying Monitoring Stack ==="

# Проверка секретов Grafana
if [ ! -f "k8s/monitoring/grafana-secrets.yaml" ]; then
    echo "WARNING: grafana-secrets.yaml not found"
    echo "Copy k8s/monitoring/grafana-secrets.yaml.example to k8s/monitoring/grafana-secrets.yaml"
    echo "and set admin password"
    exit 1
fi

# Применение манифестов
echo "[1/8] Creating Prometheus storage..."
kubectl apply -f k8s/monitoring/prometheus-storage.yaml

echo "[2/8] Creating Prometheus config..."
kubectl apply -f k8s/monitoring/prometheus-config.yaml

echo "[3/8] Deploying Prometheus..."
kubectl apply -f k8s/monitoring/prometheus-deployment.yaml

echo "[4/8] Creating Grafana storage..."
kubectl apply -f k8s/monitoring/grafana-storage.yaml

echo "[5/8] Creating Grafana datasources..."
kubectl apply -f k8s/monitoring/grafana-datasources.yaml

echo "[6/8] Creating Grafana dashboards..."
kubectl apply -f k8s/monitoring/grafana-dashboards.yaml

echo "[7/8] Applying Grafana secrets..."
kubectl apply -f k8s/monitoring/grafana-secrets.yaml

echo "[8/8] Deploying Grafana..."
kubectl apply -f k8s/monitoring/grafana-deployment.yaml

echo "[9/9] Deploying exporters..."
kubectl apply -f k8s/monitoring/postgres-exporter.yaml
kubectl apply -f k8s/monitoring/redis-exporter.yaml

echo ""
echo "=== Monitoring deployed! ==="
echo ""
echo "Access Grafana:"
echo "  kubectl port-forward svc/grafana-service 3000:3000 -n medaudit"
echo "  Then open: http://localhost:3000"
echo "  Default credentials: admin / (your password)"
echo ""
echo "Access Prometheus:"
echo "  kubectl port-forward svc/prometheus-service 9090:9090 -n medaudit"
echo "  Then open: http://localhost:9090"



