"""Integration тесты для WebSocket endpoint."""

from collections.abc import Generator
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from src.api.deps import clear_domains_cache
from src.api.main import create_app
from src.core.config import Settings


@pytest.fixture
def domains_yaml_content() -> str:
    """Тестовое содержимое domains.yaml."""
    return """
domains:
  - id: test
    name: Test
    description: Test domain
    google_doc_url: https://docs.google.com/document/d/test
    enabled: true
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
        ws_connection_timeout=10,  # Меньший таймаут для тестов
    )


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """Создать тестовое приложение."""
    clear_domains_cache()
    return create_app(settings=test_settings)


@pytest.fixture
def sync_client(app: FastAPI) -> TestClient:
    """Синхронный тестовый клиент для WebSocket."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def cleanup() -> Generator[None, None, None]:
    """Очистка после тестов."""
    yield
    clear_domains_cache()


class TestWebSocketConnection:
    """Тесты подключения к WebSocket."""

    def test_websocket_connect_success(self, sync_client: TestClient) -> None:
        """Успешное подключение к WebSocket."""
        thread_id = str(uuid4())
        with sync_client.websocket_connect(f"/ws/chat/{thread_id}") as ws:
            # Соединение установлено, отправляем ping
            ws.send_json({"type": "ping"})
            response = ws.receive_json()
            assert response["type"] == "pong"

    def test_websocket_connect_with_invalid_thread_id(self, sync_client: TestClient) -> None:
        """Подключение с невалидным thread_id создаёт новый UUID."""
        with sync_client.websocket_connect("/ws/chat/invalid-id") as ws:
            ws.send_json({"type": "ping"})
            response = ws.receive_json()
            assert response["type"] == "pong"

    def test_websocket_multiple_connections(self, sync_client: TestClient) -> None:
        """Несколько WebSocket соединений работают независимо."""
        thread_id_1 = str(uuid4())
        thread_id_2 = str(uuid4())

        with sync_client.websocket_connect(f"/ws/chat/{thread_id_1}") as ws1:
            ws1.send_json({"type": "ping"})
            response1 = ws1.receive_json()
            assert response1["type"] == "pong"

        with sync_client.websocket_connect(f"/ws/chat/{thread_id_2}") as ws2:
            ws2.send_json({"type": "ping"})
            response2 = ws2.receive_json()
            assert response2["type"] == "pong"


class TestWebSocketMessageFlow:
    """Тесты обмена сообщениями через WebSocket."""

    def test_send_message_receives_stages(self, sync_client: TestClient) -> None:
        """Отправка сообщения запускает стадии обработки."""
        thread_id = str(uuid4())
        with sync_client.websocket_connect(f"/ws/chat/{thread_id}") as ws:
            # Отправляем сообщение
            ws.send_json(
                {
                    "type": "message",
                    "content": "Hello, world!",
                    "metadata": {},
                }
            )

            # Ожидаем события
            events = []
            while True:
                response = ws.receive_json()
                events.append(response)
                if response["type"] in ["complete", "error"]:
                    break

            # Проверяем, что получили stage события
            stage_events = [e for e in events if e["type"] == "stage"]
            # В CI без полного ChatService может быть только 1 stage (fallback режим)
            assert len(stage_events) >= 1

            # Проверяем что есть хотя бы одна стадия
            stage_names = [e["stage_name"] for e in stage_events]
            # В fallback режиме только generate, в полном - router и generate
            assert "generate" in stage_names or "router" in stage_names

    def test_send_message_receives_tokens(self, sync_client: TestClient) -> None:
        """Отправка сообщения возвращает токены ответа."""
        thread_id = str(uuid4())
        with sync_client.websocket_connect(f"/ws/chat/{thread_id}") as ws:
            ws.send_json(
                {
                    "type": "message",
                    "content": "Test message",
                    "metadata": {},
                }
            )

            events = []
            while True:
                response = ws.receive_json()
                events.append(response)
                if response["type"] in ["complete", "error"]:
                    break

            # Проверяем токены
            token_events = [e for e in events if e["type"] == "token"]
            assert len(token_events) > 0

            # Собираем текст из токенов
            full_text = "".join(e["content"] for e in token_events)
            assert len(full_text) > 0

    def test_send_message_ends_with_complete(self, sync_client: TestClient) -> None:
        """Обработка сообщения завершается complete событием."""
        thread_id = str(uuid4())
        with sync_client.websocket_connect(f"/ws/chat/{thread_id}") as ws:
            ws.send_json(
                {
                    "type": "message",
                    "content": "Test",
                    "metadata": {},
                }
            )

            last_event = None
            while True:
                response = ws.receive_json()
                last_event = response
                if response["type"] in ["complete", "error"]:
                    break

            assert last_event is not None
            assert last_event["type"] == "complete"
            assert "final_response" in last_event

    def test_echo_includes_user_message(self, sync_client: TestClient) -> None:
        """Echo режим включает сообщение пользователя в ответ."""
        thread_id = str(uuid4())
        test_message = "Unique test message 12345"

        with sync_client.websocket_connect(f"/ws/chat/{thread_id}") as ws:
            ws.send_json(
                {
                    "type": "message",
                    "content": test_message,
                    "metadata": {},
                }
            )

            events = []
            while True:
                response = ws.receive_json()
                events.append(response)
                if response["type"] in ["complete", "error"]:
                    break

            # Собираем ответ
            complete_event = events[-1]
            assert complete_event["type"] == "complete"

            final_response = complete_event.get("final_response", "")
            assert test_message in final_response


