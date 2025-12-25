"""Промпты для графа чата."""

from __future__ import annotations

__all__ = [
    "COMPATIBILITY_SUBAGENT_SYSTEM_PROMPT",
    "MAIN_AGENT_SYSTEM_PROMPT",
    "MARKETING_SUBAGENT_SYSTEM_PROMPT",
    "PRODUCTS_SUBAGENT_SYSTEM_PROMPT",
]

# Импортируем промпты из отдельных модулей
from .compatibility_subagent import COMPATIBILITY_SUBAGENT_SYSTEM_PROMPT
from .main_agent import MAIN_AGENT_SYSTEM_PROMPT
from .marketing_subagent import MARKETING_SUBAGENT_SYSTEM_PROMPT
from .products_subagent import PRODUCTS_SUBAGENT_SYSTEM_PROMPT

