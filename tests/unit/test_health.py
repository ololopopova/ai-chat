"""Unit тесты для health check endpoints."""

from collections.abc import AsyncGenerator, Generator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app
from src.core.config import Settings, clear_settings_cache, get_settings


@pytest.fixture
def test_settings() -> Settings:
    """Тестовые настройки."""
    return Settings(
        app_env="development",
        app_version="0.1.0-test",
    )


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """Создать тестовое приложение с переопределёнными настройками."""
    application = create_app(settings=test_settings)
    # Переопределяем dependency
    application.dependency_overrides[get_settings] = lambda: test_settings
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Создать async HTTP клиент для тестов."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def cleanup() -> Generator[None, None, None]:
    """Очистка кэша настроек после теста."""
    yield
    clear_settings_cache()


@pytest.mark.asyncio
async def test_health_check_returns_valid_status(client: AsyncClient) -> None:
    """GET /health возвращает валидный статус (ok или degraded)."""
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # В CI без БД и Redis статус будет degraded, это нормально
    assert data["status"] in ("ok", "degraded")
    assert "version" in data
    assert "timestamp" in data
    assert "dependencies" in data


@pytest.mark.asyncio
async def test_health_check_returns_version(client: AsyncClient) -> None:
    """GET /health возвращает версию приложения."""
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["version"] == "0.1.0-test"


@pytest.mark.asyncio
async def test_health_check_returns_dependencies(client: AsyncClient) -> None:
    """GET /health возвращает статус зависимостей."""
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # Зависимости должны возвращать валидные статусы
    # (ok, error, not_configured, connection_failed в зависимости от окружения)
    valid_statuses = {"ok", "error", "not_configured", "connection_failed"}
    assert data["dependencies"]["database"] in valid_statuses
    assert data["dependencies"]["redis"] in valid_statuses
    assert data["dependencies"]["llm"] in valid_statuses


@pytest.mark.asyncio
async def test_health_check_returns_timestamp(client: AsyncClient) -> None:
    """GET /health возвращает timestamp в формате ISO."""
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # Timestamp должен быть в ISO формате
    timestamp = data["timestamp"]
    assert "T" in timestamp  # ISO format содержит T


@pytest.mark.asyncio
async def test_readiness_probe_returns_response(client: AsyncClient) -> None:
    """GET /health/ready возвращает валидный ответ."""
    response = await client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()

    # В CI без БД ready может быть False, это нормально
    assert "ready" in data
    assert isinstance(data["ready"], bool)
    assert "checks" in data


@pytest.mark.asyncio
async def test_liveness_probe_returns_alive(client: AsyncClient) -> None:
    """GET /health/live возвращает alive: true."""
    response = await client.get("/health/live")

    assert response.status_code == 200
    data = response.json()

    assert data["alive"] is True


@pytest.mark.asyncio
async def test_health_has_request_id_header(client: AsyncClient) -> None:
    """Health endpoint возвращает X-Request-ID header."""
    response = await client.get("/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_health_has_response_time_header(client: AsyncClient) -> None:
    """Health endpoint возвращает X-Response-Time header."""
    response = await client.get("/health/ready")

    assert response.status_code == 200
    # Для health endpoints логирование отключено, но timing работает
    assert "X-Response-Time" in response.headers
