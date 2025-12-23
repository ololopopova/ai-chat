"""Health check endpoints."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.schemas.health import HealthResponse, LivenessResponse, ReadinessResponse
from src.core.config import Settings, get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    response_model=HealthResponse,
    summary="Health Check",
    description="Проверка общего состояния сервиса.",
)
async def health_check(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """
    Проверить состояние сервиса.

    Возвращает:
    - status: общий статус сервиса
    - version: версия приложения
    - timestamp: текущее время сервера
    - dependencies: статус зависимостей
    """
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        timestamp=datetime.now(UTC),
        dependencies={
            "database": "not_configured",
            "redis": "not_configured",
            "llm": "not_configured",
        },
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness Probe",
    description="Kubernetes readiness probe — готов ли сервис принимать трафик.",
)
async def readiness_probe() -> ReadinessResponse:
    """
    Проверить готовность сервиса к приёму трафика.

    Используется Kubernetes для определения, можно ли
    направлять трафик на этот под.
    """
    # В будущем здесь будут проверки подключения к БД, Redis и т.д.
    checks = {
        "database": True,  # Заглушка
        "redis": True,  # Заглушка
    }

    all_ready = all(checks.values())

    return ReadinessResponse(ready=all_ready, checks=checks)


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Liveness Probe",
    description="Kubernetes liveness probe — жив ли сервис.",
)
async def liveness_probe() -> LivenessResponse:
    """
    Проверить, что сервис жив и отвечает.

    Используется Kubernetes для определения, нужно ли
    перезапустить под.
    """
    return LivenessResponse(alive=True)
