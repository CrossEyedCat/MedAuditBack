# Скрипты для генерации нагрузки

Скрипты для создания нагрузки на API и генерации метрик для тестирования мониторинга.

## PowerShell скрипт (Windows)

### Быстрый запуск

```powershell
# Убедитесь, что API доступен
kubectl port-forward svc/backend-service 8000:8000 -n medaudit

# В другом терминале запустите генератор нагрузки
.\scripts\load-generator.ps1
```

### Параметры

```powershell
.\scripts\load-generator.ps1 `
    -Url "http://localhost:8000" `
    -Duration 60 `
    -RequestsPerSecond 10 `
    -Concurrent 5
```

**Параметры:**
- `-Url` - URL API (по умолчанию: http://localhost:8000)
- `-Duration` - Длительность в секундах (по умолчанию: 60)
- `-RequestsPerSecond` - Запросов в секунду (по умолчанию: 10)
- `-Concurrent` - Параллельных запросов (по умолчанию: 5)

### Примеры

**Легкая нагрузка (для тестирования):**
```powershell
.\scripts\load-generator.ps1 -Duration 30 -RequestsPerSecond 5 -Concurrent 3
```

**Средняя нагрузка:**
```powershell
.\scripts\load-generator.ps1 -Duration 120 -RequestsPerSecond 20 -Concurrent 10
```

**Высокая нагрузка:**
```powershell
.\scripts\load-generator.ps1 -Duration 300 -RequestsPerSecond 50 -Concurrent 20
```

## Python скрипт (кроссплатформенный)

### Требования

```bash
pip install aiohttp
```

### Запуск

```bash
# Убедитесь, что API доступен
kubectl port-forward svc/backend-service 8000:8000 -n medaudit

# В другом терминале запустите генератор нагрузки
python scripts/load-generator.py
```

### Параметры

```bash
python scripts/load-generator.py \
    --url http://localhost:8000 \
    --duration 60 \
    --rps 10 \
    --concurrent 10
```

**Параметры:**
- `--url` - URL API (по умолчанию: http://localhost:8000)
- `--duration` - Длительность в секундах (по умолчанию: 60)
- `--rps` - Запросов в секунду (по умолчанию: 10)
- `--concurrent` - Параллельных запросов (по умолчанию: 10)

## Использование с Kubernetes

### Вариант 1: Port-forward

```powershell
# Терминал 1: Port-forward
kubectl port-forward svc/backend-service 8000:8000 -n medaudit

# Терминал 2: Генератор нагрузки
.\scripts\load-generator.ps1
```

### Вариант 2: Прямое подключение к сервису

Если у вас есть доступ к кластеру:

```powershell
# Получите IP сервиса
$serviceIp = kubectl get svc backend-service -n medaudit -o jsonpath='{.spec.clusterIP}'

# Запустите генератор с внутренним IP
.\scripts\load-generator.ps1 -Url "http://$serviceIp:8000"
```

### Вариант 3: Запуск внутри кластера (Job)

Создайте Job для генерации нагрузки:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: load-generator
  namespace: medaudit
spec:
  template:
    spec:
      containers:
      - name: load-generator
        image: curlimages/curl:latest
        command:
        - /bin/sh
        - -c
        - |
          for i in $(seq 1 1000); do
            curl -s http://backend-service:8000/health > /dev/null
            curl -s http://backend-service:8000/ > /dev/null
            curl -s http://backend-service:8000/metrics > /dev/null
            sleep 0.1
          done
      restartPolicy: Never
  backoffLimit: 1
```

## Проверка метрик

После запуска генератора нагрузки:

1. **Откройте Grafana:**
   ```powershell
   kubectl port-forward svc/grafana-service 3000:3000 -n medaudit
   ```

2. **Проверьте метрики:**
   - HTTP Requests Rate должен показывать активность
   - HTTP Request Duration должен отображать значения
   - Метрики должны обновляться в реальном времени

3. **Проверьте Prometheus:**
   ```powershell
   kubectl port-forward svc/prometheus-service 9090:9090 -n medaudit
   ```
   Выполните запрос: `rate(http_requests_total[5m])`

## Рекомендации

- **Для тестирования:** Используйте легкую нагрузку (5-10 RPS)
- **Для демонстрации:** Используйте среднюю нагрузку (20-30 RPS)
- **Для стресс-тестирования:** Используйте высокую нагрузку (50+ RPS)

## Остановка

Нажмите `Ctrl+C` для остановки генератора нагрузки.

## Устранение проблем

### "API is not available"

Убедитесь, что:
1. Backend поды работают: `kubectl get pods -n medaudit`
2. Port-forward активен: `kubectl port-forward svc/backend-service 8000:8000 -n medaudit`
3. API отвечает: `curl http://localhost:8000/health`

### Метрики не появляются

1. Проверьте, что метрики экспортируются: `curl http://localhost:8000/metrics`
2. Проверьте, что Prometheus собирает метрики
3. Убедитесь, что прошло достаточно времени (метрики обновляются каждые 15 секунд)



