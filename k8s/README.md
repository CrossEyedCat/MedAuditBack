# Kubernetes Deployment для MediAudit Backend

Этот каталог содержит все необходимые манифесты Kubernetes для развертывания MediAudit Backend с поддержкой горизонтального масштабирования.

## Структура файлов

```
k8s/
├── namespace.yaml              # Namespace для приложения
├── configmap.yaml              # Конфигурация приложения
├── secrets.yaml.example         # Шаблон секретов (скопируйте в secrets.yaml)
├── secrets.yaml                 # Секреты (НЕ коммитьте в git!)
├── storage-pvc.yaml            # PersistentVolumeClaim для файлов
├── postgres-statefulset.yaml   # PostgreSQL StatefulSet и Service
├── redis-statefulset.yaml      # Redis StatefulSet и Service
├── backend-deployment.yaml     # Backend Deployment и Service
├── backend-hpa.yaml            # HorizontalPodAutoscaler для Backend
├── celery-deployment.yaml      # Celery Worker Deployment
├── celery-hpa.yaml              # HorizontalPodAutoscaler для Celery
├── ingress.yaml                # Ingress для маршрутизации
├── kustomization.yaml          # Kustomize конфигурация
└── README.md                   # Эта документация
```

## Предварительные требования

1. **Kubernetes кластер** (версия 1.24+)
2. **kubectl** настроенный для работы с кластером
3. **Docker образ** приложения, собранный и загруженный в registry
4. **Metrics Server** установлен в кластере (для HPA)
5. **Ingress Controller** (например, NGINX Ingress)
6. **StorageClass** для PersistentVolumes (например, `standard`)

## Быстрый старт

### 1. Подготовка секретов

```bash
# Скопируйте шаблон секретов
cp k8s/secrets.yaml.example k8s/secrets.yaml

# Отредактируйте secrets.yaml и замените все CHANGE_ME_* значения
# Для генерации SECRET_KEY:
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Примените секреты
kubectl apply -f k8s/secrets.yaml
```

### 2. Сборка Docker образа

```bash
# Соберите production образ
docker build -f Dockerfile.prod -t medaudit-backend:latest .

# Если используете registry, загрузите образ:
docker tag medaudit-backend:latest your-registry/medaudit-backend:latest
docker push your-registry/medaudit-backend:latest

# Обновите image в backend-deployment.yaml и celery-deployment.yaml
```

### 3. Настройка ConfigMap

Отредактируйте `k8s/configmap.yaml` и настройте:
- `NLP_SERVICE_URL` - URL вашего NLP сервиса
- `CORS_ORIGINS` - разрешенные источники для CORS
- Другие параметры по необходимости

### 4. Настройка Ingress

Отредактируйте `k8s/ingress.yaml`:
- Замените `api.medaudit.example.com` на ваш домен
- Настройте TLS сертификаты (или используйте cert-manager)

### 5. Развертывание

#### Вариант 1: Использование kubectl

```bash
# Создайте namespace
kubectl apply -f k8s/namespace.yaml

# Примените все манифесты по порядку
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/storage-pvc.yaml
kubectl apply -f k8s/postgres-statefulset.yaml
kubectl apply -f k8s/redis-statefulset.yaml

# Дождитесь готовности PostgreSQL и Redis
kubectl wait --for=condition=ready pod -l app=postgres -n medaudit --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n medaudit --timeout=300s

# Разверните Backend и Celery
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-hpa.yaml
kubectl apply -f k8s/celery-deployment.yaml
kubectl apply -f k8s/celery-hpa.yaml

# Примените Ingress
kubectl apply -f k8s/ingress.yaml
```

#### Вариант 2: Использование Kustomize

```bash
kubectl apply -k k8s/
```

### 6. Проверка развертывания

```bash
# Проверьте статус подов
kubectl get pods -n medaudit

# Проверьте сервисы
kubectl get svc -n medaudit

# Проверьте HPA
kubectl get hpa -n medaudit

# Проверьте логи Backend
kubectl logs -f deployment/backend -n medaudit

# Проверьте логи Celery
kubectl logs -f deployment/celery-worker -n medaudit
```

## Горизонтальное масштабирование

### Автоматическое масштабирование (HPA)

Система настроена на автоматическое горизонтальное масштабирование:

- **Backend HPA**: 
  - Минимум: 2 реплики
  - Максимум: 10 реплик
  - Масштабирование по CPU (70%) и Memory (80%)

- **Celery Worker HPA**:
  - Минимум: 2 реплики
  - Максимум: 10 реплик
  - Масштабирование по CPU (70%) и Memory (80%)

