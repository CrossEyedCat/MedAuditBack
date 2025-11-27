# Интеграция с NLP-сервисом

## Обзор

Система интегрируется с внешним NLP-сервисом для анализа медицинских документов. Интеграция работает асинхронно через Celery задачи и callback механизм.

## Архитектура

1. **Запуск анализа**: Документ отправляется в NLP-сервис через Celery задачу
2. **Обработка**: NLP-сервис обрабатывает документ асинхронно
3. **Callback**: NLP-сервис отправляет результаты обратно через callback endpoint
4. **Сохранение**: Результаты сохраняются в БД (нарушения и сводка анализа)

## Формат запроса к NLP-сервису

**Endpoint**: `POST {NLP_SERVICE_URL}/api/analyze`

**Headers:**
```
Content-Type: application/json
Authorization: Bearer {NLP_SERVICE_API_KEY}  # Опционально
```

**Request Body:**
```json
{
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "document_id": "123e4567-e89b-12d3-a456-426614174001",
  "file_url": "http://backend.medyaudit.ru/api/v1/documents/{document_id}/download",
  "callback_url": "http://backend.medyaudit.ru/api/v1/nlp/callback"
}
```

**Поля:**
- `request_id` (UUID) - Уникальный идентификатор запроса, генерируемый бэкендом
- `document_id` (UUID) - UUID документа в БД
- `file_url` (string) - URL для скачивания файла или base64 (предпочтительно URL)
- `callback_url` (string) - URL для отправки результатов анализа

## Формат ответа от NLP-сервиса (Callback)

**Endpoint**: `POST /api/v1/nlp/callback`

**Request Body:**
```json
{
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "document_id": "123e4567-e89b-12d3-a456-426614174001",
  "status": "success",
  "analysis_result": {
    "violations": [
      {
        "code": "2.13",
        "description": "Отсутствие информированного согласия",
        "risk_level": "high",
        "regulation": "Ст. 20 ФЗ-323",
        "context": "В разделе 'Согласие на обработку данных' отсутствует подпись пациента.",
        "offset_start": 1250,
        "offset_end": 1300
      }
    ],
    "summary": {
      "total_risks": 180000,
      "critical_count": 2,
      "compliance_score": 4.0
    }
  },
  "error_message": null
}
```

**Для ошибок:**
```json
{
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "document_id": "123e4567-e89b-12d3-a456-426614174001",
  "status": "error",
  "analysis_result": null,
  "error_message": "Текст ошибки обработки"
}
```

**Поля violations:**
- `code` (string) - Код нарушения
- `description` (string) - Описание нарушения
- `risk_level` (string) - Уровень риска: `low`, `medium`, `high`, `critical`
- `regulation` (string, optional) - Ссылка на нормативный документ
- `context` (string, optional) - Контекст нарушения в документе
- `offset_start` (integer, optional) - Начало позиции в документе
- `offset_end` (integer, optional) - Конец позиции в документе

**Поля summary:**
- `total_risks` (integer) - Общее количество рисков
- `critical_count` (integer) - Количество критических нарушений
- `compliance_score` (float, optional) - Оценка соответствия

**Response (200 OK):**
```json
{
  "message": "Callback успешно обработан"
}
```

## Celery задача

### Запуск задачи

Задача запускается автоматически при создании отчета об аудите или может быть запущена вручную:

```python
from app.tasks.nlp_tasks import process_document_with_nlp

# Запуск задачи
task = process_document_with_nlp.delay(document_id="123e4567-e89b-12d3-a456-426614174001")
```

### Параметры задачи

- `document_id` (string) - UUID документа в виде строки

### Повторные попытки

Задача автоматически повторяется при ошибках с экспоненциальной задержкой:
- 1-я попытка: немедленно
- 2-я попытка: через 2 секунды
- 3-я попытка: через 4 секунды
- 4-я попытка: через 8 секунд

Максимальное количество попыток: 3

## Настройка

### Переменные окружения

```env
# URL NLP-сервиса
NLP_SERVICE_URL=http://localhost:8080

# API ключ для NLP-сервиса (опционально)
NLP_SERVICE_API_KEY=your-api-key

# URL бэкенд-приложения (для callback)
BACKEND_URL=http://localhost:8000
```

### Запуск Celery Worker

```bash
# Локально
celery -A app.core.celery_app worker --loglevel=info

# Через Docker
docker-compose up celery_worker
```

## Обработка ошибок

### Таймауты

При таймауте запроса к NLP-сервису (30 секунд) задача помечается как failed и может быть повторена.

### HTTP ошибки

Все HTTP ошибки от NLP-сервиса логируются и обрабатываются:
- `4xx` - Ошибка клиента (неверный запрос)
- `5xx` - Ошибка сервера (повторная попытка)

### Ошибки обработки

Если NLP-сервис возвращает статус `error` в callback, отчет помечается как `failed` с сохранением сообщения об ошибке.

## Логирование

Все операции логируются с использованием структурированного логирования:

- Отправка документа в NLP-сервис
- Получение callback
- Ошибки обработки
- Повторные попытки

Пример лога:
```json
{
  "event": "Document sent to NLP service",
  "document_id": "123e4567-e89b-12d3-a456-426614174001",
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "level": "info"
}
```

## Тестирование

### Mock NLP-сервис

Для тестирования можно использовать mock сервер:

```python
from unittest.mock import patch, AsyncMock

@patch('app.services.nlp.NLPService.send_document_for_analysis')
async def test_nlp_integration(mock_send):
    mock_send.return_value = {"status": "accepted"}
    # Тест логики
```

### Тестирование callback

```python
# Отправка тестового callback
response = await client.post(
    "/api/v1/nlp/callback",
    json={
        "request_id": str(request_id),
        "document_id": str(document_id),
        "status": "success",
        "analysis_result": {...}
    }
)
```

## Мониторинг

### Проверка статуса задачи

```python
from celery.result import AsyncResult

task_id = "task-id"
result = AsyncResult(task_id, app=celery_app)
print(result.state)  # PENDING, SUCCESS, FAILURE, RETRY
print(result.result)  # Результат выполнения
```

### Проверка статуса отчета

```python
# Через API
GET /api/v1/reports/{report_id}

# Статусы:
# - pending: Ожидает обработки
# - processing: Обрабатывается
# - completed: Завершено успешно
# - failed: Ошибка обработки
```

## Примеры использования

### Запуск анализа документа

```python
from app.tasks.nlp_tasks import process_document_with_nlp

# Асинхронный запуск
task = process_document_with_nlp.delay(str(document_id))

# Синхронный запуск (для тестов)
result = process_document_with_nlp(str(document_id))
```

### Обработка callback вручную

```python
from app.api.v1.endpoints.nlp import nlp_callback
from app.schemas.nlp import NLPCallbackRequest

callback_data = NLPCallbackRequest(
    request_id=uuid4(),
    document_id=uuid4(),
    status="success",
    analysis_result=...
)

result = await nlp_callback(callback_data, db_session)
```

## Troubleshooting

### Проблема: Callback не приходит

1. Проверьте, что NLP-сервис доступен
2. Проверьте URL callback в настройках
3. Проверьте логи NLP-сервиса
4. Убедитесь, что callback endpoint доступен извне

### Проблема: Задача не выполняется

1. Проверьте, что Celery worker запущен
2. Проверьте подключение к Redis
3. Проверьте логи Celery worker
4. Убедитесь, что задача зарегистрирована

### Проблема: Ошибки при сохранении результатов

1. Проверьте подключение к БД
2. Проверьте валидность данных в callback
3. Проверьте логи приложения





