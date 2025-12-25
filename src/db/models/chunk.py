"""Модель Chunk — фрагменты знаний для RAG.

Chunk представляет смысловой фрагмент текста из Google Doc,
проиндексированный для полнотекстового и векторного поиска.
"""

import uuid
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Computed,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.domain import Domain


# Размерность embedding (OpenAI text-embedding-3-large с dimensions=1536)
# Примечание: pgvector имеет ограничение 2000 dims для индексов
# Поэтому используем 1536 вместо полных 3072
EMBEDDING_DIMENSION = 1536


class Chunk(Base):
    """
    Модель фрагмента знаний.

    Attributes:
        id: UUID первичный ключ.
        domain_id: Ссылка на домен.
        content: Текст фрагмента.
        content_tsv: Полнотекстовый индекс (generated column).
        embedding: Векторное представление (3072 dims для OpenAI text-embedding-3-large).
        chunk_index: Порядковый номер в документе.
        metadata: Дополнительные данные (заголовок секции и т.д.).
        created_at: Время создания.
        domain: Связанный домен.
    """

    # Ссылка на домен
    domain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("domains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID домена",
    )

    # Текст фрагмента
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Текст фрагмента",
    )

    # Полнотекстовый индекс (генерируется автоматически из content)
    # Используем русский и английский языки
    content_tsv: Mapped[Any] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('russian', content) || to_tsvector('english', content)",
            persisted=True,
        ),
        nullable=False,
        comment="Полнотекстовый индекс",
    )

    # Векторное представление (embedding)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIMENSION),
        nullable=True,  # Может быть None до генерации embedding
        comment="Векторное представление",
    )

    # Порядковый номер в документе
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Порядковый номер в документе",
    )

    # Дополнительные метаданные (chunk_metadata чтобы избежать конфликта с Base.metadata)
    chunk_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        comment="Дополнительные данные",
    )

    # Relationships
    domain: Mapped["Domain"] = relationship(
        "Domain",
        back_populates="chunks",
    )

    # Индексы
    __table_args__ = (
        # GIN индекс для полнотекстового поиска
        Index(
            "ix_chunks_content_tsv",
            "content_tsv",
            postgresql_using="gin",
        ),
        # HNSW индекс для векторного поиска (cosine distance)
        # m=16, ef_construction=64 — хороший баланс скорости и качества
        # Используем HNSW т.к. 1536 dims < 2000 (лимит pgvector)
        Index(
            "ix_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        # Индекс для сортировки по chunk_index
        Index("ix_chunks_domain_id_chunk_index", "domain_id", "chunk_index"),
    )

    def __repr__(self) -> str:
        """Строковое представление чанка."""
        content_preview = (
            self.content[:50] + "..." if len(self.content) > 50 else self.content
        )
        return f"<Chunk(id={self.id}, domain_id={self.domain_id}, content='{content_preview}')>"

    @property
    def has_embedding(self) -> bool:
        """Проверить, есть ли embedding."""
        return self.embedding is not None


def make_tsquery(query: str) -> Any:
    """
    Создать tsquery для полнотекстового поиска.

    Args:
        query: Поисковый запрос.

    Returns:
        SQLAlchemy expression для tsquery.
    """
    # Используем plainto_tsquery для простых запросов
    # и websearch_to_tsquery для поддержки операторов
    return func.plainto_tsquery("russian", query) | func.plainto_tsquery(
        "english", query
    )
