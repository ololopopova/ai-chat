"""Pydantic схемы для RAG MCP Server."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HybridSearchInput(BaseModel):
    """
    Входные параметры для гибридного поиска.

    Субагент должен проанализировать запрос и сформировать:
    - vector_queries: 2-3 подзапроса для семантического поиска
    - fts_keywords: 5-7 ключевых слов для полнотекстового поиска
    """

    vector_queries: list[str] = Field(
        ...,
        description="2-3 подзапроса для семантического поиска (vector search)",
        min_length=1,
        max_length=5,
    )
    fts_keywords: list[str] = Field(
        ...,
        description="5-7 ключевых слов для полнотекстового поиска",
        min_length=1,
        max_length=10,
    )
    domain: str = Field(
        ...,
        description="Домен для поиска: 'products' или 'compatibility'",
    )
    top_k_per_query: int = Field(
        default=5,
        description="Сколько результатов брать на каждый подзапрос",
        ge=1,
        le=10,
    )
    final_top_k: int = Field(
        default=15,
        description="Итоговое количество результатов после rerank",
        ge=1,
        le=20,
    )
    min_score: float = Field(
        default=0.3,
        description="Минимальный порог релевантности (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    use_reranker: bool = Field(
        default=True,
        description="Использовать ли Cross-Encoder для реранжирования",
    )


class RAGChunk(BaseModel):
    """Результат поиска — один чанк."""

    chunk_id: str = Field(..., description="UUID чанка")
    content: str = Field(..., description="Текстовое содержимое")
    header: str | None = Field(None, description="Заголовок секции")
    score: float = Field(..., description="Score релевантности (0.0-1.0)")
    search_type: Literal["hybrid"] = Field(
        ..., description="Тип поиска (всегда hybrid)"
    )


class RAGSearchResult(BaseModel):
    """Результат поиска по базе знаний."""

    chunks: list[RAGChunk] = Field(..., description="Найденные чанки")
    total_found: int = Field(..., description="Общее количество найденных")
    domain: str = Field(..., description="Домен поиска")
    formatted_context: str = Field(
        ..., description="Форматированный контекст для LLM"
    )
