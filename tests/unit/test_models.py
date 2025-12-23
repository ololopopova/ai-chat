"""Тесты для моделей данных."""

import pytest

from ui.models.conversation import Conversation
from ui.models.events import (
    ChatMessage,
    EventType,
    MessageRole,
    ProgressEvent,
    StageEvent,
    StageName,
    TokenEvent,
)


class TestChatMessage:
    """Тесты для ChatMessage."""

    def test_create_user_message(self) -> None:
        """Создание сообщения пользователя."""
        msg = ChatMessage(role=MessageRole.USER, content="Привет")
        assert msg.role == "user"  # use_enum_values=True
        assert msg.content == "Привет"
        assert msg.asset_url is None

    def test_create_assistant_message_with_asset(self) -> None:
        """Создание сообщения ассистента с вложением."""
        msg = ChatMessage(
            role=MessageRole.ASSISTANT,
            content="Вот ваш баннер",
            asset_url="https://example.com/banner.png",
        )
        assert msg.role == "assistant"
        assert msg.asset_url == "https://example.com/banner.png"


class TestEvents:
    """Тесты для событий."""

    def test_stage_event(self) -> None:
        """Создание события стадии."""
        event = StageEvent(stage_name=StageName.ROUTER, message="Анализирую...")
        assert event.type == EventType.STAGE
        assert event.stage_name == StageName.ROUTER

    def test_token_event(self) -> None:
        """Создание события токена."""
        event = TokenEvent(content="Привет")
        assert event.type == EventType.TOKEN
        assert event.content == "Привет"

    def test_progress_event_validation(self) -> None:
        """Валидация прогресса 0-100."""
        event = ProgressEvent(job_id="123", progress=50, current_step="Работаю...")
        assert event.progress == 50

        with pytest.raises(ValueError):
            ProgressEvent(job_id="123", progress=150, current_step="Ошибка")


class TestConversation:
    """Тесты для Conversation."""

    def test_create_conversation(self) -> None:
        """Создание диалога."""
        conv = Conversation(thread_id="abc-123")
        assert conv.thread_id == "abc-123"
        assert conv.title == "Новый диалог"
        assert conv.messages == []

    def test_get_title_empty(self) -> None:
        """Заголовок пустого диалога."""
        conv = Conversation(thread_id="abc")
        assert conv.get_title() == "Новый диалог"

    def test_get_title_from_message(self) -> None:
        """Заголовок из первого сообщения пользователя."""
        conv = Conversation(thread_id="abc")
        conv.messages.append(ChatMessage(role=MessageRole.USER, content="Расскажи про маркетинг"))
        assert conv.get_title() == "Расскажи про маркетинг"

    def test_get_title_truncated(self) -> None:
        """Обрезка длинного заголовка."""
        conv = Conversation(thread_id="abc")
        conv.messages.append(ChatMessage(role=MessageRole.USER, content="А" * 100))
        title = conv.get_title(max_length=30)
        assert len(title) == 33  # 30 + "..."
        assert title.endswith("...")
