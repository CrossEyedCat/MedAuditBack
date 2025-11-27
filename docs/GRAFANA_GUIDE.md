# Руководство по работе с Grafana для MediAudit

## Доступ к Grafana

```powershell
kubectl port-forward svc/grafana-service 3000:3000 -n medaudit
```

Откройте в браузере: http://localhost:3000

**Учетные данные:**
- Username: `admin`
- Password: `MedAudit2024!Grafana`

## Создание дашборда

### Шаг 1: Создание нового дашборда

1. Войдите в Grafana
2. Нажмите **Dashboards** (в левом меню)
3. Нажмите **New Dashboard**
4. Нажмите **Add visualization** (или **Add panel**)

### Шаг 2: Выбор источника данных

1. В панели справа выберите **Data source**
2. Выберите **Prometheus** (уже настроен как default)
3. Если Prometheus не виден, проверьте настройки:
   - Configuration → Data sources → Prometheus
   - URL должен быть: `http://prometheus-service:9090`

## Основные метрики для отображения

### 1. HTTP Requests Rate (Скорость HTTP запросов)

**Query:**
```promql
rate(http_requests_total[5m])
```

**Настройки панели:**
- **Panel type**: Time series
- **Legend**: `{{method}} {{endpoint}}`
- **Title**: HTTP Requests Rate

### 2. HTTP Request Duration (Длительность HTTP запросов)

