# Тестирование развертывания Docker контейнеров

## Предварительные требования

1. **Docker Desktop** должен быть установлен и запущен
2. **Docker Compose** должен быть доступен
3. Минимум **4GB RAM** свободной памяти
4. Минимум **2GB** свободного места на диске

## Быстрое тестирование

### Автоматическое тестирование (рекомендуется)

#### Linux/Mac:
```bash
chmod +x scripts/test_docker_deployment.sh
./scripts/test_docker_deployment.sh
```

#### Windows PowerShell:
```powershell
.\scripts\test_docker_deployment.ps1
```

### Ручное тестирование

#### Шаг 1: Подготовка окружения

```bash
# Создайте .env файл (если его нет)
cp .env.example .env

# Или создайте вручную с минимальными настройками:
cat > .env << EOF
POSTGRES_USER=medaudit
POSTGRES_PASSWORD=medaudit_password
POSTGRES_DB=medaudit_db
SECRET_KEY=test-secret-key-change-in-production
DEBUG=True
LOG_LEVEL=INFO
BACKEND_URL=http://localhost:8000
NLP_SERVICE_URL=http://localhost:8080
EOF
```

#### Шаг 2: Остановка существующих контейнеров

```bash
docker-compose down -v
```

#### Шаг 3: Сборка образов

```bash
# Сборка всех образов
docker-compose build --no-cache

# Или только backend
docker-compose build --no-cache backend
```

**Ожидаемое время сборки**: 5-10 минут (первая сборка)

#### Шаг 4: Запуск контейнеров

```bash
docker-compose up -d
```

#### Шаг 5: Проверка статуса контейнеров

```bash
docker-compose ps
```

Ожидаемый вывод:
```
NAME                STATUS          PORTS
medaudit_backend    Up             0.0.0.0:8000->8000/tcp
medaudit_celery     Up             
medaudit_db         Up (healthy)   0.0.0.0:5432->5432/tcp
medaudit_redis      Up (healthy)   0.0.0.0:6379->6379/tcp
```

#### Шаг 6: Ожидание готовности сервисов

```bash
# Подождите 10-15 секунд для инициализации
sleep 15

# Проверьте логи backend
docker-compose logs backend | tail -20

# Проверьте логи Celery
docker-compose logs celery_worker | tail -20
```

#### Шаг 7: Применение миграций БД

```bash
docker-compose exec backend alembic upgrade head
```

Ожидаемый вывод:
```
INFO  [alembic.runtime.migration] Running upgrade -> <revision>, <description>
```

#### Шаг 8: Проверка health check

```bash
# Проверка health endpoint
curl http://localhost:8000/health

# Ожидаемый ответ:
# {"status":"ok"}
```

#### Шаг 9: Проверка API endpoints

```bash
# Корневой endpoint
curl http://localhost:8000/

# Swagger документация
curl http://localhost:8000/api/docs

# OpenAPI схема
curl http://localhost:8000/api/openapi.json
```

#### Шаг 10: Проверка подключений

```bash
# Проверка PostgreSQL
docker-compose exec db pg_isready -U medaudit

# Проверка Redis
docker-compose exec redis redis-cli ping
# Ожидаемый ответ: PONG
```

## Детальное тестирование

### Тест 1: Проверка сборки образа

```bash
# Сборка с выводом всех шагов
docker-compose build --progress=plain backend

# Проверка размера образа
docker images | grep medaudit
```

**Ожидаемый размер образа**: ~500-800 MB

### Тест 2: Проверка зависимостей

```bash
# Проверка установленных Python пакетов
docker-compose exec backend pip list

# Проверка системных библиотек для WeasyPrint
docker-compose exec backend dpkg -l | grep -E "libcairo|libpango|libgdk"
```

### Тест 3: Проверка переменных окружения

```bash
# Проверка переменных в backend
docker-compose exec backend env | grep -E "DATABASE_URL|REDIS_URL|SECRET_KEY"

# Проверка переменных в Celery
docker-compose exec celery_worker env | grep -E "DATABASE_URL|REDIS_URL"
```

### Тест 4: Проверка подключения к БД

```bash
# Подключение к PostgreSQL
docker-compose exec backend python -c "
import asyncio
from app.core.database import engine
async def test():
    async with engine.begin() as conn:
        result = await conn.execute('SELECT 1')
        print('Database connection: OK')
asyncio.run(test())
"
```

