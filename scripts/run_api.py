#!/usr/bin/env python3
"""
Скрипт запуска FastAPI сервера.

Использование:
    python scripts/run_api.py
    python scripts/run_api.py --host 127.0.0.1 --port 8080
    python scripts/run_api.py --reload --workers 4
"""

import argparse
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn

from src.core.config import get_settings


def parse_args() -> argparse.Namespace:
    """Парсинг аргументов командной строки."""
    settings = get_settings()

    parser = argparse.ArgumentParser(
        description="Запуск FastAPI сервера AI Chat",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--host",
        type=str,
        default=settings.api_host,
        help="Хост для привязки сервера",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=settings.api_port,
        help="Порт сервера",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=settings.api_workers,
        help="Количество воркеров",
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        default=settings.api_reload and settings.is_development,
        help="Включить hot reload (только для разработки)",
    )

    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Отключить hot reload",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Уровень логирования",
    )

    return parser.parse_args()


def main() -> None:
    """Главная функция запуска сервера."""
    args = parse_args()

    # Определяем, использовать ли reload
    reload = args.reload and not args.no_reload

    # При использовании reload workers должен быть 1
    workers = 1 if reload else args.workers

    print("🚀 Starting AI Chat API server...")
    print(f"   Host: {args.host}")
    print(f"   Port: {args.port}")
    print(f"   Workers: {workers}")
    print(f"   Reload: {reload}")
    print(f"   Log level: {args.log_level}")
    print()

    uvicorn.run(
        "src.api.main:app",
        host=args.host,
        port=args.port,
        workers=workers,
        reload=reload,
        log_level=args.log_level,
        access_log=True,
    )


if __name__ == "__main__":
    main()
