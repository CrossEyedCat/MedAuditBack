# Развертывание в Kubernetes

Этот документ описывает процесс развертывания MediAudit Backend в Kubernetes с поддержкой горизонтального масштабирования.

## Обзор архитектуры

Система развертывается в Kubernetes со следующими компонентами:

- **Backend API** (Deployment) - FastAPI приложение с автоматическим масштабированием (HPA)
- **Celery Worker** (Deployment) - Обработчик фоновых задач с автоматическим масштабированием (HPA)
- **PostgreSQL** (StatefulSet) - База данных
- **Redis** (StatefulSet) - Кеш и брокер сообщений
- **Ingress** - Маршрутизация внешнего трафика

## Предварительные требования

1. **Kubernetes кластер** версии 1.24 или выше
2. **kubectl** настроенный для работы с кластером
3. **Metrics Server** установлен в кластере (для HPA)
4. **Ingress Controller** (например, NGINX Ingress)
5. **StorageClass** для PersistentVolumes
6. **Docker образ** приложения, собранный и загруженный в registry

## Быстрый старт

### 1. Подготовка секретов

```bash
# Скопируйте шаблон секретов
cp k8s/secrets.yaml.example k8s/secrets.yaml

# Отредактируйте secrets.yaml и замените все CHANGE_ME_* значения
# Для генерации SECRET_KEY:
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Сборка Docker образа

```bash
# Соберите production образ
docker build -f Dockerfile.prod -t medaudit-backend:latest .

# Если используете registry, загрузите образ:
docker tag medaudit-backend:latest your-registry/medaudit-backend:latest
docker push your-registry/medaudit-backend:latest

# Обновите image в k8s/backend-deployment.yaml и k8s/celery-deployment.yaml
```

### 3. Настройка ConfigMap

Отредактируйте `k8s/configmap.yaml` и настройте:
- `NLP_SERVICE_URL` - URL вашего NLP сервиса
- `CORS_ORIGINS` - разрешенные источники для CORS
- Другие параметры по необходимости

### 4. Развертывание

#### Вариант 1: Использование скрипта (рекомендуется)

**Linux/Mac:**
```bash
chmod +x k8s/deploy.sh
./k8s/deploy.sh
```

**Windows (PowerShell):**
```powershell
.\k8s\deploy.ps1
```

#### Вариант 2: Ручное развертывание

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

# Примените Ingress (опционально)
kubectl apply -f k8s/ingress.yaml
```

#### Вариант 3: Использование Kustomize

```bash
kubectl apply -k k8s/
```

## Горизонтальное масштабирование

### Автоматическое масштабирование (HPA)

Система настроена на автоматическое горизонтальное масштабирование:

#### Backend HPA
- **Минимум реплик**: 2
- **Максимум реплик**: 10
- **Метрики масштабирования**:
  - CPU: 70% утилизация
  - Memory: 80% утилизация
- **Политика масштабирования вверх**: до 100% или +2 пода за 30 секунд
- **Политика масштабирования вниз**: до 50% за 60 секунд, окно стабилизации 5 минут

#### Celery Worker HPA
- **Минимум реплик**: 2
- **Максимум реплик**: 10
- **Метрики масштабирования**:
  - CPU: 70% утилизация
  - Memory: 80% утилизация
- **Политика масштабирования**: аналогична Backend

### Мониторинг масштабирования

```bash
# Просмотр текущего состояния HPA
kubectl get hpa -n medaudit

# Детальная информация о HPA
kubectl describe hpa backend-hpa -n medaudit
kubectl describe hpa celery-worker-hpa -n medaudit

# Просмотр метрик подов
kubectl top pods -n medaudit

# Просмотр событий масштабирования
kubectl get events -n medaudit --sort-by='.lastTimestamp' | grep -i hpa
```

### Ручное масштабирование

```bash
# Масштабирование Backend
kubectl scale deployment backend -n medaudit --replicas=5

# Масштабирование Celery Worker
kubectl scale deployment celery-worker -n medaudit --replicas=5
```

## Проверка развертывания

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

# Проверьте health check
kubectl port-forward svc/backend-service 8000:8000 -n medaudit
curl http://localhost:8000/health
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

# Просмотр истории обновлений
kubectl rollout history deployment/backend -n medaudit
```

## Миграции базы данных

Миграции выполняются автоматически через initContainer в `backend-deployment.yaml` при каждом запуске пода.

Для ручного запуска миграций:

```bash
# Создайте Job для миграций
kubectl run alembic-migration --image=medaudit-backend:latest \
  --restart=Never \
  --env="DATABASE_URL=postgresql+asyncpg://medaudit:password@postgres-service:5432/medaudit_db" \
  --command -- alembic upgrade head -n medaudit

