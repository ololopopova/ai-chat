"""Логика гибридного поиска для RAG.

Hybrid search: FTS + Vector + Multi-query + Reranking.
"""

from __future__ import annotations

from uuid import UUID

from mcp_servers.rag.schemas import RAGChunk
from src.core.logging import get_logger
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.domain_repository import DomainRepository
from src.repositories.unit_of_work import UnitOfWork
from src.services.ingest.embedding_service import EmbeddingService

logger = get_logger(__name__)


async def hybrid_search(
    vector_queries: list[str],
    fts_queries: list[str],
    domain: str,
    top_k_per_query: int = 5,
) -> list[RAGChunk]:
    """
    Гибридный поиск: множественные запросы для vector и fts.

    Args:
        vector_queries: Запросы для векторного поиска.
        fts_queries: Запросы для FTS поиска.
        domain: Домен (slug).
        top_k_per_query: Сколько результатов на запрос.

    Returns:
        Список чанков с дедупликацией.
    """
    logger.info(
        "Hybrid search",
        extra={
            "domain": domain,
            "vector_count": len(vector_queries),
            "fts_count": len(fts_queries),
        },
    )

    uow = UnitOfWork()
    embedding_service = EmbeddingService()

    try:
        # Найти домен
        async with uow:
            domain_repo = DomainRepository(uow.session)
            domain_obj = await domain_repo.get_by_slug(domain)

            if not domain_obj:
                raise ValueError(f"Domain not found: {domain}")

            domain_id = domain_obj.id

        # Словарь для дедупликации: chunk_id -> (best_score, chunk_data)
        all_results: dict[UUID, tuple[float, str, str | None]] = {}

        # 1. Vector searches
        for vq in vector_queries:
            # Генерируем embedding
            embedding = await embedding_service.generate_single(vq)

            # Ищем
            async with uow:
                chunk_repo = ChunkRepository(uow.session)
                results = await chunk_repo.search_vector(
                    embedding,
                    domain_id=domain_id,
                    limit=top_k_per_query,
                    threshold=0.0,
                )

            # Добавляем с дедупликацией
            for chunk, distance in results:
                score = 1.0 - distance  # distance -> similarity
                if chunk.id in all_results:
                    if score > all_results[chunk.id][0]:
                        all_results[chunk.id] = (
                            score,
                            chunk.content,
                            chunk.chunk_metadata.get("header")
                            if chunk.chunk_metadata
                            else None,
                        )
                else:
                    all_results[chunk.id] = (
                        score,
                        chunk.content,
                        chunk.chunk_metadata.get("header")
                        if chunk.chunk_metadata
                        else None,
                    )

        # 2. FTS searches
        for fq in fts_queries:
            async with uow:
                chunk_repo = ChunkRepository(uow.session)
                results = await chunk_repo.search_fts(
                    fq,
                    domain_id=domain_id,
                    limit=top_k_per_query,
                )

            # Нормализуем FTS scores
            if results:
                if len(results) == 1:
                    chunk, _ = results[0]
                    score = 1.0
                    header = (
                        chunk.chunk_metadata.get("header")
                        if chunk.chunk_metadata
                        else None
                    )
                    if chunk.id in all_results:
                        if score > all_results[chunk.id][0]:
                            all_results[chunk.id] = (score, chunk.content, header)
                    else:
                        all_results[chunk.id] = (score, chunk.content, header)
                else:
                    max_rank = max(rank for _, rank in results)
                    min_rank = min(rank for _, rank in results)
                    rank_range = max_rank - min_rank if max_rank > min_rank else 1.0

                    for chunk, rank in results:
                        score = (
                            (rank - min_rank) / rank_range if rank_range > 0 else 1.0
                        )
                        header = (
                            chunk.chunk_metadata.get("header")
                            if chunk.chunk_metadata
                            else None
                        )
                        if chunk.id in all_results:
                            if score > all_results[chunk.id][0]:
                                all_results[chunk.id] = (score, chunk.content, header)
                        else:
                            all_results[chunk.id] = (score, chunk.content, header)

        # 3. Сортировка по score
        sorted_results = sorted(
            all_results.items(),
            key=lambda x: x[1][0],
            reverse=True,
        )

        # 4. Создать RAGChunk объекты
        chunks = [
            RAGChunk(
                chunk_id=str(chunk_id),
                content=content,
                header=header,
                score=score,
                search_type="hybrid",
            )
            for chunk_id, (score, content, header) in sorted_results
        ]

        logger.info(
            "Hybrid search completed",
            extra={"domain": domain, "total_found": len(chunks)},
        )

        return chunks

    finally:
        await embedding_service.close()
