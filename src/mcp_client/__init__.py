"""MCP Client module for managing MCP server connections.

Provides MCPClientManager for connecting to MCP servers via stdio or HTTP transport.
"""

from src.mcp_client.manager import MCPClientManager, get_mcp_client, set_mcp_client

__all__ = ["MCPClientManager", "get_mcp_client", "set_mcp_client"]
