"""Tools для Main Agent (субагенты как инструменты)."""

from src.graph.tools.compatibility import compatibility_agent
from src.graph.tools.marketing import marketing_agent
from src.graph.tools.products import products_agent

__all__ = [
    "compatibility_agent",
    "marketing_agent",
    "products_agent",
]
