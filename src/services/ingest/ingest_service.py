"""Ingest Service — оркестрация пайплайна индексации документов.

Координирует работу:
- GoogleDocLoader (загрузка)
- HTMLParser (парсинг)
- Chunker (разбиение)
- EmbeddingService (векторизация)
- ChunkRepository (сохранение в БД)
"""

import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.core.exceptions import IngestError
from src.core.logging import get_logger
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.domain_repository import DomainRepository
from src.repositories.unit_of_work import UnitOfWork
from src.services.ingest.chunker import Chunker
from src.services.ingest.embedding_service import EmbeddingService
from src.services.ingest.google_doc_loader import GoogleDocLoader
from src.services.ingest.html_parser import HTMLParser

logger = get_logger(__name__)


@dataclass
class IngestResult:
    """
    Результат индексации домена.

    Attributes:
        agent_id: Slug домена (например, "products").
        domain_id: UUID домена в БД.
        documents_processed: Количество обработанных документов.
        chunks_created: Количество созданных чанков.
        embeddings_generated: Количество сгенерированных embeddings.
        duration_seconds: Время выполнения (секунды).
        errors: Список ошибок (если были).
    """

    agent_id: str
    domain_id: UUID
    documents_processed: int
    chunks_created: int
    embeddings_generated: int
    duration_seconds: float
    errors: list[str]

    @property
    def success(self) -> bool:
        """Проверить, успешна ли индексация."""
        return len(self.errors) == 0 and self.chunks_created > 0


