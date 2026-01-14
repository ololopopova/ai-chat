"""MCP Client Manager для управления подключениями к MCP серверам.

Поддерживает:
- stdio transport (subprocess)
- HTTP transport (remote server)
- Graceful shutdown
- Error handling без fallback
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from src.core.logging import get_logger

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

logger = get_logger(__name__)

# Тип для конфигурации MCP серверов
MCPServerConfig = dict[str, dict[str, Any]]


class MCPClientError(Exception):
    """Ошибка MCP клиента."""

    pass


class MCPServerUnavailableError(MCPClientError):
    """MCP сервер недоступен."""

    pass


class MCPClientManager:
    """
    Менеджер подключений к MCP серверам.

    Использует MultiServerMCPClient из langchain-mcp-adapters для:
    - Управления несколькими MCP серверами
    - Преобразования MCP tools в LangChain tools
    - Graceful shutdown subprocess-ов

    Example:
        >>> manager = MCPClientManager({
        ...     "rag": {
        ...         "command": "python",
        ...         "args": ["-m", "mcp_servers.rag"],
        ...         "transport": "stdio",
        ...     }
        ... })
        >>> tools = await manager.get_tools()
        >>> await manager.close()
    """

    def __init__(self, servers_config: MCPServerConfig) -> None:
        """
        Инициализация менеджера.

        Args:
            servers_config: Конфигурация MCP серверов.
                Формат:
                {
                    "server_name": {
                        "command": "python",  # для stdio
                        "args": ["-m", "module"],
                        "transport": "stdio",  # или "http"
                        "url": "http://...",  # для http transport
                    }
                }
        """
        self._servers_config = servers_config
        self._client: MultiServerMCPClient | None = None
        self._tools: list[BaseTool] = []
        self._initialized = False

        logger.info(
            "MCPClientManager created",
            extra={"servers": list(servers_config.keys())},
        )

    @property
    def is_initialized(self) -> bool:
        """Инициализирован ли клиент."""
        return self._initialized

    async def initialize(self) -> None:
        """
        Инициализировать подключения ко всем MCP серверам.

        Raises:
            MCPServerUnavailableError: Если сервер недоступен.
        """
        if self._initialized:
            logger.warning("MCPClientManager already initialized")
            return

        try:
            # Преобразуем конфигурацию в формат MultiServerMCPClient
            client_config = self._build_client_config()

            logger.info(
                "Initializing MCP client",
                extra={"config": client_config},
            )

            self._client = MultiServerMCPClient(client_config)
            self._tools = await self._client.get_tools()
            self._initialized = True

            logger.info(
                "MCP client initialized successfully",
                extra={
                    "servers": list(self._servers_config.keys()),
                    "tools_count": len(self._tools),
                    "tools": [t.name for t in self._tools],
                },
            )

        except Exception as e:
            logger.error(
                "Failed to initialize MCP client",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise MCPServerUnavailableError(f"Failed to connect to MCP servers: {e}") from e

    def _build_client_config(self) -> dict[str, Any]:
        """
        Преобразовать конфигурацию в формат MultiServerMCPClient.

        Returns:
            Конфигурация для MultiServerMCPClient.
        """
        config: dict[str, Any] = {}

        for server_name, server_config in self._servers_config.items():
            transport = server_config.get("transport", "stdio")

            if transport == "stdio":
                # Для stdio: command + args
                command = server_config.get("command", "python")
                args = server_config.get("args", [])

                # Передаём ВСЕ текущие env vars (включая OPENAI_API_KEY)
                # плюс дополнительные из конфига
                env = {
                    **os.environ,  # Все переменные текущего процесса
                    **server_config.get("env", {}),  # Дополнительные из конфига
                    "PYTHONPATH": str(Path(__file__).parent.parent.parent),
                }

                config[server_name] = {
                    "command": command,
                    "args": args,
                    "transport": "stdio",
                    "env": env,
                }

            elif transport == "http":
                # Для HTTP: url
                url = server_config.get("url")
                if not url:
                    raise MCPClientError(
                        f"HTTP transport requires 'url' for server '{server_name}'"
                    )

                config[server_name] = {
                    "url": url,
                    "transport": "http",
                }

            else:
                raise MCPClientError(
                    f"Unknown transport '{transport}' for server '{server_name}'"
                )

        return config

    async def get_tools(self, server_name: str | None = None) -> list[BaseTool]:
        """
        Получить tools из MCP серверов.

        Args:
            server_name: Опционально — имя сервера для фильтрации.

        Returns:
            Список LangChain tools.

        Raises:
            MCPClientError: Если клиент не инициализирован.
        """
        if not self._initialized:
            raise MCPClientError("MCPClientManager not initialized. Call initialize() first.")

        if server_name:
            # Фильтруем по имени сервера (имя tool содержит имя сервера)
            return [t for t in self._tools if server_name in t.name]

        return self._tools

    async def get_tool_by_name(self, tool_name: str) -> BaseTool | None:
        """
        Получить tool по имени.

        Args:
            tool_name: Имя tool.

        Returns:
            Tool или None если не найден.
        """
        if not self._initialized:
            raise MCPClientError("MCPClientManager not initialized. Call initialize() first.")

        for tool in self._tools:
            if tool.name == tool_name:
                return tool

        return None

    async def close(self) -> None:
        """Закрыть все подключения к MCP серверам."""
        if not self._initialized:
            return

        try:
            # MultiServerMCPClient автоматически управляет subprocess-ами
            # При выходе из контекста они завершаются
            logger.info("Closing MCP client connections")
            self._client = None
            self._tools = []
            self._initialized = False
            logger.info("MCP client closed successfully")

        except Exception as e:
            logger.error(
                "Error closing MCP client",
                extra={"error": str(e)},
                exc_info=True,
            )

    async def __aenter__(self) -> "MCPClientManager":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit."""
        await self.close()


# Глобальный instance для singleton pattern
_mcp_client_instance: MCPClientManager | None = None


def get_default_mcp_config() -> MCPServerConfig:
    """
    Получить конфигурацию MCP серверов из config/domains.yaml.

    Returns:
        Конфигурация MCP серверов.
    """
    from src.api.deps import load_domains_config

    try:
        config = load_domains_config()
        return config.get("mcp_servers", {})
    except Exception:
        logger.warning("Failed to load MCP config from domains.yaml, using defaults")
        return {}


def get_mcp_client() -> MCPClientManager | None:
    """
    Получить глобальный MCP client instance.

    Returns:
        MCPClientManager или None если не инициализирован.
    """
    return _mcp_client_instance


def set_mcp_client(client: MCPClientManager | None) -> None:
    """
    Установить глобальный MCP client instance.

    Args:
        client: MCPClientManager instance или None для сброса.
    """
    global _mcp_client_instance
    _mcp_client_instance = client
