# API Аутентификации

## Обзор

Система аутентификации использует JWT (JSON Web Tokens) с двумя типами токенов:
- **Access Token** - короткоживущий токен (30 минут по умолчанию) для доступа к защищенным ресурсам
- **Refresh Token** - долгоживущий токен (7 дней по умолчанию) для обновления access token

## Endpoints

### 1. Регистрация пользователя

**POST** `/api/v1/auth/register`

Регистрация нового пользователя в системе.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Требования к паролю:**
- Минимум 8 символов
- Должен содержать хотя бы одну цифру
- Должен содержать хотя бы одну букву

**Response (201 Created):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Ошибки:**
- `400 Bad Request` - Пользователь с таким email уже существует или невалидные данные
- `422 Unprocessable Entity` - Ошибка валидации (слабый пароль, невалидный email)

---

### 2. Вход пользователя

**POST** `/api/v1/auth/login`

Аутентификация существующего пользователя.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Ошибки:**
- `401 Unauthorized` - Неверный email или пароль

---

### 3. Обновление токенов

**POST** `/api/v1/auth/refresh`

Обновление access token с помощью refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Ошибки:**
- `401 Unauthorized` - Невалидный или отозванный refresh token

---

### 4. Выход пользователя

**POST** `/api/v1/auth/logout`

Выход пользователя из системы. Добавляет токены в blacklist.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**
```json
{
  "message": "Успешный выход из системы"
}
```

**Ошибки:**
- `401 Unauthorized` - Невалидный access token

---

### 5. Информация о текущем пользователе

**GET** `/api/v1/auth/me`

Получение информации о текущем аутентифицированном пользователе.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**Ошибки:**
- `401 Unauthorized` - Невалидный или отсутствующий токен
- `403 Forbidden` - Пользователь неактивен

---

## Использование токенов

### Защищенные endpoints

Для доступа к защищенным endpoints необходимо добавить заголовок `Authorization`:

```
Authorization: Bearer <access_token>
```

### Пример использования (cURL)

```bash
# Регистрация
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Вход
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Получение информации о пользователе
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"

# Обновление токена
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'

# Выход
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

### Пример использования (JavaScript/Fetch)

```javascript
// Регистрация
const register = async (email, password) => {
  const response = await fetch('http://localhost:8000/api/v1/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });
  return await response.json();
};

// Вход
const login = async (email, password) => {
  const response = await fetch('http://localhost:8000/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });
  return await response.json();
};

// Защищенный запрос
const getCurrentUser = async (accessToken) => {
  const response = await fetch('http://localhost:8000/api/v1/auth/me', {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });
  return await response.json();
};
```

---

## Безопасность

1. **Хеширование паролей**: Все пароли хранятся в БД в захешированном виде (bcrypt)
2. **JWT токены**: Используются для безопасной передачи данных аутентификации
3. **Token Blacklist**: Отозванные токены добавляются в Redis blacklist
4. **Валидация**: Все входящие данные валидируются через Pydantic схемы
5. **CORS**: Настроен для работы с фронтенд-приложением

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
- `400 Bad Request` - Неверный запрос
- `401 Unauthorized` - Требуется аутентификация или невалидные учетные данные
- `403 Forbidden` - Нет прав доступа
- `422 Unprocessable Entity` - Ошибка валидации данных


