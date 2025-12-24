#!/usr/bin/env python3
"""Заполнение доменов из YAML конфигурации.

Скрипт для синхронизации доменов из config/domains.yaml в базу данных.

Usage:
    python scripts/seed_domains.py
    python scripts/seed_domains.py --dry-run  # Только показать изменения
    python scripts/seed_domains.py --clear    # Удалить все домены перед импортом
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml

from src.core.config import get_settings
from src.core.logging import setup_logging

# Настраиваем логирование
setup_logging()
logger = logging.getLogger(__name__)


def load_domains_yaml(config_path: Path) -> list[dict[str, Any]]:
    """
    Загрузить домены из YAML файла.

    Args:
        config_path: Путь к файлу конфигурации.

    Returns:
        Список доменов из конфигурации.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Поддержка двух форматов: "domains" (старый) и "agents" (новый)
    domains: list[dict[str, Any]] = config.get("domains", [])

    # Если нет "domains", попробовать "agents" (для config/domains.yaml с агентами)
    if not domains:
        agents: list[dict[str, Any]] = config.get("agents", [])
        # Конвертировать агентов в домены
        for agent in agents:
            # Извлечь первый google_doc_url из списка, если есть
            google_docs = agent.get("google_docs", [])
            google_doc_url = google_docs[0] if google_docs else ""

            # Пропустить агентов без документов
            if not google_doc_url:
                continue

            domains.append(
                {
                    "id": agent.get("id"),
                    "name": agent.get("name"),
                    "description": agent.get("description"),
                    "google_doc_url": google_doc_url,
                    "enabled": agent.get("enabled", True),
                }
            )

    logger.info(f"Loaded {len(domains)} domains from {config_path}")

    return domains


async def seed_domains(
    domains_config: list[dict[str, Any]],
    *,
    dry_run: bool = False,
    clear_first: bool = False,
) -> None:
    """
    Синхронизировать домены в базу данных.

    Args:
        domains_config: Список доменов из YAML.
        dry_run: Только показать изменения, не применять.
        clear_first: Удалить все домены перед импортом.
    """
    from src.db.engine import create_engine_from_settings
    from src.db.session import AsyncSessionFactory
    from src.repositories.domain_repository import DomainRepository

    settings = get_settings()
    engine = create_engine_from_settings(settings)
    session_factory = AsyncSessionFactory(engine)

    try:
        async with session_factory.get_transaction() as session:
            repo = DomainRepository(session)

            # Удаляем все домены, если нужно
            if clear_first:
                if dry_run:
                    logger.info("Would delete all existing domains")
                else:
                    existing = await repo.get_all()
                    for domain in existing:
                        await repo.delete(domain.id)
                    logger.info(f"Deleted {len(existing)} existing domains")

            # Обрабатываем каждый домен из конфигурации
            created = 0
            updated = 0
            skipped = 0

            for domain_data in domains_config:
                # Маппинг YAML полей на модель
                slug = domain_data.get("id", "")
                name = domain_data.get("name", "")
                description = domain_data.get("description")
                google_doc_url = domain_data.get("google_doc_url", "")
                is_active = domain_data.get("enabled", True)

                if not slug or not name or not google_doc_url:
                    logger.warning(f"Skipping invalid domain: {domain_data}")
                    skipped += 1
                    continue

                # Проверяем, существует ли домен
                existing_domain = await repo.get_by_slug(slug)

                if existing_domain:
                    if dry_run:
                        logger.info(f"Would update domain: {slug}")
                    else:
                        await repo.update_domain(
                            existing_domain.id,
                            name=name,
                            description=description,
                            google_doc_url=google_doc_url,
                            is_active=is_active,
                        )
                        logger.info(f"Updated domain: {slug}")
                    updated += 1
                else:
                    if dry_run:
                        logger.info(f"Would create domain: {slug}")
                    else:
                        await repo.create_domain(
                            name=name,
                            slug=slug,
                            description=description,
                            google_doc_url=google_doc_url,
                            is_active=is_active,
                        )
                        logger.info(f"Created domain: {slug}")
                    created += 1

            if dry_run:
                logger.info(
                    f"Dry run complete: {created} to create, {updated} to update, {skipped} skipped"
                )
                # Откатываем транзакцию при dry-run
                await session.rollback()
            else:
                logger.info(
                    f"Seeding complete: {created} created, {updated} updated, {skipped} skipped"
                )

    finally:
        await engine.dispose()


async def list_domains() -> None:
    """Показать все домены в базе данных."""
    from src.db.engine import create_engine_from_settings
    from src.db.session import AsyncSessionFactory
    from src.repositories.domain_repository import DomainRepository

    settings = get_settings()
    engine = create_engine_from_settings(settings)
    session_factory = AsyncSessionFactory(engine)

    try:
        async with session_factory.get_session() as session:
            repo = DomainRepository(session)
            domains = await repo.get_all_ordered()

            if not domains:
                logger.info("No domains in database")
                return

            logger.info(f"Found {len(domains)} domains in database:")
            for domain in domains:
                status = "✅" if domain.is_active else "❌"
                logger.info(f"  {status} {domain.slug}: {domain.name}")

    finally:
        await engine.dispose()


async def main() -> None:
    """Главная функция скрипта."""
    parser = argparse.ArgumentParser(description="Seed domains from YAML config")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete all existing domains before seeding",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all domains in database",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to domains YAML config (default: config/domains.yaml)",
    )

    args = parser.parse_args()

    settings = get_settings()

    if args.list:
        await list_domains()
        return

    # Определяем путь к конфигурации
    config_path = args.config or settings.domains_config_path

    try:
        domains_config = load_domains_yaml(config_path)
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    if not domains_config:
        logger.warning("No domains found in config file")
        return

    await seed_domains(
        domains_config,
        dry_run=args.dry_run,
        clear_first=args.clear,
    )


if __name__ == "__main__":
    asyncio.run(main())