# Проверьте логи
kubectl logs alembic-migration -n medaudit

# Удалите Job после завершения
kubectl delete job alembic-migration -n medaudit
```

## Устранение неполадок

### Проблемы с подключением к БД

```bash
# Проверьте статус PostgreSQL
kubectl get pods -l app=postgres -n medaudit
kubectl logs -l app=postgres -n medaudit

# Проверьте подключение из пода Backend
kubectl exec -it deployment/backend -n medaudit -- pg_isready -h postgres-service

# Проверьте секреты
kubectl get secret medaudit-secrets -n medaudit -o yaml
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
kubectl top nodes

# Проверьте логи Metrics Server
kubectl logs -n kube-system -l k8s-app=metrics-server
```

### Проблемы с хранилищем

```bash
# Проверьте PVC
kubectl get pvc -n medaudit
kubectl describe pvc file-storage-pvc -n medaudit

# Проверьте PV
kubectl get pv

# Проверьте StorageClass
kubectl get storageclass
```

### Проблемы с Ingress

```bash
# Проверьте Ingress
kubectl get ingress -n medaudit
kubectl describe ingress medaudit-ingress -n medaudit

# Проверьте Ingress Controller
kubectl get pods -n ingress-nginx
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller
```

## Удаление развертывания

### Использование скрипта

**Linux/Mac:**
```bash
chmod +x k8s/undeploy.sh
./k8s/undeploy.sh
```

**Windows (PowerShell):**
```powershell
.\k8s\undeploy.ps1
```

### Ручное удаление

```bash
# Удаление ресурсов
kubectl delete -f k8s/ingress.yaml
kubectl delete -f k8s/backend-hpa.yaml
kubectl delete -f k8s/celery-hpa.yaml
kubectl delete -f k8s/backend-deployment.yaml
kubectl delete -f k8s/celery-deployment.yaml
kubectl delete -f k8s/postgres-statefulset.yaml
kubectl delete -f k8s/redis-statefulset.yaml
kubectl delete -f k8s/storage-pvc.yaml
kubectl delete -f k8s/configmap.yaml
kubectl delete -f k8s/secrets.yaml
kubectl delete -f k8s/namespace.yaml
```

## Производительность и оптимизация

### Рекомендации по ресурсам

Текущие настройки ресурсов:

- **Backend Pod**: 
  - Requests: 512Mi RAM, 500m CPU
  - Limits: 2Gi RAM, 2000m CPU

- **Celery Worker Pod**:
  - Requests: 512Mi RAM, 500m CPU
  - Limits: 2Gi RAM, 2000m CPU
  - Concurrency: 4 воркера на под

- **PostgreSQL**:
  - Requests: 256Mi RAM, 250m CPU
  - Limits: 1Gi RAM, 1000m CPU
  - Storage: 20Gi

- **Redis**:
  - Requests: 128Mi RAM, 100m CPU
  - Limits: 512Mi RAM, 500m CPU
  - Storage: 5Gi

### Оптимизация

1. **Настройка количества workers**: Отредактируйте `Dockerfile.prod` и измените `--workers` в зависимости от CPU
2. **Настройка concurrency Celery**: Измените `--concurrency` в `celery-deployment.yaml`
3. **Настройка ресурсов**: Адаптируйте requests/limits в зависимости от реальной нагрузки
4. **Node Affinity**: Используйте Node Affinity для размещения подов на определенных нодах
5. **Pod Disruption Budget**: Создайте PDB для обеспечения доступности во время обновлений

### Пример Pod Disruption Budget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: backend-pdb
  namespace: medaudit
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: backend
```

## Безопасность

### Рекомендации

1. **Секреты**: Никогда не коммитьте `secrets.yaml` в git
2. **Network Policies**: Рассмотрите возможность добавления NetworkPolicies
3. **RBAC**: Настройте ServiceAccounts с минимальными необходимыми правами
4. **TLS**: Используйте TLS для всех внешних соединений
5. **Образы**: Используйте сканирование образов на уязвимости
6. **Secrets Management**: Используйте внешние системы управления секретами (Vault, Sealed Secrets)

### Пример NetworkPolicy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-netpol
  namespace: medaudit
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
```

## Мониторинг и логирование

Рекомендуется настроить:

1. **Prometheus** для сбора метрик
2. **Grafana** для визуализации
3. **ELK Stack** или **Loki** для централизованного логирования
4. **AlertManager** для уведомлений
5. **Jaeger** или **Zipkin** для трейсинга

## Дополнительные ресурсы

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Horizontal Pod Autoscaler](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)





