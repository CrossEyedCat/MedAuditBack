# Формат ответов API

## Стандартизированный формат ответов

Все ответы API следуют единому формату для обеспечения совместимости с фронтенд-приложением.

## Успешные ответы

### Стандартный формат

```json
{
  "success": true,
  "data": { ... },
  "message": "Опциональное сообщение"
}
```

### Примеры

**Регистрация пользователя:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Список документов:**
```json
{
  "items": [ ... ],
  "total": 10,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

**Детальная информация:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  ...
}
```

## Ответы с ошибками

### Стандартный формат

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Человекочитаемое сообщение об ошибке",
    "details": {
      "field": "Дополнительная информация",
      ...
    }
  }
}
```

### Коды ошибок

- `VALIDATION_ERROR` - Ошибка валидации данных (422)
- `UNAUTHORIZED` - Требуется аутентификация (401)
- `FORBIDDEN` - Нет прав доступа (403)
- `NOT_FOUND` - Ресурс не найден (404)
- `CONFLICT` - Конфликт данных (409)
- `RATE_LIMIT_EXCEEDED` - Превышен лимит запросов (429)
- `INTERNAL_SERVER_ERROR` - Внутренняя ошибка сервера (500)

### Примеры

**Ошибка валидации:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Ошибка валидации данных",
    "details": {
      "errors": [
        {
          "field": "email",
          "message": "Невалидный email адрес",
          "type": "value_error"
        }
      ]
    }
  }
}
```

**Ресурс не найден:**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Документ не найден",
    "details": {}
  }
}
```

**Превышен лимит запросов:**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Превышен лимит запросов. Максимум 5 запросов за 60 секунд.",
    "details": {}
  }
}
```

## HTTP статус коды

- `200 OK` - Успешный запрос
- `201 Created` - Ресурс успешно создан
- `204 No Content` - Успешное удаление (без тела ответа)
- `400 Bad Request` - Неверный запрос
- `401 Unauthorized` - Требуется аутентификация
- `403 Forbidden` - Нет прав доступа
- `404 Not Found` - Ресурс не найден
- `409 Conflict` - Конфликт данных
- `422 Unprocessable Entity` - Ошибка валидации
- `429 Too Many Requests` - Превышен лимит запросов
- `500 Internal Server Error` - Внутренняя ошибка сервера

## Обработка ошибок на фронтенде

### Пример обработки (JavaScript)

```javascript
async function apiCall(url, options) {
  try {
    const response = await fetch(url, options);
    const data = await response.json();

    if (!response.ok) {
      // Обработка ошибок
      if (data.error) {
        const errorCode = data.error.code;
        const errorMessage = data.error.message;
        
        switch (errorCode) {
          case 'VALIDATION_ERROR':
            // Показать ошибки валидации
            console.error('Ошибки валидации:', data.error.details.errors);
            break;
          case 'UNAUTHORIZED':
            // Перенаправить на страницу входа
            window.location.href = '/login';
            break;
          case 'RATE_LIMIT_EXCEEDED':
            // Показать сообщение о лимите
            alert('Превышен лимит запросов. Попробуйте позже.');
            break;
          default:
            alert(errorMessage);
        }
      }
      throw new Error(errorMessage || 'Произошла ошибка');
    }

    return data;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}
```

## Пагинация

Все списковые endpoints поддерживают пагинацию:

**Query параметры:**
- `page` (int, default: 1) - Номер страницы
- `page_size` (int, default: 20, max: 100) - Размер страницы

**Формат ответа:**
```json
{
  "items": [ ... ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "pages": 5
}
```

## Фильтрация и сортировка

**Query параметры:**
- `status` - Фильтр по статусу
- `order_by` - Поле для сортировки
- `order_direction` - Направление сортировки (asc/desc)

**Пример:**
```
GET /api/v1/reports/?status=completed&order_by=created_at&order_direction=desc&page=1&page_size=20
```

## Загрузка файлов

**Успешная загрузка:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "original_filename": "document.pdf",
  "file_size": 102400,
  "mime_type": "application/pdf",
  "status": "pending",
  "message": "Документ успешно загружен"
}
```

## Экспорт файлов

Экспорт файлов (PDF, и т.д.) возвращает файл напрямую с соответствующими заголовками:
- `Content-Type: application/pdf`
- `Content-Disposition: attachment; filename="report.pdf"`


