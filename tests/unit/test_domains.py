"""Unit тесты для domains endpoints."""

from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from tempfile import NamedTemporaryFile

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
  - id: test_domain_1
    name: Тестовый домен 1
    description: Описание тестового домена 1
    google_docs:
      - https://docs.google.com/document/d/test1
    enabled: true

  - id: test_domain_2
    name: Тестовый домен 2
    description: Описание тестового домена 2
    google_docs:
      - https://docs.google.com/document/d/test2
    enabled: false

main_agent:
  model: gpt-5.2
  max_iterations: 10
  timeout: 60

subagents:
  allow_parallel_agents: true
  max_parallel_agents: 3
"""


@pytest.fixture
def temp_domains_file(domains_yaml_content: str) -> Path:
    """Создать временный файл domains.yaml."""
    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(domains_yaml_content)
        return Path(f.name)


@pytest.fixture
def test_settings(temp_domains_file: Path) -> Settings:
    """Тестовые настройки с путём к временному файлу."""
    return Settings(
        app_env="development",
        app_version="0.1.0-test",
        domains_config_path=temp_domains_file,
    )


@pytest.fixture
def app(test_settings: Settings, temp_domains_file: Path) -> FastAPI:
    """Создать тестовое приложение."""
    # Очищаем кэш перед созданием приложения
    clear_domains_cache()
    clear_settings_cache()

    application = create_app(settings=test_settings)

    # Переопределяем dependencies
    application.dependency_overrides[get_settings] = lambda: test_settings

    # Переопределяем domains config
    def get_test_domains_config() -> dict:
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
def cleanup_cache() -> Generator[None, None, None]:
    """Очистить кэш доменов и настроек после каждого теста."""
    yield
    clear_domains_cache()
    clear_settings_cache()


class TestDomainsEndpoint:
    """Тесты для GET /api/v1/domains."""

    @pytest.mark.asyncio
    async def test_get_domains_returns_list(self, client: AsyncClient) -> None:
        """GET /api/v1/domains возвращает список доменов."""
        response = await client.get("/api/v1/domains")

        assert response.status_code == 200
        data = response.json()

        assert "domains" in data
        assert "total" in data
        assert isinstance(data["domains"], list)

    @pytest.mark.asyncio
    async def test_get_domains_returns_correct_count(self, client: AsyncClient) -> None:
        """GET /api/v1/domains возвращает правильное количество доменов."""
        response = await client.get("/api/v1/domains")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert len(data["domains"]) == 2

    @pytest.mark.asyncio
    async def test_domain_has_required_fields(self, client: AsyncClient) -> None:
        """Каждый домен содержит обязательные поля."""
        response = await client.get("/api/v1/domains")

        assert response.status_code == 200
        data = response.json()

        for domain in data["domains"]:
            assert "id" in domain
            assert "name" in domain
            assert "description" in domain
            assert "is_active" in domain

    @pytest.mark.asyncio
    async def test_domain_values_are_correct(self, client: AsyncClient) -> None:
        """Значения доменов соответствуют конфигурации."""
        response = await client.get("/api/v1/domains")

        assert response.status_code == 200
        data = response.json()

        # Находим первый домен
        domains_by_id = {d["id"]: d for d in data["domains"]}

        assert "test_domain_1" in domains_by_id
        domain1 = domains_by_id["test_domain_1"]
        assert domain1["name"] == "Тестовый домен 1"
        assert domain1["description"] == "Описание тестового домена 1"
        assert domain1["is_active"] is True

        # Находим второй домен (disabled)
        assert "test_domain_2" in domains_by_id
        domain2 = domains_by_id["test_domain_2"]
        assert domain2["is_active"] is False


class TestDomainsConfigLoading:
    """Тесты для загрузки конфигурации доменов."""

    def test_load_domains_config_success(self, temp_domains_file: Path) -> None:
        """Успешная загрузка конфигурации из файла."""
        clear_domains_cache()
        config = load_domains_config(temp_domains_file)

        assert "agents" in config
        assert len(config["agents"]) == 2

    def test_load_domains_config_file_not_found(self) -> None:
        """Ошибка при отсутствии файла конфигурации."""
        clear_domains_cache()
        with pytest.raises(FileNotFoundError):
            load_domains_config(Path("/nonexistent/path/domains.yaml"))

    def test_load_domains_config_caching(self, temp_domains_file: Path) -> None:
        """Конфигурация кэшируется."""
        clear_domains_cache()

        # Первый вызов
        config1 = load_domains_config(temp_domains_file)
        # Второй вызов (должен вернуть кэшированный результат)
        config2 = load_domains_config(temp_domains_file)

        assert config1 is config2  # Тот же объект из кэша
