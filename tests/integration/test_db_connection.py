"""Тесты подключения к базе данных.

Проверяют:
- Подключение к PostgreSQL
- Наличие расширений
- Работу connection pool
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


class TestDatabaseConnection:
    """Тесты подключения к базе данных."""

    async def test_can_connect_to_database(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Проверить, что можем подключиться к БД."""
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    async def test_pgvector_extension_installed(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Проверить, что расширение pgvector установлено."""
        result = await db_session.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        )
        assert result.scalar() is not None, "pgvector extension is not installed"

    async def test_pg_trgm_extension_installed(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Проверить, что расширение pg_trgm установлено."""
        result = await db_session.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")
        )
        assert result.scalar() is not None, "pg_trgm extension is not installed"

    async def test_can_create_vector(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Проверить, что можем создавать векторы."""
        result = await db_session.execute(text("SELECT '[1,2,3]'::vector"))
        assert result.scalar() is not None

    async def test_tables_exist(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Проверить, что все таблицы созданы."""
        result = await db_session.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
        )
        tables = [row[0] for row in result.fetchall()]

        expected_tables = ["chunks", "conversations", "domains", "jobs"]
        for table in expected_tables:
            assert table in tables, f"Table '{table}' not found"

    async def test_job_status_enum_exists(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Проверить, что ENUM job_status создан."""
        result = await db_session.execute(
            text("""
                SELECT 1 FROM pg_type
                WHERE typname = 'job_status'
            """)
        )
        assert result.scalar() is not None, "ENUM job_status not found"


class TestConnectionPool:
    """Тесты connection pool."""

    async def test_multiple_connections(
        self,
        db_engine,
    ) -> None:
        """Проверить работу нескольких соединений."""
        import asyncio

        async def query(n: int) -> int:
            async with db_engine.connect() as conn:
                result = await conn.execute(text(f"SELECT {n}"))
                return result.scalar()

        # Запускаем несколько запросов параллельно
        results = await asyncio.gather(*[query(i) for i in range(5)])
        assert results == [0, 1, 2, 3, 4]

    async def test_pool_reuses_connections(
        self,
        db_engine,
    ) -> None:
        """Проверить, что пул переиспользует соединения."""
        pool = db_engine.pool

        # Делаем несколько запросов
        for _ in range(5):
            async with db_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

        # Проверяем, что не создали слишком много соединений
        assert pool.checkedin() <= pool.size() + 1
