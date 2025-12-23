"""Base model class для SQLAlchemy ORM.

Определяет базовый класс с общими полями и naming conventions.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, MetaData
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

# Naming conventions для автоматического именования constraints
# Это важно для Alembic migrations
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Базовый класс для всех ORM моделей.

    Attributes:
        id: UUID первичный ключ (генерируется автоматически).
        created_at: Время создания записи (UTC).

    Note:
        Все таблицы наследуют эти поля.
        Для моделей с updated_at используйте TimestampMixin.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # Автоматическое имя таблицы из имени класса
    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        """Генерировать имя таблицы из имени класса (snake_case + 's')."""
        # CamelCase -> snake_case + pluralize
        name = cls.__name__
        # Domain -> domains, Chunk -> chunks, etc.
        result = ""
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                result += "_"
            result += char.lower()
        return result + "s"

    # Общие поля для всех моделей
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Строковое представление модели."""
        return f"<{self.__class__.__name__}(id={self.id})>"

    def to_dict(self) -> dict[str, Any]:
        """Преобразовать модель в словарь."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class TimestampMixin:
    """
    Mixin для моделей с updated_at.

    Добавляет поле updated_at, которое обновляется при каждом изменении.
    """

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
