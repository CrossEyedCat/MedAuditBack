# Руководство по развертыванию MediAudit Backend

Полное руководство по развертыванию системы MediAudit Backend в Kubernetes.

## Предварительные требования

### 1. Установка Docker Desktop

1. Скачайте Docker Desktop: https://www.docker.com/products/docker-desktop
2. Установите и запустите Docker Desktop
3. Включите Kubernetes:
   - Откройте Settings → Kubernetes
   - Установите галочку "Enable Kubernetes"
   - Нажмите "Apply & Restart"

### 2. Установка kubectl

**Windows (PowerShell):**
```powershell
# Скачайте kubectl.exe и добавьте в PATH
# Или используйте Chocolatey:
choco install kubernetes-cli
```

**Проверка установки:**
```powershell
kubectl version --client
```

## Быстрое развертывание (автоматическое)

### Windows

```powershell
# Перейдите в директорию проекта
cd C:\Users\Admin\WebstormProjects\MedAuditBack

# Запустите скрипт автоматического развертывания
.\k8s\deploy-all.ps1
```

Скрипт автоматически:
- ✅ Проверит окружение (Docker, kubectl, Kubernetes)
- ✅ Соберет Docker образ
- ✅ Создаст namespace
- ✅ Применит секреты и конфигурацию
- ✅ Развернет все компоненты
- ✅ Выполнит миграции БД
- ✅ Опционально развернет мониторинг

## Ручное развертывание (пошаговое)

### Шаг 1: Подготовка секретов

```powershell
# Скопируйте пример секретов
Copy-Item k8s\secrets.yaml.example k8s\secrets.yaml

# Отредактируйте секреты (установите пароли)
notepad k8s\secrets.yaml
```

**Важно:** Установите надежные пароли для:
- `POSTGRES_PASSWORD` - пароль PostgreSQL
- `SECRET_KEY` - секретный ключ для JWT (сгенерируйте случайную строку)

### Шаг 2: Сборка Docker образа

```powershell
docker build -f Dockerfile.prod -t medaudit-backend:latest .
```

### Шаг 3: Создание namespace

```powershell
kubectl apply -f k8s\namespace.yaml
```

### Шаг 4: Применение секретов и конфигурации

```powershell
kubectl apply -f k8s\secrets.yaml
kubectl apply -f k8s\configmap.yaml
```

### Шаг 5: Развертывание хранилища

```powershell
kubectl apply -f k8s\storage-pvc.yaml
```

### Шаг 6: Развертывание PostgreSQL

```powershell
kubectl apply -f k8s\postgres-statefulset.yaml

# Дождитесь готовности PostgreSQL
kubectl wait --for=condition=ready pod -l app=postgres -n medaudit --timeout=300s
```

### Шаг 7: Развертывание Redis

```powershell
kubectl apply -f k8s\redis-statefulset.yaml

# Дождитесь готовности Redis
kubectl wait --for=condition=ready pod -l app=redis -n medaudit --timeout=300s
```

### Шаг 8: Развертывание Backend и Celery

```powershell
kubectl apply -f k8s\backend-deployment.yaml
kubectl apply -f k8s\celery-deployment.yaml
kubectl apply -f k8s\backend-hpa.yaml
kubectl apply -f k8s\celery-hpa.yaml

# Дождитесь готовности подов
kubectl wait --for=condition=ready pod -l app=backend -n medaudit --timeout=300s
kubectl wait --for=condition=ready pod -l app=celery-worker -n medaudit --timeout=300s
```

### Шаг 9: Выполнение миграций БД

```powershell
# Получите имя пода Backend
$backendPod = kubectl get pods -n medaudit -l app=backend -o jsonpath='{.items[0].metadata.name}'

# Выполните миграции
kubectl exec $backendPod -n medaudit -- alembic upgrade head
```

### Шаг 10: Проверка развертывания

```powershell
# Проверьте статус всех подов
kubectl get pods -n medaudit

# Проверьте логи Backend
kubectl logs -f deployment/backend -n medaudit

# Проверьте health check
kubectl port-forward svc/backend-service 8000:8000 -n medaudit
# В другом терминале:
curl http://localhost:8000/health
```

## Развертывание мониторинга (опционально)

### Подготовка секретов Grafana

```powershell
Copy-Item k8s\monitoring\grafana-secrets.yaml.example k8s\monitoring\grafana-secrets.yaml
notepad k8s\monitoring\grafana-secrets.yaml
```

### Развертывание мониторинга

```powershell
# Используйте скрипт
.\k8s\monitoring\deploy-monitoring.ps1

# Или вручную:
kubectl apply -f k8s\monitoring\
```

## Доступ к приложению

### Backend API

