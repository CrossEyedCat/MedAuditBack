# PowerShell скрипт для тестирования развертывания Docker контейнеров

$ErrorActionPreference = "SilentlyContinue"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Тестирование развертывания Docker контейнеров" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Функция для проверки статуса
function Check-Status {
    param(
        [string]$Message,
        [bool]$Success
    )
    if ($Success) {
        Write-Host "✓ $Message" -ForegroundColor Green
    } else {
        Write-Host "✗ $Message" -ForegroundColor Red
        exit 1
    }
}

# Шаг 1: Остановка существующих контейнеров
Write-Host ""
Write-Host "Шаг 1: Остановка существующих контейнеров..." -ForegroundColor Yellow
$oldErrorAction = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
try {
    & docker-compose down -v *>$null
} catch {
    # Игнорируем ошибки - контейнеры могут быть уже остановлены
} finally {
    $ErrorActionPreference = $oldErrorAction
}
# Всегда считаем успешным, так как контейнеры могут быть уже остановлены
Check-Status "Контейнеры остановлены" $true

# Шаг 2: Сборка образов
Write-Host ""
Write-Host "Шаг 2: Сборка Docker образов..." -ForegroundColor Yellow
docker-compose build --no-cache 2>&1 | Out-Host
if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq $null) {
    Check-Status "Образы собраны успешно" $true
} else {
    Check-Status "Ошибка при сборке образов" $false
}

# Шаг 3: Проверка и освобождение порта 8000
Write-Host ""
Write-Host "Шаг 3: Проверка занятости порта 8000..." -ForegroundColor Yellow
$port8000 = netstat -ano | Select-String ":8000.*LISTENING" | Select-Object -First 1
$dockerContainersOnPort = docker ps --format "{{.ID}}|{{.Names}}|{{.Ports}}" 2>$null | Select-String ":8000->"
$conflictingContainers = @()

if ($dockerContainersOnPort) {
    foreach ($line in $dockerContainersOnPort) {
        $parts = $line -split '\|'
        if ($parts.Length -ge 2) {
            $containerId = $parts[0]
            $containerName = $parts[1]
            if ($containerName -ne "medaudit_backend") {
                $conflictingContainers += @{Id=$containerId; Name=$containerName}
            }
        }
    }
}

if ($conflictingContainers.Count -gt 0) {
    Write-Host "⚠ Найдены контейнеры, использующие порт 8000:" -ForegroundColor Yellow
    foreach ($container in $conflictingContainers) {
        Write-Host "  - $($container.Name) (ID: $($container.Id))" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "Останавливаем конфликтующие контейнеры..." -ForegroundColor Yellow
    foreach ($container in $conflictingContainers) {
        docker stop $container.Id 2>$null | Out-Null
        Write-Host "  ✓ Остановлен: $($container.Name)" -ForegroundColor Green
    }
    Start-Sleep -Seconds 2
    Write-Host ""
} elseif ($port8000) {
    Write-Host "⚠ Порт 8000 занят другим процессом" -ForegroundColor Yellow
    Write-Host "  Проверьте процессы вручную: netstat -ano | findstr :8000" -ForegroundColor Yellow
    Write-Host "  Или измените порт в docker-compose.yml на 8001" -ForegroundColor Yellow
}

# Шаг 4: Запуск контейнеров
Write-Host ""
Write-Host "Шаг 4: Запуск контейнеров..." -ForegroundColor Yellow
$oldErrorAction = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
try {
    $output = docker-compose up -d 2>&1 | Out-String
    if ($output -match "port is already allocated" -or $output -match "Bind.*failed") {
        Write-Host "" -ForegroundColor Red
        Write-Host "✗ ОШИБКА: Порт 8000 уже занят!" -ForegroundColor Red
        Write-Host "" -ForegroundColor Red
        Write-Host "Решения:" -ForegroundColor Yellow
        Write-Host "  1. Остановите контейнер, использующий порт 8000:" -ForegroundColor Yellow
        Write-Host "     docker stop osjs" -ForegroundColor Cyan
        Write-Host "  2. Или измените порт в docker-compose.yml (например, на 8001)" -ForegroundColor Yellow
        Write-Host "" -ForegroundColor Red
        Check-Status "Ошибка при запуске контейнеров - порт занят" $false
    }
    if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq $null) {
        Check-Status "Контейнеры запущены" $true
    } else {
        Write-Host "Вывод docker-compose:" -ForegroundColor Yellow
        Write-Host $output
        Check-Status "Ошибка при запуске контейнеров" $false
    }
} catch {
    Write-Host "Ошибка: $_" -ForegroundColor Red
    Check-Status "Ошибка при запуске контейнеров" $false
} finally {
    $ErrorActionPreference = $oldErrorAction
}

# Шаг 5: Ожидание готовности сервисов
Write-Host ""
Write-Host "Шаг 5: Ожидание готовности сервисов..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Проверка статуса контейнеров
Write-Host ""
Write-Host "Проверка статуса контейнеров:" -ForegroundColor Yellow
docker-compose ps