### Ручное масштабирование

```bash
# Масштабирование Backend
kubectl scale deployment backend -n medaudit --replicas=5

# Масштабирование Celery Worker
kubectl scale deployment celery-worker -n medaudit --replicas=5
```

### Мониторинг масштабирования

```bash
# Просмотр текущего состояния HPA
kubectl describe hpa backend-hpa -n medaudit
kubectl describe hpa celery-worker-hpa -n medaudit

# Просмотр метрик
kubectl top pods -n medaudit
kubectl top nodes
```

## Обновление приложения

### Rolling Update

```bash
# Обновите образ в deployment
kubectl set image deployment/backend backend=medaudit-backend:v1.1.0 -n medaudit
kubectl set image deployment/celery-worker celery-worker=medaudit-backend:v1.1.0 -n medaudit

# Проверьте статус обновления
kubectl rollout status deployment/backend -n medaudit
kubectl rollout status deployment/celery-worker -n medaudit

# Откат при необходимости
kubectl rollout undo deployment/backend -n medaudit
kubectl rollout undo deployment/celery-worker -n medaudit
```

## Миграции базы данных

Миграции выполняются автоматически через initContainer в `backend-deployment.yaml`. 

Для ручного запуска миграций:

```bash
# Создайте Job для миграций
kubectl run alembic-migration --image=medaudit-backend:latest \
  --restart=Never \
  --env="DATABASE_URL=postgresql+asyncpg://medaudit:password@postgres-service:5432/medaudit_db" \
  --command -- alembic upgrade head -n medaudit

# Проверьте логи
kubectl logs alembic-migration -n medaudit
```

## Устранение неполадок

### Проблемы с подключением к БД

```bash
# Проверьте статус PostgreSQL
kubectl get pods -l app=postgres -n medaudit
kubectl logs -l app=postgres -n medaudit

# Проверьте подключение из пода Backend
kubectl exec -it deployment/backend -n medaudit -- pg_isready -h postgres-service
```

### Проблемы с Redis

```bash
# Проверьте статус Redis
kubectl get pods -l app=redis -n medaudit
kubectl logs -l app=redis -n medaudit

# Проверьте подключение
kubectl exec -it deployment/backend -n medaudit -- redis-cli -h redis-service ping
```

### Проблемы с масштабированием

```bash
# Проверьте Metrics Server
kubectl get deployment metrics-server -n kube-system

# Проверьте события HPA
kubectl describe hpa backend-hpa -n medaudit

# Проверьте метрики
kubectl top pods -n medaudit
```

### Проблемы с хранилищем

```bash
# Проверьте PVC
kubectl get pvc -n medaudit
kubectl describe pvc file-storage-pvc -n medaudit

# Проверьте PV
kubectl get pv
```

## Производительность

### Рекомендации по ресурсам

- **Backend Pod**: 
  - Requests: 512Mi RAM, 500m CPU
  - Limits: 2Gi RAM, 2000m CPU

- **Celery Worker Pod**:
  - Requests: 512Mi RAM, 500m CPU
  - Limits: 2Gi RAM, 2000m CPU

- **PostgreSQL**:
  - Requests: 256Mi RAM, 250m CPU
  - Limits: 1Gi RAM, 1000m CPU
  - Storage: 20Gi

- **Redis**:
  - Requests: 128Mi RAM, 100m CPU
  - Limits: 512Mi RAM, 500m CPU
  - Storage: 5Gi

### Оптимизация

1. Настройте `--workers` в CMD Dockerfile.prod в зависимости от CPU
2. Настройте `--concurrency` для Celery в зависимости от нагрузки
3. Настройте ресурсы в зависимости от реальной нагрузки
4. Используйте Node Affinity для размещения подов на определенных нодах

## Безопасность

1. **Секреты**: Никогда не коммитьте `secrets.yaml` в git
2. **Network Policies**: Рассмотрите возможность добавления NetworkPolicies для ограничения трафика
3. **RBAC**: Настройте ServiceAccounts с минимальными необходимыми правами
4. **TLS**: Используйте TLS для всех внешних соединений
5. **Образы**: Используйте сканирование образов на уязвимости

## Мониторинг и логирование

Рекомендуется настроить:

1. **Prometheus** для метрик
2. **Grafana** для визуализации
3. **ELK Stack** или **Loki** для централизованного логирования
4. **AlertManager** для уведомлений

## Дополнительные ресурсы

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Horizontal Pod Autoscaler](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)



