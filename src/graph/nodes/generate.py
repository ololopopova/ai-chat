"""Generate node — генерация ответа на основе знаний домена."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from langchain_core.messages import AIMessage, BaseMessage

from src.core.logging import get_logger

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
from src.graph.prompts import GENERATE_PROMPT
from src.graph.state import ChatState, Stage
from src.graph.templates import ERROR_GENERATION_FAILED, ERROR_NO_MESSAGE
from src.llm import get_llm_provider
from src.llm.utils import extract_text_from_response

logger = get_logger(__name__)


def _get_domain_context(domain: str | None) -> str:
    """Получить контекст для домена."""
    # TODO: Здесь будет RAG — поиск релевантных чанков
    # Пока возвращаем заглушку
    if not domain:
        return ""

    domain_contexts = {
        "marketing": "Ты эксперт по маркетингу и рекламе.",
        "product": "Ты эксперт по продуктовому менеджменту.",
        "support": "Ты специалист технической поддержки.",
    }

    return domain_contexts.get(domain, "")


async def generate_node(state: ChatState) -> dict[str, Any]:
    """
    Узел генерации ответа.

    Генерирует ответ на вопрос пользователя в контексте
    определённого домена.

    Args:
        state: Текущее состояние графа

    Returns:
        Обновление состояния с новым сообщением и stage
    """
    messages = state.get("messages", [])
    domain = state.get("domain")

    if not messages:
        logger.warning("Generate received empty messages")
        return {
            "messages": [AIMessage(content=ERROR_NO_MESSAGE)],
            "stage": Stage.GENERATE,
        }

    # Получаем последнее сообщение пользователя
    last_message = messages[-1]
    user_content = last_message.content if hasattr(last_message, "content") else str(last_message)

    logger.info(
        "Generating response",
        extra={
            "domain": domain,
            "message_preview": user_content[:50] if user_content else "empty",
        },
    )

    # Формируем chain: prompt | model
    context = _get_domain_context(domain)
    provider = get_llm_provider()
    model = cast("BaseChatModel", provider.model)
    chain = GENERATE_PROMPT | model

    # Собираем историю для MessagesPlaceholder
    history_limit = 10
    history: list[BaseMessage] = []
    for msg in messages[:-1][-history_limit:]:  # Все кроме последнего (input)
        if hasattr(msg, "type") and hasattr(msg, "content"):
            history.append(msg)

    try:
        response = await chain.ainvoke(
            {
                "domain": domain or "general",
                "context": context,
                "history": history,
                "input": user_content,
            }
        )
        # GPT-5.x возвращает content как список блоков, извлекаем текст
        raw_content = response.content if hasattr(response, "content") else response
        response_text = extract_text_from_response(raw_content)

        logger.info(
            "Response generated",
            extra={"response_length": len(response_text)},
        )

        return {
            "messages": [AIMessage(content=response_text)],
            "stage": Stage.GENERATE,
        }

    except Exception as e:
        logger.exception("Generate error", extra={"error": str(e)})
        return {
            "messages": [AIMessage(content=ERROR_GENERATION_FAILED)],
            "stage": Stage.GENERATE,
        }
