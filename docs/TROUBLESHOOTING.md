# Устранение проблем при развертывании

## Проблема: Порт 8000 уже занят

### Симптомы:
```
Error response from daemon: driver failed programming external connectivity on endpoint medaudit_backend: Bind for 0.0.0.0:8000 failed: port is already allocated
```

### Решения:

#### Вариант 1: Остановить контейнер, использующий порт

```bash
# Найти контейнер, использующий порт 8000
docker ps | findstr 8000

# Остановить контейнер (например, osjs)
docker stop osjs

# Или удалить контейнер
docker rm -f osjs
```

#### Вариант 2: Изменить порт в docker-compose.yml

Измените порт в `docker-compose.yml`:

```yaml
backend:
  ports:
    - "8001:8000"  # Внешний порт 8001, внутренний 8000
```

Затем используйте `http://localhost:8001` вместо `http://localhost:8000`

#### Вариант 3: Освободить порт вручную

```powershell
# Windows PowerShell
# Найти процесс, использующий порт 8000
netstat -ano | findstr :8000

# Остановить процесс (замените PID на реальный ID процесса)
taskkill /PID <PID> /F
```

## Проблема: Конфликт версий зависимостей

### Симптомы:
```
ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/latest/topics/dependency-resolution/
celery[redis] 5.3.4 depends on redis!=4.5.5, <5.0.0 and >=4.5.2
```

### Решение:

Убедитесь, что в `requirements.txt` указаны совместимые версии:

```txt
redis==4.6.0
celery==5.3.4
# Не используйте celery[redis] отдельно, если redis уже указан
```

## Проблема: База данных не создается

### Симптомы:
```
FATAL: database "medaudit" does not exist
```

### Решение:

Проверьте переменные окружения в `.env`:

```env
POSTGRES_DB=medaudit_db
POSTGRES_USER=medaudit
POSTGRES_PASSWORD=medaudit_password
```

Убедитесь, что `DATABASE_URL` в docker-compose.yml использует правильное имя БД:

```yaml
DATABASE_URL=postgresql+asyncpg://medaudit:medaudit_password@db:5432/medaudit_db
```

## Проблема: Контейнеры не запускаются

### Симптомы:
Контейнеры имеют статус "Created" но не "Up"

### Решение:

1. Проверьте логи:
```bash
docker-compose logs backend
docker-compose logs celery_worker
```

2. Проверьте зависимости:
```bash
docker-compose ps
```

3. Перезапустите контейнеры:
```bash
docker-compose restart
```

## Проблема: Миграции не применяются

### Симптомы:
```
ERROR: Can't locate revision identified by 'xxxxx'
```

### Решение:

1. Проверьте текущую версию миграций:
```bash
docker-compose exec backend alembic current
```

2. Примените миграции с нуля:
```bash
docker-compose exec backend alembic upgrade head
```

3. Если проблема сохраняется, пересоздайте БД:
```bash
docker-compose down -v
docker-compose up -d db
# Подождите пока БД запустится
docker-compose exec backend alembic upgrade head
```

## Проблема: Redis не подключается

### Симптомы:
```
Error connecting to Redis
```

### Решение:

1. Проверьте, что Redis запущен:
```bash
docker-compose ps redis
```

2. Проверьте подключение:
```bash
docker-compose exec redis redis-cli ping
# Должно вернуть: PONG
```

3. Проверьте переменную окружения:
```bash
docker-compose exec backend env | grep REDIS_URL
```

## Проблема: Celery worker не запускается

### Симптомы:
Celery worker не появляется в списке активных workers

### Решение:

1. Проверьте логи:
```bash
docker-compose logs celery_worker
```

2. Проверьте подключение к Redis:
```bash
docker-compose exec celery_worker python -c "from app.core.redis import init_redis; import asyncio; asyncio.run(init_redis())"
```

3. Перезапустите worker:
```bash
docker-compose restart celery_worker
```

## Проблема: Ошибки при сборке образа

### Симптомы:
```
ERROR: process "/bin/sh -c pip install --no-cache-dir -r requirements.txt" did not complete successfully
```

### Решение:

1. Очистите кеш Docker:
```bash
docker system prune -a
```

2. Пересоберите без кеша:
```bash
docker-compose build --no-cache
```

3. Проверьте системные зависимости в Dockerfile

## Проблема: Файлы не сохраняются

### Симптомы:
Загруженные файлы исчезают после перезапуска контейнера

### Решение:

Убедитесь, что volume `file_storage` настроен в docker-compose.yml:

```yaml
volumes:
  file_storage:
```

И подключен к контейнеру:

```yaml
backend:
  volumes:
    - file_storage:/app/storage
```

## Проблема: Медленная работа

### Решение:

1. Увеличьте ресурсы Docker Desktop
2. Используйте production конфигурацию без `--reload`
3. Оптимизируйте запросы к БД
4. Используйте кеширование

## Получение помощи

Если проблема не решена:

1. Соберите информацию:
```bash
docker-compose logs > logs.txt
docker-compose ps -a > containers.txt
```

2. Проверьте версии:
```bash
docker --version
docker-compose --version
```

3. Создайте issue с описанием проблемы и собранной информацией


