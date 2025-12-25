"""
Субагенты как ReAct графы с RAG.

Каждый субагент:
- Полноценный ReAct граф с инструментами (RAG search)
- Доступ к истории через InjectedState
- Свой LLM для query planning
- Wrapper @tool для вызова из Main Agent
"""

from __future__ import annotations

__all__ = [
    "compatibility_agent",
    "marketing_agent",
    "products_agent",
]

from src.graph.subagents.compatibility import compatibility_agent
from src.graph.subagents.marketing import marketing_agent
from src.graph.subagents.products import products_agent
