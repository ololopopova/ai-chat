"""Интеграционные тесты репозиториев.

Тестируют CRUD операции и специфичные методы каждого репозитория.
"""

import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.job import JobStatus
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.domain_repository import DomainRepository
from src.repositories.job_repository import JobRepository

pytestmark = pytest.mark.asyncio


class TestDomainRepository:
    """Тесты DomainRepository."""

    async def test_create_domain(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Проверить создание домена."""
        repo = DomainRepository(db_session)

        domain = await repo.create_domain(
            name="Тестовый домен",
            slug="test-domain",
            description="Описание тестового домена",
            google_doc_url="https://docs.google.com/test",
            is_active=True,
        )

        assert domain.id is not None
        assert domain.name == "Тестовый домен"
        assert domain.slug == "test-domain"
        assert domain.is_active is True

    async def test_get_by_slug(
        self,
        db_session: AsyncSession,
        sample_domain: dict[str, Any],
    ) -> None:
        """Проверить поиск по slug."""
        repo = DomainRepository(db_session)

        # Создаём домен
        created = await repo.create_domain(**sample_domain)

        # Ищем по slug
        found = await repo.get_by_slug(sample_domain["slug"])

        assert found is not None
        assert found.id == created.id

    async def test_get_active_domains(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Проверить получение активных доменов."""
        repo = DomainRepository(db_session)

        # Создаём активный и неактивный домены
        await repo.create_domain(
            name="Active",
            slug="active",
            google_doc_url="https://docs.google.com/active",
            is_active=True,
        )
        await repo.create_domain(
            name="Inactive",
            slug="inactive",
            google_doc_url="https://docs.google.com/inactive",
            is_active=False,
        )

        active = await repo.get_active()

        assert len(active) == 1
        assert active[0].slug == "active"

    async def test_update_domain(
        self,
        db_session: AsyncSession,
        sample_domain: dict[str, Any],
    ) -> None:
        """Проверить обновление домена."""
        repo = DomainRepository(db_session)

        created = await repo.create_domain(**sample_domain)

        updated = await repo.update_domain(
            created.id,
            name="Updated Name",
        )

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.updated_at > created.created_at

    async def test_delete_domain(
        self,
        db_session: AsyncSession,
        sample_domain: dict[str, Any],
    ) -> None:
        """Проверить удаление домена."""
        repo = DomainRepository(db_session)

        created = await repo.create_domain(**sample_domain)

        deleted = await repo.delete(created.id)
        assert deleted is True

        found = await repo.get(created.id)
        assert found is None

    async def test_slug_uniqueness(
        self,
        db_session: AsyncSession,
        sample_domain: dict[str, Any],
    ) -> None:
        """Проверить уникальность slug."""
        repo = DomainRepository(db_session)

        await repo.create_domain(**sample_domain)

        # Проверяем существование
        exists = await repo.slug_exists(sample_domain["slug"])
        assert exists is True


class TestChunkRepository:
    """Тесты ChunkRepository."""

    async def test_create_chunk(
        self,
        db_session: AsyncSession,
        sample_domain: dict[str, Any],
    ) -> None:
        """Проверить создание чанка."""
        domain_repo = DomainRepository(db_session)
        chunk_repo = ChunkRepository(db_session)

        domain = await domain_repo.create_domain(**sample_domain)

        chunk = await chunk_repo.create_chunk(
            domain_id=domain.id,
            content="Тестовый контент для поиска",
            chunk_index=0,
        )

        assert chunk.id is not None
        assert chunk.domain_id == domain.id
        assert chunk.content == "Тестовый контент для поиска"

    async def test_get_by_domain(
        self,
        db_session: AsyncSession,
        sample_domain: dict[str, Any],
    ) -> None:
        """Проверить получение чанков по домену."""
        domain_repo = DomainRepository(db_session)
        chunk_repo = ChunkRepository(db_session)

        domain = await domain_repo.create_domain(**sample_domain)

        # Создаём несколько чанков
        for i in range(3):
            await chunk_repo.create_chunk(
                domain_id=domain.id,
                content=f"Chunk {i}",
                chunk_index=i,
            )

        chunks = await chunk_repo.get_by_domain(domain.id)

        assert len(chunks) == 3
        assert chunks[0].chunk_index == 0
        assert chunks[2].chunk_index == 2

    async def test_search_fts(
        self,
        db_session: AsyncSession,
        sample_domain: dict[str, Any],
    ) -> None:
        """Проверить полнотекстовый поиск."""
        domain_repo = DomainRepository(db_session)
        chunk_repo = ChunkRepository(db_session)

        domain = await domain_repo.create_domain(**sample_domain)

        # Создаём чанки с разным контентом
        await chunk_repo.create_chunk(
            domain_id=domain.id,
            content="Python programming language",
            chunk_index=0,
        )
        await chunk_repo.create_chunk(
            domain_id=domain.id,
            content="JavaScript for web development",
            chunk_index=1,
        )

        # Ищем по тексту
        results = await chunk_repo.search_fts("Python")

        assert len(results) >= 1
        chunk, _rank = results[0]
        assert "Python" in chunk.content

    async def test_search_vector(
        self,
        db_session: AsyncSession,
        sample_domain: dict[str, Any],
        sample_embedding: list[float],
    ) -> None:
        """Проверить векторный поиск."""
        domain_repo = DomainRepository(db_session)
        chunk_repo = ChunkRepository(db_session)

        domain = await domain_repo.create_domain(**sample_domain)

        # Создаём чанк с embedding
        await chunk_repo.create_chunk(
            domain_id=domain.id,
            content="Test content with embedding",
            chunk_index=0,
            embedding=sample_embedding,
        )

        # Ищем по вектору
        results = await chunk_repo.search_vector(
            sample_embedding,
            limit=5,
        )

        assert len(results) >= 1
        _chunk, distance = results[0]
        assert distance == 0.0  # Тот же вектор

    async def test_create_batch(
        self,
        db_session: AsyncSession,
        sample_domain: dict[str, Any],
    ) -> None:
        """Проверить batch создание чанков."""
        domain_repo = DomainRepository(db_session)
        chunk_repo = ChunkRepository(db_session)

        domain = await domain_repo.create_domain(**sample_domain)

        chunks_data = [
            {"domain_id": domain.id, "content": f"Batch chunk {i}", "chunk_index": i}
            for i in range(10)
        ]

        count = await chunk_repo.create_batch(chunks_data)
        assert count == 10

        total = await chunk_repo.count_by_domain(domain.id)
        assert total == 10

    async def test_delete_by_domain(
        self,
        db_session: AsyncSession,
        sample_domain: dict[str, Any],
    ) -> None:
        """Проверить удаление чанков по домену."""
        domain_repo = DomainRepository(db_session)
        chunk_repo = ChunkRepository(db_session)

        domain = await domain_repo.create_domain(**sample_domain)

        # Создаём чанки
        for i in range(5):
            await chunk_repo.create_chunk(
                domain_id=domain.id,
                content=f"Chunk {i}",
                chunk_index=i,
            )

        # Удаляем
        deleted = await chunk_repo.delete_by_domain(domain.id)
        assert deleted == 5

        remaining = await chunk_repo.count_by_domain(domain.id)
        assert remaining == 0


class TestConversationRepository:
    """Тесты ConversationRepository."""

    async def test_create_conversation(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Проверить создание диалога."""
        repo = ConversationRepository(db_session)

        thread_id = f"test-thread-{uuid.uuid4().hex[:8]}"

        conv = await repo.upsert(
            thread_id=thread_id,
            title="Test Conversation",
            messages=[],
        )

        assert conv.id is not None
        assert conv.thread_id == thread_id
        assert conv.title == "Test Conversation"

    async def test_upsert_update(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Проверить upsert обновление."""
        repo = ConversationRepository(db_session)

        thread_id = f"test-thread-{uuid.uuid4().hex[:8]}"

        # Создаём
        created = await repo.upsert(
            thread_id=thread_id,
            title="Original Title",
        )

        # Обновляем
        updated = await repo.upsert(
            thread_id=thread_id,
            title="Updated Title",
        )

        assert updated.id == created.id
        assert updated.title == "Updated Title"

    async def test_add_message(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Проверить добавление сообщения."""
        repo = ConversationRepository(db_session)

        thread_id = f"test-thread-{uuid.uuid4().hex[:8]}"

        await repo.upsert(thread_id=thread_id)

        updated = await repo.add_message(
            thread_id=thread_id,
            role="user",
            content="Hello!",
        )

        assert updated is not None
        assert len(updated.messages) == 1
        assert updated.messages[0]["role"] == "user"
        assert updated.messages[0]["content"] == "Hello!"

    async def test_get_by_thread(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Проверить поиск по thread_id."""
        repo = ConversationRepository(db_session)

        thread_id = f"test-thread-{uuid.uuid4().hex[:8]}"

        await repo.upsert(thread_id=thread_id, title="Test")

        found = await repo.get_by_thread(thread_id)

        assert found is not None
        assert found.thread_id == thread_id

    async def test_delete_by_thread(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Проверить удаление по thread_id."""
        repo = ConversationRepository(db_session)

        thread_id = f"test-thread-{uuid.uuid4().hex[:8]}"

        await repo.upsert(thread_id=thread_id)

        deleted = await repo.delete_by_thread(thread_id)
        assert deleted is True

        found = await repo.get_by_thread(thread_id)
        assert found is None


class TestJobRepository:
    """Тесты JobRepository."""

    async def test_create_job(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Проверить создание задачи."""
        repo = JobRepository(db_session)

        job = await repo.create_job(
            tool_name="banner.generate",
            input_params={"text": "Test banner"},
        )

        assert job.id is not None
        assert job.tool_name == "banner.generate"
        assert job.status == JobStatus.QUEUED
        assert job.progress == 0

    async def test_job_lifecycle(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Проверить жизненный цикл задачи."""
        repo = JobRepository(db_session)

        # Создаём
        job = await repo.create_job(
            tool_name="test.tool",
            input_params={"key": "value"},
        )
        assert job.status == JobStatus.QUEUED

        # Запускаем
        job = await repo.start_job(job.id)
        assert job is not None
        assert job.status == JobStatus.RUNNING
        assert job.started_at is not None

        # Обновляем прогресс
        job = await repo.update_progress(job.id, 50, "Processing...")
        assert job is not None
        assert job.progress == 50
        assert job.current_step == "Processing..."

        # Завершаем
        job = await repo.complete_job(job.id, {"result": "success"})
        assert job is not None
        assert job.status == JobStatus.COMPLETED
        assert job.progress == 100
        assert job.completed_at is not None
        assert job.result == {"result": "success"}

    async def test_fail_job(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Проверить обработку ошибки."""
        repo = JobRepository(db_session)

        job = await repo.create_job(
            tool_name="failing.tool",
            input_params={},
        )

        await repo.start_job(job.id)

        job = await repo.fail_job(job.id, "Something went wrong")

        assert job is not None
        assert job.status == JobStatus.FAILED
        assert job.error == "Something went wrong"
        assert job.completed_at is not None

    async def test_get_pending(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Проверить получение задач в очереди."""
        repo = JobRepository(db_session)

        # Создаём несколько задач
        for i in range(3):
            await repo.create_job(
                tool_name=f"tool.{i}",
                input_params={},
            )

        pending = await repo.get_pending(limit=10)

        assert len(pending) == 3
        assert all(j.status == JobStatus.QUEUED for j in pending)

    async def test_get_by_thread(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Проверить получение задач по thread."""
        repo = JobRepository(db_session)

        thread_id = f"test-thread-{uuid.uuid4().hex[:8]}"

        # Создаём задачи для thread
        for i in range(2):
            await repo.create_job(
                tool_name=f"tool.{i}",
                input_params={},
                thread_id=thread_id,
            )

        # Создаём задачу без thread
        await repo.create_job(
            tool_name="other.tool",
            input_params={},
        )

        jobs = await repo.get_by_thread(thread_id)

        assert len(jobs) == 2
        assert all(j.thread_id == thread_id for j in jobs)


class TestTransactionRollback:
    """Тесты транзакций и rollback."""

    async def test_rollback_on_error(
        self,
        db_session: AsyncSession,
        sample_domain: dict[str, Any],
    ) -> None:
        """Проверить откат при ошибке."""
        repo = DomainRepository(db_session)

        # Создаём домен
        domain = await repo.create_domain(**sample_domain)
        domain_id = domain.id

        # Симулируем ошибку и rollback
        await db_session.rollback()

        # После rollback домен не должен существовать
        found = await repo.get(domain_id)
        assert found is None
