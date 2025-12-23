"""Unit тесты для Pydantic схем API."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.api.schemas.chat import ChatMessageRequest, ErrorResponse, PingMessage, PongMessage
from src.api.schemas.domain import DomainInfo, DomainsResponse
from src.api.schemas.health import (
    DependencyStatus,
    HealthResponse,
    LivenessResponse,
    ReadinessResponse,
)


class TestHealthSchemas:
    """Тесты для схем health endpoints."""

    def test_health_response_defaults(self) -> None:
        """HealthResponse создаётся с дефолтными значениями."""
        response = HealthResponse(
            status="ok",
            version="0.1.0",
        )

        assert response.status == "ok"
        assert response.version == "0.1.0"
        assert isinstance(response.timestamp, datetime)
        assert response.dependencies == {}

    def test_health_response_with_dependencies(self) -> None:
        """HealthResponse с зависимостями."""
        response = HealthResponse(
            status="degraded",
            version="0.1.0",
            dependencies={"database": "ok", "redis": "error"},
        )

        assert response.status == "degraded"
        assert response.dependencies["database"] == "ok"
        assert response.dependencies["redis"] == "error"

    def test_health_response_status_validation(self) -> None:
        """HealthResponse валидирует статус."""
        # Валидные статусы
        for status in ["ok", "degraded", "error"]:
            response = HealthResponse(status=status, version="0.1.0")  # type: ignore[arg-type]
            assert response.status == status

    def test_dependency_status_creation(self) -> None:
        """DependencyStatus создаётся корректно."""
        status = DependencyStatus(status="ok", message="Connected")

        assert status.status == "ok"
        assert status.message == "Connected"

    def test_readiness_response(self) -> None:
        """ReadinessResponse создаётся корректно."""
        response = ReadinessResponse(
            ready=True,
            checks={"database": True, "redis": False},
        )

        assert response.ready is True
        assert response.checks["database"] is True
        assert response.checks["redis"] is False

    def test_liveness_response(self) -> None:
        """LivenessResponse создаётся корректно."""
        response = LivenessResponse(alive=True)
        assert response.alive is True


class TestDomainSchemas:
    """Тесты для схем domains."""

    def test_domain_info_creation(self) -> None:
        """DomainInfo создаётся корректно."""
        domain = DomainInfo(
            id="marketing",
            name="Маркетинг",
            description="Вопросы о маркетинге",
            is_active=True,
        )

        assert domain.id == "marketing"
        assert domain.name == "Маркетинг"
        assert domain.description == "Вопросы о маркетинге"
        assert domain.is_active is True

    def test_domain_info_default_is_active(self) -> None:
        """DomainInfo по умолчанию is_active=True."""
        domain = DomainInfo(
            id="test",
            name="Test",
            description="Test domain",
        )

        assert domain.is_active is True

    def test_domains_response_empty(self) -> None:
        """DomainsResponse с пустым списком."""
        response = DomainsResponse()

        assert response.domains == []
        assert response.total == 0

    def test_domains_response_with_domains(self) -> None:
        """DomainsResponse со списком доменов."""
        domains = [
            DomainInfo(id="d1", name="Domain 1", description="Desc 1"),
            DomainInfo(id="d2", name="Domain 2", description="Desc 2"),
        ]
        response = DomainsResponse(domains=domains, total=2)

        assert len(response.domains) == 2
        assert response.total == 2


class TestChatSchemas:
    """Тесты для схем chat."""

    def test_chat_message_request_valid(self) -> None:
        """ChatMessageRequest валидируется корректно."""
        message = ChatMessageRequest(
            content="Hello, world!",
        )

        assert message.type == "message"
        assert message.content == "Hello, world!"
        assert message.metadata == {}

    def test_chat_message_request_with_metadata(self) -> None:
        """ChatMessageRequest с метаданными."""
        message = ChatMessageRequest(
            content="Test message",
            metadata={"key": "value"},
        )

        assert message.metadata == {"key": "value"}

    def test_chat_message_request_empty_content_fails(self) -> None:
        """ChatMessageRequest не принимает пустой контент."""
        with pytest.raises(ValidationError):
            ChatMessageRequest(content="")

    def test_chat_message_request_too_long_content_fails(self) -> None:
        """ChatMessageRequest не принимает слишком длинный контент."""
        with pytest.raises(ValidationError):
            ChatMessageRequest(content="x" * 10001)

    def test_error_response_creation(self) -> None:
        """ErrorResponse создаётся корректно."""
        error = ErrorResponse(
            message="Something went wrong",
            code="INTERNAL_ERROR",
        )

        assert error.type == "error"
        assert error.message == "Something went wrong"
        assert error.code == "INTERNAL_ERROR"
        assert isinstance(error.timestamp, datetime)

    def test_error_response_with_timestamp(self) -> None:
        """ErrorResponse с заданным timestamp."""
        ts = datetime(2024, 12, 23, 10, 30, 0, tzinfo=UTC)
        error = ErrorResponse(
            message="Error",
            code="TEST",
            timestamp=ts,
        )

        assert error.timestamp == ts

    def test_ping_message(self) -> None:
        """PingMessage создаётся корректно."""
        ping = PingMessage()
        assert ping.type == "ping"

    def test_pong_message(self) -> None:
        """PongMessage создаётся корректно."""
        pong = PongMessage()

        assert pong.type == "pong"
        assert isinstance(pong.timestamp, datetime)


class TestSchemasSerialization:
    """Тесты сериализации схем в JSON."""

    def test_health_response_json(self) -> None:
        """HealthResponse сериализуется в JSON."""
        response = HealthResponse(
            status="ok",
            version="0.1.0",
            timestamp=datetime(2024, 12, 23, 10, 30, 0, tzinfo=UTC),
        )

        json_data = response.model_dump(mode="json")

        assert json_data["status"] == "ok"
        assert json_data["version"] == "0.1.0"
        assert "2024-12-23" in json_data["timestamp"]

    def test_error_response_json(self) -> None:
        """ErrorResponse сериализуется в JSON."""
        error = ErrorResponse(
            message="Test error",
            code="TEST_CODE",
            timestamp=datetime(2024, 12, 23, 10, 30, 0, tzinfo=UTC),
        )

        json_data = error.model_dump(mode="json")

        assert json_data["type"] == "error"
        assert json_data["message"] == "Test error"
        assert json_data["code"] == "TEST_CODE"

    def test_domains_response_json(self) -> None:
        """DomainsResponse сериализуется в JSON."""
        response = DomainsResponse(
            domains=[
                DomainInfo(id="test", name="Test", description="Description"),
            ],
            total=1,
        )

        json_data = response.model_dump(mode="json")

        assert len(json_data["domains"]) == 1
        assert json_data["total"] == 1
        assert json_data["domains"][0]["id"] == "test"
