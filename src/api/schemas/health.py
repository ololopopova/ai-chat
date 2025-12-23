"""Схемы для health check endpoints."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    """Получить текущее время в UTC."""
    return datetime.now(UTC)


class DependencyStatus(BaseModel):
    """Статус зависимости."""

    status: Literal["ok", "degraded", "error", "not_configured"]
    message: str | None = None


class HealthResponse(BaseModel):
    """Ответ health check endpoint."""

    status: Literal["ok", "degraded", "error"]
    version: str
    timestamp: datetime = Field(default_factory=_utc_now)
    dependencies: dict[str, str] = Field(default_factory=dict)

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "ok",
                "version": "0.1.0",
                "timestamp": "2024-12-23T10:30:00Z",
                "dependencies": {
                    "database": "not_configured",
                    "redis": "not_configured",
                    "llm": "not_configured",
                },
            }
        }
    }


class ReadinessResponse(BaseModel):
    """Ответ readiness probe."""

    ready: bool
    checks: dict[str, bool] = Field(default_factory=dict)


class LivenessResponse(BaseModel):
    """Ответ liveness probe."""

    alive: bool
