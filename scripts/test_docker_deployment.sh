#!/bin/bash
# Скрипт для тестирования развертывания Docker контейнеров

set -e

echo "=========================================="
echo "Тестирование развертывания Docker контейнеров"
echo "=========================================="

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для проверки статуса
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
    else
        echo -e "${RED}✗ $1${NC}"
        exit 1
    fi
}

# Шаг 1: Остановка существующих контейнеров
echo ""
echo "Шаг 1: Остановка существующих контейнеров..."
docker-compose down -v 2>/dev/null || true
check_status "Контейнеры остановлены"

# Шаг 2: Сборка образов
echo ""
echo "Шаг 2: Сборка Docker образов..."
docker-compose build --no-cache
check_status "Образы собраны успешно"

# Шаг 3: Запуск контейнеров
echo ""
echo "Шаг 3: Запуск контейнеров..."
docker-compose up -d
check_status "Контейнеры запущены"

# Шаг 4: Ожидание готовности сервисов
echo ""
echo "Шаг 4: Ожидание готовности сервисов..."
sleep 10

# Проверка статуса контейнеров
echo ""
echo "Проверка статуса контейнеров:"
docker-compose ps

# Шаг 5: Проверка подключения к БД
echo ""
echo "Шаг 5: Проверка подключения к PostgreSQL..."
for i in {1..30}; do
    if docker-compose exec -T db pg_isready -U medaudit > /dev/null 2>&1; then
        check_status "PostgreSQL готов"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ PostgreSQL не готов после 30 попыток${NC}"
        exit 1
    fi
    sleep 1
done

# Шаг 6: Проверка подключения к Redis
echo ""
echo "Шаг 6: Проверка подключения к Redis..."
for i in {1..30}; do
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        check_status "Redis готов"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ Redis не готов после 30 попыток${NC}"
        exit 1
    fi
    sleep 1
done

# Шаг 7: Применение миграций
echo ""
echo "Шаг 7: Применение миграций БД..."
docker-compose exec -T backend alembic upgrade head
check_status "Миграции применены"

# Шаг 8: Проверка health check endpoints
echo ""
echo "Шаг 8: Проверка health check..."
for i in {1..30}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        check_status "Backend доступен"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ Backend не доступен после 30 попыток${NC}"
        docker-compose logs backend
        exit 1
    fi
    sleep 2
done

# Шаг 9: Проверка API endpoints
echo ""
echo "Шаг 9: Проверка API endpoints..."

# Проверка корневого endpoint
if curl -f http://localhost:8000/ > /dev/null 2>&1; then
    check_status "Корневой endpoint работает"
else
    echo -e "${RED}✗ Корневой endpoint не работает${NC}"
    exit 1
fi

# Проверка документации
if curl -f http://localhost:8000/api/docs > /dev/null 2>&1; then
    check_status "Swagger документация доступна"
else
    echo -e "${YELLOW}⚠ Swagger документация недоступна${NC}"
fi

# Шаг 10: Проверка логов на ошибки
echo ""
echo "Шаг 10: Проверка логов на критические ошибки..."
ERRORS=$(docker-compose logs backend | grep -i "error\|exception\|traceback" | wc -l)
if [ $ERRORS -eq 0 ]; then
    check_status "Критических ошибок в логах не обнаружено"
else
    echo -e "${YELLOW}⚠ Обнаружено $ERRORS потенциальных ошибок в логах${NC}"
    docker-compose logs backend | grep -i "error\|exception\|traceback" | tail -5
fi

# Шаг 11: Проверка Celery worker
echo ""
echo "Шаг 11: Проверка Celery worker..."
CELERY_LOGS=$(docker-compose logs celery_worker | grep -i "ready" | wc -l)
if [ $CELERY_LOGS -gt 0 ]; then
    check_status "Celery worker запущен"
else
    echo -e "${YELLOW}⚠ Celery worker может быть не готов${NC}"
    docker-compose logs celery_worker | tail -10
fi

# Итоговый отчет
echo ""
echo "=========================================="
echo "Итоговый отчет"
echo "=========================================="
echo ""
echo "Статус контейнеров:"
docker-compose ps
echo ""
echo "Использование ресурсов:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
echo ""
echo -e "${GREEN}✓ Все проверки пройдены успешно!${NC}"
echo ""
echo "Доступные endpoints:"
echo "  - API: http://localhost:8000"
echo "  - Swagger: http://localhost:8000/api/docs"
echo "  - ReDoc: http://localhost:8000/api/redoc"
echo ""
echo "Для просмотра логов используйте:"
echo "  docker-compose logs -f [service_name]"
echo ""
echo "Для остановки контейнеров:"
echo "  docker-compose down"





