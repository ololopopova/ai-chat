"""Pytest fixtures для тестирования AI Chat приложения."""

import os
import sys
import uuid
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import pytest

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Type alias для FastAPI приложения
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
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
    # Используем тестовую БД если указана, иначе основную
    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://ai_chat:ai_chat_secret@localhost:5433/ai_chat_test",
    )

    return Settings(
        app_env="development",
        app_version="0.1.0-test",
        app_debug=True,
        domains_config_path=temp_domains_file,
        cors_origins=["http://localhost:8501", "http://test"],
        ws_connection_timeout=10,  # Меньший таймаут для тестов
        database_url=test_db_url,
        database_echo=False,
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


# ============================================================
# Database Fixtures
# ============================================================


@pytest.fixture(scope="session")
def db_url() -> str:
    """URL для тестовой базы данных."""
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://ai_chat:ai_chat_secret@localhost:5433/ai_chat_test",
    )


@pytest.fixture(scope="session")
async def db_engine(db_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """
    Создать async engine для тестовой БД.

    Scope: session — один engine на все тесты.
    """
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(
        db_url,
        echo=False,
        pool_size=2,
        max_overflow=5,
        pool_pre_ping=True,
    )

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
async def setup_test_db(db_engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """
    Инициализировать тестовую БД (создать таблицы).

    Scope: session — выполняется один раз перед всеми тестами.
    """
    from sqlalchemy import text

    from src.db.base import Base

    # Импортируем модели для metadata
    from src.db.models import Chunk, Conversation, Domain, Job  # noqa: F401

    async with db_engine.begin() as conn:
        # Создаём расширения
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

        # Создаём таблицы
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Cleanup после всех тестов (опционально)
    # async with db_engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(
    db_engine: AsyncEngine,
    setup_test_db: None,  # noqa: ARG001
) -> AsyncGenerator[AsyncSession, None]:
    """
    Создать async session для теста с автоматическим rollback.

    Каждый тест получает чистую сессию с откатом в конце.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    async with session_factory() as session, session.begin():
        yield session
        # Откатываем все изменения после теста
        await session.rollback()


@pytest.fixture
def sample_domain() -> dict[str, Any]:
    """Тестовые данные для создания домена."""
    unique_id = uuid.uuid4().hex[:8]
    return {
        "name": f"Test Domain {unique_id}",
        "slug": f"test-domain-{unique_id}",
        "description": "Test domain description",
        "google_doc_url": f"https://docs.google.com/document/d/{unique_id}",
        "is_active": True,
    }


@pytest.fixture
def sample_embedding() -> list[float]:
    """Тестовый embedding вектор (1536 dims для OpenAI)."""
    import random

    random.seed(42)  # Для воспроизводимости
    # Генерируем нормализованный вектор
    vec = [random.random() for _ in range(1536)]
    norm = sum(x * x for x in vec) ** 0.5
    return [x / norm for x in vec]


@pytest.fixture
def sample_chunks_data() -> list[dict[str, Any]]:
    """Тестовые данные для создания чанков."""
    return [
        {
            "content": "Python is a programming language",
            "chunk_index": 0,
        },
        {
            "content": "JavaScript is used for web development",
            "chunk_index": 1,
        },
        {
            "content": "Machine learning with Python",
            "chunk_index": 2,
        },
    ]


# ============================================================
# LLM / LangGraph Fixtures
# ============================================================


@pytest.fixture
def mock_llm_provider():
    """Mock LLM провайдер для тестов без реальных API вызовов."""
    from tests.mocks.llm_mock import MockLLMProvider

    return MockLLMProvider(
        responses={
            "маркетинг": "marketing",
            "продукт": "product",
            "поддержка": "support",
            "погода": "off_topic",
        }
    )


@pytest.fixture
def mock_llm_provider_with_responses():
    """Фабрика для создания mock LLM провайдера с кастомными ответами."""
    from tests.mocks.llm_mock import MockLLMProvider

    def _create(responses: dict[str, str]) -> MockLLMProvider:
        return MockLLMProvider(responses=responses)

    return _create


@pytest.fixture
def mock_checkpointer():
    """Mock checkpointer для тестов без PostgreSQL."""
    from unittest.mock import AsyncMock, MagicMock

    checkpointer = MagicMock()
    checkpointer.setup = AsyncMock()
    checkpointer.aget = AsyncMock(return_value=None)
    checkpointer.aput = AsyncMock()
    checkpointer.alist = AsyncMock(return_value=[])

    return checkpointer


@pytest.fixture
def chat_service_no_checkpointer():
    """ChatService без checkpointer для unit тестов."""
    from src.services.chat_service import ChatService

    return ChatService(checkpointer=None)


@pytest.fixture
def sample_thread_id() -> str:
    """Тестовый thread_id."""
    return str(uuid.uuid4())