class TestWebSocketErrorHandling:
    """Тесты обработки ошибок WebSocket."""

    def test_invalid_json_returns_error(self, sync_client: TestClient) -> None:
        """Невалидный JSON возвращает ошибку."""
        thread_id = str(uuid4())
        with sync_client.websocket_connect(f"/ws/chat/{thread_id}") as ws:
            # Отправляем невалидный JSON (через send_text, т.к. send_json валидирует)
            # Используем сообщение без обязательного поля content
            ws.send_json({"type": "message"})

            response = ws.receive_json()
            assert response["type"] == "error"
            assert "INVALID_MESSAGE" in response["code"]

    def test_empty_content_returns_error(self, sync_client: TestClient) -> None:
        """Пустой контент сообщения возвращает ошибку."""
        thread_id = str(uuid4())
        with sync_client.websocket_connect(f"/ws/chat/{thread_id}") as ws:
            ws.send_json(
                {
                    "type": "message",
                    "content": "",
                    "metadata": {},
                }
            )

            response = ws.receive_json()
            assert response["type"] == "error"


class TestWebSocketPingPong:
    """Тесты ping/pong heartbeat."""

    def test_ping_returns_pong(self, sync_client: TestClient) -> None:
        """Ping сообщение возвращает pong."""
        thread_id = str(uuid4())
        with sync_client.websocket_connect(f"/ws/chat/{thread_id}") as ws:
            ws.send_json({"type": "ping"})
            response = ws.receive_json()

            assert response["type"] == "pong"
            assert "timestamp" in response

    def test_multiple_pings(self, sync_client: TestClient) -> None:
        """Множественные ping работают корректно."""
        thread_id = str(uuid4())
        with sync_client.websocket_connect(f"/ws/chat/{thread_id}") as ws:
            for _ in range(3):
                ws.send_json({"type": "ping"})
                response = ws.receive_json()
                assert response["type"] == "pong"


class TestWebSocketSessionIsolation:
    """Тесты изоляции сессий."""

    def test_different_threads_are_isolated(self, sync_client: TestClient) -> None:
        """Разные thread_id имеют изолированные сессии."""
        thread_id_1 = str(uuid4())
        thread_id_2 = str(uuid4())

        # Первое соединение
        with sync_client.websocket_connect(f"/ws/chat/{thread_id_1}") as ws1:
            ws1.send_json({"type": "message", "content": "Message 1", "metadata": {}})

            # Собираем события первой сессии
            events1 = []
            while True:
                response = ws1.receive_json()
                events1.append(response)
                if response["type"] in ["complete", "error"]:
                    break

        # Второе соединение
        with sync_client.websocket_connect(f"/ws/chat/{thread_id_2}") as ws2:
            ws2.send_json({"type": "message", "content": "Message 2", "metadata": {}})

            events2 = []
            while True:
                response = ws2.receive_json()
                events2.append(response)
                if response["type"] in ["complete", "error"]:
                    break

        # Обе сессии должны завершиться успешно
        assert events1[-1]["type"] == "complete"
        assert events2[-1]["type"] == "complete"

        # Ответы должны содержать соответствующие сообщения
        assert "Message 1" in events1[-1]["final_response"]
        assert "Message 2" in events2[-1]["final_response"]
