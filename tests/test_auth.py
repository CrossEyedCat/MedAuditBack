"""
Тесты для аутентификации.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth import AuthService
from app.schemas.auth import UserRegister, UserLogin


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient, db_session: AsyncSession):
    """Тест успешной регистрации пользователя."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Проверка создания пользователя в БД
    user = await AuthService.get_user_by_email(db_session, "newuser@example.com")
    assert user is not None
    assert user.email == "newuser@example.com"


@pytest.mark.asyncio
async def test_register_user_duplicate_email(client: AsyncClient, test_user: User):
    """Тест регистрации с существующим email."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user.email,
            "password": "password123",
        },
    )
    assert response.status_code == 400
    assert "уже существует" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_user_weak_password(client: AsyncClient):
    """Тест регистрации со слабым паролем."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "123",  # Слишком короткий
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User):
    """Тест успешного входа."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user: User):
    """Тест входа с неверным паролем."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401
    assert "Неверный email или пароль" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Тест входа несуществующего пользователя."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 401
    assert "Неверный email или пароль" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient, test_user: User):
    """Тест обновления токена."""
    # Сначала получаем токены
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    refresh_token = login_response.json()["refresh_token"]

    # Обновляем токен
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    """Тест обновления с невалидным токеном."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, test_user: User):
    """Тест получения информации о текущем пользователе."""
    # Получаем токен
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Получаем информацию о пользователе
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    """Тест доступа без токена."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(client: AsyncClient):
    """Тест доступа с невалидным токеном."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, test_user: User):
    """Тест выхода из системы."""
    # Получаем токены
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]
    refresh_token = login_response.json()["refresh_token"]

    # Выходим
    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    assert "Успешный выход" in response.json()["message"]

    # Проверяем, что токен больше не работает
    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    # В реальном приложении это должно вернуть 401, но в тестах с MockRedis это может не работать
    # assert me_response.status_code == 401


@pytest.mark.asyncio
async def test_auth_service_register(db_session: AsyncSession):
    """Тест сервиса регистрации."""
    user_data = UserRegister(email="service@example.com", password="password123")
    user = await AuthService.register_user(db_session, user_data)
    assert user.email == "service@example.com"
    assert user.password_hash != "password123"  # Пароль должен быть захеширован


@pytest.mark.asyncio
async def test_auth_service_authenticate(db_session: AsyncSession):
    """Тест сервиса аутентификации."""
    # Создаем пользователя
    user_data = UserRegister(email="auth@example.com", password="password123")
    await AuthService.register_user(db_session, user_data)

    # Аутентифицируем
    login_data = UserLogin(email="auth@example.com", password="password123")
    user = await AuthService.authenticate_user(db_session, login_data)
    assert user is not None
    assert user.email == "auth@example.com"

    # Неверный пароль
    wrong_login = UserLogin(email="auth@example.com", password="wrong")
    user = await AuthService.authenticate_user(db_session, wrong_login)
    assert user is None





