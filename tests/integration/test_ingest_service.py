"""Integration тесты для Ingest Service.

Используют mock HTML (без реального Google Doc) и mock embeddings.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db.models.domain import Domain
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.domain_repository import DomainRepository
from src.repositories.unit_of_work import UnitOfWork
from src.services.ingest import IngestService


@pytest.fixture
def mock_html() -> str:
    """Mock HTML документа Google Docs."""
    return """
    <html>
    <body>
        <h1>БАДы и добавки</h1>
        <p>Базовые добавки для здоровья и биохакинга.</p>
        <table>
            <tr><td>Добавка</td><td>Дозировка</td></tr>
            <tr><td>Ашваганда</td><td>300-600 мг</td></tr>
            <tr><td>Мелатонин</td><td>1-3 мг</td></tr>
        </table>

        <h1>Микродозинг грибов</h1>
        <p>Информация о микродозинге псилоцибиновых грибов.</p>
        <p>Рекомендуемые дозировки и схемы приёма.</p>

        <h1>Курс биохакинга</h1>
        <p>Комплексный подход к оптимизации здоровья.</p>
    </body>
    </html>
    """


@pytest.fixture
def mock_embeddings() -> list[list[float]]:
    """Mock embeddings (1536 dims)."""
    # Создаём 3 вектора (соответствует 3 секциям в mock_html)
    return [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]


@pytest.mark.asyncio
async def test_ingest_full_pipeline_mock(
    mock_html: str,
    mock_embeddings: list[list[float]],
    db_session_factory: AsyncMock,  # noqa: ARG001
) -> None:
    """Полный пайплайн индексации с mock данными."""
    # Mock UnitOfWork и репозитории
    uow = MagicMock(spec=UnitOfWork)
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock()
    uow.commit = AsyncMock()

    # Mock домен
    test_domain = Domain(
        id=uuid.uuid4(),
        name="Products Agent",
        slug="products",
        google_doc_url="https://docs.google.com/document/d/TEST123/edit",
        is_active=True,
    )

    # Mock DomainRepository
    mock_domain_repo = MagicMock(spec=DomainRepository)
    mock_domain_repo.get_by_slug = AsyncMock(return_value=test_domain)

    # Mock ChunkRepository
    mock_chunk_repo = MagicMock(spec=ChunkRepository)
    mock_chunk_repo.delete_by_domain = AsyncMock(return_value=0)
    mock_chunk_repo.create_batch = AsyncMock(return_value=3)  # 3 чанка

    # Патчим репозитории
    with (
        patch(
            "src.services.ingest.ingest_service.DomainRepository",
            return_value=mock_domain_repo,
        ),
        patch(
            "src.services.ingest.ingest_service.ChunkRepository",
            return_value=mock_chunk_repo,
        ),
        patch("src.services.ingest.ingest_service.GoogleDocLoader") as MockLoader,
    ):
        mock_loader_instance = MockLoader.return_value
        mock_loader_instance.load = AsyncMock(return_value=mock_html)

        # Mock EmbeddingService
        with patch("src.services.ingest.ingest_service.EmbeddingService") as MockEmbedding:
            mock_embedding_instance = MockEmbedding.return_value
            mock_embedding_instance.generate_batch = AsyncMock(return_value=mock_embeddings)
            mock_embedding_instance.close = AsyncMock()

            # Создать сервис
            service = IngestService(uow)

            # Выполнить индексацию
            result = await service.ingest_agent("products")

            # Проверки
            assert result.success
            assert result.agent_id == "products"
            assert result.chunks_created == 3
            assert result.embeddings_generated == 3
            assert result.documents_processed == 1
            assert len(result.errors) == 0

            # Проверить вызовы
            mock_loader_instance.load.assert_called_once()
            mock_embedding_instance.generate_batch.assert_called_once()
            mock_chunk_repo.delete_by_domain.assert_called_once_with(test_domain.id)
            mock_chunk_repo.create_batch.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_handles_errors(db_session_factory: AsyncMock) -> None:  # noqa: ARG001
    """Обработка ошибок при индексации."""
    # Mock UnitOfWork
    uow = MagicMock(spec=UnitOfWork)
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock()

    # Mock DomainRepository — домен не найден
    mock_domain_repo = MagicMock(spec=DomainRepository)
    mock_domain_repo.get_by_slug = AsyncMock(return_value=None)

    with patch(
        "src.services.ingest.ingest_service.DomainRepository",
        return_value=mock_domain_repo,
    ):
        service = IngestService(uow)

        # Попытка индексации несуществующего домена
        with pytest.raises(Exception):  # noqa: B017 - IngestError
            await service.ingest_agent("nonexistent")
