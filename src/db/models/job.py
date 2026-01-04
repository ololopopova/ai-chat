"""Модель Job — фоновые задачи.

Job отслеживает состояние и прогресс долгих операций
(например, генерация баннера, индексация документов).
"""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import Enum, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class JobStatus(str, enum.Enum):
    """Статусы задачи."""

    QUEUED = "queued"  # В очереди
    RUNNING = "running"  # Выполняется
    COMPLETED = "completed"  # Завершена успешно
    FAILED = "failed"  # Завершена с ошибкой
    CANCELLED = "cancelled"  # Отменена


class Job(Base):
    """
    Модель фоновой задачи.

    Attributes:
        id: UUID первичный ключ.
        thread_id: Связь с диалогом (опционально).
        tool_name: Название инструмента (например, "banner.generate").
        status: Статус задачи (queued/running/completed/failed/cancelled).
        progress: Прогресс выполнения 0-100.
        current_step: Текущий шаг выполнения.
        input_params: Входные параметры задачи.
        result: Результат выполнения.
        error: Текст ошибки (при failed).
        created_at: Время создания.
        started_at: Время начала выполнения.
        completed_at: Время завершения.
    """

    # Связь с диалогом (опционально)
    thread_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="ID связанного диалога",
    )

    # Название инструмента
    tool_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Название инструмента",
    )

    # Статус задачи
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", create_constraint=True),
        nullable=False,
        default=JobStatus.QUEUED,
        index=True,
        comment="Статус задачи",
    )

    # Прогресс выполнения (0-100)
    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Прогресс 0-100",
    )

    # Текущий шаг
    current_step: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Текущий шаг выполнения",
    )

    # Входные параметры
    input_params: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Входные параметры",
    )

    # Результат выполнения
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        comment="Результат выполнения",
    )

    # Текст ошибки
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Текст ошибки",
    )

    # Время начала выполнения
    started_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Время начала",
    )

    # Время завершения
    completed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Время завершения",
    )

    # Индексы
    __table_args__ = (
        Index("ix_jobs_created_at", "created_at"),
        Index("ix_jobs_status_created_at", "status", "created_at"),
    )

    def __repr__(self) -> str:
        """Строковое представление задачи."""
        return (
            f"<Job(id={self.id}, tool='{self.tool_name}', "
            f"status={self.status.value}, progress={self.progress}%)>"
        )

    @property
    def is_finished(self) -> bool:
        """Проверить, завершена ли задача."""
        return self.status in (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        )

    @property
    def is_running(self) -> bool:
        """Проверить, выполняется ли задача."""
        return self.status == JobStatus.RUNNING

    @property
    def is_successful(self) -> bool:
        """Проверить, успешно ли завершена задача."""
        return self.status == JobStatus.COMPLETED

    def start(self) -> None:
        """Отметить начало выполнения задачи."""
        from datetime import UTC, datetime

        self.status = JobStatus.RUNNING
        self.started_at = datetime.now(UTC)

    def complete(self, result: dict[str, Any] | None = None) -> None:
        """
        Отметить успешное завершение задачи.

        Args:
            result: Результат выполнения.
        """
        from datetime import UTC, datetime

        self.status = JobStatus.COMPLETED
        self.progress = 100
        self.completed_at = datetime.now(UTC)
        if result is not None:
            self.result = result

    def fail(self, error: str) -> None:
        """
        Отметить неудачное завершение задачи.

        Args:
            error: Текст ошибки.
        """
        from datetime import UTC, datetime

        self.status = JobStatus.FAILED
        self.completed_at = datetime.now(UTC)
        self.error = error

    def cancel(self) -> None:
        """Отменить задачу."""
        from datetime import UTC, datetime

        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.now(UTC)

    def update_progress(self, progress: int, step: str | None = None) -> None:
        """
        Обновить прогресс выполнения.

        Args:
            progress: Новое значение прогресса (0-100).
            step: Текущий шаг (опционально).
        """
        self.progress = max(0, min(100, progress))
        if step is not None:
            self.current_step = step
