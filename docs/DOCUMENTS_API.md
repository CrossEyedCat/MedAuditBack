# API Документов

## Обзор

API для работы с документами позволяет пользователям загружать, просматривать, скачивать и удалять документы. Все операции требуют аутентификации и проверяют права доступа пользователя.

## Поддерживаемые типы файлов

- `application/pdf` - PDF документы
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document` - DOCX документы
- `image/jpeg` - JPEG изображения
- `image/png` - PNG изображения

## Максимальный размер файла

50 МБ (52,428,800 байт)

## Endpoints

### 1. Загрузка документа

**POST** `/api/v1/documents/upload`

Загрузка документа в систему.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Request:**
- `file` (file, required) - Загружаемый файл

**Response (201 Created):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "123e4567-e89b-12d3-a456-426614174001",
  "original_filename": "document.pdf",
  "stored_filename": "a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf",
  "file_size": 102400,
  "mime_type": "application/pdf",
  "file_hash": "abc123def456...",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00",
  "message": "Документ успешно загружен"
}
```

**Ошибки:**
- `400 Bad Request` - Невалидный тип файла или размер превышает лимит
- `401 Unauthorized` - Требуется аутентификация
- `409 Conflict` - Документ с таким содержимым уже существует (дубликат)

---

### 2. Список документов

**GET** `/api/v1/documents/`

Получение списка документов пользователя с пагинацией и фильтрацией.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `status` (optional) - Фильтр по статусу: `pending`, `processing`, `completed`, `failed`
- `mime_type` (optional) - Фильтр по типу файла (например, `application/pdf`)
- `page` (optional, default: 1) - Номер страницы
- `page_size` (optional, default: 20) - Размер страницы (1-100)
- `order_by` (optional, default: `created_at`) - Поле для сортировки
- `order_direction` (optional, default: `desc`) - Направление сортировки: `asc` или `desc`

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "user_id": "123e4567-e89b-12d3-a456-426614174001",
      "original_filename": "document.pdf",
      "stored_filename": "a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf",
      "file_size": 102400,
      "mime_type": "application/pdf",
      "file_hash": "abc123def456...",
      "status": "pending",
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ],
  "total": 10,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

**Примеры запросов:**
```
GET /api/v1/documents/?status=completed&page=1&page_size=10
GET /api/v1/documents/?mime_type=application/pdf&order_by=created_at&order_direction=desc
```

---

### 3. Информация о документе

**GET** `/api/v1/documents/{document_id}`

Получение детальной информации о документе.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "123e4567-e89b-12d3-a456-426614174001",
  "original_filename": "document.pdf",
  "stored_filename": "a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf",
  "file_size": 102400,
  "mime_type": "application/pdf",
  "file_hash": "abc123def456...",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**Ошибки:**
- `404 Not Found` - Документ не найден или нет прав доступа

---

### 4. Удаление документа

**DELETE** `/api/v1/documents/{document_id}`

Удаление документа и связанного файла.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (204 No Content)**

**Ошибки:**
- `404 Not Found` - Документ не найден или нет прав доступа

---

### 5. Скачивание документа

**GET** `/api/v1/documents/{document_id}/download`

Скачивание файла документа.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
- Content-Type: соответствующий MIME-тип файла
- Content-Disposition: attachment; filename="original_filename"
- Тело ответа: содержимое файла

**Ошибки:**
- `404 Not Found` - Документ не найден, файл не найден на сервере или нет прав доступа

---

## Статусы документов

- `pending` - Документ загружен, ожидает обработки
- `processing` - Документ обрабатывается
- `completed` - Обработка завершена успешно
- `failed` - Ошибка при обработке

---

## Примеры использования

### cURL

```bash
# Загрузка документа
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@document.pdf"

# Список документов
curl -X GET "http://localhost:8000/api/v1/documents/?page=1&page_size=10" \
  -H "Authorization: Bearer <access_token>"

# Информация о документе
curl -X GET http://localhost:8000/api/v1/documents/{document_id} \
  -H "Authorization: Bearer <access_token>"

# Скачивание документа
curl -X GET http://localhost:8000/api/v1/documents/{document_id}/download \
  -H "Authorization: Bearer <access_token>" \
  -o downloaded_file.pdf

# Удаление документа
curl -X DELETE http://localhost:8000/api/v1/documents/{document_id} \
  -H "Authorization: Bearer <access_token>"
```

### JavaScript/Fetch

```javascript
// Загрузка документа
const uploadDocument = async (file, accessToken) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('http://localhost:8000/api/v1/documents/upload', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
    body: formData,
  });
  return await response.json();
};

// Список документов
const getDocuments = async (accessToken, filters = {}) => {
  const params = new URLSearchParams(filters);
  const response = await fetch(`http://localhost:8000/api/v1/documents/?${params}`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });
  return await response.json();
};

// Скачивание документа
const downloadDocument = async (documentId, accessToken) => {
  const response = await fetch(`http://localhost:8000/api/v1/documents/${documentId}/download`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'document.pdf';
  a.click();
};
```

### Python (requests)

```python
import requests

# Загрузка документа
def upload_document(file_path, access_token):
    url = "http://localhost:8000/api/v1/documents/upload"
    headers = {"Authorization": f"Bearer {access_token}"}
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, headers=headers, files=files)
    return response.json()

# Список документов
def get_documents(access_token, page=1, page_size=20):
    url = "http://localhost:8000/api/v1/documents/"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"page": page, "page_size": page_size}
    response = requests.get(url, headers=headers, params=params)
    return response.json()

# Скачивание документа
def download_document(document_id, access_token, save_path):
    url = f"http://localhost:8000/api/v1/documents/{document_id}/download"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers, stream=True)
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
```

---

## Безопасность

1. **Аутентификация**: Все endpoints требуют валидации JWT токена
2. **Проверка прав доступа**: Пользователи могут работать только со своими документами
3. **Валидация файлов**: Проверка типа и размера файла перед сохранением
4. **Санитизация имен файлов**: Очистка от опасных символов и путей
5. **Проверка дубликатов**: Предотвращение загрузки одинаковых файлов по хешу

---

## Обработка ошибок

Все ошибки возвращаются в стандартном формате:

```json
{
  "detail": "Описание ошибки"
}
```

**HTTP статус коды:**
- `200 OK` - Успешный запрос
- `201 Created` - Ресурс успешно создан
- `204 No Content` - Ресурс успешно удален
- `400 Bad Request` - Невалидный запрос (тип файла, размер)
- `401 Unauthorized` - Требуется аутентификация
- `403 Forbidden` - Нет прав доступа
- `404 Not Found` - Документ не найден
- `409 Conflict` - Документ с таким содержимым уже существует





