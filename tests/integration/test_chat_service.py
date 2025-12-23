"""Integration тесты для ChatService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.chat_service import (
    ChatService,
    CompleteEvent,
    ErrorEvent,
    StageEvent,
    TokenEvent,
)


class TestChatEvents:
    """Тесты для событий чата."""

    def test_stage_event_to_dict(self) -> None:
        """StageEvent сериализуется корректно."""
        event = StageEvent(stage="router", status="active", message="Обработка...")
        data = event.to_dict()

        assert data["type"] == "stage"
        assert data["stage_name"] == "router"
        assert data["status"] == "active"
        assert data["message"] == "Обработка..."

    def test_token_event_to_dict(self) -> None:
        """TokenEvent сериализуется корректно."""
        event = TokenEvent(token="Hello")
        data = event.to_dict()

        assert data["type"] == "token"
        assert data["content"] == "Hello"

    def test_complete_event_to_dict(self) -> None:
        """CompleteEvent сериализуется корректно."""
        event = CompleteEvent(response="Full response", thread_id="thread-123")
        data = event.to_dict()

        assert data["type"] == "complete"
        assert data["final_response"] == "Full response"
        assert data["thread_id"] == "thread-123"
        assert data["asset_url"] is None

    def test_error_event_to_dict(self) -> None:
        """ErrorEvent сериализуется корректно."""
        event = ErrorEvent(error="Something failed", code="TEST_ERROR")
        data = event.to_dict()

        assert data["type"] == "error"
        assert data["message"] == "Something failed"
        assert data["code"] == "TEST_ERROR"


class TestChatService:
    """Тесты для ChatService."""

    def test_chat_service_init_no_checkpointer(self) -> None:
        """ChatService инициализируется без checkpointer."""
        service = ChatService()
        assert service._checkpointer is None
        assert service._graph is None

    def test_chat_service_lazy_graph(self) -> None:
        """Граф создаётся лениво."""
        service = ChatService()
        assert service._graph is None
        graph = service.graph
        assert service._graph is not None
        assert graph is service._graph

    @pytest.mark.asyncio
    async def test_chat_service_context_manager(self) -> None:
        """ChatService работает как контекстный менеджер."""
        async with ChatService() as service:
            assert service is not None

    @pytest.mark.asyncio
    async def test_process_message_yields_events(self) -> None:
        """process_message генерирует события."""
        # Мокаем граф чтобы не вызывать реальный LLM
        mock_state = {
            "messages": [MagicMock(type="ai", content="Test response")],
            "stage": MagicMock(value="generate"),
        }

        async def mock_astream(*_args, **_kwargs):
            yield mock_state

        with patch.object(
            ChatService,
            "graph",
            new_callable=lambda: property(
                lambda _self: MagicMock(
                    astream=mock_astream,
                    aget_state=AsyncMock(return_value=MagicMock(values=mock_state)),
                )
            ),
        ):
            service = ChatService()

            events = []
            async for event in service.process_message("Hello", "thread-123"):
                events.append(event)

            # Должны быть события разных типов
            event_types = [type(e).__name__ for e in events]
            assert "StageEvent" in event_types

    @pytest.mark.asyncio
    async def test_process_message_handles_errors(self) -> None:
        """process_message ловит ошибки и возвращает ErrorEvent."""
        service = ChatService()

        # Мокаем граф чтобы он выбрасывал ошибку
        mock_graph = MagicMock()

        async def failing_astream(*_args, **_kwargs):
            raise Exception("Test error")
            yield

        mock_graph.astream = failing_astream
        service._graph = mock_graph

        events = []
        async for event in service.process_message("Hello", "thread-123"):
            events.append(event)

        # Последнее событие должно быть ErrorEvent
        error_events = [e for e in events if isinstance(e, ErrorEvent)]
        assert len(error_events) == 1
        assert "Test error" in error_events[0].error


class TestChatServiceIntegration:
    """Интеграционные тесты ChatService с мок LLM."""

    @pytest.mark.asyncio
    async def test_full_flow_with_mock_llm(self) -> None:
        """Полный flow с моком LLM."""
        # Патчим LLM провайдер чтобы использовать mock
        with patch.dict("os.environ", {}, clear=True):
            # Без API ключа будет использоваться MockChatModel
            service = ChatService()

            events = []
            async for event in service.process_message(
                "Как продвигать продукт?", "test-thread-001"
            ):
                events.append(event)

            # Проверяем, что были события
            assert len(events) > 0

            # Должен быть хотя бы один StageEvent
            stage_events = [e for e in events if isinstance(e, StageEvent)]
            assert len(stage_events) >= 1

            # Должен быть CompleteEvent или ErrorEvent в конце
            final_event = events[-1]
            assert isinstance(final_event, (CompleteEvent, ErrorEvent))

    @pytest.mark.asyncio
    async def test_astream_tokens(self) -> None:
        """astream_tokens возвращает только токены."""
        with patch.dict("os.environ", {}, clear=True):
            service = ChatService()

            tokens = []
            async for token in service.astream_tokens("Test", "thread-123"):
                tokens.append(token)
                if len(tokens) > 10:  # Ограничиваем для теста
                    break

            # Токены должны быть строками
            for token in tokens:
                assert isinstance(token, str)