### Тест 5: Проверка подключения к Redis

```bash
# Тест Redis через Python
docker-compose exec backend python -c "
import asyncio
from app.core.redis import init_redis
async def test():
    redis = await init_redis()
    await redis.set('test', 'value')
    value = await redis.get('test')
    print(f'Redis connection: OK, value={value}')
asyncio.run(test())
"
```

### Тест 6: Проверка Celery

```bash
# Проверка статуса Celery worker
docker-compose exec celery_worker celery -A app.core.celery_app inspect active

# Проверка зарегистрированных задач
docker-compose exec celery_worker celery -A app.core.celery_app inspect registered
```

### Тест 7: Функциональное тестирование API

```bash
# Регистрация пользователя
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPassword123"}'

# Вход
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPassword123"}'

# Сохраните access_token из ответа для следующих запросов
TOKEN="your-access-token-here"

# Проверка информации о пользователе
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

## Проверка производительности

### Использование ресурсов

```bash
# Мониторинг использования ресурсов
docker stats --no-stream

# Ожидаемые значения:
# - CPU: < 5% в покое
# - Memory: ~200-500 MB на контейнер
```

### Время запуска

```bash
# Измерение времени запуска
time docker-compose up -d

# Ожидаемое время: < 30 секунд
```

## Устранение проблем

### Проблема: Контейнеры не запускаются

```bash
# Проверка логов
docker-compose logs

# Проверка конкретного сервиса
docker-compose logs backend
docker-compose logs db
docker-compose logs redis
```

### Проблема: Backend не может подключиться к БД

```bash
# Проверка доступности БД из backend
docker-compose exec backend ping db

# Проверка переменных окружения
docker-compose exec backend env | grep DATABASE_URL
```

### Проблема: Ошибки при сборке образа

```bash
# Очистка кеша Docker
docker system prune -a

# Пересборка без кеша
docker-compose build --no-cache --pull
```

### Проблема: Порт уже занят

```bash
# Проверка занятых портов
netstat -an | grep -E "8000|5432|6379"

# Изменение портов в docker-compose.yml
```

### Проблема: Ошибки миграций

```bash
# Проверка текущей версии миграций
docker-compose exec backend alembic current

# Откат последней миграции
docker-compose exec backend alembic downgrade -1

# Повторное применение
docker-compose exec backend alembic upgrade head
```

## Чек-лист успешного развертывания

- [ ] Все контейнеры запущены и имеют статус "Up"
- [ ] PostgreSQL доступен и готов (healthcheck passed)
- [ ] Redis доступен и отвечает на ping
- [ ] Backend отвечает на health check (200 OK)
- [ ] Миграции применены успешно
- [ ] Swagger документация доступна
- [ ] Celery worker запущен и готов
- [ ] API endpoints отвечают корректно
- [ ] Нет критических ошибок в логах
- [ ] Использование ресурсов в пределах нормы

## Очистка после тестирования

```bash
# Остановка и удаление контейнеров
docker-compose down

# Удаление с volumes (удалит данные БД!)
docker-compose down -v

# Удаление образов
docker-compose down --rmi all

# Полная очистка
docker-compose down -v --rmi all
```

## Дополнительные тесты

### Тест перезапуска контейнеров

```bash
# Перезапуск всех контейнеров
docker-compose restart

# Проверка, что все сервисы восстановились
docker-compose ps
```

### Тест устойчивости к сбоям

```bash
# Остановка одного контейнера
docker-compose stop db

# Проверка поведения других сервисов
docker-compose logs backend

# Восстановление
docker-compose start db
```

### Тест масштабирования

```bash
# Запуск нескольких экземпляров backend
docker-compose up -d --scale backend=3

# Проверка балансировки нагрузки (требует настройки nginx)
```

## Заключение

После успешного прохождения всех тестов система готова к развертыванию в production окружении.

Для production развертывания:
1. Обновите переменные окружения в `.env`
2. Используйте `docker-compose.prod.yml` (создайте на основе `docker-compose.yml`)
3. Настройте SSL сертификаты
4. Настройте мониторинг и логирование
5. Настройте резервное копирование БД





