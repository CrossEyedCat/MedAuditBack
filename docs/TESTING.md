# Руководство по тестированию

## Запуск тестов

### Все тесты

```bash
pytest
```

### С покрытием кода

```bash
pytest --cov=app --cov-report=html --cov-report=term
```

### Конкретный файл тестов

```bash
pytest tests/test_auth.py
```

### Конкретный тест

```bash
pytest tests/test_auth.py::test_login_success
```

### С verbose выводом

```bash
pytest -v
```

## Типы тестов

### Unit-тесты

Тестируют отдельные компоненты изолированно:

- `tests/test_auth.py` - Тесты аутентификации
- `tests/test_models.py` - Тесты моделей БД
- `tests/test_documents.py` - Тесты работы с документами
- `tests/test_nlp.py` - Тесты интеграции с NLP
- `tests/test_reports.py` - Тесты API отчетов

### Integration-тесты

Тестируют взаимодействие компонентов:

- `tests/test_integration.py` - Полные циклы работы системы

### Нагрузочные тесты

Тестируют производительность:

- `tests/test_load.py` - Нагрузочное тестирование endpoints

## Покрытие кода

Цель: **80%+ покрытие кода**

Проверка покрытия:

```bash
pytest --cov=app --cov-report=term-missing
```

Генерация HTML отчета:

```bash
pytest --cov=app --cov-report=html
# Открыть htmlcov/index.html в браузере
```

## CI/CD

Автоматический запуск тестов настроен в `.github/workflows/ci.yml`:

- Запуск при push в main/develop
- Запуск при создании pull request
- Проверка покрытия кода (минимум 80%)
- Линтинг кода (flake8)

## Тестовые данные

Тестовые данные создаются автоматически через фикстуры в `tests/conftest.py`:

- `test_user` - Тестовый пользователь
- `db_session` - Сессия БД для тестов
- `client` - HTTP клиент для тестов

## Mock и Stub

Для изоляции тестов используются:

- Mock Redis (в `tests/conftest.py`)
- In-memory SQLite для БД
- Mock NLP сервиса (в тестах NLP)

## Примеры тестов

### Тест endpoint

```python
@pytest.mark.asyncio
async def test_get_documents(client: AsyncClient, test_user: User):
    login_response = await client.post("/api/v1/auth/login", ...)
    access_token = login_response.json()["access_token"]
    
    response = await client.get(
        "/api/v1/documents/",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    
    assert response.status_code == 200
    assert "items" in response.json()
```

### Тест сервиса

```python
@pytest.mark.asyncio
async def test_document_service_create(db_session: AsyncSession):
    document = await DocumentService.create_document(...)
    assert document.id is not None
```

## Troubleshooting

### Проблема: Тесты не запускаются

1. Убедитесь, что установлены все зависимости: `pip install -r requirements.txt`
2. Проверьте, что pytest-asyncio установлен
3. Проверьте версию Python (3.11+)

### Проблема: Ошибки подключения к БД

Тесты используют in-memory SQLite, проверьте `tests/conftest.py`

### Проблема: Ошибки Redis

Тесты используют Mock Redis, проверьте `tests/conftest.py`


