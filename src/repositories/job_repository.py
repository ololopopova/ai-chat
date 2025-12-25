"""Репозиторий для работы с задачами.

Реализует CRUD и методы управления жизненным циклом Job модели.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.job import Job, JobStatus
from src.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    """
    Репозиторий для работы с фоновыми задачами.

    Расширяет BaseRepository методами для:
    - Управления статусом и прогрессом
    - Получения задач по фильтрам
    - Работы с очередью
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализировать репозиторий.

        Args:
            session: AsyncSession для работы с БД.
        """
        super().__init__(Job, session)

    async def create_job(
        self,
        *,
        tool_name: str,
        input_params: dict[str, Any],
        thread_id: str | None = None,
    ) -> Job:
        """
        Создать новую задачу.

        Args:
            tool_name: Название инструмента.
            input_params: Входные параметры.
            thread_id: Связь с диалогом (опционально).

        Returns:
            Созданная задача в статусе QUEUED.
        """
        return await self.create(
            tool_name=tool_name,
            input_params=input_params,
            thread_id=thread_id,
            status=JobStatus.QUEUED,
            progress=0,
        )

    async def update_status(
        self,
        id: uuid.UUID,
        status: JobStatus,
    ) -> Job | None:
        """
        Обновить статус задачи.

        Args:
            id: UUID задачи.
            status: Новый статус.

        Returns:
            Обновлённая задача или None.
        """
        job = await self.get(id)
        if job is None:
            return None

        if status == JobStatus.RUNNING:
            job.start()
        elif status == JobStatus.COMPLETED:
            job.complete()
        elif status == JobStatus.FAILED:
            job.fail("Status changed to FAILED")
        elif status == JobStatus.CANCELLED:
            job.cancel()
        else:
            job.status = status

        await self.session.flush()
        return job

    async def update_progress(
        self,
        id: uuid.UUID,
        progress: int,
        step: str | None = None,
    ) -> Job | None:
        """
        Обновить прогресс задачи.

        Args:
            id: UUID задачи.
            progress: Новое значение прогресса (0-100).
            step: Текущий шаг (опционально).

        Returns:
            Обновлённая задача или None.
        """
        job = await self.get(id)
        if job is None:
            return None

        job.update_progress(progress, step)
        await self.session.flush()
        return job

    async def complete_job(
        self,
        id: uuid.UUID,
        result: dict[str, Any] | None = None,
    ) -> Job | None:
        """
        Отметить задачу как завершённую.

        Args:
            id: UUID задачи.
            result: Результат выполнения.

        Returns:
            Обновлённая задача или None.
        """
        job = await self.get(id)
        if job is None:
            return None

        job.complete(result)
        await self.session.flush()
        return job

    async def fail_job(
        self,
        id: uuid.UUID,
        error: str,
    ) -> Job | None:
        """
        Отметить задачу как неудачную.

        Args:
            id: UUID задачи.
            error: Текст ошибки.

        Returns:
            Обновлённая задача или None.
        """
        job = await self.get(id)
        if job is None:
            return None

        job.fail(error)
        await self.session.flush()
        return job

    async def cancel_job(self, id: uuid.UUID) -> Job | None:
        """
        Отменить задачу.

        Args:
            id: UUID задачи.

        Returns:
            Обновлённая задача или None.
        """
        job = await self.get(id)
        if job is None:
            return None

        job.cancel()
        await self.session.flush()
        return job

    async def get_by_thread(
        self,
        thread_id: str,
        *,
        limit: int = 10,
    ) -> list[Job]:
        """
        Получить задачи по thread_id.

        Args:
            thread_id: Внешний идентификатор thread.
            limit: Максимальное количество результатов.

        Returns:
            Список задач, отсортированных по created_at DESC.
        """
        stmt = (
            select(Job)
            .where(Job.thread_id == thread_id)
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_pending(self, *, limit: int = 10) -> list[Job]:
        """
        Получить задачи в очереди (QUEUED).

        Args:
            limit: Максимальное количество результатов.

        Returns:
            Список задач в очереди, отсортированных по created_at.
        """
        stmt = (
            select(Job)
            .where(Job.status == JobStatus.QUEUED)
            .order_by(Job.created_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_running(self, *, limit: int = 10) -> list[Job]:
        """
        Получить выполняющиеся задачи.

        Args:
            limit: Максимальное количество результатов.

        Returns:
            Список выполняющихся задач.
        """
        stmt = (
            select(Job)
            .where(Job.status == JobStatus.RUNNING)
            .order_by(Job.started_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_status(
        self,
        status: JobStatus,
        *,
        limit: int = 100,
    ) -> list[Job]:
        """
        Получить задачи по статусу.

        Args:
            status: Статус для фильтрации.
            limit: Максимальное количество результатов.

        Returns:
            Список задач с указанным статусом.
        """
        stmt = (
            select(Job)
            .where(Job.status == status)
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_tool(
        self,
        tool_name: str,
        *,
        limit: int = 100,
    ) -> list[Job]:
        """
        Получить задачи по названию инструмента.

        Args:
            tool_name: Название инструмента.
            limit: Максимальное количество результатов.

        Returns:
            Список задач для указанного инструмента.
        """
        stmt = (
            select(Job)
            .where(Job.tool_name == tool_name)
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def start_job(self, id: uuid.UUID) -> Job | None:
        """
        Запустить задачу (перевести в RUNNING).

        Args:
            id: UUID задачи.

        Returns:
            Обновлённая задача или None.
        """
        job = await self.get(id)
        if job is None:
            return None

        job.start()
        await self.session.flush()
        return job
