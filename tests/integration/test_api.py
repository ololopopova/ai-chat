"""Integration тесты для REST API."""

from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.deps import clear_domains_cache, get_domains_config, load_domains_config
from src.api.main import create_app
from src.core.config import Settings, clear_settings_cache, get_settings


@pytest.fixture
def domains_yaml_content() -> str:
    """Тестовое содержимое domains.yaml."""
    return """
agents:
  - id: marketing
    name: Marketing Agent
    description: Эксперт по маркетингу и рекламе
    enabled: true
    google_docs:
      - https://docs.google.com/document/d/marketing

  - id: support
    name: Support Agent
    description: Эксперт по технической поддержке
    enabled: true
    google_docs:
      - https://docs.google.com/document/d/support

main_agent:
  model: gpt-5.2
  max_iterations: 10
  timeout: 60

subagents:
  allow_parallel: false
  max_parallel: 3
"""


@pytest.fixture
def temp_domains_file(domains_yaml_content: str) -> Path:
    """Создать временный файл domains.yaml."""
    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(domains_yaml_content)
        return Path(f.name)


@pytest.fixture
def test_settings(temp_domains_file: Path) -> Settings:
    """Тестовые настройки."""
    return Settings(
        app_env="development",
        app_version="0.1.0-test",
        domains_config_path=temp_domains_file,
        cors_origins=["http://localhost:8501", "http://test"],
    )


@pytest.fixture
def app(test_settings: Settings, temp_domains_file: Path) -> FastAPI:
    """Создать тестовое приложение."""
    clear_domains_cache()
    clear_settings_cache()

    application = create_app(settings=test_settings)

    # Переопределяем dependencies
    application.dependency_overrides[get_settings] = lambda: test_settings

    def get_test_domains_config() -> dict[str, Any]:
        return load_domains_config(temp_domains_file)

    application.dependency_overrides[get_domains_config] = get_test_domains_config

    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Создать async HTTP клиент для тестов."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def cleanup() -> Generator[None, None, None]:
    """Очистка после тестов."""
    yield
    clear_domains_cache()
    clear_settings_cache()


class TestCORSIntegration:
    """Тесты CORS настроек."""

    @pytest.mark.asyncio
    async def test_cors_allows_configured_origin(self, client: AsyncClient) -> None:
        """CORS разрешает настроенный origin."""
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:8501",
                "Access-Control-Request-Method": "GET",
            },
        )

        # OPTIONS должен вернуть 200 с CORS заголовками
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    @pytest.mark.asyncio
    async def test_cors_headers_on_response(self, client: AsyncClient) -> None:
        """CORS заголовки присутствуют в ответе."""
        response = await client.get(
            "/health",
            headers={"Origin": "http://localhost:8501"},
        )

        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:8501"


class TestMiddlewareIntegration:
    """Тесты middleware."""

    @pytest.mark.asyncio
    async def test_request_id_generated(self, client: AsyncClient) -> None:
        """Request ID генерируется автоматически."""
        response = await client.get("/health")

        assert response.status_code == 200
        request_id = response.headers.get("X-Request-ID")
        assert request_id is not None
        assert len(request_id) > 0

    @pytest.mark.asyncio
    async def test_request_id_preserved(self, client: AsyncClient) -> None:
        """Request ID из запроса сохраняется в ответе."""
        custom_id = "test-request-id-12345"
        response = await client.get(
            "/health",
            headers={"X-Request-ID": custom_id},
        )

        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == custom_id

    @pytest.mark.asyncio
    async def test_response_time_header(self, client: AsyncClient) -> None:
        """X-Response-Time header присутствует."""
        response = await client.get("/health")

        assert response.status_code == 200
        response_time = response.headers.get("X-Response-Time")
        assert response_time is not None
        assert "ms" in response_time


class TestFullAPIFlow:
    """Тесты полного flow API."""

    @pytest.mark.asyncio
    async def test_health_then_domains_flow(self, client: AsyncClient) -> None:
        """Последовательные запросы работают корректно."""
        # Проверяем health (в CI без БД статус может быть degraded)
        health_response = await client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json()["status"] in ("ok", "degraded")

        # Затем domains
        domains_response = await client.get("/api/v1/domains")
        assert domains_response.status_code == 200
        # Должен быть хотя бы один агент (products, compatibility, marketing)
        assert domains_response.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_multiple_health_checks(self, client: AsyncClient) -> None:
        """Множественные health check запросы."""
        for _ in range(5):
            response = await client.get("/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_all_health_endpoints(self, client: AsyncClient) -> None:
        """Все health endpoints работают."""
        endpoints = ["/health", "/health/ready", "/health/live"]

        for endpoint in endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 200, f"Failed for {endpoint}"


class TestErrorHandling:
    """Тесты обработки ошибок."""

    @pytest.mark.asyncio
    async def test_not_found_endpoint(self, client: AsyncClient) -> None:
        """Несуществующий endpoint возвращает 404."""
        response = await client.get("/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_method_not_allowed(self, client: AsyncClient) -> None:
        """Неверный метод возвращает 405."""
        response = await client.post("/health")
        assert response.status_code == 405
