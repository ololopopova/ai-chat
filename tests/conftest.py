"""Pytest fixtures для тестирования AI Chat приложения."""

import sys
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Type alias для FastAPI приложения
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from src.api.deps import clear_domains_cache
from src.api.main import create_app
from src.core.config import Settings, clear_settings_cache
from ui.mock.mock_client import MockApiClient
from ui.models.events import ChatMessage, MessageRole

# ============================================================
# UI / Mock Client Fixtures
# ============================================================


@pytest.fixture
def mock_client() -> MockApiClient:
    """Создать экземпляр mock клиента для тестов."""
    return MockApiClient()


@pytest.fixture
def sample_user_message() -> ChatMessage:
    """Создать тестовое сообщение пользователя."""
    return ChatMessage(
        role=MessageRole.USER,
        content="Тестовое сообщение",
    )


@pytest.fixture
def sample_assistant_message() -> ChatMessage:
    """Создать тестовое сообщение ассистента."""
    return ChatMessage(
        role=MessageRole.ASSISTANT,
        content="Тестовый ответ ассистента",
    )


# ============================================================
# API / FastAPI Fixtures
# ============================================================


@pytest.fixture
def test_domains_yaml() -> str:
    """Тестовое содержимое domains.yaml."""
    return """
domains:
  - id: test_marketing
    name: Тестовый маркетинг
    description: Тестовые вопросы о маркетинге
    google_doc_url: https://docs.google.com/document/d/test-marketing
    enabled: true

  - id: test_support
    name: Тестовая поддержка
    description: Тестовые вопросы поддержки
    google_doc_url: https://docs.google.com/document/d/test-support
    enabled: true

routing:
  fallback_to_offtopic: true
  ask_clarification_on_multiple: true
"""


@pytest.fixture
def temp_domains_file(test_domains_yaml: str) -> Path:
    """Создать временный файл domains.yaml для тестов."""
    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(test_domains_yaml)
        return Path(f.name)


@pytest.fixture
def test_settings(temp_domains_file: Path) -> Settings:
    """Тестовые настройки приложения."""
    return Settings(
        app_env="development",
        app_version="0.1.0-test",
        app_debug=True,
        domains_config_path=temp_domains_file,
        cors_origins=["http://localhost:8501", "http://test"],
        ws_connection_timeout=10,  # Меньший таймаут для тестов
    )


@pytest.fixture
def test_app(test_settings: Settings) -> FastAPI:
    """Создать тестовое FastAPI приложение."""
    clear_domains_cache()
    clear_settings_cache()
    return create_app(settings=test_settings)


@pytest.fixture
async def async_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Создать async HTTP клиент для API тестов."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sync_test_client(test_app: FastAPI) -> TestClient:
    """Создать синхронный тестовый клиент (для WebSocket тестов)."""
    return TestClient(test_app)


@pytest.fixture(autouse=True)
def cleanup_caches() -> Generator[None, None, None]:
    """Автоматическая очистка кэшей после каждого теста."""
    yield
    clear_domains_cache()
    clear_settings_cache()
