"""
Тесты для модуля документов.
"""
import io
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.services.document import DocumentService
from app.schemas.document import DocumentFilterParams
from app.utils.password import get_password_hash


@pytest.mark.asyncio
async def test_upload_document_success(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест успешной загрузки документа."""
    # Получаем токен
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Создаем тестовый файл
    file_content = b"Test PDF content"
    files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}

    response = await client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files,
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["original_filename"] == "test.pdf"
    assert data["file_size"] == len(file_content)
    assert data["mime_type"] == "application/pdf"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_upload_document_unauthorized(client: AsyncClient):
    """Тест загрузки документа без аутентификации."""
    file_content = b"Test content"
    files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}

    response = await client.post(
        "/api/v1/documents/upload",
        files=files,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_upload_document_invalid_type(client: AsyncClient, test_user: User):
    """Тест загрузки документа недопустимого типа."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    file_content = b"Test content"
    files = {"file": ("test.exe", io.BytesIO(file_content), "application/x-msdownload")}

    response = await client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files,
    )

    assert response.status_code == 400
    assert "не разрешен" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_document_duplicate(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест загрузки дубликата документа."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    file_content = b"Duplicate test content"

    # Первая загрузка
    files1 = {"file": ("test1.pdf", io.BytesIO(file_content), "application/pdf")}
    response1 = await client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files1,
    )
    assert response1.status_code == 201

    # Вторая загрузка того же файла
    files2 = {"file": ("test2.pdf", io.BytesIO(file_content), "application/pdf")}
    response2 = await client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files2,
    )
    assert response2.status_code == 409
    assert "уже существует" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_get_documents_list(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест получения списка документов."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Создаем несколько документов
    for i in range(3):
        file_content = f"Test content {i}".encode()
        files = {"file": (f"test{i}.pdf", io.BytesIO(file_content), "application/pdf")}
        await client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {access_token}"},
            files=files,
        )

    # Получаем список
    response = await client.get(
        "/api/v1/documents/",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert len(data["items"]) >= 3


@pytest.mark.asyncio
async def test_get_documents_with_filters(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест получения списка документов с фильтрами."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Создаем документы разных типов
    pdf_content = b"PDF content"
    png_content = b"PNG content"
    
    files_pdf = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
    files_png = {"file": ("test.png", io.BytesIO(png_content), "image/png")}
    
    await client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files_pdf,
    )
    await client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files_png,
    )

    # Фильтр по типу файла
    response = await client.get(
        "/api/v1/documents/?mime_type=application/pdf",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert all(doc["mime_type"] == "application/pdf" for doc in data["items"])


@pytest.mark.asyncio
async def test_get_document_by_id(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест получения документа по ID."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Загружаем документ
    file_content = b"Test content"
    files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
    upload_response = await client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files,
    )
    document_id = upload_response.json()["id"]

    # Получаем документ
    response = await client.get(
        f"/api/v1/documents/{document_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == document_id
    assert data["original_filename"] == "test.pdf"


@pytest.mark.asyncio
async def test_get_document_not_found(client: AsyncClient, test_user: User):
    """Тест получения несуществующего документа."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    from uuid import uuid4
    fake_id = uuid4()

    response = await client.get(
        f"/api/v1/documents/{fake_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест удаления документа."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Загружаем документ
    file_content = b"Test content"
    files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
    upload_response = await client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files,
    )
    document_id = upload_response.json()["id"]

    # Удаляем документ
    response = await client.delete(
        f"/api/v1/documents/{document_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 204

    # Проверяем, что документ удален
    get_response = await client.get(
        f"/api/v1/documents/{document_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_document_service_create(db_session: AsyncSession, test_user: User):
    """Тест сервиса создания документа."""
    document = await DocumentService.create_document(
        db=db_session,
        user_id=test_user.id,
        original_filename="test.pdf",
        stored_filename="stored_test.pdf",
        file_size=100,
        mime_type="application/pdf",
        file_hash="test_hash",
    )

    assert document.id is not None
    assert document.original_filename == "test.pdf"
    assert document.status == DocumentStatus.PENDING


@pytest.mark.asyncio
async def test_document_service_get_by_user(db_session: AsyncSession, test_user: User):
    """Тест сервиса получения документов пользователя."""
    # Создаем несколько документов
    for i in range(3):
        await DocumentService.create_document(
            db=db_session,
            user_id=test_user.id,
            original_filename=f"test{i}.pdf",
            stored_filename=f"stored_test{i}.pdf",
            file_size=100,
            mime_type="application/pdf",
            file_hash=f"hash{i}",
        )

    filters = DocumentFilterParams(page=1, page_size=10)
    documents, total = await DocumentService.get_documents_by_user(db_session, test_user.id, filters)

    assert len(documents) == 3
    assert total == 3


@pytest.mark.asyncio
async def test_document_service_check_duplicate(db_session: AsyncSession, test_user: User):
    """Тест проверки дубликатов."""
    file_hash = "test_hash_123"

    # Создаем первый документ
    doc1 = await DocumentService.create_document(
        db=db_session,
        user_id=test_user.id,
        original_filename="test1.pdf",
        stored_filename="stored1.pdf",
        file_size=100,
        mime_type="application/pdf",
        file_hash=file_hash,
    )

    # Проверяем дубликат
    duplicate = await DocumentService.check_duplicate_by_hash(db_session, file_hash, test_user.id)
    assert duplicate is not None
    assert duplicate.id == doc1.id

    # Проверяем другой хеш
    no_duplicate = await DocumentService.check_duplicate_by_hash(db_session, "other_hash", test_user.id)
    assert no_duplicate is None


