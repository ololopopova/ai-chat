"""Integration тесты для RAG Service.

Используют mock embeddings и mock данные в БД.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db.models.chunk import Chunk
from src.db.models.domain import Domain
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.domain_repository import DomainRepository
from src.repositories.unit_of_work import UnitOfWork
from src.services.rag_service import RAGService


@pytest.fixture
def test_domain() -> Domain:
    """Тестовый домен."""
    return Domain(
        id=uuid.uuid4(),
        name="Products Agent",
        slug="products",
        google_doc_url="https://docs.google.com/document/d/TEST/edit",
        is_active=True,
    )


@pytest.fixture
def test_chunks(test_domain: Domain) -> list[Chunk]:
    """Тестовые чанки."""
    return [
        Chunk(
            id=uuid.uuid4(),
            domain_id=test_domain.id,
            content="Ашваганда — адаптоген для снижения стресса.",
            chunk_index=0,
            chunk_metadata={"header": "БАДы", "header_level": 1},
            embedding=[0.1] * 3072,
        ),
        Chunk(
            id=uuid.uuid4(),
            domain_id=test_domain.id,
            content="Мелатонин — гормон сна, принимать перед сном.",
            chunk_index=1,
            chunk_metadata={"header": "БАДы", "header_level": 1},
            embedding=[0.2] * 3072,
        ),
        Chunk(
            id=uuid.uuid4(),
            domain_id=test_domain.id,
            content="Микродозинг грибов помогает улучшить креативность.",
            chunk_index=2,
            chunk_metadata={"header": "Микродозинг", "header_level": 1},
            embedding=[0.3] * 3072,
        ),
    ]


@pytest.mark.asyncio
async def test_rag_search_fts(
    test_domain: Domain,
    test_chunks: list[Chunk],
) -> None:
    """FTS поиск возвращает релевантные результаты."""
    # Mock UnitOfWork
    uow = MagicMock(spec=UnitOfWork)
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock()

    # Mock репозитории
    mock_domain_repo = MagicMock(spec=DomainRepository)
    mock_domain_repo.get_by_slug = AsyncMock(return_value=test_domain)

    mock_chunk_repo = MagicMock(spec=ChunkRepository)
    # FTS возвращает чанк с мелатонином (rank=1.5)
    mock_chunk_repo.search_fts = AsyncMock(return_value=[(test_chunks[1], 1.5)])

    with (
        patch("src.services.rag_service.DomainRepository", return_value=mock_domain_repo),
        patch("src.services.rag_service.ChunkRepository", return_value=mock_chunk_repo),
    ):
        service = RAGService(uow)
        results = await service.search(
            query="мелатонин",
            agent_id="products",
            top_k=5,
            min_score=0.0,
            search_type="fts",
        )

        assert len(results) == 1
        assert "Мелатонин" in results[0].content
        assert results[0].search_type == "fts"
        assert results[0].score > 0.0


@pytest.mark.asyncio
async def test_rag_search_vector(
    test_domain: Domain,
    test_chunks: list[Chunk],
) -> None:
    """Vector поиск возвращает релевантные результаты."""
    # Mock UnitOfWork
    uow = MagicMock(spec=UnitOfWork)
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock()

    # Mock репозитории
    mock_domain_repo = MagicMock(spec=DomainRepository)
    mock_domain_repo.get_by_slug = AsyncMock(return_value=test_domain)

    mock_chunk_repo = MagicMock(spec=ChunkRepository)
    # Vector возвращает чанк с ашвагандой (distance=0.2)
    mock_chunk_repo.search_vector = AsyncMock(return_value=[(test_chunks[0], 0.2)])

    # Mock EmbeddingService
    with patch("src.services.rag_service.EmbeddingService") as MockEmbedding:
        mock_embedding = MockEmbedding.return_value
        mock_embedding.generate_single = AsyncMock(return_value=[0.1] * 3072)
        mock_embedding.close = AsyncMock()

        with (
            patch("src.services.rag_service.DomainRepository", return_value=mock_domain_repo),
            patch("src.services.rag_service.ChunkRepository", return_value=mock_chunk_repo),
        ):
            service = RAGService(uow)
            results = await service.search(
                query="адаптоген стресс",
                agent_id="products",
                top_k=5,
                min_score=0.0,
                search_type="vector",
            )

            assert len(results) == 1
            assert "Ашваганда" in results[0].content
            assert results[0].search_type == "vector"
            # Similarity = 1 - distance = 1 - 0.2 = 0.8
            assert abs(results[0].score - 0.8) < 0.01


@pytest.mark.asyncio
async def test_rag_search_filters_by_agent(
    test_domain: Domain,
) -> None:
    """Поиск фильтрует по agent_id."""
    # Mock UnitOfWork
    uow = MagicMock(spec=UnitOfWork)
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock()

    # Mock репозитории
    mock_domain_repo = MagicMock(spec=DomainRepository)
    mock_domain_repo.get_by_slug = AsyncMock(return_value=test_domain)

    mock_chunk_repo = MagicMock(spec=ChunkRepository)
    mock_chunk_repo.search_fts = AsyncMock(return_value=[])

    with (
        patch("src.services.rag_service.DomainRepository", return_value=mock_domain_repo),
        patch("src.services.rag_service.ChunkRepository", return_value=mock_chunk_repo),
    ):
        service = RAGService(uow)
        _results = await service.search(
            query="test",
            agent_id="products",
            top_k=5,
            search_type="fts",
        )

        # Проверить, что вызван search_fts с domain_id
        mock_chunk_repo.search_fts.assert_called_once()
        call_kwargs = mock_chunk_repo.search_fts.call_args.kwargs
        assert call_kwargs["domain_id"] == test_domain.id


@pytest.mark.asyncio
async def test_rag_get_context_formats_correctly(
    test_domain: Domain,
    test_chunks: list[Chunk],
) -> None:
    """get_context форматирует контекст для LLM."""
    # Mock UnitOfWork
    uow = MagicMock(spec=UnitOfWork)
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock()

    # Mock репозитории
    mock_domain_repo = MagicMock(spec=DomainRepository)
    mock_domain_repo.get_by_slug = AsyncMock(return_value=test_domain)

    # Mock для hybrid search (упрощённо)
    with patch.object(RAGService, "search") as mock_search:
        from src.services.rag_service import RAGResult

        mock_search.return_value = [
            RAGResult(
                chunk_id=test_chunks[0].id,
                content=test_chunks[0].content,
                header="БАДы",
                score=0.9,
                search_type="hybrid",
            ),
        ]

        with patch("src.services.rag_service.DomainRepository", return_value=mock_domain_repo):
            service = RAGService(uow)
            context = await service.get_context(
                query="ашваганда",
                agent_id="products",
            )

            # Проверить формат
            assert "## БАДы (из базы знаний)" in context
            assert "Ашваганда — адаптоген" in context
