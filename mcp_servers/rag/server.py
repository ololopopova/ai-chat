"""RAG MCP Server - сервер поиска по базе знаний.

Предоставляет MCP tools для гибридного RAG поиска через протокол MCP.
"""

from __future__ import annotations

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool

from mcp_servers.rag.schemas import HybridSearchInput
from mcp_servers.rag.tools import hybrid_search
from src.core.logging import get_logger

logger = get_logger(__name__)


# Создаём MCP сервер
app = Server("rag-search")


@app.list_tools()  # type: ignore[untyped-decorator, no-untyped-call]
async def list_tools() -> list[Tool]:
    """
    Список доступных RAG tools.

    Returns:
        Список MCP tools для поиска.
    """
    return [
        Tool(
            name="hybrid_search",
            description=(
                "Гибридный поиск по базе знаний с reranking. "
                "Выполняет параллельный поиск по vector_queries (семантика) "
                "и fts_keywords (ключевые слова), затем дедупликацию, "
                "reranking через Cross-Encoder и возврат топ-15 результатов."
            ),
            inputSchema=HybridSearchInput.model_json_schema(),
        ),
    ]


@app.call_tool()  # type: ignore[untyped-decorator]
async def call_tool(name: str, arguments: dict[str, Any]) -> list[Any]:
    """
    Вызов RAG tool.

    Args:
        name: Имя tool ("hybrid_search").
        arguments: Аргументы для tool.

    Returns:
        Результат выполнения tool.

    Raises:
        ValueError: Если tool не найден.
    """
    logger.info("MCP tool called", extra={"tool_name": name})

    if name == "hybrid_search":
        # Валидация входных данных
        input_data = HybridSearchInput(**arguments)

        # Выполняем поиск
        result = await hybrid_search(input_data)

        # Возвращаем результат в MCP формате
        return [
            {
                "type": "text",
                "text": result.formatted_context,
            }
        ]

    error_msg = f"Unknown tool: {name}"
    logger.error("Unknown tool called", extra={"tool_name": name})
    raise ValueError(error_msg)


async def main() -> None:
    """Запуск MCP сервера."""
    logger.info("Starting RAG MCP Server")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
