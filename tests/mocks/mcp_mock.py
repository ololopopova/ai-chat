"""Моки для MCP клиента."""

from __future__ import annotations

from typing import Any


class MockMCPClient:
    """Mock MCP клиент для тестов."""

    def __init__(self, tools: dict[str, dict[str, Any]] | None = None) -> None:
        """
        Инициализация mock MCP клиента.

        Args:
            tools: Словарь инструментов {name: tool_config}
        """
        self._tools = tools or {}
        self._call_history: list[dict[str, Any]] = []

    def list_tools(self) -> list[dict[str, Any]]:
        """Список доступных инструментов."""
        return [
            {
                "name": name,
                "description": config.get("description", ""),
                "parameters": config.get("parameters", {}),
            }
            for name, config in self._tools.items()
        ]

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Вызов инструмента.

        Args:
            tool_name: Имя инструмента
            arguments: Аргументы вызова

        Returns:
            Результат вызова
        """
        self._call_history.append(
            {
                "tool": tool_name,
                "arguments": arguments,
            }
        )

        if tool_name not in self._tools:
            return {"error": f"Tool {tool_name} not found"}

        tool = self._tools[tool_name]
        mock_result = tool.get("mock_result", {"success": True})

        return mock_result

    @property
    def call_history(self) -> list[dict[str, Any]]:
        """История вызовов."""
        return self._call_history


def create_mock_mcp_client(tools: dict[str, dict[str, Any]] | None = None) -> MockMCPClient:
    """
    Создать mock MCP клиент.

    Args:
        tools: Конфигурация инструментов

    Returns:
        MockMCPClient instance

    Example:
        client = create_mock_mcp_client({
            "banner.generate": {
                "description": "Generate banner",
                "parameters": {"logo": "str", "text": "str"},
                "mock_result": {"url": "http://example.com/banner.png"},
            },
        })
    """
    return MockMCPClient(tools=tools)
