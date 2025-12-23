"""Репозиторий для работы с доменами.

Реализует CRUD и специфичные методы для Domain модели.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.domain import Domain
from src.repositories.base import BaseRepository


class DomainRepository(BaseRepository[Domain]):
    """
    Репозиторий для работы с доменами знаний.

    Расширяет BaseRepository методами для:
    - Поиска по slug
    - Получения активных доменов
    - Batch операций
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализировать репозиторий.

        Args:
            session: AsyncSession для работы с БД.
        """
        super().__init__(Domain, session)

    async def get_by_slug(self, slug: str) -> Domain | None:
        """
        Получить домен по slug.

        Args:
            slug: URL-friendly идентификатор домена.

        Returns:
            Domain или None, если не найден.
        """
        stmt = select(Domain).where(Domain.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active(self, *, skip: int = 0, limit: int = 100) -> list[Domain]:
        """
        Получить все активные домены.

        Args:
            skip: Количество записей для пропуска.
            limit: Максимальное количество записей.

        Returns:
            Список активных доменов.
        """
        stmt = (
            select(Domain)
            .where(Domain.is_active.is_(True))
            .order_by(Domain.name)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_ordered(self, *, skip: int = 0, limit: int = 100) -> list[Domain]:
        """
        Получить все домены, отсортированные по имени.

        Args:
            skip: Количество записей для пропуска.
            limit: Максимальное количество записей.

        Returns:
            Список доменов.
        """
        stmt = select(Domain).order_by(Domain.name).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_domain(
        self,
        *,
        name: str,
        slug: str,
        google_doc_url: str,
        description: str | None = None,
        is_active: bool = True,
    ) -> Domain:
        """
        Создать новый домен.

        Args:
            name: Название домена.
            slug: URL-friendly идентификатор.
            google_doc_url: Ссылка на Google Doc.
            description: Описание домена.
            is_active: Активен ли домен.

        Returns:
            Созданный домен.
        """
        return await self.create(
            name=name,
            slug=slug,
            description=description,
            google_doc_url=google_doc_url,
            is_active=is_active,
        )

    async def update_domain(
        self,
        id: uuid.UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        google_doc_url: str | None = None,
        is_active: bool | None = None,
    ) -> Domain | None:
        """
        Обновить домен.

        Args:
            id: UUID домена.
            name: Новое название.
            description: Новое описание.
            google_doc_url: Новая ссылка на Google Doc.
            is_active: Активен ли домен.

        Returns:
            Обновлённый домен или None.
        """
        update_data: dict[str, str | bool] = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if google_doc_url is not None:
            update_data["google_doc_url"] = google_doc_url
        if is_active is not None:
            update_data["is_active"] = is_active

        if not update_data:
            return await self.get(id)

        return await self.update(id, **update_data)

    async def activate(self, id: uuid.UUID) -> Domain | None:
        """
        Активировать домен.

        Args:
            id: UUID домена.

        Returns:
            Обновлённый домен или None.

        Note:
            updated_at обновляется автоматически через TimestampMixin.
        """
        return await self.update(id, is_active=True)

    async def deactivate(self, id: uuid.UUID) -> Domain | None:
        """
        Деактивировать домен.

        Args:
            id: UUID домена.

        Returns:
            Обновлённый домен или None.

        Note:
            updated_at обновляется автоматически через TimestampMixin.
        """
        return await self.update(id, is_active=False)

    async def slug_exists(self, slug: str, exclude_id: uuid.UUID | None = None) -> bool:
        """
        Проверить, существует ли домен с таким slug.

        Args:
            slug: Slug для проверки.
            exclude_id: ID домена для исключения (при обновлении).

        Returns:
            True если slug уже используется.
        """
        from sqlalchemy import func

        stmt = select(func.count()).where(Domain.slug == slug)

        if exclude_id is not None:
            stmt = stmt.where(Domain.id != exclude_id)

        result = await self.session.execute(stmt)
        return (result.scalar() or 0) > 0
