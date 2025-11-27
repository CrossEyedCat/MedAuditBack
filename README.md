# MediAudit Backend

Система для автоматического аудита медицинской документации с использованием NLP.

## Технологический стек

- **Python 3.11+**
- **FastAPI** - современный веб-фреймворк
- **PostgreSQL 15** - база данных
- **Redis** - кеширование и брокер сообщений
- **Celery** - асинхронные задачи
- **Docker & Docker Compose** - контейнеризация

## Установка и запуск

### Предварительные требования

- Docker и Docker Compose (для локальной разработки)
- Kubernetes (для production развертывания)
- Python 3.11+ (для локальной разработки)

### Быстрый старт с Docker (локальная разработка)

1. Клонируйте репозиторий
2. Скопируйте `.env.example` в `.env` и настройте переменные окружения:
   ```bash
   cp .env.example .env
   ```
3. Запустите контейнеры:
   ```bash
   docker-compose up -d
   ```
4. Примените миграции:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```
5. API будет доступно по адресу: http://localhost:8000
6. Документация API: http://localhost:8000/api/docs

### Развертывание в Kubernetes (Production)

**Автоматическое развертывание (рекомендуется):**

```powershell
# Windows
.\k8s\deploy-all.ps1
```

**Ручное развертывание:**

См. подробное руководство: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

**Быстрая проверка:**

```powershell
# Проверьте статус
kubectl get pods -n medaudit

# Откройте API
kubectl port-forward svc/backend-service 8000:8000 -n medaudit
```

### Локальная разработка

1. Создайте виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

3. Запустите PostgreSQL и Redis через Docker:
   ```bash
   docker-compose up -d db redis
   ```

4. Настройте переменные окружения в `.env`

5. Примените миграции:
   ```bash
   alembic upgrade head
   ```

6. Запустите сервер разработки:
   ```bash
   uvicorn app.main:app --reload
   ```

## Структура проекта

```
MedAuditBack/
├── app/
│   ├── api/              # API endpoints
│   │   └── v1/
│   ├── core/             # Основные настройки
│   │   ├── config.py     # Конфигурация
│   │   ├── database.py   # Подключение к БД
│   │   ├── redis.py      # Подключение к Redis
│   │   └── logging.py    # Логирование
│   ├── models/           # Модели БД
│   ├── schemas/          # Pydantic схемы
│   ├── services/         # Бизнес-логика
│   ├── utils/            # Утилиты
│   └── main.py           # Точка входа
├── alembic/              # Миграции БД
├── storage/              # Хранилище файлов
├── docker-compose.yml    # Docker конфигурация
├── Dockerfile            # Образ приложения
├── requirements.txt      # Зависимости Python
└── README.md
```

## Миграции базы данных

Создать новую миграцию:
```bash
alembic revision --autogenerate -m "описание изменений"
```

Применить миграции:
```bash
alembic upgrade head
```

Откатить последнюю миграцию:
```bash
alembic downgrade -1
```

## Тестирование

Запуск тестов:
```bash
pytest
```

С покрытием кода:
```bash
pytest --cov=app --cov-report=html --cov-report=term
```

Проверка покрытия (минимум 80%):
```bash
pytest --cov=app --cov-report=term-missing
```

Подробнее см. [docs/TESTING.md](docs/TESTING.md)

## Переменные окружения

Основные переменные окружения описаны в `.env.example`. Обязательно настройте:
- `DATABASE_URL` - подключение к PostgreSQL
- `REDIS_URL` - подключение к Redis
- `SECRET_KEY` - секретный ключ для JWT (сгенерируйте новый для production)

## Развертывание в Kubernetes

Для production развертывания с поддержкой горизонтального масштабирования используйте Kubernetes.

### Быстрый старт на Windows

**Автоматическая проверка и развертывание:**
```powershell
.\k8s\check-and-deploy.ps1
```

Скрипт автоматически:
- Проверит наличие Docker и kubectl
- Проверит доступность Kubernetes кластера
- Установит Metrics Server (если нужно)
- Создаст файл секретов из шаблона
- Соберет Docker образ (если нужно)
- Развернет приложение

**Ручное развертывание:**

1. Убедитесь, что Kubernetes кластер запущен:
   - Docker Desktop: Settings → Kubernetes → Enable Kubernetes
   - Или используйте Minikube/Kind

2. Подготовьте секреты:
   ```powershell
   Copy-Item k8s\secrets.yaml.example k8s\secrets.yaml
   # Отредактируйте k8s/secrets.yaml
   ```

3. Соберите Docker образ:
   ```powershell
   docker build -f Dockerfile.prod -t medaudit-backend:latest .
   ```

4. Разверните:
   ```powershell
   .\k8s\deploy.ps1
   ```

**Документация:**
- [Быстрый старт на Windows](k8s/QUICKSTART_WINDOWS.md)
- [Полная документация Kubernetes](docs/KUBERNETES_DEPLOYMENT.md)

### Особенности Kubernetes развертывания

- ✅ Автоматическое горизонтальное масштабирование (HPA)
- ✅ Минимум 2 реплики Backend и Celery Worker
- ✅ Масштабирование до 10 реплик на основе CPU/Memory
- ✅ Автоматические health checks и readiness probes
- ✅ Автоматическое выполнение миграций БД
- ✅ Persistent storage для файлов и данных

## Документация

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- OpenAPI JSON: http://localhost:8000/api/openapi.json
- [Kubernetes Deployment](docs/KUBERNETES_DEPLOYMENT.md)

## Лицензия

Проект разработан для MediAudit.