```powershell
kubectl port-forward svc/backend-service 8000:8000 -n medaudit
```

Откройте в браузере:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

### Grafana (если развернут)

```powershell
kubectl port-forward svc/grafana-service 3000:3000 -n medaudit
```

Откройте: http://localhost:3000
- Username: `admin`
- Password: (из `grafana-secrets.yaml`)

### Prometheus (если развернут)

```powershell
kubectl port-forward svc/prometheus-service 9090:9090 -n medaudit
```

Откройте: http://localhost:9090

## Полезные команды

### Просмотр статуса

```powershell
# Все ресурсы
kubectl get all -n medaudit

# Только поды
kubectl get pods -n medaudit

# Детальная информация о поде
kubectl describe pod <pod-name> -n medaudit
```

### Просмотр логов

```powershell
# Логи Backend
kubectl logs -f deployment/backend -n medaudit

# Логи Celery
kubectl logs -f deployment/celery-worker -n medaudit

# Логи конкретного пода
kubectl logs <pod-name> -n medaudit
```

### Масштабирование

```powershell
# Масштабирование Backend вручную
kubectl scale deployment backend -n medaudit --replicas=5

# HPA автоматически масштабирует на основе CPU/Memory
kubectl get hpa -n medaudit
```

### Перезапуск компонентов

```powershell
# Перезапуск Backend
kubectl rollout restart deployment/backend -n medaudit

# Перезапуск Celery
kubectl rollout restart deployment/celery-worker -n medaudit
```

### Обновление образа

```powershell
# Пересоберите образ
docker build -f Dockerfile.prod -t medaudit-backend:latest .

# Удалите deployment для пересоздания с новым образом
kubectl delete deployment backend -n medaudit
kubectl apply -f k8s\backend-deployment.yaml
```

## Устранение неполадок

### Поды не запускаются

```powershell
# Проверьте события
kubectl get events -n medaudit --sort-by='.lastTimestamp'

# Проверьте описание пода
kubectl describe pod <pod-name> -n medaudit
```

### Проблемы с подключением к БД

```powershell
# Проверьте статус PostgreSQL
kubectl get pod postgres-0 -n medaudit

# Проверьте логи PostgreSQL
kubectl logs postgres-0 -n medaudit

# Проверьте подключение из Backend пода
kubectl exec deployment/backend -n medaudit -- pg_isready -h postgres-service -U medaudit
```

### Проблемы с хранилищем

```powershell
# Проверьте PVC
kubectl get pvc -n medaudit

# Проверьте StorageClass
kubectl get storageclass
```

### Очистка и переразвертывание

```powershell
# Удалите все ресурсы
kubectl delete namespace medaudit

# Или используйте скрипт
.\k8s\undeploy.ps1

# Затем разверните заново
.\k8s\deploy-all.ps1
```

## Архитектура развертывания

```
┌─────────────────────────────────────────────────┐
│              Kubernetes Cluster                 │
│                                                 │
│  ┌──────────────┐  ┌──────────────┐           │
│  │   Backend    │  │    Celery    │           │
│  │  (2-10 pods) │  │  (2-10 pods) │           │
│  └──────┬───────┘  └──────┬───────┘           │
│         │                  │                    │
│         └──────────┬───────┘                    │
│                    │                            │
│  ┌─────────────────┴─────────────────┐       │
│  │  PostgreSQL  │  Redis  │  Storage  │       │
│  └─────────────────────────────────────┘       │
│                                                 │
│  ┌──────────────┐  ┌──────────────┐           │
│  │  Prometheus  │  │   Grafana    │           │
│  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────┘
```

## Производительность

- **Минимум реплик**: 2 для Backend и Celery
- **Максимум реплик**: 10 (настраивается в HPA)
- **Автомасштабирование**: на основе CPU (70%) и Memory (80%)
- **Хранилище**: 50GB для файлов, 20GB для PostgreSQL, 5GB для Redis

## Безопасность

- ✅ Секреты хранятся в Kubernetes Secrets
- ✅ Пароли не попадают в Git (`.gitignore`)
- ✅ HTTPS через Ingress (настройте сертификаты)
- ✅ Rate limiting включен в production
- ✅ CORS настроен для разрешенных источников

## Дополнительная документация

- [Kubernetes Deployment](docs/KUBERNETES_DEPLOYMENT.md)
- [Monitoring Guide](docs/MONITORING.md)
- [Quickstart Windows](k8s/QUICKSTART_WINDOWS.md)

## Поддержка

При возникновении проблем:
1. Проверьте логи: `kubectl logs -f deployment/backend -n medaudit`
2. Проверьте события: `kubectl get events -n medaudit`
3. Проверьте документацию в `docs/`





