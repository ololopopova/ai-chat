"""Unit-тесты для MCP Client Manager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mcp_client.manager import (
    MCPClientError,
    MCPClientManager,
    MCPServerUnavailableError,
    get_mcp_client,
    set_mcp_client,
)

# =============================================================================
# TESTS: MCPClientManager initialization
# =============================================================================


def test_mcp_client_manager_creation() -> None:
    """Тест: создание MCPClientManager."""
    config = {
        "rag": {
            "command": "python",
            "args": ["-m", "mcp_servers.rag"],
            "transport": "stdio",
        }
    }

    manager = MCPClientManager(config)

    assert manager is not None
    assert not manager.is_initialized


def test_mcp_client_manager_with_http_transport() -> None:
    """Тест: создание с HTTP transport."""
    config = {
        "rag": {
            "transport": "http",
            "url": "http://localhost:8100/mcp",
        }
    }

    manager = MCPClientManager(config)

    assert manager is not None
    assert not manager.is_initialized


def test_mcp_client_manager_http_without_url_raises() -> None:
    """Тест: HTTP transport без url вызывает ошибку."""
    config = {
        "rag": {
            "transport": "http",
            # url отсутствует
        }
    }

    manager = MCPClientManager(config)

    with pytest.raises(MCPClientError, match="requires 'url'"):
        manager._build_client_config()


def test_mcp_client_manager_unknown_transport_raises() -> None:
    """Тест: неизвестный transport вызывает ошибку."""
    config = {
        "rag": {
            "transport": "unknown",
        }
    }

    manager = MCPClientManager(config)

    with pytest.raises(MCPClientError, match="Unknown transport"):
        manager._build_client_config()


# =============================================================================
# TESTS: MCPClientManager operations
# =============================================================================


@pytest.mark.asyncio
async def test_mcp_client_manager_get_tools_not_initialized() -> None:
    """Тест: get_tools без инициализации вызывает ошибку."""
    config = {"rag": {"command": "python", "args": [], "transport": "stdio"}}
    manager = MCPClientManager(config)

    with pytest.raises(MCPClientError, match="not initialized"):
        await manager.get_tools()


@pytest.mark.asyncio
async def test_mcp_client_manager_get_tool_by_name_not_initialized() -> None:
    """Тест: get_tool_by_name без инициализации вызывает ошибку."""
    config = {"rag": {"command": "python", "args": [], "transport": "stdio"}}
    manager = MCPClientManager(config)

    with pytest.raises(MCPClientError, match="not initialized"):
        await manager.get_tool_by_name("hybrid_search")


@pytest.mark.asyncio
async def test_mcp_client_manager_close_without_init() -> None:
    """Тест: close без инициализации не вызывает ошибку."""
    config = {"rag": {"command": "python", "args": [], "transport": "stdio"}}
    manager = MCPClientManager(config)

    # Не должно вызывать исключение
    await manager.close()


# =============================================================================
# TESTS: Singleton pattern
# =============================================================================


def test_get_mcp_client_returns_none_initially() -> None:
    """Тест: get_mcp_client возвращает None до инициализации."""
    # Сбрасываем глобальное состояние
    set_mcp_client(None)

    assert get_mcp_client() is None


def test_set_mcp_client_works() -> None:
    """Тест: set_mcp_client устанавливает клиент."""
    config = {"rag": {"command": "python", "args": [], "transport": "stdio"}}
    manager = MCPClientManager(config)

    set_mcp_client(manager)

    assert get_mcp_client() is manager

    # Cleanup
    set_mcp_client(None)


# =============================================================================
# TESTS: Integration with mock MultiServerMCPClient
# =============================================================================


@pytest.mark.asyncio
async def test_mcp_client_manager_initialize_success() -> None:
    """Тест: успешная инициализация с mock."""
    config = {"rag": {"command": "python", "args": [], "transport": "stdio"}}
    manager = MCPClientManager(config)

    mock_tools = [MagicMock(name="hybrid_search")]

    with patch("src.mcp_client.manager.MultiServerMCPClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.get_tools = AsyncMock(return_value=mock_tools)
        mock_client_class.return_value = mock_client

        await manager.initialize()

        assert manager.is_initialized
        mock_client_class.assert_called_once()
        mock_client.get_tools.assert_awaited_once()


@pytest.mark.asyncio
async def test_mcp_client_manager_initialize_failure() -> None:
    """Тест: ошибка при инициализации."""
    config = {"rag": {"command": "python", "args": [], "transport": "stdio"}}
    manager = MCPClientManager(config)

    with patch("src.mcp_client.manager.MultiServerMCPClient") as mock_client_class:
        mock_client_class.side_effect = Exception("Connection failed")

        with pytest.raises(MCPServerUnavailableError, match="Connection failed"):
            await manager.initialize()

        assert not manager.is_initialized


@pytest.mark.asyncio
async def test_mcp_client_manager_get_tools_success() -> None:
    """Тест: получение tools после инициализации."""
    config = {"rag": {"command": "python", "args": [], "transport": "stdio"}}
    manager = MCPClientManager(config)

    mock_tool = MagicMock()
    mock_tool.name = "hybrid_search"
    mock_tools = [mock_tool]

    with patch("src.mcp_client.manager.MultiServerMCPClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.get_tools = AsyncMock(return_value=mock_tools)
        mock_client_class.return_value = mock_client

        await manager.initialize()
        tools = await manager.get_tools()

        assert len(tools) == 1
        assert tools[0].name == "hybrid_search"


@pytest.mark.asyncio
async def test_mcp_client_manager_get_tool_by_name_success() -> None:
    """Тест: получение tool по имени."""
    config = {"rag": {"command": "python", "args": [], "transport": "stdio"}}
    manager = MCPClientManager(config)

    mock_tool = MagicMock()
    mock_tool.name = "hybrid_search"
    mock_tools = [mock_tool]

    with patch("src.mcp_client.manager.MultiServerMCPClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.get_tools = AsyncMock(return_value=mock_tools)
        mock_client_class.return_value = mock_client

        await manager.initialize()
        tool = await manager.get_tool_by_name("hybrid_search")

        assert tool is not None
        assert tool.name == "hybrid_search"


@pytest.mark.asyncio
async def test_mcp_client_manager_get_tool_by_name_not_found() -> None:
    """Тест: tool не найден."""
    config = {"rag": {"command": "python", "args": [], "transport": "stdio"}}
    manager = MCPClientManager(config)

    mock_tools: list[MagicMock] = []

    with patch("src.mcp_client.manager.MultiServerMCPClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.get_tools = AsyncMock(return_value=mock_tools)
        mock_client_class.return_value = mock_client

        await manager.initialize()
        tool = await manager.get_tool_by_name("nonexistent")

        assert tool is None


@pytest.mark.asyncio
async def test_mcp_client_manager_context_manager() -> None:
    """Тест: использование как async context manager."""
    config = {"rag": {"command": "python", "args": [], "transport": "stdio"}}

    with patch("src.mcp_client.manager.MultiServerMCPClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.get_tools = AsyncMock(return_value=[])
        mock_client_class.return_value = mock_client

        async with MCPClientManager(config) as manager:
            assert manager.is_initialized

        # После выхода из контекста — не инициализирован
        assert not manager.is_initialized
