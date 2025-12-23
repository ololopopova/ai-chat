"""Тесты для Mock API клиента."""

import pytest

from ui.mock.mock_client import MockApiClient
from ui.models.events import EventType


class TestMockApiClient:
    """Тесты для MockApiClient."""

    def test_create_thread(self) -> None:
        """Создание thread возвращает UUID."""
        client = MockApiClient()
        thread_id = client.create_thread()

        assert thread_id is not None
        assert len(thread_id) == 36  # UUID формат
        assert client.thread_id == thread_id

    def test_detect_scenario_banner(self) -> None:
        """Определение сценария баннера."""
        client = MockApiClient()
        assert client._detect_scenario("Сделай баннер") == "banner"
        assert client._detect_scenario("Нужна картинка") == "banner"

    def test_detect_scenario_error(self) -> None:
        """Определение сценария ошибки."""
        client = MockApiClient()
        assert client._detect_scenario("Сломай всё") == "error"
        assert client._detect_scenario("Вызови ошибку") == "error"

    def test_detect_scenario_offtopic(self) -> None:
        """Определение сценария off-topic."""
        client = MockApiClient()
        assert client._detect_scenario("Какая погода?") == "offtopic"
        assert client._detect_scenario("Расскажи анекдот") == "offtopic"

    def test_detect_scenario_rag(self) -> None:
        """Определение сценария RAG (по умолчанию)."""
        client = MockApiClient()
        assert client._detect_scenario("Расскажи про маркетинг") == "rag"
        assert client._detect_scenario("Как создать продукт?") == "rag"

    @pytest.mark.asyncio
    async def test_send_message_rag_scenario(self) -> None:
        """RAG сценарий возвращает правильные события."""
        client = MockApiClient()
        events = []

        async for event in client.send_message("Расскажи про маркетинг"):
            events.append(event)

        # Должны быть: STAGE, STAGE, STAGE, TOKEN..., COMPLETE
        assert events[0].type == EventType.STAGE
        assert events[-1].type == EventType.COMPLETE
        assert any(e.type == EventType.TOKEN for e in events)

    @pytest.mark.asyncio
    async def test_send_message_error_scenario(self) -> None:
        """Error сценарий возвращает событие ошибки."""
        client = MockApiClient()
        events = []

        async for event in client.send_message("Сломай"):
            events.append(event)

        assert events[-1].type == EventType.ERROR
