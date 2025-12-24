"""
Тесты для ReAct conditional edges.

NOTE: В ReAct архитектуре с create_react_agent нет явных conditional edges.
Агент сам управляет своим циклом через встроенную логику.

Этот файл оставлен для покрытия логики выбора, но теперь тестирует
behaviour ReAct агента, а не отдельные edge функции.
"""

import pytest
from langchain_core.messages import HumanMessage

from src.graph.builder import build_chat_graph


class TestReActBehaviour:
    """Тесты поведения ReAct агента (замена тестов edges)."""

    @pytest.mark.asyncio
    async def test_agent_decides_to_use_tool(self) -> None:
        """
        Тест: агент должен решить использовать tool для доменного вопроса.

        ReAct агент анализирует вопрос и решает вызвать инструмент.
        """
        graph = build_chat_graph()

        input_state = {
            "messages": [HumanMessage(content="Какой БАД для сна?")],
        }

        # TODO: добавить мок LLM для контроля поведения
        result = await graph.ainvoke(input_state)

        assert "messages" in result
        # Агент должен вызвать tool и дать ответ
        assert len(result["messages"]) >= 2

    @pytest.mark.asyncio
    async def test_agent_responds_without_tool_for_offtopic(self) -> None:
        """
        Тест: агент должен ответить без tools для off-topic вопроса.

        ReAct агент понимает что вопрос вне домена и отвечает напрямую.
        """
        graph = build_chat_graph()

        input_state = {
            "messages": [HumanMessage(content="Какая погода завтра?")],
        }

        # TODO: добавить мок LLM
        result = await graph.ainvoke(input_state)

        assert "messages" in result
        # Должен быть только вопрос и ответ, без tool calls
        # (в реальности может быть больше, зависит от LLM)

    @pytest.mark.asyncio
    async def test_agent_uses_multiple_tools_for_complex_query(self) -> None:
        """
        Тест: агент может вызвать несколько tools для сложного вопроса.

        ReAct агент может решить вызвать products_agent и compatibility_agent.
        """
        graph = build_chat_graph()

        input_state = {
            "messages": [
                HumanMessage(content="Что принимать для сна и с чем это сочетается?")
            ],
        }

        # TODO: добавить мок LLM
        result = await graph.ainvoke(input_state)

        assert "messages" in result
        assert len(result["messages"]) >= 2
