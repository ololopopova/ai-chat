"""Репозиторий для работы с чанками знаний.

Реализует CRUD и методы поиска (FTS + Vector) для Chunk модели.
"""

import uuid
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.chunk import EMBEDDING_DIMENSION, Chunk
from src.repositories.base import BaseRepository


class ChunkRepository(BaseRepository[Chunk]):
    """
    Репозиторий для работы с фрагментами знаний.

    Расширяет BaseRepository методами для:
    - Полнотекстового поиска (FTS)
    - Векторного поиска (pgvector)
    - Гибридного поиска
    - Batch операций
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализировать репозиторий.

        Args:
            session: AsyncSession для работы с БД.
        """
        super().__init__(Chunk, session)

    async def get_by_domain(
        self,
        domain_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Chunk]:
        """
        Получить чанки по домену.

        Args:
            domain_id: UUID домена.
            skip: Количество записей для пропуска.
            limit: Максимальное количество записей.

        Returns:
            Список чанков, отсортированных по chunk_index.
        """
        stmt = (
            select(Chunk)
            .where(Chunk.domain_id == domain_id)
            .order_by(Chunk.chunk_index)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_fts(
        self,
        query: str,
        *,
        domain_id: uuid.UUID | None = None,
        limit: int = 10,
    ) -> list[tuple[Chunk, float]]:
        """
        Полнотекстовый поиск по чанкам.

        Args:
            query: Поисковый запрос.
            domain_id: Опциональный фильтр по домену.
            limit: Максимальное количество результатов.

        Returns:
            Список кортежей (Chunk, rank) отсортированных по релевантности.
        """
        # Создаём tsquery для русского и английского языков
        tsquery = func.plainto_tsquery("russian", query)

        # Вычисляем ранг
        rank = func.ts_rank(Chunk.content_tsv, tsquery)

        # Строим запрос
        stmt = (
            select(Chunk, rank.label("rank"))
            .where(Chunk.content_tsv.op("@@")(tsquery))
            .order_by(rank.desc())
            .limit(limit)
        )

        # Фильтр по домену
        if domain_id is not None:
            stmt = stmt.where(Chunk.domain_id == domain_id)

        result = await self.session.execute(stmt)
        return [(row.Chunk, row.rank) for row in result.all()]

    async def search_vector(
        self,
        embedding: list[float],
        *,
        domain_id: uuid.UUID | None = None,
        limit: int = 10,
        threshold: float | None = None,
    ) -> list[tuple[Chunk, float]]:
        """
        Векторный поиск по чанкам (cosine similarity).

        Args:
            embedding: Вектор запроса (1536 dims для OpenAI).
            domain_id: Опциональный фильтр по домену.
            limit: Максимальное количество результатов.
            threshold: Минимальный порог схожести (0-1).

        Returns:
            Список кортежей (Chunk, distance) отсортированных по близости.
            Меньшее значение distance = большая схожесть.
        """
        if len(embedding) != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSION}, "
                f"got {len(embedding)}"
            )

        # Cosine distance (меньше = лучше)
        distance = Chunk.embedding.cosine_distance(embedding)

        # Строим запрос
        stmt = (
            select(Chunk, distance.label("distance"))
            .where(Chunk.embedding.is_not(None))
            .order_by(distance)
            .limit(limit)
        )

        # Фильтр по домену
        if domain_id is not None:
            stmt = stmt.where(Chunk.domain_id == domain_id)

        # Фильтр по порогу (cosine distance = 1 - similarity)
        if threshold is not None:
            max_distance = 1.0 - threshold
            stmt = stmt.where(distance <= max_distance)

        result = await self.session.execute(stmt)
        return [(row.Chunk, row.distance) for row in result.all()]

    async def create_chunk(
        self,
        *,
        domain_id: uuid.UUID,
        content: str,
        chunk_index: int = 0,
        embedding: list[float] | None = None,
        chunk_metadata: dict[str, Any] | None = None,
    ) -> Chunk:
        """
        Создать новый чанк.

        Args:
            domain_id: UUID домена.
            content: Текст фрагмента.
            chunk_index: Порядковый номер.
            embedding: Векторное представление.
            chunk_metadata: Дополнительные данные.

        Returns:
            Созданный чанк.
        """
        return await self.create(
            domain_id=domain_id,
            content=content,
            chunk_index=chunk_index,
            embedding=embedding,
            chunk_metadata=chunk_metadata,
        )

    async def create_batch(
        self,
        chunks_data: list[dict[str, Any]],
    ) -> int:
        """
        Создать множество чанков за одну операцию.

        Args:
            chunks_data: Список словарей с данными чанков.
                Каждый словарь должен содержать:
                - domain_id: UUID
                - content: str
                - chunk_index: int (опционально)
                - embedding: list[float] (опционально)
                - metadata: dict (опционально)

        Returns:
            Количество созданных чанков.
        """
        if not chunks_data:
            return 0

        chunks = [Chunk(**data) for data in chunks_data]
        self.session.add_all(chunks)
        await self.session.flush()

        return len(chunks)

    async def delete_by_domain(self, domain_id: uuid.UUID) -> int:
        """
        Удалить все чанки домена.

        Args:
            domain_id: UUID домена.

        Returns:
            Количество удалённых чанков.
        """
        stmt = delete(Chunk).where(Chunk.domain_id == domain_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return int(result.rowcount or 0)  # type: ignore[attr-defined]

    async def count_by_domain(self, domain_id: uuid.UUID) -> int:
        """
        Подсчитать количество чанков в домене.

        Args:
            domain_id: UUID домена.

        Returns:
            Количество чанков.
        """
        stmt = select(func.count()).where(Chunk.domain_id == domain_id)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def update_embedding(
        self,
        id: uuid.UUID,
        embedding: list[float],
    ) -> Chunk | None:
        """
        Обновить embedding чанка.

        Args:
            id: UUID чанка.
            embedding: Новый вектор.

        Returns:
            Обновлённый чанк или None.
        """
        return await self.update(id, embedding=embedding)

    async def get_without_embedding(
        self,
        *,
        domain_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> list[Chunk]:
        """
        Получить чанки без embedding (для индексации).

        Args:
            domain_id: Опциональный фильтр по домену.
            limit: Максимальное количество результатов.

        Returns:
            Список чанков без embedding.
        """
        stmt = (
            select(Chunk).where(Chunk.embedding.is_(None)).order_by(Chunk.created_at).limit(limit)
        )

        if domain_id is not None:
            stmt = stmt.where(Chunk.domain_id == domain_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
