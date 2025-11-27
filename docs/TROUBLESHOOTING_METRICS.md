# Устранение проблем с метриками в Grafana

## Проблема: "No data" в панелях Grafana

### Диагностика

1. **Проверьте статус подов:**
   ```powershell
   kubectl get pods -n medaudit
   ```
   Backend поды должны быть в статусе `Running`, не `CrashLoopBackOff`

2. **Проверьте доступность метрик:**
   ```powershell
   # Port-forward к backend
   kubectl port-forward svc/backend-service 8000:8000 -n medaudit
   
   # В другом терминале проверьте метрики
   curl http://localhost:8000/metrics
   ```
   Должны быть видны метрики `http_requests_total`, `http_request_duration_seconds` и т.д.

3. **Проверьте Prometheus targets:**
   ```powershell
   # Port-forward к Prometheus
   kubectl port-forward svc/prometheus-service 9090:9090 -n medaudit
   
   # Откройте http://localhost:9090/targets
   # Проверьте статус target "backend"
   ```

4. **Проверьте запросы в Prometheus:**
   ```powershell
   # В Prometheus UI выполните запросы:
   http_requests_total
   rate(http_requests_total[5m])
   ```

### Решения

#### Backend поды не работают

Если backend поды в статусе `CrashLoopBackOff`:

```powershell
# Проверьте логи
kubectl logs deployment/backend -n medaudit

# Перезапустите deployment
kubectl rollout restart deployment/backend -n medaudit

# Проверьте статус
kubectl get pods -n medaudit -l app=backend
```

#### Prometheus не собирает метрики

**Проблема:** Prometheus не может найти backend через service discovery из-за отсутствия RBAC прав.

**Решение:** Используйте static_configs вместо kubernetes_sd_configs:

```yaml
- job_name: 'backend'
  static_configs:
    - targets: ['backend-service:8000']
      labels:
        service: 'backend'
        namespace: 'medaudit'
  metrics_path: '/metrics'
  scrape_interval: 10s
```

После изменения конфигурации:
```powershell
kubectl apply -f k8s/monitoring/prometheus-config.yaml
kubectl delete pod -l app=prometheus -n medaudit
```

#### Метрики не генерируются

Запустите генератор нагрузки для создания метрик:

```powershell
# Terminal 1: Port-forward
kubectl port-forward svc/backend-service 8000:8000 -n medaudit

# Terminal 2: Генератор нагрузки
.\scripts\load-generator.ps1 -Duration 60 -RequestsPerSecond 10
```

#### Grafana не подключается к Prometheus

1. Проверьте datasource в Grafana:
   - Configuration → Data sources → Prometheus
   - URL должен быть: `http://prometheus-service:9090`
   - Нажмите "Save & Test"

2. Проверьте доступность Prometheus из Grafana:
   ```powershell
   kubectl exec deployment/grafana -n medaudit -- wget -qO- http://prometheus-service:9090/api/v1/status/config
   ```

### Проверка работоспособности

**Шаг 1: Проверьте метрики в Prometheus**

```powershell
kubectl port-forward svc/prometheus-service 9090:9090 -n medaudit
```

Откройте http://localhost:9090 и выполните запросы:
- `up{job="backend"}` - должен вернуть 1
- `http_requests_total` - должен показать метрики (если была нагрузка)

**Шаг 2: Проверьте datasource в Grafana**

```powershell
kubectl port-forward svc/grafana-service 3000:3000 -n medaudit
```

1. Войдите в Grafana (admin / MedAudit2024!Grafana)
2. Configuration → Data sources → Prometheus
3. Нажмите "Save & Test"
4. Должно показать "Data source is working"

**Шаг 3: Создайте тестовую панель**

1. Dashboards → New Dashboard → Add visualization
2. Выберите Prometheus как datasource
3. Запрос: `up{job="backend"}`
4. Должно показать значение 1 (если backend работает)

### Частые проблемы

#### "No data points"

- Убедитесь, что метрики существуют в Prometheus
- Проверьте временной диапазон (Last 6 hours)
- Убедитесь, что запрос PromQL синтаксически корректен

#### "Datasource not found"

- Проверьте, что Prometheus datasource настроен
- Перезапустите Grafana: `kubectl rollout restart deployment/grafana -n medaudit`

#### Метрики появляются с задержкой

- Prometheus собирает метрики каждые 15 секунд
- Grafana обновляет данные каждые 10-30 секунд
- Подождите 30-60 секунд после генерации нагрузки

### Полезные команды

```powershell
# Проверка метрик из backend
kubectl port-forward svc/backend-service 8000:8000 -n medaudit
curl http://localhost:8000/metrics | Select-String "http_requests"

# Проверка targets в Prometheus
kubectl exec deployment/prometheus -n medaudit -- wget -qO- http://localhost:9090/api/v1/targets | ConvertFrom-Json | Select-Object -ExpandProperty data | Select-Object -ExpandProperty activeTargets

# Перезапуск Prometheus
kubectl delete pod -l app=prometheus -n medaudit

# Перезапуск Grafana
kubectl delete pod -l app=grafana -n medaudit

# Проверка логов Prometheus
kubectl logs deployment/prometheus -n medaudit --tail=50
```





