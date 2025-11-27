# Мониторинг MediAudit Backend

Этот каталог содержит манифесты для развертывания стека мониторинга на базе Prometheus и Grafana.

## Компоненты

- **Prometheus** - сбор и хранение метрик
- **Grafana** - визуализация метрик и дашборды
- **PostgreSQL Exporter** - экспорт метрик PostgreSQL
- **Redis Exporter** - экспорт метрик Redis

## Быстрый старт

### 1. Подготовка секретов

```powershell
# Windows
Copy-Item k8s\monitoring\grafana-secrets.yaml.example k8s\monitoring\grafana-secrets.yaml
notepad k8s\monitoring\grafana-secrets.yaml
```

```bash
# Linux/Mac
cp k8s/monitoring/grafana-secrets.yaml.example k8s/monitoring/grafana-secrets.yaml
nano k8s/monitoring/grafana-secrets.yaml
```

Установите пароль администратора Grafana.

### 2. Обновление секретов приложения

Убедитесь, что в `k8s/secrets.yaml` есть `POSTGRES_CONNECTION_STRING` для PostgreSQL exporter.

### 3. Развертывание

```powershell
# Windows
.\k8s\monitoring\deploy-monitoring.ps1
```

```bash
# Linux/Mac
chmod +x k8s/monitoring/deploy-monitoring.sh
./k8s/monitoring/deploy-monitoring.sh
```

### 4. Доступ

**Grafana:**
```bash
kubectl port-forward svc/grafana-service 3000:3000 -n medaudit
```
Откройте http://localhost:3000 (admin / ваш пароль)

**Prometheus:**
```bash
kubectl port-forward svc/prometheus-service 9090:9090 -n medaudit
```
Откройте http://localhost:9090

## Структура файлов

- `prometheus-deployment.yaml` - Deployment и Service для Prometheus
- `prometheus-config.yaml` - ConfigMap с конфигурацией Prometheus
- `prometheus-storage.yaml` - PVC для хранения данных Prometheus
- `grafana-deployment.yaml` - Deployment и Service для Grafana
- `grafana-storage.yaml` - PVC для хранения данных Grafana
- `grafana-datasources.yaml` - ConfigMap с источниками данных Grafana
- `grafana-dashboards.yaml` - ConfigMap с дашбордами Grafana
- `grafana-secrets.yaml.example` - Шаблон секретов Grafana
- `postgres-exporter.yaml` - Exporter для PostgreSQL
- `redis-exporter.yaml` - Exporter для Redis
- `deploy-monitoring.sh` / `deploy-monitoring.ps1` - Скрипты развертывания

## Метрики приложения

Приложение экспортирует метрики на endpoint `/metrics`:

- HTTP метрики (запросы, длительность)
- Метрики БД (запросы, длительность)
- Метрики Redis (операции, длительность)
- Метрики Celery (задачи, статусы)
- Бизнес-метрики (документы, отчеты, нарушения)

## Дашборды

Grafana автоматически загружает дашборды из ConfigMap. Вы можете создавать дополнительные дашборды через веб-интерфейс Grafana.

## Дополнительная информация

См. [docs/MONITORING.md](../../docs/MONITORING.md) для подробной документации.



