# Быстрое тестирование Docker развертывания

## Быстрый старт

1. **Убедитесь, что Docker Desktop запущен**

2. **Создайте .env файл** (если его нет):
```bash
# Windows PowerShell
@"
POSTGRES_USER=medaudit
POSTGRES_PASSWORD=medaudit_password
POSTGRES_DB=medaudit_db
SECRET_KEY=test-secret-key-for-docker-testing
DEBUG=True
LOG_LEVEL=INFO
BACKEND_URL=http://localhost:8000
NLP_SERVICE_URL=http://localhost:8080
"@ | Out-File -FilePath .env -Encoding utf8

# Linux/Mac
cat > .env << EOF
POSTGRES_USER=medaudit
POSTGRES_PASSWORD=medaudit_password
POSTGRES_DB=medaudit_db
SECRET_KEY=test-secret-key-for-docker-testing
DEBUG=True
LOG_LEVEL=INFO
BACKEND_URL=http://localhost:8000
NLP_SERVICE_URL=http://localhost:8080
EOF
```

3. **Запустите автоматическое тестирование**:

**Windows PowerShell:**
```powershell
.\scripts\test_docker_deployment.ps1
```

**Linux/Mac:**
```bash
chmod +x scripts/test_docker_deployment.sh
./scripts/test_docker_deployment.sh
```

4. **Или выполните вручную**:

```bash
# Остановка существующих контейнеров
docker-compose down -v

# Сборка образов
docker-compose build

# Запуск контейнеров
docker-compose up -d

# Ожидание готовности (10-15 секунд)
sleep 15

# Применение миграций
docker-compose exec backend alembic upgrade head

# Проверка health check
curl http://localhost:8000/health

# Проверка статуса
docker-compose ps
```

## Проверка результатов

После успешного запуска:

- ✅ API доступен: http://localhost:8000
- ✅ Swagger документация: http://localhost:8000/api/docs
- ✅ ReDoc документация: http://localhost:8000/api/redoc
- ✅ Health check: http://localhost:8000/health

## Просмотр логов

```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f backend
docker-compose logs -f celery_worker
docker-compose logs -f db
docker-compose logs -f redis
```

## Остановка

```bash
# Остановка контейнеров
docker-compose down

# Остановка с удалением volumes (удалит данные БД!)
docker-compose down -v
```

## Устранение проблем

Если что-то не работает:

1. Проверьте, что Docker Desktop запущен
2. Проверьте логи: `docker-compose logs`
3. Проверьте статус: `docker-compose ps`
4. Пересоберите образы: `docker-compose build --no-cache`
5. См. подробную документацию: `docs/DOCKER_TESTING.md`

## Что проверяется

Автоматический скрипт проверяет:

- ✅ Сборку Docker образов
- ✅ Запуск всех контейнеров
- ✅ Готовность PostgreSQL
- ✅ Готовность Redis
- ✅ Применение миграций БД
- ✅ Доступность backend API
- ✅ Работу health check endpoints
- ✅ Запуск Celery worker
- ✅ Отсутствие критических ошибок в логах

## Следующие шаги

После успешного тестирования:

1. Настройте production переменные окружения
2. Создайте `docker-compose.prod.yml` для production
3. Настройте SSL сертификаты
4. Настройте мониторинг
5. Настройте резервное копирование

Подробнее: `docs/DEPLOYMENT.md`


