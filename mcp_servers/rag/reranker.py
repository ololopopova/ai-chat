"""Reranker для RAG поиска.

Cross-Encoder для переранжирования результатов поиска.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sentence_transformers import CrossEncoder

from src.core.logging import get_logger
from mcp_servers.rag.schemas import RAGChunk

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class Reranker:
    """Cross-Encoder reranker для улучшения качества RAG."""

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-12-v2",
    ) -> None:
        """Инициализация."""
        logger.info("Initializing Reranker", extra={"model": model_name})
        self._model = CrossEncoder(model_name)

    def rerank(
        self,
        query: str,
        chunks: list[RAGChunk],
        top_k: int = 15,
    ) -> list[RAGChunk]:
        """
        Переранжировать чанки.

        Args:
            query: Поисковый запрос.
            chunks: Список чанков для переранжирования.
            top_k: Количество результатов после rerank.

        Returns:
            Переранжированный список (топ-K).
        """
        if not chunks:
            return []

        logger.debug(
            "Reranking",
            extra={"query_length": len(query), "chunks_count": len(chunks), "top_k": top_k},
        )

        # Формируем пары (query, chunk_content)
        pairs = [(query, chunk.content) for chunk in chunks]

        # Получаем scores от cross-encoder
        scores = self._model.predict(pairs)

        # Обновляем scores и сортируем
        reranked = []
        for chunk, new_score in zip(chunks, scores, strict=False):
            # Создаем новый чанк с обновленным score
            reranked_chunk = RAGChunk(
                chunk_id=chunk.chunk_id,
                content=chunk.content,
                header=chunk.header,
                score=float(new_score),
                search_type=chunk.search_type,
            )
            reranked.append(reranked_chunk)

        # Сортируем по новым scores
        reranked.sort(key=lambda c: c.score, reverse=True)

        # Берём топ-K
        final = reranked[:top_k]

        logger.info(
            "Reranking completed",
            extra={
                "input_count": len(chunks),
                "output_count": len(final),
                "top_scores": [c.score for c in final[:5]],
            },
        )

        return final

