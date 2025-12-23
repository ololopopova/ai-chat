"""Clarify node — уточняющие вопросы при неоднозначности домена."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from src.core.logging import get_logger
from src.graph.state import ChatState, Stage
from src.graph.templates import CLARIFY_MESSAGE

logger = get_logger(__name__)


def _get_domain_names() -> dict[str, str]:
    """Получить названия доменов."""
    # TODO: Загружать из БД
    return {
        "marketing": "Маркетинг и реклама",
        "product": "Продуктовая разработка",
        "support": "Техническая поддержка",
    }


async def clarify_node(state: ChatState) -> dict[str, Any]:
    """
    Узел уточнения домена.

    Генерирует уточняющий вопрос, когда запрос может
    относиться к нескольким доменам.

    Args:
        state: Текущее состояние графа

    Returns:
        Обновление состояния с уточняющим сообщением
    """
    matched_domains = state.get("matched_domains", [])

    logger.info(
        "Generating clarification",
        extra={"matched_domains": matched_domains},
    )

    domain_names = _get_domain_names()

    # Формируем список опций
    if matched_domains:
        options_list = []
        for i, slug in enumerate(matched_domains, 1):
            name = domain_names.get(slug, slug)
            options_list.append(f"{i}. {name}")
        options = "\n".join(options_list)
    else:
        # Если нет конкретных доменов — показываем все
        options_list = [f"{i}. {name}" for i, name in enumerate(domain_names.values(), 1)]
        options = "\n".join(options_list)

    clarify_message = CLARIFY_MESSAGE.format(options=options)

    return {
        "messages": [AIMessage(content=clarify_message)],
        "stage": Stage.CLARIFY,
    }

