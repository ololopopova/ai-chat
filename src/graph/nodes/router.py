"""Router node — определение домена и маршрутизация запроса."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from src.core.logging import get_logger

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
from src.graph.prompts import ROUTER_PROMPT
from src.graph.state import ChatState, Route, Stage
from src.llm import get_llm_provider
from src.llm.utils import extract_text_from_response

logger = get_logger(__name__)


def _get_domains_list() -> str:
    """Получить список доменов для промпта."""
    # TODO: Загружать из БД или конфига
    # Пока используем hardcoded список
    domains = [
        {
            "slug": "marketing",
            "name": "Маркетинг и реклама",
            "description": "Вопросы о маркетинговых стратегиях",
        },
        {
            "slug": "product",
            "name": "Продуктовая разработка",
            "description": "Вопросы о продуктовом менеджменте",
        },
        {
            "slug": "support",
            "name": "Техническая поддержка",
            "description": "FAQ и решение проблем",
        },
    ]

    lines = []
    for d in domains:
        lines.append(f"- {d['slug']}: {d['name']} — {d['description']}")
    return "\n".join(lines)


def _parse_router_response(response: str) -> tuple[Route, str | None, list[str] | None]:
    """
    Парсинг ответа роутера.

    Returns:
        (route, domain, matched_domains)
    """
    response = response.strip().lower()

    # Убираем возможные кавычки
    response = response.strip("\"'")

    if response == "clarify":
        return Route.CLARIFY, None, None
    elif response == "off_topic":
        return Route.OFF_TOPIC, None, None
    else:
        # Считаем, что это slug домена
        return Route.GENERATE, response, [response]


async def router_node(state: ChatState) -> dict[str, Any]:
    """
    Узел маршрутизации запроса.

    Определяет домен вопроса и выбирает следующий узел:
    - generate: вопрос в рамках домена
    - clarify: нужно уточнение (несколько доменов)
    - off_topic: вопрос вне всех доменов

    Args:
        state: Текущее состояние графа

    Returns:
        Обновление состояния с route, domain и stage
    """
    messages = state.get("messages", [])
    if not messages:
        logger.warning("Router received empty messages")
        return {
            "route": Route.OFF_TOPIC,
            "stage": Stage.ROUTER,
        }

    # Получаем последнее сообщение пользователя
    last_message = messages[-1]
    user_content = last_message.content if hasattr(last_message, "content") else str(last_message)

    logger.info(
        "Router processing message",
        extra={"message_preview": user_content[:50] if user_content else "empty"},
    )

    # Формируем chain: prompt | model
    domains_list = _get_domains_list()
    provider = get_llm_provider()
    model = cast("BaseChatModel", provider.model)
    chain = ROUTER_PROMPT | model

    try:
        response = await chain.ainvoke(
            {
                "domains_list": domains_list,
                "input": user_content,
            }
        )
        # GPT-5.x возвращает content как список блоков, извлекаем текст
        raw_content = response.content if hasattr(response, "content") else response
        response_text = extract_text_from_response(raw_content)

        route, domain, matched_domains = _parse_router_response(response_text)

        logger.info(
            "Router decision",
            extra={
                "route": route.value,
                "domain": domain,
                "response": response_text,
            },
        )

        return {
            "route": route,
            "domain": domain,
            "matched_domains": matched_domains,
            "stage": Stage.ROUTER,
        }

    except Exception as e:
        logger.exception("Router error", extra={"error": str(e)})
        # При ошибке — off_topic
        return {
            "route": Route.OFF_TOPIC,
            "stage": Stage.ROUTER,
        }
