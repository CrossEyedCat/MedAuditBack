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

- Docker и Docker Compose
- Python 3.11+ (для локальной разработки)

### Быстрый старт с Docker

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

## Документация

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- OpenAPI JSON: http://localhost:8000/api/openapi.json

## Лицензия

Проект разработан для MediAudit.

