"""Модель Domain — домены знаний.

Домен представляет тематическую область, привязанную к Google Doc.
Используется для маршрутизации вопросов и RAG-поиска.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.chunk import Chunk


class Domain(Base, TimestampMixin):
    """
    Модель домена знаний.

    Attributes:
        id: UUID первичный ключ.
        name: Название домена (например, "Маркетинг и реклама").
        slug: URL-friendly идентификатор (например, "marketing").
        description: Описание домена.
        google_doc_url: Ссылка на Google Doc с базой знаний.
        is_active: Флаг активности домена.
        created_at: Время создания.
        updated_at: Время последнего обновления.
        chunks: Связанные фрагменты знаний.
    """

    # Основные поля
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Название домена",
    )

    slug: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-friendly идентификатор",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Описание домена",
    )

    google_doc_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Ссылка на Google Doc",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Активен ли домен",
    )

    # Relationships
    chunks: Mapped[list["Chunk"]] = relationship(
        "Chunk",
        back_populates="domain",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Timestamps из TimestampMixin
    updated_at: Mapped[datetime]

    # Индексы
    __table_args__ = (Index("ix_domains_is_active", "is_active"),)

    def __repr__(self) -> str:
        """Строковое представление домена."""
        return f"<Domain(id={self.id}, slug='{self.slug}', name='{self.name}')>"
