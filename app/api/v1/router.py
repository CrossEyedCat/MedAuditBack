"""
Главный роутер API v1.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, documents, nlp, reports

api_router = APIRouter()

# Подключение роутеров
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(nlp.router, prefix="/nlp", tags=["nlp"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])

