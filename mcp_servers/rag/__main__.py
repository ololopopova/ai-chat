"""Entry point для запуска RAG MCP Server.

ВАЖНО: MCP использует stdout для JSON-RPC протокола.
ВСЁ логирование должно идти в stderr.
"""

import logging
import sys

# Перенаправляем ВСЕ логи в stderr ДО любых импортов
# Это предотвращает инициализацию stdout логгеров из src модулей
logging.basicConfig(
    level=logging.WARNING,  # Минимизируем шум
    stream=sys.stderr,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,  # Перезаписать любую существующую конфигурацию
)

# Теперь можно импортировать остальное
import asyncio  # noqa: E402

from mcp_servers.rag.server import main  # noqa: E402

if __name__ == "__main__":
    asyncio.run(main())
