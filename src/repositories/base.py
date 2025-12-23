"""Базовый репозиторий с generic CRUD операциями.

Реализует паттерн Repository для типизированного доступа к данным.
"""

import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import ColumnElement, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import Base

# TypeVar для generic модели
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):  # noqa: UP046
    """
    Базовый репозиторий с CRUD операциями.

    Attributes:
        model: Класс ORM модели.
        session: AsyncSession для работы с БД.

    Features:
        - CRUD операции (get, create, update, delete)
        - Пагинация (skip/limit)
        - Фильтрация (find_by, find_one_by)
        - Batch операции (create_many, update_many, delete_many)
        - Подсчёт и проверка существования

    Example:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(User, session)
    """

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        """
        Инициализировать репозиторий.

        Args:
            model: Класс ORM модели.
            session: AsyncSession для работы с БД.
        """
        self.model = model
        self.session = session

    async def get(self, id: uuid.UUID) -> ModelType | None:
        """
        Получить запись по ID.

        Args:
            id: UUID записи.

        Returns:
            Модель или None, если не найдена.
        """
        return await self.session.get(self.model, id)

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """
        Получить список записей с пагинацией.

        Args:
            skip: Количество записей для пропуска.
            limit: Максимальное количество записей.

        Returns:
            Список моделей.
        """
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **data: Any) -> ModelType:
        """
        Создать новую запись.

        Args:
            **data: Данные для создания записи.

        Returns:
            Созданная модель.
        """
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(
        self,
        id: uuid.UUID,
        **data: Any,
    ) -> ModelType | None:
        """
        Обновить запись по ID.

        Args:
            id: UUID записи.
            **data: Данные для обновления.

        Returns:
            Обновлённая модель или None, если не найдена.
        """
        # Фильтруем None значения
        update_data = {k: v for k, v in data.items() if v is not None}

        if not update_data:
            return await self.get(id)

        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**update_data)
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()

        row = result.scalar_one_or_none()
        return row

    async def delete(self, id: uuid.UUID) -> bool:
        """
        Удалить запись по ID.

        Args:
            id: UUID записи.

        Returns:
            True если запись удалена, False если не найдена.
        """
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return bool(result.rowcount and result.rowcount > 0)  # type: ignore[attr-defined]

    async def count(self) -> int:
        """
        Подсчитать общее количество записей.

        Returns:
            Количество записей в таблице.
        """
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def exists(self, id: uuid.UUID) -> bool:
        """
        Проверить существование записи по ID.

        Args:
            id: UUID записи.

        Returns:
            True если запись существует.
        """
        stmt = select(func.count()).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return (result.scalar() or 0) > 0

    # ==========================================
    # Фильтрация
    # ==========================================

    async def find_by(
        self,
        *filters: ColumnElement[bool],
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """
        Найти записи по условиям.

        Args:
            *filters: SQLAlchemy условия фильтрации.
            skip: Количество записей для пропуска.
            limit: Максимальное количество записей.

        Returns:
            Список найденных моделей.

        Example:
            users = await repo.find_by(
                User.is_active == True,
                User.role == "admin",
                limit=10,
            )
        """
        stmt = select(self.model).where(*filters).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_one_by(
        self,
        *filters: ColumnElement[bool],
    ) -> ModelType | None:
        """
        Найти одну запись по условиям.

        Args:
            *filters: SQLAlchemy условия фильтрации.

        Returns:
            Найденная модель или None.
        """
        stmt = select(self.model).where(*filters).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_by(self, *filters: ColumnElement[bool]) -> int:
        """
        Подсчитать количество записей по условиям.

        Args:
            *filters: SQLAlchemy условия фильтрации.

        Returns:
            Количество записей.
        """
        stmt = select(func.count()).select_from(self.model).where(*filters)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    # ==========================================
    # Batch операции
    # ==========================================

    async def create_many(self, items: Sequence[dict[str, Any]]) -> list[ModelType]:
        """
        Создать несколько записей за один раз.

        Args:
            items: Список словарей с данными для создания.

        Returns:
            Список созданных моделей.

        Example:
            users = await repo.create_many([
                {"name": "Alice", "email": "alice@example.com"},
                {"name": "Bob", "email": "bob@example.com"},
            ])
        """
        instances = [self.model(**data) for data in items]
        self.session.add_all(instances)
        await self.session.flush()

        # Refresh all instances to get generated values
        for instance in instances:
            await self.session.refresh(instance)

        return instances

    async def delete_many(self, ids: Sequence[uuid.UUID]) -> int:
        """
        Удалить несколько записей по ID.

        Args:
            ids: Список UUID для удаления.

        Returns:
            Количество удалённых записей.
        """
        if not ids:
            return 0

        stmt = delete(self.model).where(self.model.id.in_(ids))
        result = await self.session.execute(stmt)
        await self.session.flush()
        # CursorResult имеет rowcount, но Result[Any] - нет в типах
        return getattr(result, "rowcount", 0) or 0

    async def get_by_ids(self, ids: Sequence[uuid.UUID]) -> list[ModelType]:
        """
        Получить записи по списку ID.

        Args:
            ids: Список UUID для получения.

        Returns:
            Список найденных моделей (порядок не гарантирован).
        """
        if not ids:
            return []

        stmt = select(self.model).where(self.model.id.in_(ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
