"""Health check endpoints."""

import logging
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends

from src.api.schemas.health import HealthResponse, LivenessResponse, ReadinessResponse
from src.core.config import Settings, get_settings

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)


async def check_database() -> tuple[bool, str]:
    """
    Проверить подключение к PostgreSQL.

    Returns:
        Tuple (is_ok, status_message).
    """
    try:
        from src.db.engine import check_database_connection, get_engine

        engine = get_engine()
        is_ok = await check_database_connection(engine, timeout_seconds=5.0)
        return (is_ok, "ok" if is_ok else "connection_failed")
    except Exception as e:
        logger.warning("Database health check failed", extra={"error": str(e)})
        return (False, f"error: {type(e).__name__}")


async def check_redis() -> tuple[bool, str]:
    """
    Проверить подключение к Redis.

    Returns:
        Tuple (is_ok, status_message).
    """
    try:
        import asyncio

        import redis.asyncio as redis

        from src.core.config import get_settings

        settings = get_settings()
        client = redis.from_url(
            settings.redis_url,
            socket_timeout=settings.redis_socket_timeout,
            socket_connect_timeout=settings.redis_socket_connect_timeout,
        )

        try:
            async with asyncio.timeout(5.0):
                await client.ping()
                return (True, "ok")
        finally:
            await client.aclose()
    except Exception as e:
        logger.warning("Redis health check failed", extra={"error": str(e)})
        return (False, f"error: {type(e).__name__}")


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
    # Проверяем зависимости параллельно
    import asyncio

    results = await asyncio.gather(
        check_database(),
        check_redis(),
        return_exceptions=True,
    )

    db_check = results[0]
    redis_check = results[1]

    # Обрабатываем результаты
    if isinstance(db_check, BaseException):
        db_ok, db_status = False, f"error: {type(db_check).__name__}"
    else:
        db_ok, db_status = db_check

    if isinstance(redis_check, BaseException):
        redis_ok, redis_status = False, f"error: {type(redis_check).__name__}"
    else:
        redis_ok, redis_status = redis_check

    # Определяем общий статус
    all_ok = db_ok and redis_ok
    overall_status: Literal["ok", "degraded", "error"] = "ok" if all_ok else "degraded"

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        timestamp=datetime.now(UTC),
        dependencies={
            "database": db_status,
            "redis": redis_status,
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
    import asyncio

    # Проверяем критичные зависимости
    results = await asyncio.gather(
        check_database(),
        check_redis(),
        return_exceptions=True,
    )

    db_check = results[0]
    redis_check = results[1]

    db_ok = not isinstance(db_check, BaseException) and db_check[0]
    redis_ok = not isinstance(redis_check, BaseException) and redis_check[0]

    checks = {
        "database": db_ok,
        "redis": redis_ok,
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