**Query для p95:**
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**Query для p99:**
```promql
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

**Настройки панели:**
- **Panel type**: Time series
- **Legend**: p95, p99
- **Title**: HTTP Request Duration (p95, p99)
- **Unit**: seconds (s)

### 3. HTTP Requests по статус кодам

**Query:**
```promql
sum by (status_code) (rate(http_requests_total[5m]))
```

**Настройки панели:**
- **Panel type**: Time series
- **Legend**: `{{status_code}}`
- **Title**: HTTP Requests by Status Code

### 4. Активные поды (Active Pods)

**Query:**
```promql
count(kube_pod_status_phase{phase="Running",namespace="medaudit"})
```

**Настройки панели:**
- **Panel type**: Stat
- **Title**: Active Pods
- **Unit**: short

### 5. CPU Usage (Использование CPU)

**Query:**
```promql
rate(container_cpu_usage_seconds_total{namespace="medaudit"}[5m])
```

**Настройки панели:**
- **Panel type**: Time series
- **Legend**: `{{pod}}`
- **Title**: CPU Usage
- **Unit**: percent (0.0-1.0)

### 6. Memory Usage (Использование памяти)

**Query:**
```promql
container_memory_usage_bytes{namespace="medaudit"}
```

**Настройки панели:**
- **Panel type**: Time series
- **Legend**: `{{pod}}`
- **Title**: Memory Usage
- **Unit**: bytes (IEC)

### 7. Загруженные документы

**Query:**
```promql
sum(documents_uploaded_total)
```

**Настройки панели:**
- **Panel type**: Stat
- **Title**: Documents Uploaded
- **Unit**: short

### 8. Обработанные документы

**Query:**
```promql
sum by (status) (documents_processed_total)
```

**Настройки панели:**
- **Panel type**: Time series
- **Legend**: `{{status}}`
- **Title**: Documents Processed

### 9. Сгенерированные отчеты

**Query:**
```promql
sum by (status) (reports_generated_total)
```

**Настройки панели:**
- **Panel type**: Time series
- **Legend**: `{{status}}`
- **Title**: Reports Generated

### 10. Обнаруженные нарушения

**Query:**
```promql
sum by (risk_level) (violations_detected_total)
```

**Настройки панели:**
- **Panel type**: Pie chart
- **Legend**: `{{risk_level}}`
- **Title**: Violations by Risk Level

## Создание комплексного дашборда

### Пример структуры дашборда "MediAudit Overview"

1. **Верхний ряд:**
   - HTTP Requests Rate (12 колонок)
   - HTTP Request Duration (12 колонок)

2. **Второй ряд:**
   - Active Pods (6 колонок)
   - Documents Uploaded (6 колонок)

3. **Третий ряд:**
   - CPU Usage (12 колонок)
   - Memory Usage (12 колонок)

4. **Четвертый ряд:**
   - Documents Processed (12 колонок)
   - Reports Generated (12 колонок)

5. **Пятый ряд:**
   - Violations by Risk Level (24 колонки)

## Полезные PromQL запросы

### Фильтрация по endpoint

```promql
rate(http_requests_total{endpoint="/api/v1/documents/upload"}[5m])
```

### Фильтрация по методу

```promql
rate(http_requests_total{method="POST"}[5m])
```

### Ошибки (5xx)

```promql
sum(rate(http_requests_total{status_code=~"5.."}[5m]))
```

### Успешные запросы (2xx)

```promql
sum(rate(http_requests_total{status_code=~"2.."}[5m]))
```

### Средняя длительность запросов

```promql
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])
```

### Количество активных подключений к БД

```promql
active_connections{connection_type="database"}
```

### Размер очереди задач

```promql
queue_size{queue_name="celery"}
```

## Настройка алертов

### Пример алерта: Высокая ошибка

1. Перейдите в **Alerting** → **Alert rules**
2. Нажмите **New alert rule**
3. Настройте:
   - **Name**: High Error Rate
   - **Query**: `sum(rate(http_requests_total{status_code=~"5.."}[5m])) > 0.1`
   - **Condition**: When `A` is above `0.1`
   - **Evaluation**: Every `1m` for `5m`

### Пример алерта: Высокая длительность запросов

1. **Name**: High Response Time
2. **Query**: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
3. **Condition**: When `A` is above `1` (секунда)
4. **Evaluation**: Every `1m` for `5m`

### Пример алерта: Под недоступен

1. **Name**: Pod Down
2. **Query**: `kube_pod_status_phase{phase!="Running",namespace="medaudit"}`
3. **Condition**: When `A` is above `0`
4. **Evaluation**: Every `30s` for `2m`

## Экспорт и импорт дашборда

### Экспорт дашборда

1. Откройте дашборд
2. Нажмите **Dashboard settings** (шестеренка)
3. Перейдите на вкладку **JSON Model**
4. Скопируйте JSON
5. Сохраните в файл

### Импорт дашборда

1. **Dashboards** → **Import**
2. Вставьте JSON или загрузите файл
3. Выберите Prometheus как datasource
4. Нажмите **Import**

## Готовые дашборды

Можно использовать готовые дашборды из Grafana Dashboard Library:

1. **Kubernetes Cluster Monitoring** (ID: 7249)
2. **Node Exporter Full** (ID: 1860)
3. **PostgreSQL Database** (ID: 9628)
4. **Redis Dashboard** (ID: 11835)

Для импорта:
- **Dashboards** → **Import**
- Введите ID дашборда
- Нажмите **Load**

## Полезные советы

1. **Используйте переменные** для фильтрации:
   - Settings → Variables → New variable
   - Type: Query
   - Query: `label_values(http_requests_total, endpoint)`

2. **Настройте время обновления:**
   - В правом верхнем углу выберите интервал (например, Last 6 hours)
   - Нажмите на иконку обновления для автообновления

3. **Используйте аннотации** для отметки событий:
   - Добавьте аннотацию при деплое, рестарте и т.д.

4. **Создайте папки** для организации:
   - Dashboards → Manage → New folder

5. **Настройте уведомления:**
   - Alerting → Notification channels
   - Добавьте email, Slack, webhook и т.д.

## Проверка доступности метрик

Проверьте, что метрики доступны в Prometheus:

```powershell
# Откройте Prometheus
kubectl port-forward svc/prometheus-service 9090:9090 -n medaudit
```

В Prometheus UI выполните запросы:
- `http_requests_total`
- `http_request_duration_seconds`
- `documents_uploaded_total`

Если метрики не видны, проверьте:
1. Backend экспортирует метрики: `curl http://localhost:8000/metrics`
2. Prometheus собирает метрики: Status → Targets в Prometheus UI
3. Правильность запросов PromQL

## Решение проблем

### Метрики не отображаются

1. Проверьте, что Prometheus datasource настроен правильно
2. Проверьте доступность метрик в Prometheus UI
3. Убедитесь, что запрос PromQL синтаксически корректен
4. Проверьте временной диапазон (метрики могут быть старыми)

### Ошибка "No data"

1. Проверьте, что метрики существуют в Prometheus
2. Расширьте временной диапазон
3. Проверьте фильтры в запросе
4. Убедитесь, что метки экспортируются из приложения

### Дашборд не сохраняется

1. Проверьте права доступа
2. Убедитесь, что вы вошли в систему
3. Попробуйте экспортировать и импортировать заново