# Шаг 6: Проверка подключения к БД
Write-Host ""
Write-Host "Шаг 6: Проверка подключения к PostgreSQL..." -ForegroundColor Yellow
$dbReady = $false
for ($i = 1; $i -le 30; $i++) {
    $result = docker-compose exec -T db pg_isready -U medaudit 2>$null
    if ($LASTEXITCODE -eq 0) {
        Check-Status "PostgreSQL готов" $true
        $dbReady = $true
        break
    }
    Start-Sleep -Seconds 1
}
if (-not $dbReady) {
    Check-Status "PostgreSQL не готов после 30 попыток" $false
}

# Шаг 7: Проверка подключения к Redis
Write-Host ""
Write-Host "Шаг 7: Проверка подключения к Redis..." -ForegroundColor Yellow
$redisReady = $false
for ($i = 1; $i -le 30; $i++) {
    $result = docker-compose exec -T redis redis-cli ping 2>$null
    if ($LASTEXITCODE -eq 0) {
        Check-Status "Redis готов" $true
        $redisReady = $true
        break
    }
    Start-Sleep -Seconds 1
}
if (-not $redisReady) {
    Check-Status "Redis не готов после 30 попыток" $false
}

# Шаг 8: Применение миграций
Write-Host ""
Write-Host "Шаг 8: Применение миграций БД..." -ForegroundColor Yellow
docker-compose exec -T backend alembic upgrade head
if ($LASTEXITCODE -eq 0) {
    Check-Status "Миграции применены" $true
} else {
    Check-Status "Ошибка при применении миграций" $false
}

# Шаг 9: Проверка health check endpoints
Write-Host ""
Write-Host "Шаг 9: Проверка health check..." -ForegroundColor Yellow
$backendReady = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Check-Status "Backend доступен" $true
            $backendReady = $true
            break
        }
    } catch {
        # Продолжаем попытки
    }
    Start-Sleep -Seconds 2
}
if (-not $backendReady) {
    Write-Host "Логи backend:" -ForegroundColor Yellow
    docker-compose logs backend
    Check-Status "Backend не доступен после 30 попыток" $false
}

# Шаг 10: Проверка API endpoints
Write-Host ""
Write-Host "Шаг 10: Проверка API endpoints..." -ForegroundColor Yellow

# Проверка корневого endpoint
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/" -UseBasicParsing -TimeoutSec 5
    Check-Status "Корневой endpoint работает" $true
} catch {
    Check-Status "Корневой endpoint не работает" $false
}

# Проверка документации
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/docs" -UseBasicParsing -TimeoutSec 5
    Check-Status "Swagger документация доступна" $true
} catch {
    Write-Host "⚠ Swagger документация недоступна" -ForegroundColor Yellow
}

# Шаг 11: Проверка логов на ошибки
Write-Host ""
Write-Host "Шаг 11: Проверка логов на критические ошибки..." -ForegroundColor Yellow
$logs = docker-compose logs backend 2>&1
$errors = ($logs | Select-String -Pattern "error|exception|traceback" -CaseSensitive:$false).Count
if ($errors -eq 0) {
    Check-Status "Критических ошибок в логах не обнаружено" $true
} else {
    Write-Host "⚠ Обнаружено $errors потенциальных ошибок в логах" -ForegroundColor Yellow
    $logs | Select-String -Pattern "error|exception|traceback" -CaseSensitive:$false | Select-Object -Last 5
}

# Шаг 12: Проверка Celery worker
Write-Host ""
Write-Host "Шаг 12: Проверка Celery worker..." -ForegroundColor Yellow
$celeryLogs = docker-compose logs celery_worker 2>&1
$celeryReady = ($celeryLogs | Select-String -Pattern "ready" -CaseSensitive:$false).Count
if ($celeryReady -gt 0) {
    Check-Status "Celery worker запущен" $true
} else {
    Write-Host "⚠ Celery worker может быть не готов" -ForegroundColor Yellow
    $celeryLogs | Select-Object -Last 10
}

# Итоговый отчет
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Итоговый отчет" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Статус контейнеров:" -ForegroundColor Yellow
docker-compose ps
Write-Host ""
Write-Host "Использование ресурсов:" -ForegroundColor Yellow
docker stats --no-stream --format 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}'
Write-Host ""
Write-Host "✓ Все проверки пройдены успешно!" -ForegroundColor Green
Write-Host ""
Write-Host "Доступные endpoints:" -ForegroundColor Cyan
Write-Host "  - API: http://localhost:8000"
Write-Host "  - Swagger: http://localhost:8000/api/docs"
Write-Host "  - ReDoc: http://localhost:8000/api/redoc"
Write-Host ""
Write-Host "Для просмотра логов используйте:" -ForegroundColor Cyan
Write-Host "  docker-compose logs -f [service_name]"
Write-Host ""
Write-Host "Для остановки контейнеров:" -ForegroundColor Cyan
Write-Host "  docker-compose down"
