# Быстрый старт MediAudit Backend

## Первый запуск проекта

### 1. Настройка переменных окружения

Скопируйте файл `.env.example` в `.env`:

```bash
cp .env.example .env
```

Или создайте файл `.env` вручную и заполните необходимые переменные (см. `.env.example`).

**Важно**: Для production обязательно измените `SECRET_KEY` на безопасный случайный ключ:
```bash
# Генерация секретного ключа (Linux/Mac)
openssl rand -hex 32

# Или используйте Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Запуск через Docker Compose (рекомендуется)

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f backend

# Остановка сервисов
docker-compose down
```

### 3. Применение миграций базы данных

После первого запуска контейнеров необходимо применить миграции:

```bash
# Через Docker
docker-compose exec backend alembic upgrade head

# Или локально (если БД запущена локально)
alembic upgrade head
```

### 4. Создание начальной миграции (если нужно)

Если вы изменили модели и нужно создать новую миграцию:

```bash
# Через Docker
docker-compose exec backend alembic revision --autogenerate -m "описание изменений"

# Или локально
alembic revision --autogenerate -m "описание изменений"
```

Затем примените миграцию:
```bash
alembic upgrade head
```

### 5. Проверка работы API

После запуска проверьте:

1. **Health check**: http://localhost:8000/health
2. **Корневой endpoint**: http://localhost:8000/
3. **Документация Swagger**: http://localhost:8000/api/docs
4. **Документация ReDoc**: http://localhost:8000/api/redoc

### 6. Локальная разработка (без Docker)

Если вы хотите запускать приложение локально:

1. **Установите зависимости**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Запустите PostgreSQL и Redis через Docker**:
   ```bash
   docker-compose up -d db redis
   ```

3. **Настройте `.env`** с правильными URL для локального подключения:
   ```
   DATABASE_URL=postgresql+asyncpg://medaudit:medaudit_password@localhost:5432/medaudit_db
   REDIS_URL=redis://localhost:6379/0
   ```

4. **Примените миграции**:
   ```bash
   alembic upgrade head
   ```

5. **Запустите сервер разработки**:
   ```bash
   uvicorn app.main:app --reload
   ```

## Структура базы данных

После применения миграций будут созданы следующие таблицы:

- `users` - пользователи системы
- `documents` - загруженные документы
- `audit_reports` - отчеты об аудите
- `violations` - выявленные нарушения
- `analysis_summaries` - сводки анализа

## Полезные команды

### Docker Compose

```bash
# Перезапуск сервисов
docker-compose restart

# Просмотр статуса
docker-compose ps

# Остановка и удаление контейнеров (с данными)
docker-compose down -v

# Пересборка образа
docker-compose build --no-cache backend
```

### Alembic (миграции)

```bash
# Просмотр текущей версии
alembic current

# Просмотр истории миграций
alembic history

# Откат на одну версию назад
alembic downgrade -1

# Откат всех миграций
alembic downgrade base
```

### Тестирование

```bash
# Запуск тестов
pytest

# С покрытием кода
pytest --cov=app --cov-report=html

# Конкретный тест
pytest tests/test_auth.py
```

## Решение проблем

### Проблема: Не удается подключиться к БД

1. Проверьте, что PostgreSQL запущен:
   ```bash
   docker-compose ps db
   ```

2. Проверьте переменные окружения в `.env`

3. Проверьте логи:
   ```bash
   docker-compose logs db
   ```

### Проблема: Ошибки миграций

1. Убедитесь, что БД создана и доступна

2. Проверьте текущую версию:
   ```bash
   alembic current
   ```

3. Если нужно начать заново (осторожно, удалит данные!):
   ```bash
   alembic downgrade base
   alembic upgrade head
   ```

### Проблема: Порт уже занят

Измените порты в `docker-compose.yml` или остановите процесс, использующий порт.

## Следующие шаги

После успешного запуска можно переходить к:

1. Реализации системы аутентификации (Задача 1.2)
2. Созданию API для загрузки документов (Задача 2.1)
3. Интеграции с NLP-сервисом (Задача 2.2)

См. `CHECKLIST.md` для детального плана разработки.


