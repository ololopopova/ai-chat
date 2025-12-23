"""Pydantic схемы для API endpoints."""

from src.api.schemas.chat import ChatMessageRequest, ErrorResponse
from src.api.schemas.domain import DomainInfo, DomainsResponse
from src.api.schemas.health import DependencyStatus, HealthResponse

__all__ = [
    "ChatMessageRequest",
    "DependencyStatus",
    "DomainInfo",
    "DomainsResponse",
    "ErrorResponse",
    "HealthResponse",
]
