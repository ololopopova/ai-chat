"""Off-topic node — ответ на вопросы вне доменов."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from src.core.logging import get_logger
from src.graph.state import ChatState, Stage
from src.graph.templates import OFF_TOPIC_MESSAGE

logger = get_logger(__name__)


def _get_available_domains_text() -> str:
    """Получить текст со списком доступных доменов."""
    # TODO: Загружать из БД
    domains = [
        ("Маркетинг и реклама", "стратегии, кампании, брендинг"),
        ("Продуктовая разработка", "менеджмент, roadmap, фичи"),
        ("Техническая поддержка", "FAQ, решение проблем"),
    ]

    lines = [f"• {name} — {desc}" for name, desc in domains]
    return "\n".join(lines)


async def off_topic_node(state: ChatState) -> dict[str, Any]:
    """
    Узел обработки off-topic запросов.

    Мягко отказывает пользователю и предлагает
    переформулировать вопрос в рамках доступных тем.

    Args:
        state: Текущее состояние графа

    Returns:
        Обновление состояния с off-topic сообщением
    """
    messages = state.get("messages", [])

    # Логируем off-topic запрос для аналитики
    if messages:
        last_message = messages[-1]
        content = last_message.content if hasattr(last_message, "content") else str(last_message)
        logger.info(
            "Off-topic request",
            extra={"message_preview": content[:100] if content else "empty"},
        )

    domains_list = _get_available_domains_text()
    response = OFF_TOPIC_MESSAGE.format(domains_list=domains_list)

    return {
        "messages": [AIMessage(content=response)],
        "stage": Stage.OFF_TOPIC,
    }
