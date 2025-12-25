"""ChatService — оркестрация ReAct Main Agent с LangGraph и стримингом событий."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage

from src.core.logging import get_logger
from src.graph.builder import build_chat_graph
from src.graph.state import Stage

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.graph.state import CompiledStateGraph

logger = get_logger(__name__)


class ChatEvent:
    """Базовый класс для событий чата."""

    def to_dict(self) -> dict[str, Any]:
        """Преобразовать в словарь для JSON."""
        raise NotImplementedError


class StageEvent(ChatEvent):
    """Событие смены стадии обработки."""

    def __init__(
        self, stage: str, status: str = "active", message: str | None = None
    ) -> None:
        self.type = "stage"
        self.stage = stage
        self.status = status
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        """Преобразовать в словарь для JSON."""
        return {
            "type": self.type,
            "stage_name": self.stage,
            "status": self.status,
            "message": self.message,
        }


class TokenEvent(ChatEvent):
    """Событие токена (стриминг ответа)."""

    def __init__(self, token: str) -> None:
        self.type = "token"
        self.token = token

    def to_dict(self) -> dict[str, Any]:
        """Преобразовать в словарь для JSON."""
        return {
            "type": self.type,
            "content": self.token,
        }


class CompleteEvent(ChatEvent):
    """Событие завершения обработки."""

    def __init__(self, response: str, thread_id: str) -> None:
        self.type = "complete"
        self.response = response
        self.thread_id = thread_id

    def to_dict(self) -> dict[str, Any]:
        """Преобразовать в словарь для JSON."""
        return {
            "type": self.type,
            "final_response": self.response,
            "thread_id": self.thread_id,
            "asset_url": None,
        }


class ErrorEvent(ChatEvent):
    """Событие ошибки."""

    def __init__(self, error: str, code: str = "GRAPH_ERROR") -> None:
        self.type = "error"
        self.error = error
        self.code = code

    def to_dict(self) -> dict[str, Any]:
        """Преобразовать в словарь для JSON."""
        return {
            "type": self.type,
            "message": self.error,
            "code": self.code,
        }


# Маппинг стадий для UI (ReAct архитектура)
STAGE_MESSAGES: dict[Stage, str] = {
    Stage.THINKING: "Анализирую запрос...",
    Stage.CALLING_TOOL: "Вызываю специалиста...",
    Stage.SYNTHESIZING: "Формирую ответ...",
    Stage.COMPLETE: "Готово",
}


class ChatService:
    """
    Сервис обработки чат-сообщений с ReAct Main Agent.

    Оркестрирует LangGraph ReAct агента и предоставляет стриминг событий
    для WebSocket клиентов.

    ReAct Agent сам управляет своим циклом:
    - Думает (анализ запроса)
    - Действует (вызов tools/субагентов)
    - Наблюдает (получение результатов)
    - Синтезирует (финальный ответ)

    Поддерживает:
    - Стриминг стадий (StageEvent) для timeline UI
    - Стриминг токенов (TokenEvent) для ответа
    - Персистентность состояния через checkpointer
    """

    def __init__(self, checkpointer: BaseCheckpointSaver[Any] | None = None) -> None:
        """
        Инициализация сервиса.

        Args:
            checkpointer: Checkpointer для персистентности.
                         Если None, состояние не сохраняется между вызовами.
        """
        self._checkpointer = checkpointer
        self._graph: CompiledStateGraph[Any] | None = None

    @property
    def graph(self) -> CompiledStateGraph[Any]:
        """Lazy-initialized граф."""
        if self._graph is None:
            self._graph = build_chat_graph(checkpointer=self._checkpointer)
        return self._graph

    async def process_message(
        self,
        message: str,
        thread_id: str,
    ) -> AsyncIterator[ChatEvent]:
        """
        Обработать сообщение пользователя со стримингом событий.

        Args:
            message: Текст сообщения пользователя
            thread_id: ID сессии диалога (для персистентности)

        Yields:
            ChatEvent события для отправки клиенту:
            - StageEvent: смена этапа обработки
            - TokenEvent: токен ответа (при стриминге LLM)
            - CompleteEvent: завершение обработки
            - ErrorEvent: ошибка

        Example:
            async with ChatService(checkpointer) as service:
                async for event in service.process_message("Привет", "thread-123"):
                    await websocket.send_json(event.to_dict())
        """
        logger.info(
            "Processing message",
            extra={
                "thread_id": thread_id[:8],
                "message_length": len(message),
            },
        )

        config: RunnableConfig = {
            "configurable": {
                "thread_id": thread_id,
            },
        }

        input_state = {
            "messages": [HumanMessage(content=message)],
        }

        try:
            # Stage: Thinking (начало обработки)
            yield StageEvent(
                stage=Stage.THINKING.value,
                status="active",
                message=STAGE_MESSAGES[Stage.THINKING],
            )

            full_response = ""
            current_stage: Stage | None = Stage.THINKING
            is_calling_tool = False

            # Используем astream_events для реального стриминга токенов
            async for event in self.graph.astream_events(
                input_state,
                config,
                version="v2",
            ):
                event_kind = event.get("event", "")
                event_name = event.get("name", "")
                event_data = event.get("data", {})

                # Обнаружение вызова tool (субагента)
                if event_kind == "on_tool_start":
                    tool_name = event_name
                    logger.debug(f"Tool called: {tool_name}")

                    # Переключаем стадию на CALLING_TOOL
                    if not is_calling_tool:
                        if current_stage:
                            yield StageEvent(
                                stage=current_stage.value, status="completed"
                            )

                        current_stage = Stage.CALLING_TOOL
                        is_calling_tool = True

                        # Красивые сообщения для разных агентов
                        tool_messages = {
                            "products_agent": "Консультируюсь со специалистом по продуктам...",
                            "compatibility_agent": "Проверяю сочетаемость...",
                            "marketing_agent": "Обращаюсь к маркетологу...",
                        }
                        message_text = tool_messages.get(
                            tool_name, STAGE_MESSAGES[Stage.CALLING_TOOL]
                        )

                        yield StageEvent(
                            stage=current_stage.value,
                            status="active",
                            message=message_text,
                        )

                # Tool завершил работу
                elif event_kind == "on_tool_end":
                    logger.debug(f"Tool completed: {event_name}")
                    # Остаёмся в CALLING_TOOL если есть ещё tools

                # Стриминг финального ответа от LLM
                elif event_kind == "on_chat_model_stream":
                    # Если начался стриминг финального ответа — переключаемся на SYNTHESIZING
                    if current_stage != Stage.SYNTHESIZING:
                        if current_stage:
                            yield StageEvent(
                                stage=current_stage.value, status="completed"
                            )

                        current_stage = Stage.SYNTHESIZING
                        yield StageEvent(
                            stage=current_stage.value,
                            status="active",
                            message=STAGE_MESSAGES[Stage.SYNTHESIZING],
                        )

                    chunk = event_data.get("chunk")
                    if chunk and hasattr(chunk, "content"):
                        content = chunk.content
                        if isinstance(content, str) and content:
                            full_response += content
                            yield TokenEvent(token=content)
                        elif isinstance(content, list):
                            # GPT-5.x формат с блоками
                            for block in content:
                                if (
                                    isinstance(block, dict)
                                    and block.get("type") == "text"
                                ):
                                    text = block.get("text", "")
                                    if text:
                                        full_response += text
                                        yield TokenEvent(token=text)

                # Финальное сообщение (fallback если не было стриминга)
                elif event_kind == "on_chain_end" and event_name == "LangGraph":
                    output_final: dict[str, Any] = event_data.get("output", {})
                    messages_final: list[Any] = output_final.get("messages", [])
                    if messages_final and not full_response:
                        last_msg = messages_final[-1]
                        if hasattr(last_msg, "content"):
                            from src.llm.utils import extract_text_from_response

                            content = extract_text_from_response(last_msg.content)
                            if content:
                                full_response = content
                                # Стримим посимвольно для эффекта печати
                                for char in content:
                                    yield TokenEvent(token=char)

            # Завершаем текущую стадию
            if current_stage:
                final_stage_value = (
                    current_stage.value
                    if isinstance(current_stage, Stage)
                    else str(current_stage)
                )
                yield StageEvent(
                    stage=final_stage_value,
                    status="completed",
                )

            # Отправляем complete
            yield CompleteEvent(
                response=full_response,
                thread_id=thread_id,
            )

            logger.info(
                "Message processed",
                extra={
                    "thread_id": thread_id[:8],
                    "response_length": len(full_response),
                },
            )

        except Exception as e:
            logger.exception(
                "Error processing message",
                extra={"thread_id": thread_id[:8], "error": str(e)},
            )
            yield ErrorEvent(
                error=str(e),
                code="GRAPH_ERROR",
            )

    async def astream_tokens(
        self,
        message: str,
        thread_id: str,
    ) -> AsyncIterator[str]:
        """
        Стриминг только токенов ответа (для простых use cases).

        Args:
            message: Текст сообщения
            thread_id: ID сессии

        Yields:
            Токены ответа
        """
        async for event in self.process_message(message, thread_id):
            if isinstance(event, TokenEvent):
                yield event.token

    async def __aenter__(self) -> ChatService:
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit."""
        # Cleanup если нужен
        pass
