"""Схемы для domains endpoints."""

from pydantic import BaseModel, Field


class DomainInfo(BaseModel):
    """Информация о домене."""

    id: str
    name: str
    description: str
    is_active: bool = True

    model_config = {"json_schema_extra": {
        "example": {
            "id": "marketing",
            "name": "Маркетинг",
            "description": "Вопросы о рекламных кампаниях и продвижении",
            "is_active": True,
        }
    }}


class DomainsResponse(BaseModel):
    """Ответ со списком доменов."""

    domains: list[DomainInfo] = Field(default_factory=list)
    total: int = 0

    model_config = {"json_schema_extra": {
        "example": {
            "domains": [
                {
                    "id": "marketing",
                    "name": "Маркетинг",
                    "description": "Вопросы о рекламных кампаниях",
                    "is_active": True,
                },
                {
                    "id": "support",
                    "name": "Поддержка",
                    "description": "Техническая поддержка",
                    "is_active": True,
                },
            ],
            "total": 2,
        }
    }}

