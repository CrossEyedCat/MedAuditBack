# Мониторинг MediAudit Backend

Система мониторинга использует Prometheus для сбора метрик и Grafana для визуализации.

## Архитектура мониторинга

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Backend   │────▶│  Prometheus   │────▶│   Grafana   │
│   (метрики) │     │  (сбор)       │     │ (визуализ.) │
└─────────────┘     └──────────────┘     └─────────────┘
                            ▲
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────┴──────┐  ┌────────┴────────┐  ┌──────┴──────┐
│ PostgreSQL   │  │     Redis       │  │   Celery    │
│  Exporter    │  │    Exporter     │  │   Worker    │
└──────────────┘  └─────────────────┘  └─────────────┘
```

## Развертывание мониторинга

### Предварительные требования

1. Kubernetes кластер с запущенным приложением
2. Достаточно ресурсов для Prometheus и Grafana

### Быстрый старт

1. **Подготовьте секреты Grafana:**

```powershell
# Windows
Copy-Item k8s\monitoring\grafana-secrets.yaml.example k8s\monitoring\grafana-secrets.yaml
# Отредактируйте пароль администратора
notepad k8s\monitoring\grafana-secrets.yaml
```

```bash
# Linux/Mac
cp k8s/monitoring/grafana-secrets.yaml.example k8s/monitoring/grafana-secrets.yaml
# Отредактируйте пароль администратора
nano k8s/monitoring/grafana-secrets.yaml
```

2. **Обновите секреты с connection string для PostgreSQL exporter:**

Добавьте в `k8s/secrets.yaml`:
```yaml
POSTGRES_CONNECTION_STRING: "postgresql://medaudit:YOUR_PASSWORD@postgres-service:5432/medaudit_db?sslmode=disable"
```

3. **Разверните мониторинг:**

```powershell
# Windows
.\k8s\monitoring\deploy-monitoring.ps1
```

```bash
# Linux/Mac
chmod +x k8s/monitoring/deploy-monitoring.sh
./k8s/monitoring/deploy-monitoring.sh
```

Или вручную:
```bash
kubectl apply -f k8s/monitoring/
```

## Доступ к мониторингу

### Grafana

```bash
kubectl port-forward svc/grafana-service 3000:3000 -n medaudit
```

Откройте в браузере: http://localhost:3000

**Учетные данные по умолчанию:**
- Username: `admin`
- Password: (из `grafana-secrets.yaml`)

### Prometheus

```bash
kubectl port-forward svc/prometheus-service 9090:9090 -n medaudit
```

Откройте в браузере: http://localhost:9090

## Метрики приложения

### HTTP метрики

- `http_requests_total` - Общее количество HTTP запросов
  - Метки: `method`, `endpoint`, `status_code`
- `http_request_duration_seconds` - Длительность HTTP запросов
  - Метки: `method`, `endpoint`
  - Гистограмма с квантилями

### Метрики базы данных

- `db_queries_total` - Количество запросов к БД
  - Метки: `query_type`
- `db_query_duration_seconds` - Длительность запросов к БД
  - Метки: `query_type`

### Метрики Redis

- `redis_operations_total` - Количество операций Redis
  - Метки: `operation`
- `redis_operation_duration_seconds` - Длительность операций Redis
  - Метки: `operation`

### Метрики Celery

- `celery_tasks_total` - Количество задач Celery
  - Метки: `task_name`, `status`
- `celery_task_duration_seconds` - Длительность задач Celery
  - Метки: `task_name`

### Метрики бизнес-логики

- `documents_uploaded_total` - Загруженные документы
  - Метки: `file_type`
- `documents_processed_total` - Обработанные документы
  - Метки: `status`
- `reports_generated_total` - Сгенерированные отчеты
  - Метки: `status`
- `violations_detected_total` - Обнаруженные нарушения
  - Метки: `risk_level`

### Метрики системы

- `active_connections` - Активные подключения
  - Метки: `connection_type`
- `queue_size` - Размер очереди задач
  - Метки: `queue_name`

## Endpoint метрик

Метрики доступны по адресу:
```
GET /metrics
```

Пример использования:
```bash
curl http://localhost:8000/metrics
```

## Дашборды Grafana

### MediAudit Overview

Основной дашборд включает:
- HTTP Requests Rate - скорость запросов
- HTTP Request Duration - длительность запросов (p95, p99)
- Active Pods - количество активных подов
- CPU Usage - использование CPU
- Memory Usage - использование памяти

### Создание собственных дашбордов

1. Войдите в Grafana
2. Перейдите в Dashboards → New Dashboard
3. Добавьте панели с PromQL запросами

Примеры запросов:

```promql
# Скорость HTTP запросов
rate(http_requests_total[5m])

