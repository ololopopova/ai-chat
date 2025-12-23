#!/usr/bin/env python3
"""Инициализация базы данных.

Скрипт для создания таблиц и применения миграций.

Usage:
    python scripts/init_db.py
    python scripts/init_db.py --check  # Только проверка подключения
    python scripts/init_db.py --drop   # Удалить все таблицы (ОПАСНО!)
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import get_settings
from src.core.logging import setup_logging

# Настраиваем логирование
setup_logging()
logger = logging.getLogger(__name__)


async def check_connection() -> bool:
    """Проверить подключение к базе данных."""
    from src.db.engine import check_database_connection, create_engine_from_settings

    settings = get_settings()
    engine = create_engine_from_settings(settings)

    try:
        is_ok = await check_database_connection(engine, timeout_seconds=10.0)
        if is_ok:
            logger.info("✅ Database connection successful")
        else:
            logger.error("❌ Database connection failed")
        return is_ok
    finally:
        await engine.dispose()


async def check_extensions() -> bool:
    """Проверить наличие необходимых расширений PostgreSQL."""
    from sqlalchemy import text

    from src.db.engine import create_engine_from_settings

    settings = get_settings()
    engine = create_engine_from_settings(settings)

    try:
        async with engine.connect() as conn:
            # Проверяем pgvector
            result = await conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
            has_vector = result.scalar() is not None

            # Проверяем pg_trgm
            result = await conn.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")
            )
            has_trgm = result.scalar() is not None

            if has_vector:
                logger.info("✅ Extension 'vector' (pgvector) is installed")
            else:
                logger.warning("⚠️ Extension 'vector' (pgvector) is NOT installed")

            if has_trgm:
                logger.info("✅ Extension 'pg_trgm' is installed")
            else:
                logger.warning("⚠️ Extension 'pg_trgm' is NOT installed")

            return has_vector and has_trgm
    finally:
        await engine.dispose()


async def drop_all_tables() -> None:
    """Удалить все таблицы (ОПАСНО!)."""
    from sqlalchemy import text

    from src.db.base import Base
    from src.db.engine import create_engine_from_settings

    # Импортируем модели для metadata
    from src.db.models import Chunk, Conversation, Domain, Job  # noqa: F401

    settings = get_settings()
    engine = create_engine_from_settings(settings)

    try:
        logger.warning("⚠️ Dropping all tables...")

        async with engine.begin() as conn:
            # Удаляем все таблицы
            await conn.run_sync(Base.metadata.drop_all)

            # Удаляем ENUM типы
            await conn.execute(text("DROP TYPE IF EXISTS job_status CASCADE"))

        logger.info("✅ All tables dropped")
    finally:
        await engine.dispose()


async def create_all_tables() -> None:
    """Создать все таблицы напрямую (без миграций)."""
    from src.db.base import Base
    from src.db.engine import create_engine_from_settings

    # Импортируем модели для metadata
    from src.db.models import Chunk, Conversation, Domain, Job  # noqa: F401

    settings = get_settings()
    engine = create_engine_from_settings(settings)

    try:
        logger.info("Creating all tables...")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("✅ All tables created")
    finally:
        await engine.dispose()


def run_migrations() -> None:
    """Применить миграции Alembic."""
    import subprocess

    logger.info("Running Alembic migrations...")

    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        logger.info("✅ Migrations applied successfully")
        if result.stdout:
            logger.info(result.stdout)
    else:
        logger.error("❌ Migration failed")
        if result.stderr:
            logger.error(result.stderr)
        sys.exit(1)


async def main() -> None:
    """Главная функция скрипта."""
    parser = argparse.ArgumentParser(description="Initialize database")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check connection and extensions",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all tables (DANGEROUS!)",
    )
    parser.add_argument(
        "--no-migrate",
        action="store_true",
        help="Skip Alembic migrations, use SQLAlchemy create_all",
    )

    args = parser.parse_args()

    settings = get_settings()
    logger.info(f"Database URL: {settings.database_url.split('@')[-1]}")  # Без пароля

    # Проверяем подключение
    if not await check_connection():
        logger.error("Cannot connect to database. Is PostgreSQL running?")
        logger.info("Hint: Run 'docker compose -f docker/docker-compose.yml up -d'")
        sys.exit(1)

    # Проверяем расширения
    await check_extensions()

    if args.check:
        return

    if args.drop:
        confirm = input("⚠️ Are you sure you want to DROP ALL TABLES? (yes/no): ")
        if confirm.lower() != "yes":
            logger.info("Aborted")
            return
        await drop_all_tables()

    if args.no_migrate:
        await create_all_tables()
    else:
        run_migrations()

    logger.info("✅ Database initialization complete")


if __name__ == "__main__":
    asyncio.run(main())
