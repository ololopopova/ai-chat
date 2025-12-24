"""Состояние графа для ReAct Main Agent."""

from enum import Enum
from typing import Annotated, Any

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class Stage(str, Enum):
    """
    Стадии обработки для UI timeline.

    ReAct агент управляет своим циклом, но мы можем отслеживать
    ключевые этапы для отображения прогресса пользователю.
    """

    THINKING = "thinking"  # Агент анализирует запрос
    CALLING_TOOL = "calling_tool"  # Вызывает инструмент (субагента)
    SYNTHESIZING = "synthesizing"  # Формирует финальный ответ
    COMPLETE = "complete"  # Завершил работу


class ChatState(TypedDict, total=False):
    """
    Состояние ReAct Main Agent.

    Используем минималистичное состояние, т.к. create_react_agent
    сам управляет циклом вызова tools и генерации ответов.

    Attributes:
        messages: История сообщений с add_messages reducer.
                  Автоматически объединяет новые сообщения с существующими.
                  Включает user messages, AI responses, tool calls и tool results.
        stage: Текущий этап обработки для UI timeline (опционально).
    """

    # Обязательное поле с reducer для автоматического merge сообщений
    # ReAct агент добавляет сюда: AIMessage, ToolMessage, HumanMessage
    messages: Annotated[list[Any], add_messages]

    # Опциональное поле для отслеживания стадии (для UI)
    stage: Stage | None
