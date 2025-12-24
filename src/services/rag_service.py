"""RAG Service — Hybrid Search (FTS + Vector).

Реализует поиск по базе знаний с объединением:
- Full-Text Search (PostgreSQL FTS)
- Vector Search (pgvector cosine similarity)
"""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from src.core.logging import get_logger
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.domain_repository import DomainRepository
from src.repositories.unit_of_work import UnitOfWork
from src.services.ingest.embedding_service import EmbeddingService

logger = get_logger(__name__)


@dataclass
class RAGResult:
    """
    Результат поиска по базе знаний.

    Attributes:
        chunk_id: UUID чанка.
        content: Текстовое содержимое чанка.
        header: Заголовок секции (из metadata).
        score: Итоговый score (0.0-1.0, выше = лучше).
        search_type: Тип поиска ("fts", "vector", "hybrid").
    """

    chunk_id: UUID
    content: str
    header: str | None
    score: float
    search_type: Literal["fts", "vector", "hybrid"]

    def __repr__(self) -> str:
        """Строковое представление."""
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return (
            f"<RAGResult(score={self.score:.3f}, type={self.search_type}, "
            f"content='{content_preview}')>"
        )


class RAGService:
    """
    Сервис поиска по базе знаний (RAG).

    Поддерживает три режима:
    1. FTS — полнотекстовый поиск (ts_rank)
    2. Vector — семантический поиск (cosine similarity)
    3. Hybrid — объединение FTS + Vector с весами
    """

    def __init__(
        self,
        uow: UnitOfWork,
        embedding_service: EmbeddingService | None = None,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
    ) -> None:
        """
        Инициализация сервиса.

        Args:
            uow: Unit of Work для работы с БД.
            embedding_service: Сервис embeddings (если None, создаётся автоматически).
            dense_weight: Вес векторного поиска в hybrid (0.0-1.0).
            sparse_weight: Вес FTS поиска в hybrid (0.0-1.0).

        Note:
            dense_weight + sparse_weight должны давать 1.0 для корректной нормализации.
        """
        self._uow = uow
        self._embedding_service = embedding_service
        self._dense_weight = dense_weight
        self._sparse_weight = sparse_weight

        # Валидация весов
        total_weight = dense_weight + sparse_weight
        if not (0.99 <= total_weight <= 1.01):  # Допускаем небольшую погрешность
            logger.warning(
                "Hybrid weights sum is not 1.0",
                extra={"dense": dense_weight, "sparse": sparse_weight, "sum": total_weight},
            )

    async def search(
        self,
        query: str,
        agent_id: str,
        top_k: int = 5,
        min_score: float = 0.7,
        search_type: Literal["fts", "vector", "hybrid"] = "hybrid",
    ) -> list[RAGResult]:
        """
        Поиск по базе знаний.

        Args:
            query: Поисковый запрос.
            agent_id: Slug домена (например, "products").
            top_k: Максимальное количество результатов.
            min_score: Минимальный порог релевантности (0.0-1.0).
            search_type: Тип поиска ("fts", "vector", "hybrid").

        Returns:
            Список результатов, отсортированных по score (убывание).

        Raises:
            ValueError: Если домен не найден или некорректные параметры.
        """
        logger.debug(
            "RAG search",
            extra={
                "query": query[:100],
                "agent_id": agent_id,
                "top_k": top_k,
                "min_score": min_score,
                "search_type": search_type,
            },
        )

        # Найти домен
        async with self._uow:
            domain_repo = DomainRepository(self._uow.session)
            domain = await domain_repo.get_by_slug(agent_id)

            if not domain:
                raise ValueError(f"Domain not found: {agent_id}")

            domain_id = domain.id

        # Выполнить поиск в зависимости от типа
        if search_type == "fts":
            results = await self._search_fts(query, domain_id, top_k, min_score)
        elif search_type == "vector":
            results = await self._search_vector(query, domain_id, top_k, min_score)
        else:  # hybrid
            results = await self._search_hybrid(query, domain_id, top_k, min_score)

        logger.info(
            "RAG search completed",
            extra={
                "agent_id": agent_id,
                "search_type": search_type,
                "results_count": len(results),
            },
        )

        return results

    async def _search_fts(
        self,
        query: str,
        domain_id: UUID,
        top_k: int,
        min_score: float,
    ) -> list[RAGResult]:
        """FTS поиск."""
        async with self._uow:
            chunk_repo = ChunkRepository(self._uow.session)
            fts_results = await chunk_repo.search_fts(
                query,
                domain_id=domain_id,
                limit=top_k,
            )

        # Нормализовать FTS scores в диапазон [0, 1]
        if not fts_results:
            return []

        # Нормализовать rank к [0, 1]
        results: list[RAGResult]

        if len(fts_results) == 1:
            # Одиночный результат - присвоить максимальный score
            chunk, _ = fts_results[0]
            results = [
                RAGResult(
                    chunk_id=chunk.id,
                    content=chunk.content,
                    header=chunk.chunk_metadata.get("header") if chunk.chunk_metadata else None,
                    score=1.0,
                    search_type="fts",
                )
            ]
        else:
            max_rank = max(rank for _, rank in fts_results)
            min_rank = min(rank for _, rank in fts_results)
            rank_range = max_rank - min_rank if max_rank > min_rank else 1.0

            results = []

            for chunk, rank in fts_results:
                # Нормализация: (rank - min) / (max - min)
                normalized_score = (rank - min_rank) / rank_range if rank_range > 0 else 1.0

                if normalized_score >= min_score:
                    results.append(
                        RAGResult(
                            chunk_id=chunk.id,
                            content=chunk.content,
                            header=chunk.chunk_metadata.get("header")
                            if chunk.chunk_metadata
                            else None,
                            score=normalized_score,
                            search_type="fts",
                        )
                    )

        return results

    async def _search_vector(
        self,
        query: str,
        domain_id: UUID,
        top_k: int,
        min_score: float,
    ) -> list[RAGResult]:
        """Vector поиск."""
        # Генерировать embedding для запроса
        embedding_service = self._embedding_service or EmbeddingService()

        try:
            query_embedding = await embedding_service.generate_single(query)
        finally:
            if self._embedding_service is None:
                await embedding_service.close()

        async with self._uow:
            chunk_repo = ChunkRepository(self._uow.session)
            vector_results = await chunk_repo.search_vector(
                query_embedding,
                domain_id=domain_id,
                limit=top_k,
                threshold=min_score,
            )

        results: list[RAGResult] = []

        for chunk, distance in vector_results:
            # Конвертировать distance в similarity: sim = 1 - distance
            similarity = 1.0 - distance

            if similarity >= min_score:
                results.append(
                    RAGResult(
                        chunk_id=chunk.id,
                        content=chunk.content,
                        header=chunk.chunk_metadata.get("header") if chunk.chunk_metadata else None,
                        score=similarity,
                        search_type="vector",
                    )
                )

        return results

    async def _search_hybrid(
        self,
        query: str,
        domain_id: UUID,
        top_k: int,
        min_score: float,
    ) -> list[RAGResult]:
        """
        Hybrid поиск (FTS + Vector merge).

        Алгоритм:
        1. Выполнить FTS и Vector поиски параллельно (с увеличенным top_k)
        2. Нормализовать scores
        3. Объединить результаты с весами
        4. Отсортировать по final_score
        5. Взять top_k
        6. Отфильтровать по min_score
        """
        # Увеличиваем лимит для каждого поиска, чтобы после merge получить достаточно результатов
        search_limit = top_k * 2

        # Генерировать embedding для запроса
        embedding_service = self._embedding_service or EmbeddingService()

        try:
            query_embedding = await embedding_service.generate_single(query)
        finally:
            if self._embedding_service is None:
                await embedding_service.close()

        # Выполнить оба поиска
        async with self._uow:
            chunk_repo = ChunkRepository(self._uow.session)

            # FTS
            fts_results = await chunk_repo.search_fts(
                query,
                domain_id=domain_id,
                limit=search_limit,
            )

            # Vector
            vector_results = await chunk_repo.search_vector(
                query_embedding,
                domain_id=domain_id,
                limit=search_limit,
                threshold=0.0,  # Не фильтруем здесь, будем фильтровать после merge
            )

        # Нормализовать FTS scores
        fts_scores: dict[UUID, float] = {}
        if fts_results:
            if len(fts_results) == 1:
                # Одиночный результат - присвоить максимальный score
                chunk, _ = fts_results[0]
                fts_scores[chunk.id] = 1.0
            else:
                max_rank = max(rank for _, rank in fts_results)
                min_rank = min(rank for _, rank in fts_results)
                rank_range = max_rank - min_rank if max_rank > min_rank else 1.0

                for chunk, rank in fts_results:
                    normalized = (rank - min_rank) / rank_range if rank_range > 0 else 1.0
                    fts_scores[chunk.id] = normalized

        # Vector scores (конвертировать distance в similarity)
        vector_scores: dict[UUID, float] = {}
        for chunk, distance in vector_results:
            vector_scores[chunk.id] = 1.0 - distance

        # Объединить результаты
        all_chunk_ids = set(fts_scores.keys()) | set(vector_scores.keys())
        merged: dict[
            UUID, tuple[float, str, str | None]
        ] = {}  # chunk_id -> (score, content, header)

        # Получить chunks для формирования результатов
        chunk_map = {chunk.id: chunk for chunk, _ in fts_results}
        chunk_map.update({chunk.id: chunk for chunk, _ in vector_results})

        for chunk_id in all_chunk_ids:
            fts_score = fts_scores.get(chunk_id, 0.0)
            vector_score = vector_scores.get(chunk_id, 0.0)

            # Взвешенная сумма
            final_score = self._dense_weight * vector_score + self._sparse_weight * fts_score

            chunk_opt = chunk_map.get(chunk_id)
            if chunk_opt:
                header = (
                    chunk_opt.chunk_metadata.get("header") if chunk_opt.chunk_metadata else None
                )
                merged[chunk_id] = (final_score, chunk_opt.content, header)

        # Отсортировать по score (убывание)
        sorted_items = sorted(merged.items(), key=lambda x: x[1][0], reverse=True)

        # Взять top_k
        top_items = sorted_items[:top_k]

        # Отфильтровать по min_score
        results: list[RAGResult] = []
        for chunk_id, (score, content, header) in top_items:
            if score >= min_score:
                results.append(
                    RAGResult(
                        chunk_id=chunk_id,
                        content=content,
                        header=header,
                        score=score,
                        search_type="hybrid",
                    )
                )

        return results

    async def get_context(
        self,
        query: str,
        agent_id: str,
        top_k: int = 5,
        min_score: float = 0.7,
    ) -> str:
        """
        Получить текстовый контекст для LLM.

        Args:
            query: Поисковый запрос.
            agent_id: Slug домена.
            top_k: Количество чанков.
            min_score: Минимальный score.

        Returns:
            Форматированный контекст для передачи в LLM.

        Format:
            ## Заголовок1 (из базы знаний)

            Содержимое чанка 1

            ## Заголовок2 (из базы знаний)

            Содержимое чанка 2
        """
        results = await self.search(query, agent_id, top_k, min_score, search_type="hybrid")

        if not results:
            return ""

        context_parts: list[str] = []

        for result in results:
            header = result.header or "Информация"
            section = f"## {header} (из базы знаний)\n\n{result.content}"
            context_parts.append(section)

        return "\n\n".join(context_parts)
