"""Endpoints для работы с доменами."""

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
    summary="Список доменов",
    description="Получить список всех доступных тематических доменов.",
)
async def get_domains(
    domains_config: Annotated[dict[str, Any], Depends(get_domains_config)],
) -> DomainsResponse:
    """
    Получить список доступных доменов.

    Домены загружаются из config/domains.yaml при старте сервера
    и кэшируются.
    """
    try:
        raw_domains = domains_config.get("domains", [])
        domains = []

        for domain_data in raw_domains:
            domain = DomainInfo(
                id=domain_data.get("id", ""),
                name=domain_data.get("name", ""),
                description=domain_data.get("description", ""),
                is_active=domain_data.get("enabled", True),
            )
            domains.append(domain)

        logger.info(f"Loaded {len(domains)} domains")

        return DomainsResponse(
            domains=domains,
            total=len(domains),
        )

    except Exception as e:
        logger.exception("Failed to load domains")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load domains configuration: {e}",
        ) from e

