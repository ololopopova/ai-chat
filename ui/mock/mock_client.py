"""Mock API клиент для имитации backend без реального соединения."""

from __future__ import annotations

import asyncio
import random
import uuid
from typing import TYPE_CHECKING, ClassVar

from ui.models.events import (
    CompleteEvent,
    ErrorEvent,
    EventType,
    ProgressEvent,
    StageEvent,
    StageName,
    StreamEvent,
    TokenEvent,
    ToolEndEvent,
    ToolStartEvent,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator


class MockApiClient:
    """
    Mock клиент для имитации стриминга событий от backend.

    Реализует 4 сценария:
    1. Обычный RAG ответ
    2. Ответ с инструментом (генерация баннера)
    3. Ошибка
    4. Off-topic ответ
    """

    # Ключевые слова для определения сценария
    BANNER_KEYWORDS: ClassVar[list[str]] = ["баннер", "banner", "картинк", "изображ"]
    ERROR_KEYWORDS: ClassVar[list[str]] = ["ошибк", "error", "сломай"]
    OFFTOPIC_KEYWORDS: ClassVar[list[str]] = ["погода", "weather", "анекдот", "joke"]

    # Тестовые ответы
    RAG_RESPONSES: ClassVar[list[str]] = [
        "Согласно нашей документации, для создания эффективной маркетинговой кампании "
        "необходимо определить целевую аудиторию, выбрать каналы продвижения и "
        "разработать ключевые сообщения. Важно также установить KPI и регулярно "
        "отслеживать результаты.",
        "Продуктовая разработка включает несколько ключевых этапов: исследование "
        "рынка, формирование гипотез, создание прототипа, тестирование с пользователями "
        "и итеративное улучшение. Рекомендуется использовать методологию Agile.",
        "Техническая поддержка рекомендует в первую очередь проверить подключение "
        "к сети, очистить кэш приложения и убедиться, что используется актуальная "
        "версия. Если проблема сохраняется, обратитесь в службу поддержки.",
    ]

    BANNER_RESPONSE: ClassVar[str] = (
        "Готово! Я создал для вас рекламный баннер. "
        "На нём размещён яркий фон с градиентом, ваш логотип и привлекательный текст. "
        "Баннер оптимизирован для социальных сетей."
    )

    OFFTOPIC_RESPONSE: ClassVar[str] = (
        "Извините, я могу помочь только с вопросами о маркетинге, "
        "продуктовой разработке и технической поддержке. "
        "Пожалуйста, переформулируйте ваш вопрос в рамках этих тем."
    )

    # Тестовое изображение баннера
    MOCK_BANNER_URL: ClassVar[str] = (
        "https://placehold.co/1200x628/6366f1/ffffff?text=AI+Generated+Banner"
    )

    def __init__(self) -> None:
        """Инициализация mock клиента."""
        self._current_thread_id: str | None = None

    def create_thread(self) -> str:
        """
        Создать новый thread (сессию диалога).

        Returns:
            Уникальный идентификатор thread
        """
        self._current_thread_id = str(uuid.uuid4())
        return self._current_thread_id

    @property
    def thread_id(self) -> str | None:
        """Текущий thread_id."""
        return self._current_thread_id

    def _detect_scenario(self, message: str) -> str:
        """
        Определить сценарий ответа по содержимому сообщения.

        Args:
            message: Текст сообщения пользователя

        Returns:
            Название сценария: 'banner', 'error', 'offtopic', 'rag'
        """
        message_lower = message.lower()

        if any(kw in message_lower for kw in self.BANNER_KEYWORDS):
            return "banner"
        if any(kw in message_lower for kw in self.ERROR_KEYWORDS):
            return "error"
        if any(kw in message_lower for kw in self.OFFTOPIC_KEYWORDS):
            return "offtopic"
        return "rag"

    async def _stream_tokens(self, text: str) -> AsyncIterator[TokenEvent]:
        """
        Стриминг текста по токенам (словам).

        Args:
            text: Текст для стриминга

        Yields:
            TokenEvent для каждого токена
        """
        words = text.split()
        for i, word in enumerate(words):
            # Добавляем пробел перед словом (кроме первого)
            token = f" {word}" if i > 0 else word
            yield TokenEvent(type=EventType.TOKEN, content=token)
            # Случайная задержка для реалистичности
            await asyncio.sleep(random.uniform(0.02, 0.05))

    async def _scenario_rag(self) -> AsyncIterator[StreamEvent]:
        """
        Сценарий обычного RAG ответа.

        Yields:
            События: stage -> stage -> stage -> tokens -> complete
        """
        # Стадия: определение темы
        yield StageEvent(
            type=EventType.STAGE,
            stage_name=StageName.ROUTER,
            message="Анализирую запрос...",
        )
        await asyncio.sleep(0.3)

        # Стадия: поиск информации
        yield StageEvent(
            type=EventType.STAGE,
            stage_name=StageName.RETRIEVE,
            message="Ищу релевантную информацию...",
        )
        await asyncio.sleep(0.5)

        # Стадия: генерация ответа
        yield StageEvent(
            type=EventType.STAGE,
            stage_name=StageName.GENERATE,
            message="Формирую ответ...",
        )
        await asyncio.sleep(0.2)

        # Стриминг ответа
        response = random.choice(self.RAG_RESPONSES)
        async for token_event in self._stream_tokens(response):
            yield token_event

        # Завершение
        yield CompleteEvent(
            type=EventType.COMPLETE,
            final_response=response,
        )

    async def _scenario_banner(self) -> AsyncIterator[StreamEvent]:
        """
        Сценарий с генерацией баннера.

        Yields:
            События: stage -> stage -> tool_start -> progress... -> tool_end -> tokens -> complete
        """
        job_id = str(uuid.uuid4())

        # Стадия: определение темы
        yield StageEvent(
            type=EventType.STAGE,
            stage_name=StageName.ROUTER,
            message="Анализирую запрос...",
        )
        await asyncio.sleep(0.3)

        # Стадия: выбор инструмента
        yield StageEvent(
            type=EventType.STAGE,
            stage_name=StageName.TOOL_SELECT,
            message="Выбираю инструмент для задачи...",
        )
        await asyncio.sleep(0.4)

        # Начало работы инструмента
        yield ToolStartEvent(
            type=EventType.TOOL_START,
            tool_name="banner.generate",
            tool_input={"format": "social", "style": "modern"},
        )
        await asyncio.sleep(0.2)

        # Прогресс генерации
        progress_steps = [
            (10, "Подготовка..."),
            (30, "Генерация фона..."),
            (60, "Добавление текста..."),
            (90, "Финализация..."),
        ]

        for progress, step in progress_steps:
            yield ProgressEvent(
                type=EventType.PROGRESS,
                job_id=job_id,
                progress=progress,
                current_step=step,
            )
            await asyncio.sleep(random.uniform(0.4, 0.8))

        # Завершение инструмента
        yield ToolEndEvent(
            type=EventType.TOOL_END,
            tool_name="banner.generate",
            success=True,
            result="Баннер успешно создан",
            asset_url=self.MOCK_BANNER_URL,
        )
        await asyncio.sleep(0.2)

        # Стриминг описания результата
        async for token_event in self._stream_tokens(self.BANNER_RESPONSE):
            yield token_event

        # Завершение
        yield CompleteEvent(
            type=EventType.COMPLETE,
            final_response=self.BANNER_RESPONSE,
            asset_url=self.MOCK_BANNER_URL,
        )

    async def _scenario_error(self) -> AsyncIterator[StreamEvent]:
        """
        Сценарий с ошибкой.

        Yields:
            События: stage -> error
        """
        # Стадия: определение темы
        yield StageEvent(
            type=EventType.STAGE,
            stage_name=StageName.ROUTER,
            message="Анализирую запрос...",
        )
        await asyncio.sleep(0.3)

        # Ошибка
        yield ErrorEvent(
            type=EventType.ERROR,
            message="Произошла ошибка при обработке запроса. Попробуйте позже.",
            code="PROCESSING_ERROR",
        )

    async def _scenario_offtopic(self) -> AsyncIterator[StreamEvent]:
        """
        Сценарий off-topic ответа.

        Yields:
            События: stage -> tokens -> complete
        """
        # Стадия: определение темы
        yield StageEvent(
            type=EventType.STAGE,
            stage_name=StageName.ROUTER,
            message="Анализирую запрос...",
        )
        await asyncio.sleep(0.3)

        # Стриминг ответа
        async for token_event in self._stream_tokens(self.OFFTOPIC_RESPONSE):
            yield token_event

        # Завершение
        yield CompleteEvent(
            type=EventType.COMPLETE,
            final_response=self.OFFTOPIC_RESPONSE,
        )

    async def send_message(self, message: str) -> AsyncIterator[StreamEvent]:
        """
        Отправить сообщение и получить поток событий (асинхронно).

        Args:
            message: Текст сообщения пользователя

        Yields:
            StreamEvent события от "backend"
        """
        scenario = self._detect_scenario(message)

        match scenario:
            case "banner":
                async for event in self._scenario_banner():
                    yield event
            case "error":
                async for event in self._scenario_error():
                    yield event
            case "offtopic":
                async for event in self._scenario_offtopic():
                    yield event
            case _:
                async for event in self._scenario_rag():
                    yield event

    def send_message_sync(self, message: str) -> Iterator[StreamEvent]:
        """
        Отправить сообщение и получить поток событий (синхронно).

        Args:
            message: Текст сообщения пользователя

        Yields:
            StreamEvent события от "backend"
        """
        # Для mock клиента используем asyncio.run для каждого сценария
        scenario = self._detect_scenario(message)

        async def collect_events() -> list[StreamEvent]:
            events: list[StreamEvent] = []
            match scenario:
                case "banner":
                    async for event in self._scenario_banner():
                        events.append(event)
                case "error":
                    async for event in self._scenario_error():
                        events.append(event)
                case "offtopic":
                    async for event in self._scenario_offtopic():
                        events.append(event)
                case _:
                    async for event in self._scenario_rag():
                        events.append(event)
            return events

        events = asyncio.run(collect_events())
        yield from events
