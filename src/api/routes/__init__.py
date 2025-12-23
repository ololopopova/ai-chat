"""API routes для FastAPI приложения."""

from fastapi import APIRouter

from src.api.routes.chat import router as chat_router
from src.api.routes.domains import router as domains_router
from src.api.routes.health import router as health_router

# Главный роутер API v1
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(domains_router, tags=["domains"])

__all__ = [
    "api_router",
    "chat_router",
    "domains_router",
    "health_router",
]

