"""Абстракция для обработчиков сообщений."""

from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

from src.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from ui.models.events import StreamEvent

logger = get_logger(__name__)


class MessageHandler(ABC):
    """
    Абстрактный базовый класс для обработчиков сообщений.

    Определяет интерфейс, который должны реализовать все обработчики
    сообщений (EchoHandler, LLMHandler, RAGHandler и т.д.)
    """

    @abstractmethod
    def process_message(self, message: str, thread_id: str) -> AsyncIterator[StreamEvent]:
        """
        Обработать сообщение и сгенерировать поток событий.

        Args:
            message: Текст сообщения пользователя
            thread_id: ID сессии диалога

        Yields:
            StreamEvent события для отправки клиенту
        """
        ...


class EchoMessageHandler(MessageHandler):
    """
    Временный обработчик сообщений в режиме echo.

    Имитирует работу LLM + RAG системы для демонстрации
    стриминга событий. Будет заменён на реальную интеграцию
    в Phase 4-5.
    """

    # Тестовые ответы для демонстрации
    ECHO_RESPONSES: ClassVar[list[str]] = [
        "Спасибо за ваше сообщение! Это демонстрационный режим echo. "
        "В будущих версиях здесь будет интеграция с LLM и RAG системой.",
        "Ваш запрос получен. Сейчас система работает в режиме эхо-ответов. "
        "Полноценная обработка будет добавлена позже.",
        "Привет! Я пока работаю в тестовом режиме и могу только "
        "демонстрировать поток событий. Скоро здесь появится настоящий ИИ!",
    ]

    async def process_message(self, message: str, thread_id: str) -> AsyncIterator[StreamEvent]:
        """
        Обработать сообщение и сгенерировать поток событий.

        Args:
            message: Текст сообщения пользователя
            thread_id: ID сессии диалога

        Yields:
            StreamEvent события для отправки клиенту
        """
        # Импортируем здесь, чтобы избежать циклических импортов
        from ui.models.events import (
            CompleteEvent,
            EventType,
            StageEvent,
            StageName,
            TokenEvent,
        )

        logger.info(
            "Processing message",
            extra={"thread_id": thread_id[:8], "message_length": len(message)},
        )

        # Stage: Router
        yield StageEvent(
            type=EventType.STAGE,
            stage_name=StageName.ROUTER,
            message="Анализирую запрос...",
        )
        await asyncio.sleep(0.3)

        # Stage: Generate
        yield StageEvent(
            type=EventType.STAGE,
            stage_name=StageName.GENERATE,
            message="Формирую ответ...",
        )
        await asyncio.sleep(0.2)

        # Выбираем ответ
        response = random.choice(self.ECHO_RESPONSES)

        # Добавляем эхо пользовательского сообщения
        full_response = f"{response}\n\nВаше сообщение: «{message}»"

        # Стриминг токенов (посимвольно для демонстрации)
        for char in full_response:
            yield TokenEvent(
                type=EventType.TOKEN,
                content=char,
            )
            # Небольшая задержка для реалистичности
            await asyncio.sleep(random.uniform(0.01, 0.03))

        # Complete
        yield CompleteEvent(
            type=EventType.COMPLETE,
            final_response=full_response,
            asset_url=None,
        )

        logger.info(
            "Message processed",
            extra={"thread_id": thread_id[:8], "response_length": len(full_response)},
        )
