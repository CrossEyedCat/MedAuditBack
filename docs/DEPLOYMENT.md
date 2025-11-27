# Инструкция по развертыванию

## Подготовка к развертыванию

### 1. Переменные окружения

Создайте файл `.env` на основе `.env.example` и заполните все необходимые переменные:

```bash
# Обязательные переменные
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
REDIS_URL=redis://host:6379/0
SECRET_KEY=<сгенерируйте-безопасный-ключ>

# Production настройки
DEBUG=False
LOG_LEVEL=INFO
BACKEND_URL=https://api.medyaudit.ru
NLP_SERVICE_URL=https://nlp.medyaudit.ru

# CORS (укажите домены фронтенда)
CORS_ORIGINS=https://medyaudit.ru,https://www.medyaudit.ru
```

### 2. Генерация SECRET_KEY

```bash
# Linux/Mac
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

## Развертывание через Docker Compose

### Production конфигурация

Создайте `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - medaudit_network

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - medaudit_network

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    volumes:
      - file_storage:/app/storage
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=False
      - LOG_LEVEL=INFO
    depends_on:
      - db
      - redis
    restart: unless-stopped
    networks:
      - medaudit_network

  celery_worker:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A app.core.celery_app worker --loglevel=info --concurrency=4
    volumes:
      - file_storage:/app/storage
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - db
      - redis
      - backend
    restart: unless-stopped
    networks:
      - medaudit_network

volumes:
  postgres_data:
  redis_data:
  file_storage:

networks:
  medaudit_network:
    driver: bridge
```

### Запуск

```bash
# Применить миграции
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Запуск сервисов
docker-compose -f docker-compose.prod.yml up -d

# Просмотр логов
docker-compose -f docker-compose.prod.yml logs -f
```

## Развертывание на сервере

### 1. Установка зависимостей

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python и зависимостей
sudo apt install python3.11 python3.11-venv python3-pip postgresql-client -y

# Установка Docker и Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt install docker-compose-plugin -y
```

### 2. Настройка PostgreSQL

```bash
# Создание БД
sudo -u postgres psql
CREATE DATABASE medaudit_db;
CREATE USER medaudit WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE medaudit_db TO medaudit;
\q
```

### 3. Настройка Nginx (опционально)

Создайте конфигурацию `/etc/nginx/sites-available/medaudit`:

```nginx
server {
    listen 80;
    server_name api.medyaudit.ru;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. SSL сертификаты (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.medyaudit.ru
```

## Мониторинг

### Логи

```bash
# Логи приложения
docker-compose logs -f backend

# Логи Celery
docker-compose logs -f celery_worker

# Логи БД
docker-compose logs -f db
```

### Health checks

```bash
# Проверка API
curl http://localhost:8000/health

# Проверка БД
docker-compose exec db pg_isready

# Проверка Redis
docker-compose exec redis redis-cli ping
```

## Резервное копирование

### БД

```bash
# Создание бэкапа
docker-compose exec db pg_dump -U medaudit medaudit_db > backup_$(date +%Y%m%d).sql

# Восстановление
docker-compose exec -T db psql -U medaudit medaudit_db < backup_20240101.sql
```

### Файлы

```bash
# Бэкап хранилища файлов
tar -czf storage_backup_$(date +%Y%m%d).tar.gz storage/
```

## Обновление

```bash
# 1. Остановка сервисов
docker-compose down

# 2. Обновление кода
git pull origin main

# 3. Пересборка образов
docker-compose build --no-cache

# 4. Применение миграций
docker-compose up -d db
docker-compose exec backend alembic upgrade head

# 5. Запуск сервисов
docker-compose up -d
```

## Troubleshooting

### Проблема: Приложение не запускается

1. Проверьте логи: `docker-compose logs backend`
2. Проверьте переменные окружения в `.env`
3. Убедитесь, что БД и Redis доступны

### Проблема: Миграции не применяются

1. Проверьте подключение к БД
2. Убедитесь, что Alembic настроен правильно
3. Проверьте текущую версию: `alembic current`

### Проблема: Celery задачи не выполняются

1. Проверьте, что Celery worker запущен: `docker-compose ps celery_worker`
2. Проверьте подключение к Redis
3. Проверьте логи: `docker-compose logs celery_worker`





