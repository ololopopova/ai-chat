"""RAG MCP Tools - hybrid search с reranking.

Вся логика поиска находится здесь, в MCP server.

Архитектура загрузки модели:
1. Dockerfile: модель кэшируется в образ (~50MB)
2. API startup: модель загружается в RAM (если use_reranker=true в config)
3. Runtime: переиспользуется синглтон (быстро, без повторной загрузки)
"""

from __future__ import annotations

from mcp_servers.rag.reranker import Reranker
from mcp_servers.rag.schemas import HybridSearchInput, RAGSearchResult
from mcp_servers.rag.search import hybrid_search as do_hybrid_search

from src.core.logging import get_logger

logger = get_logger(__name__)

# Синглтон: Reranker инициализируется 1 раз и переиспользуется
_reranker_instance: Reranker | None = None


def get_reranker() -> Reranker:
    """
    Получить синглтон Reranker.
    
    Ленивая инициализация: модель загружается только при первом вызове.
    В production модель предзагружается при старте API (см. src/api/main.py).
    
    Returns:
        Reranker instance (синглтон, переиспользуется).
    """
    global _reranker_instance
    if _reranker_instance is None:
        logger.info("Initializing Reranker singleton (first call)")
        _reranker_instance = Reranker()
    return _reranker_instance


async def hybrid_search(input_data: HybridSearchInput) -> RAGSearchResult:
    """
    Гибридный поиск с reranking.

    Алгоритм:
    1. Параллельный поиск по каждому vector_query
    2. Параллельный поиск по каждому fts_keyword
    3. Дедупликация (макс. score для каждого чанка)
    4. Reranking через Cross-Encoder (топ-30 → топ-15)
    5. Фильтрация по min_score
    6. Форматирование контекста

    Args:
        input_data: Параметры поиска.

    Returns:
        RAGSearchResult с чанками и форматированным контекстом.
    """
    logger.info(
        "MCP hybrid_search called",
        extra={
            "domain": input_data.domain,
            "vector_queries": input_data.vector_queries,
            "fts_keywords": input_data.fts_keywords,
        },
    )

    try:
        # 1. Гибридный поиск
        chunks = await do_hybrid_search(
            vector_queries=input_data.vector_queries,
            fts_queries=input_data.fts_keywords,
            domain=input_data.domain,
            top_k_per_query=input_data.top_k_per_query,
        )

        logger.info(
            "Search completed, starting reranking",
            extra={"chunks_before_rerank": len(chunks)},
        )

        # 2. Reranking (если включено и есть результаты)
        if input_data.use_reranker and chunks:
            reranker = get_reranker()  # Используем синглтон
            # Комбинируем запросы для reranking
            combined_query = " ".join(input_data.vector_queries)
            chunks = reranker.rerank(
                query=combined_query,
                chunks=chunks,
                top_k=input_data.final_top_k,
            )
        else:
            # Без reranker просто берём топ-K
            chunks = chunks[: input_data.final_top_k]

        # 3. Фильтрация по min_score
        filtered_chunks = [
            chunk for chunk in chunks if chunk.score >= input_data.min_score
        ]

        logger.info(
            "MCP hybrid_search completed",
            extra={
                "domain": input_data.domain,
                "results_after_filter": len(filtered_chunks),
                "top_scores": [c.score for c in filtered_chunks[:5]] if filtered_chunks else [],
            },
        )

        # 4. Форматируем контекст для LLM
        context_parts: list[str] = []
        for chunk in filtered_chunks:
            header = chunk.header or "Информация"
            section = f"## {header}\n\n{chunk.content}"
            context_parts.append(section)

        formatted_context = "\n\n".join(context_parts) if context_parts else ""

        return RAGSearchResult(
            chunks=filtered_chunks,
            total_found=len(filtered_chunks),
            domain=input_data.domain,
            formatted_context=formatted_context,
        )

    except Exception as e:
        logger.error(
            "MCP hybrid_search failed",
            extra={
                "domain": input_data.domain,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        # Возвращаем пустой результат при ошибке
        return RAGSearchResult(
            chunks=[],
            total_found=0,
            domain=input_data.domain,
            formatted_context=f"❌ Ошибка поиска: {e}",
        )
