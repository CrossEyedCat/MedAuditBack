# Быстрый старт генератора нагрузки

## Простой запуск

### 1. Проверьте доступность API

```powershell
# Проверка health endpoint
Invoke-WebRequest -Uri "http://localhost:8000/health"
```

Если API недоступен, запустите port-forward:

```powershell
kubectl port-forward svc/backend-service 8000:8000 -n medaudit
```

### 2. Запустите генератор нагрузки

#### Вариант 1: С настройками по умолчанию
```powershell
.\scripts\load-generator.ps1
```
- Скорость: 100 запросов/сек
- Параллельно: 50 запросов
- Длительность: 60 секунд

#### Вариант 2: Высокая нагрузка (10x)
```powershell
.\scripts\load-generator.ps1 -Duration 120 -RequestsPerSecond 150 -Concurrent 80
```
- Скорость: 150 запросов/сек
- Параллельно: 80 запросов
- Длительность: 120 секунд

#### Вариант 3: Кастомные параметры
```powershell
.\scripts\load-generator.ps1 `
    -Url "http://localhost:8000" `
    -Duration 120 `
    -RequestsPerSecond 100 `
    -Concurrent 50
```

## Параметры

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `-Url` | URL API | `http://localhost:8000` |
| `-Duration` | Длительность в секундах | `60` |
| `-RequestsPerSecond` | Скорость запросов | `100` |
| `-Concurrent` | Параллельных запросов | `50` |

## Примеры использования

### Тестовая нагрузка (для разработки)
```powershell
.\scripts\load-generator.ps1 -Duration 30 -RequestsPerSecond 10 -Concurrent 5
```

### Средняя нагрузка
```powershell
.\scripts\load-generator.ps1 -Duration 60 -RequestsPerSecond 50 -Concurrent 25
```

### Высокая нагрузка (тест авт scaling)
```powershell
.\scripts\load-generator.ps1 -Duration 120 -RequestsPerSecond 150 -Concurrent 80
```

### Экстремальная нагрузка
```powershell
.\scripts\load-generator.ps1 -Duration 180 -RequestsPerSecond 200 -Concurrent 100
```

## Мониторинг

После запуска генератора проверьте метрики:

### Prometheus
```
http://localhost:9090
```
Запросы:
- `sum(rate(http_requests_total[1m]))` - текущая скорость
- `sum(http_requests_total)` - общее количество запросов

### Grafana
```
http://localhost:3000
```
Логин: `admin` / `MedAudit2024!Grafana`

Создайте панель с запросом:
```
rate(http_requests_total[5m])
```

## Остановка

Нажмите `Ctrl+C` в окне генератора для остановки.

## Troubleshooting

### Ошибка: "API is not available"
1. Проверьте, что port-forward запущен:
   ```powershell
   kubectl port-forward svc/backend-service 8000:8000 -n medaudit
   ```

2. Проверьте статус подов:
   ```powershell
   kubectl get pods -n medaudit -l app=backend
   ```

### Низкая скорость запросов
- Увеличьте параметр `-Concurrent`
- Проверьте производительность backend подов
- Проверьте метрики CPU/Memory в Grafana

### Метрики не появляются в Grafana
- Подождите 15-30 секунд (Prometheus скрейпит каждые 15 секунд)
- Проверьте, что Prometheus может достучаться до backend:
  ```
  http://localhost:9090/targets
  ```

