"""Endpoints для работы с агентами (бывшие домены)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_domains_config
from src.api.schemas.domain import DomainInfo, DomainsResponse
from src.core.logging import get_logger

router = APIRouter(prefix="/domains")
logger = get_logger(__name__)


@router.get(
    "",
    response_model=DomainsResponse,
    summary="Список агентов (доменов)",
    description=(
        "Получить список всех доступных специализированных агентов. "
        "API endpoint сохранил название /domains для обратной совместимости, "
        "но теперь возвращает информацию об агентах."
    ),
)
async def get_domains(
    domains_config: Annotated[dict[str, Any], Depends(get_domains_config)],
) -> DomainsResponse:
    """
    Получить список доступных агентов (субагентов Main Agent).

    Агенты загружаются из config/domains.yaml при старте сервера
    и кэшируются. Каждый агент — это специализированный инструмент
    с определённой областью знаний.

    Returns:
        DomainsResponse с информацией об агентах (совместимо со старым форматом)
    """
    try:
        # В новом формате агенты хранятся в ключе "agents"
        raw_agents = domains_config.get("agents", [])
        domains = []

        for agent_data in raw_agents:
            # Преобразуем агента в формат DomainInfo для обратной совместимости
            domain = DomainInfo(
                id=agent_data.get("id", ""),
                name=agent_data.get("name", ""),
                description=agent_data.get("description", ""),
                is_active=agent_data.get("enabled", True),
            )
            domains.append(domain)

        logger.info(f"Loaded {len(domains)} agents")

        return DomainsResponse(
            domains=domains,
            total=len(domains),
        )

    except Exception as e:
        logger.exception("Failed to load agents configuration")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load agents configuration: {e}",
        ) from e
