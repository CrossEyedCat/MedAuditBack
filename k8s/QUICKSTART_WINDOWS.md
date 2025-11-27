# Быстрый запуск на Windows

## Предварительные требования

У вас уже установлены:
- ✅ Docker (версия 27.2.0)
- ✅ kubectl (версия 1.30.2)

## Шаг 1: Запуск Kubernetes кластера

У вас есть несколько вариантов:

### Вариант 1: Docker Desktop с Kubernetes (рекомендуется)

1. Откройте **Docker Desktop**
2. Перейдите в **Settings** → **Kubernetes**
3. Включите опцию **Enable Kubernetes**
4. Нажмите **Apply & Restart**
5. Дождитесь запуска кластера (иконка Kubernetes станет зеленой)

### Вариант 2: Minikube

Если Docker Desktop не поддерживает Kubernetes, установите Minikube:

```powershell
# Скачайте и установите Minikube
# https://minikube.sigs.k8s.io/docs/start/

# Запустите Minikube
minikube start

# Настройте kubectl для работы с Minikube
minikube kubectl -- get pods -A
```

### Вариант 3: Kind (Kubernetes in Docker)

```powershell
# Установите Kind
choco install kind
# или через Chocolatey: winget install kind

# Создайте кластер
kind create cluster --name medaudit

# Проверьте подключение
kubectl cluster-info --context kind-medaudit
```

## Шаг 2: Проверка кластера

После запуска кластера проверьте подключение:

```powershell
kubectl cluster-info
kubectl get nodes
```

Должен быть виден хотя бы один узел в состоянии `Ready`.

## Шаг 3: Установка Metrics Server (для HPA)

Metrics Server необходим для автоматического масштабирования:

```powershell
# Для Docker Desktop (если не установлен автоматически)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Для Minikube
minikube addons enable metrics-server

# Проверьте установку
kubectl get deployment metrics-server -n kube-system
```

## Шаг 4: Подготовка секретов

```powershell
# Скопируйте шаблон секретов
Copy-Item k8s\secrets.yaml.example k8s\secrets.yaml

# Откройте файл в редакторе
notepad k8s\secrets.yaml
```

Замените в файле `k8s/secrets.yaml`:
- `CHANGE_ME_STRONG_PASSWORD` → придумайте надежный пароль для PostgreSQL
- `CHANGE_ME_GENERATE_STRONG_SECRET_KEY` → сгенерируйте секретный ключ:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Шаг 5: Сборка Docker образа

```powershell
# Соберите production образ
docker build -f Dockerfile.prod -t medaudit-backend:latest .

# Если используете Minikube, загрузите образ в Minikube:
minikube image load medaudit-backend:latest
```

## Шаг 6: Настройка ConfigMap (опционально)

Отредактируйте `k8s/configmap.yaml` при необходимости:
- `NLP_SERVICE_URL` - URL вашего NLP сервиса
- `CORS_ORIGINS` - разрешенные источники для CORS

## Шаг 7: Развертывание

### Автоматическое развертывание (рекомендуется):

```powershell
.\k8s\deploy.ps1
```

### Ручное развертывание:

```powershell
# 1. Создайте namespace
kubectl apply -f k8s/namespace.yaml

# 2. Примените ConfigMap и Secrets
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml

# 3. Создайте PVC
kubectl apply -f k8s/storage-pvc.yaml

# 4. Разверните PostgreSQL и Redis
kubectl apply -f k8s/postgres-statefulset.yaml
kubectl apply -f k8s/redis-statefulset.yaml

# 5. Дождитесь готовности БД (это может занять 1-2 минуты)
kubectl wait --for=condition=ready pod -l app=postgres -n medaudit --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n medaudit --timeout=300s

# 6. Разверните Backend и Celery
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-hpa.yaml
kubectl apply -f k8s/celery-deployment.yaml
kubectl apply -f k8s/celery-hpa.yaml
```

## Шаг 8: Проверка развертывания

```powershell
# Проверьте статус подов
kubectl get pods -n medaudit

# Проверьте сервисы
kubectl get svc -n medaudit

# Проверьте HPA
kubectl get hpa -n medaudit

# Просмотрите логи Backend
kubectl logs -f deployment/backend -n medaudit

# Просмотрите логи Celery
kubectl logs -f deployment/celery-worker -n medaudit
```

## Шаг 9: Доступ к приложению

### Вариант 1: Port Forwarding (для локального тестирования)

```powershell
# Откройте порт для доступа к Backend
kubectl port-forward svc/backend-service 8000:8000 -n medaudit
```

Теперь приложение доступно по адресу: http://localhost:8000

### Вариант 2: Ingress (для production)

Если у вас установлен Ingress Controller (например, NGINX Ingress):

```powershell
# Отредактируйте k8s/ingress.yaml и замените домен
# Затем примените:
kubectl apply -f k8s/ingress.yaml
```

## Устранение проблем

### Проблема: "ImagePullBackOff" или "ErrImagePull"

Если образ не найден, убедитесь что:
1. Образ собран локально: `docker images | grep medaudit-backend`
2. Для Minikube: образ загружен в Minikube: `minikube image load medaudit-backend:latest`
3. Или используйте Docker Hub registry (загрузите образ туда)

### Проблема: "Pending" поды

Проверьте:
```powershell
kubectl describe pod <pod-name> -n medaudit
kubectl get events -n medaudit --sort-by='.lastTimestamp'
```

### Проблема: HPA не работает

Проверьте Metrics Server:
```powershell
kubectl get deployment metrics-server -n kube-system
kubectl top nodes
kubectl top pods -n medaudit
```

Если метрики не доступны, установите Metrics Server (см. Шаг 3).

### Проблема: StorageClass не найден

Для Docker Desktop обычно используется `hostpath` или `docker-desktop`:
```powershell
# Проверьте доступные StorageClass
kubectl get storageclass

# Если нужно, отредактируйте storage-pvc.yaml и замените storageClassName
```

## Удаление развертывания

```powershell
.\k8s\undeploy.ps1
```

Или вручную:
```powershell
kubectl delete namespace medaudit
```

## Полезные команды

```powershell
# Просмотр всех ресурсов в namespace
kubectl get all -n medaudit

# Просмотр логов конкретного пода
kubectl logs <pod-name> -n medaudit

# Подключение к поду (для отладки)
kubectl exec -it <pod-name> -n medaudit -- /bin/sh

# Масштабирование вручную
kubectl scale deployment backend -n medaudit --replicas=3

# Просмотр событий
kubectl get events -n medaudit --sort-by='.lastTimestamp'

# Описание ресурса
kubectl describe deployment backend -n medaudit
```

## Следующие шаги

1. Настройте мониторинг (Prometheus, Grafana)
2. Настройте логирование (ELK Stack, Loki)
3. Настройте CI/CD для автоматического развертывания
4. Настройте backup для PostgreSQL
5. Настройте SSL/TLS сертификаты для Ingress





