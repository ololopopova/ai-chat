"""Pytest fixtures для тестирования AI Chat приложения."""

import sys
from pathlib import Path

import pytest

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.mock.mock_client import MockApiClient
from ui.models.events import ChatMessage, MessageRole


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