# 95-й перцентиль длительности запросов
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Количество активных подов
count(kube_pod_status_phase{phase="Running",namespace="medaudit"})

# Использование CPU
rate(container_cpu_usage_seconds_total{namespace="medaudit"}[5m])

# Использование памяти
container_memory_usage_bytes{namespace="medaudit"}
```

## Алерты

### Настройка Alertmanager

Для настройки алертов создайте `k8s/monitoring/alertmanager-config.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: medaudit
data:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m
    route:
      group_by: ['alertname']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 12h
      receiver: 'web.hook'
    receivers:
    - name: 'web.hook'
      webhook_configs:
      - url: 'http://your-webhook-url'
```

### Примеры правил алертов

Создайте `k8s/monitoring/prometheus-rules.yaml`:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: medaudit-alerts
  namespace: medaudit
spec:
  groups:
  - name: medaudit
    rules:
    - alert: HighErrorRate
      expr: rate(http_requests_total{status_code=~"5.."}[5m]) > 0.1
      for: 5m
      annotations:
        summary: "High error rate detected"
    
    - alert: HighResponseTime
      expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
      for: 5m
      annotations:
        summary: "High response time detected"
    
    - alert: PodDown
      expr: kube_pod_status_phase{phase!="Running",namespace="medaudit"} > 0
      for: 5m
      annotations:
        summary: "Pod is down"
```

## Экспортеры

### PostgreSQL Exporter

Собирает метрики PostgreSQL:
- Количество подключений
- Размер БД
- Статистика запросов
- Репликация (если используется)

### Redis Exporter

Собирает метрики Redis:
- Использование памяти
- Количество ключей
- Hit/Miss ratio
- Операции в секунду

## Хранение данных

- **Prometheus**: 30 дней хранения метрик (настраивается)
- **Grafana**: Дашборды и настройки хранятся в PersistentVolume

## Масштабирование

Prometheus и Grafana можно масштабировать:

```bash
# Масштабирование Prometheus (если нужно)
kubectl scale deployment prometheus -n medaudit --replicas=2

# Масштабирование Grafana (если нужно)
kubectl scale deployment grafana -n medaudit --replicas=2
```

## Устранение неполадок

### Prometheus не собирает метрики

```bash
# Проверьте конфигурацию
kubectl get configmap prometheus-config -n medaudit -o yaml

# Проверьте логи
kubectl logs deployment/prometheus -n medaudit

# Проверьте доступность метрик
kubectl exec -it deployment/prometheus -n medaudit -- wget -qO- http://backend-service:8000/metrics
```

### Grafana не подключается к Prometheus

```bash
# Проверьте datasource
kubectl get configmap grafana-datasources -n medaudit -o yaml

# Проверьте доступность Prometheus из Grafana
kubectl exec -it deployment/grafana -n medaudit -- wget -qO- http://prometheus-service:9090/api/v1/status/config
```

### Метрики не экспортируются из приложения

```bash
# Проверьте endpoint метрик
kubectl exec -it deployment/backend -n medaudit -- curl http://localhost:8000/metrics

# Проверьте логи приложения
kubectl logs deployment/backend -n medaudit
```

## Дополнительные ресурсы

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)



