"""CLI команда для индексации документов.

Использование:
    python scripts/ingest.py --agent products
    python scripts/ingest.py --all
    python scripts/ingest.py --agent products -v
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Добавить корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.logging import get_logger  # noqa: E402
from src.db.session import get_session_factory  # noqa: E402
from src.repositories.unit_of_work import UnitOfWork  # noqa: E402
from src.services.ingest import IngestService  # noqa: E402

logger = get_logger(__name__)


def format_duration(seconds: float) -> str:
    """Форматировать время выполнения."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"


async def ingest_agent(agent_id: str, verbose: bool = False) -> None:
    """Индексировать один агент."""
    print(f"\n🔄 Индексация агента: {agent_id}")

    # Создать UoW
    session_factory = get_session_factory()
    uow = UnitOfWork(session_factory)

    # Создать сервис
    service = IngestService(uow)

    try:
        # Выполнить индексацию
        result = await service.ingest_agent(agent_id)

        # Вывод результата
        if result.success:
            print("   Загрузка документа... ✓")
            print(f"   Парсинг HTML... ✓ (найдено секций: {result.chunks_created})")
            print(
                f"   Генерация embeddings... ✓ ({result.embeddings_generated}/{result.chunks_created})"
            )
            print("   Сохранение в БД... ✓")
            print("\n✅ Готово!")
            print(f"   Чанков создано: {result.chunks_created}")
            print(f"   Время: {format_duration(result.duration_seconds)}")

            if verbose and result.errors:
                print("\n⚠️  Warnings:")
                for error in result.errors:
                    print(f"   - {error}")
        else:
            print("\n❌ Ошибка индексации!")
            for error in result.errors:
                print(f"   - {error}")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        if verbose:
            logger.exception("Ingest failed")
        sys.exit(1)


async def ingest_all(verbose: bool = False) -> None:
    """Индексировать все агенты."""
    print("\n🔄 Индексация всех агентов с базами знаний...")

    # Создать UoW
    session_factory = get_session_factory()
    uow = UnitOfWork(session_factory)

    # Создать сервис
    service = IngestService(uow)

    try:
        # Выполнить индексацию всех
        results = await service.ingest_all()

        # Статистика
        total = len(results)
        success_count = sum(1 for r in results.values() if r.success)
        failed_count = total - success_count
        total_chunks = sum(r.chunks_created for r in results.values())
        total_time = sum(r.duration_seconds for r in results.values())

        # Вывод по каждому агенту
        print("\nРезультаты:")
        for agent_id, result in results.items():
            status = "✓" if result.success else "✗"
            chunks = result.chunks_created
            duration = format_duration(result.duration_seconds)
            print(f"  {status} {agent_id:<15} {chunks:>3} чанков, {duration}")

            if verbose and result.errors:
                for error in result.errors:
                    print(f"      ⚠️  {error}")

        # Итоговая статистика
        print(f"\n{'=' * 50}")
        print(f"✅ Успешно:     {success_count}/{total}")
        print(f"❌ Ошибки:      {failed_count}/{total}")
        print(f"📦 Всего чанков: {total_chunks}")
        print(f"⏱️  Общее время:  {format_duration(total_time)}")

        if failed_count > 0:
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        if verbose:
            logger.exception("Ingest all failed")
        sys.exit(1)


def main() -> None:
    """Точка входа CLI."""
    parser = argparse.ArgumentParser(
        description="Индексация документов для AI Chat",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  %(prog)s --agent products          # Индексировать агента products
  %(prog)s --all                      # Индексировать все агенты
  %(prog)s --agent compatibility -v   # Verbose режим
        """,
    )

    # Аргументы
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--agent",
        type=str,
        help="ID агента для индексации (slug домена)",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Индексировать все активные агенты",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose режим (подробный вывод)",
    )

    args = parser.parse_args()

    # Выполнить команду
    if args.agent:
        asyncio.run(ingest_agent(args.agent, verbose=args.verbose))
    elif args.all:
        asyncio.run(ingest_all(verbose=args.verbose))


if __name__ == "__main__":
    main()
