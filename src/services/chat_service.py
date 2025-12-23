"""ChatService — оркестрация чата с LangGraph и стримингом событий."""

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

    pass


class StageEvent(ChatEvent):
    """Событие смены стадии обработки."""

    def __init__(self, stage: str, status: str = "active", message: str | None = None) -> None:
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


# Маппинг стадий для UI
STAGE_MESSAGES: dict[Stage, str] = {
    Stage.ROUTER: "Определяю тему запроса...",
    Stage.CLARIFY: "Нужно уточнение...",
    Stage.RETRIEVE: "Ищу информацию...",
    Stage.GENERATE: "Формирую ответ...",
    Stage.OFF_TOPIC: "Вопрос вне темы...",
}


class ChatService:
    """
    Сервис обработки чат-сообщений.

    Оркестрирует LangGraph и предоставляет стриминг событий
    для WebSocket клиентов.

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
            # Stage: Router
            yield StageEvent(
                stage=Stage.ROUTER.value,
                status="active",
                message=STAGE_MESSAGES[Stage.ROUTER],
            )

            full_response = ""
            current_stage: Stage | None = None
            current_node: str | None = None  # Отслеживаем текущий узел

            # Используем astream_events для реального стриминга токенов
            async for event in self.graph.astream_events(
                input_state,
                config,
                version="v2",
            ):
                event_kind = event.get("event", "")
                event_name = event.get("name", "")
                event_data = event.get("data", {})

                # Обновление стадии при входе в узел
                if event_kind == "on_chain_start" and event_name in (
                    "router",
                    "generate",
                    "clarify",
                    "off_topic",
                ):
                    current_node = event_name

                    # Определяем стадию по имени узла
                    stage_map = {
                        "router": Stage.ROUTER,
                        "generate": Stage.GENERATE,
                        "clarify": Stage.CLARIFY,
                        "off_topic": Stage.OFF_TOPIC,
                    }
                    new_stage = stage_map.get(event_name)
                    if new_stage and new_stage != current_stage:
                        # Завершаем предыдущую
                        if current_stage:
                            prev_value = (
                                current_stage.value
                                if isinstance(current_stage, Stage)
                                else str(current_stage)
                            )
                            yield StageEvent(stage=prev_value, status="completed")

                        current_stage = new_stage
                        stage_message = STAGE_MESSAGES.get(current_stage, "Обработка...")
                        yield StageEvent(
                            stage=current_stage.value,
                            status="active",
                            message=stage_message,
                        )

                # Стриминг токенов от LLM — ТОЛЬКО от generate node!
                elif event_kind == "on_chat_model_stream" and current_node == "generate":
                    chunk = event_data.get("chunk")
                    if chunk and hasattr(chunk, "content"):
                        content = chunk.content
                        if isinstance(content, str) and content:
                            full_response += content
                            yield TokenEvent(token=content)
                        elif isinstance(content, list):
                            # GPT-5.x формат
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    text = block.get("text", "")
                                    if text:
                                        full_response += text
                                        yield TokenEvent(token=text)

                # Завершение узла — для clarify/off_topic отправляем ответ
                elif event_kind == "on_chain_end" and event_name in ("clarify", "off_topic"):
                    output = event_data.get("output", {})
                    messages = output.get("messages", [])
                    if messages:
                        last_msg = messages[-1]
                        if hasattr(last_msg, "content"):
                            from src.llm.utils import extract_text_from_response

                            content = extract_text_from_response(last_msg.content)
                            if content and not full_response:
                                full_response = content
                                # Стримим посимвольно для эффекта печати
                                for char in content:
                                    yield TokenEvent(token=char)

                # Финальное сообщение (fallback)
                elif event_kind == "on_chain_end" and event_name == "LangGraph":
                    output = event_data.get("output", {})
                    messages = output.get("messages", [])
                    if messages and not full_response:
                        last_msg = messages[-1]
                        if hasattr(last_msg, "content"):
                            from src.llm.utils import extract_text_from_response

                            content = extract_text_from_response(last_msg.content)
                            if content:
                                full_response = content
                                for char in content:
                                    yield TokenEvent(token=char)

            # Завершаем текущую стадию
            if current_stage:
                final_stage_value = (
                    current_stage.value if isinstance(current_stage, Stage) else str(current_stage)
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
