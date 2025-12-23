"""Моки для LLM провайдера."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock


class MockAIMessage:
    """Mock AI сообщение."""

    def __init__(self, content: str) -> None:
        self.content = content
        self.type = "ai"


class MockAIMessageChunk:
    """Mock чанк для стриминга."""

    def __init__(self, content: str) -> None:
        self.content = content
        self.type = "AIMessageChunk"


class MockChatModel:
    """Mock чат модель для тестов."""

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        """
        Инициализация mock модели.

        Args:
            responses: Словарь {input_pattern: response}
        """
        self._responses = responses or {}
        self._default_response = "Mock response for testing"
        self._call_count = 0
        self._last_messages: list[Any] = []

    async def ainvoke(self, messages: list, **_kwargs: Any) -> MockAIMessage:
        """Mock async invoke."""
        self._call_count += 1
        self._last_messages = messages

        # Извлекаем содержимое последнего сообщения
        if messages:
            last_content = ""
            last_msg = messages[-1]
            if hasattr(last_msg, "content"):
                last_content = last_msg.content
            elif isinstance(last_msg, dict):
                last_content = last_msg.get("content", "")

            # Ищем совпадение в responses
            for pattern, response in self._responses.items():
                if pattern.lower() in last_content.lower():
                    return MockAIMessage(content=response)

        return MockAIMessage(content=self._default_response)

    async def astream(self, messages: list, **kwargs: Any):
        """Mock async stream."""
        response = await self.ainvoke(messages, **kwargs)
        words = response.content.split()

        for word in words:
            await asyncio.sleep(0.01)
            yield MockAIMessageChunk(content=word + " ")

    @property
    def call_count(self) -> int:
        """Количество вызовов."""
        return self._call_count

    @property
    def last_messages(self) -> list[Any]:
        """Последние переданные сообщения."""
        return self._last_messages


class MockLLMProvider:
    """Mock LLM провайдер для тестов."""

    def __init__(
        self,
        responses: dict[str, str] | None = None,
        should_fail: bool = False,
        fail_error: Exception | None = None,
    ) -> None:
        """
        Инициализация mock провайдера.

        Args:
            responses: Словарь ответов {pattern: response}
            should_fail: Если True, вызовы будут падать
            fail_error: Исключение для выброса при should_fail
        """
        self._responses = responses or {}
        self._should_fail = should_fail
        self._fail_error = fail_error or Exception("Mock LLM failure")
        self._model = MockChatModel(responses)

    @property
    def model(self) -> MockChatModel:
        """Получить mock модель."""
        if self._should_fail:
            raise self._fail_error
        return self._model

    async def ainvoke_with_retry(self, messages: list, **kwargs: Any) -> MockAIMessage:
        """Mock invoke с retry."""
        if self._should_fail:
            raise self._fail_error
        return await self._model.ainvoke(messages, **kwargs)


def create_mock_llm_response(content: str) -> MagicMock:
    """
    Создать mock ответ LLM.

    Args:
        content: Содержимое ответа

    Returns:
        MagicMock с атрибутом content
    """
    response = MagicMock()
    response.content = content
    response.type = "ai"
    return response


def create_mock_llm_provider(
    responses: dict[str, str] | None = None,
) -> MockLLMProvider:
    """
    Создать mock LLM провайдер.

    Args:
        responses: Словарь {pattern: response} для matching

    Returns:
        MockLLMProvider instance

    Example:
        provider = create_mock_llm_provider({
            "маркетинг": "marketing",
            "поддержка": "support",
        })
    """
    return MockLLMProvider(responses=responses)


def create_failing_llm_provider(error: Exception | None = None) -> MockLLMProvider:
    """
    Создать mock LLM провайдер который всегда падает.

    Args:
        error: Исключение для выброса

    Returns:
        MockLLMProvider который падает при вызовах
    """
    return MockLLMProvider(should_fail=True, fail_error=error)