class IngestService:
    """
    Сервис индексации документов.

    Полный пайплайн:
    1. Загрузить Google Doc по URL из домена
    2. Распарсить HTML
    3. Разбить на чанки
    4. Сгенерировать embeddings
    5. Удалить старые чанки домена
    6. Сохранить новые чанки в БД
    """

    def __init__(
        self,
        uow: UnitOfWork,
        embedding_service: EmbeddingService | None = None,
        min_chunk_size: int = 100,
    ) -> None:
        """
        Инициализация сервиса.

        Args:
            uow: Unit of Work для работы с БД.
            embedding_service: Сервис embeddings (если None, создаётся автоматически).
            min_chunk_size: Минимальный размер чанка в символах.
        """
        self._uow = uow
        self._embedding_service = embedding_service
        self._min_chunk_size = min_chunk_size

        # Компоненты пайплайна
        self._loader = GoogleDocLoader()
        self._parser = HTMLParser()
        self._chunker = Chunker(min_chunk_size=min_chunk_size)

    async def ingest_agent(self, agent_id: str) -> IngestResult:
        """
        Индексировать домен по agent_id (slug).

        Args:
            agent_id: Slug домена (например, "products").

        Returns:
            Результат индексации.

        Raises:
            IngestError: При критических ошибках.
        """
        start_time = time.time()
        errors: list[str] = []

        logger.info("Starting ingest for agent", extra={"agent_id": agent_id})

        try:
            # 1. Найти домен
            async with self._uow:
                domain_repo = DomainRepository(self._uow.session)
                domain = await domain_repo.get_by_slug(agent_id)

                if not domain:
                    raise IngestError(f"Domain not found: {agent_id}")

                if not domain.google_doc_url:
                    raise IngestError(f"Domain {agent_id} has no google_doc_url")

                domain_id = domain.id
                doc_url = domain.google_doc_url

            # 2. Загрузить HTML
            logger.info(
                "Loading document", extra={"agent_id": agent_id, "url": doc_url}
            )
            try:
                html = await self._loader.load(doc_url)
            except IngestError as e:
                errors.append(f"Load error: {e}")
                raise

            # 3. Парсинг HTML
            logger.info("Parsing HTML", extra={"agent_id": agent_id})
            try:
                sections = self._parser.parse(html)
            except Exception as e:
                error_msg = f"Parse error: {e}"
                errors.append(error_msg)
                raise IngestError(error_msg) from e

            # 4. Разбиение на чанки
            logger.info(
                "Chunking document",
                extra={"agent_id": agent_id, "sections_count": len(sections)},
            )
            try:
                chunks = self._chunker.chunk_sections(sections)
            except Exception as e:
                error_msg = f"Chunking error: {e}"
                errors.append(error_msg)
                raise IngestError(error_msg) from e

            if not chunks:
                error_msg = "No chunks created (document might be empty)"
                errors.append(error_msg)
                raise IngestError(error_msg)

            # 5. Генерация embeddings
            logger.info(
                "Generating embeddings",
                extra={"agent_id": agent_id, "chunks_count": len(chunks)},
            )

            # Используем переданный сервис или создаём новый
            embedding_service = self._embedding_service or EmbeddingService()

            try:
                texts = [chunk.content for chunk in chunks]
                embeddings = await embedding_service.generate_batch(texts)
            except Exception as e:
                error_msg = f"Embedding error: {e}"
                errors.append(error_msg)
                raise IngestError(error_msg) from e
            finally:
                # Закрыть сервис, если создали его здесь
                if self._embedding_service is None:
                    await embedding_service.close()

            # 6. Подготовить данные для БД
            chunks_data: list[dict[str, Any]] = []
            for chunk, embedding in zip(chunks, embeddings):  # noqa: B905
                chunk_dict = chunk.to_dict(domain_id)
                chunk_dict["embedding"] = embedding
                chunks_data.append(chunk_dict)

            # 7. Сохранить в БД (удалить старые + вставить новые)
            logger.info(
                "Saving to database",
                extra={"agent_id": agent_id, "chunks_count": len(chunks_data)},
            )

            async with self._uow:
                chunk_repo = ChunkRepository(self._uow.session)

                # Удалить старые чанки
                deleted_count = await chunk_repo.delete_by_domain(domain_id)
                logger.debug(
                    "Deleted old chunks",
                    extra={"agent_id": agent_id, "deleted_count": deleted_count},
                )

                # Создать новые чанки
                created_count = await chunk_repo.create_batch(chunks_data)

                await self._uow.commit()

            duration = time.time() - start_time

            result = IngestResult(
                agent_id=agent_id,
                domain_id=domain_id,
                documents_processed=1,
                chunks_created=created_count,
                embeddings_generated=len(embeddings),
                duration_seconds=duration,
                errors=errors,
            )

            logger.info(
                "Ingest completed successfully",
                extra={
                    "agent_id": agent_id,
                    "chunks": created_count,
                    "duration_sec": f"{duration:.2f}",
                },
            )

            return result

        except IngestError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            errors.append(error_msg)
            logger.error("Ingest failed", extra={"agent_id": agent_id, "error": str(e)})
            raise IngestError(error_msg) from e

    async def ingest_all(self) -> dict[str, IngestResult]:
        """
        Индексировать все активные домены с google_doc_url.

        Returns:
            Словарь {agent_id: IngestResult} для каждого домена.

        Note:
            Ошибки индексации отдельных доменов не прерывают процесс,
            они записываются в IngestResult.errors.
        """
        logger.info("Starting ingest for all agents")

        # Получить все активные домены
        async with self._uow:
            domain_repo = DomainRepository(self._uow.session)
            domains = await domain_repo.get_active()

        # Фильтровать домены с google_doc_url
        domains_to_ingest = [d for d in domains if d.google_doc_url]

        logger.info(
            "Found domains to ingest",
            extra={"total_domains": len(domains), "with_docs": len(domains_to_ingest)},
        )

        results: dict[str, IngestResult] = {}

        for domain in domains_to_ingest:
            try:
                result = await self.ingest_agent(domain.slug)
                results[domain.slug] = result
            except IngestError as e:
                # Записать ошибку, но продолжить
                logger.error(
                    "Failed to ingest agent",
                    extra={"agent_id": domain.slug, "error": str(e)},
                )
                results[domain.slug] = IngestResult(
                    agent_id=domain.slug,
                    domain_id=domain.id,
                    documents_processed=0,
                    chunks_created=0,
                    embeddings_generated=0,
                    duration_seconds=0.0,
                    errors=[str(e)],
                )

        logger.info(
            "Ingest all completed",
            extra={
                "total": len(results),
                "success": sum(1 for r in results.values() if r.success),
                "failed": sum(1 for r in results.values() if not r.success),
            },
        )

        return results
