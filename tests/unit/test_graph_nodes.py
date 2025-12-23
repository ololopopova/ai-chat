"""Тесты для узлов графа."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.graph.nodes.clarify import clarify_node
from src.graph.nodes.off_topic import off_topic_node
from src.graph.nodes.router import _parse_router_response, router_node
from src.graph.state import ChatState, Route, Stage


class TestRouterParsing:
    """Тесты для парсинга ответа роутера."""

    def test_parse_generate_response(self) -> None:
        """Парсинг ответа с доменом."""
        route, domain, matched = _parse_router_response("marketing")
        assert route == Route.GENERATE
        assert domain == "marketing"
        assert matched == ["marketing"]

    def test_parse_clarify_response(self) -> None:
        """Парсинг clarify ответа."""
        route, domain, matched = _parse_router_response("clarify")
        assert route == Route.CLARIFY
        assert domain is None
        assert matched is None

    def test_parse_off_topic_response(self) -> None:
        """Парсинг off_topic ответа."""
        route, domain, matched = _parse_router_response("off_topic")
        assert route == Route.OFF_TOPIC
        assert domain is None
        assert matched is None

    def test_parse_with_quotes(self) -> None:
        """Парсинг ответа с кавычками."""
        route, domain, _matched = _parse_router_response('"marketing"')
        assert route == Route.GENERATE
        assert domain == "marketing"

    def test_parse_with_whitespace(self) -> None:
        """Парсинг ответа с пробелами."""
        route, _domain, _matched = _parse_router_response("  clarify  ")
        assert route == Route.CLARIFY

    def test_parse_uppercase(self) -> None:
        """Парсинг ответа в uppercase."""
        route, _domain, _matched = _parse_router_response("CLARIFY")
        assert route == Route.CLARIFY


class TestRouterNode:
    """Тесты для router_node."""

    @pytest.mark.asyncio
    async def test_router_empty_messages(self) -> None:
        """Роутер возвращает off_topic при пустых сообщениях."""
        state: ChatState = {"messages": []}
        result = await router_node(state)
        assert result["route"] == Route.OFF_TOPIC
        assert result["stage"] == Stage.ROUTER

    @pytest.mark.asyncio
    async def test_router_with_mock_llm(self) -> None:
        """Роутер корректно работает с моком LLM."""
        state: ChatState = {
            "messages": [HumanMessage(content="Как продвигать продукт?")],
        }

        # Мокаем LLM провайдер
        mock_response = MagicMock()
        mock_response.content = "marketing"

        mock_model = AsyncMock()
        mock_model.ainvoke = AsyncMock(return_value=mock_response)

        mock_provider = MagicMock()
        mock_provider.model = mock_model

        with patch("src.graph.nodes.router.get_llm_provider", return_value=mock_provider):
            result = await router_node(state)

        assert result["route"] == Route.GENERATE
        assert result["domain"] == "marketing"
        assert result["stage"] == Stage.ROUTER


class TestClarifyNode:
    """Тесты для clarify_node."""

    @pytest.mark.asyncio
    async def test_clarify_with_matched_domains(self) -> None:
        """Clarify генерирует уточнение с указанными доменами."""
        state: ChatState = {
            "messages": [HumanMessage(content="Помогите")],
            "matched_domains": ["marketing", "support"],
        }

        result = await clarify_node(state)

        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
        assert result["stage"] == Stage.CLARIFY

        # Проверяем, что в ответе есть опции
        content = result["messages"][0].content
        assert "1." in content or "2." in content

    @pytest.mark.asyncio
    async def test_clarify_without_domains(self) -> None:
        """Clarify показывает все домены если matched_domains пуст."""
        state: ChatState = {
            "messages": [],
            "matched_domains": [],
        }

        result = await clarify_node(state)

        assert "messages" in result
        assert result["stage"] == Stage.CLARIFY


class TestOffTopicNode:
    """Тесты для off_topic_node."""

    @pytest.mark.asyncio
    async def test_off_topic_response(self) -> None:
        """Off-topic генерирует вежливый отказ."""
        state: ChatState = {
            "messages": [HumanMessage(content="Какая погода?")],
        }

        result = await off_topic_node(state)

        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)

        content = result["messages"][0].content
        # Проверяем, что есть список доменов
        assert "•" in content or "-" in content
        # Проверяем, что есть вежливый отказ
        assert "не могу" in content.lower() or "извини" in content.lower()

    @pytest.mark.asyncio
    async def test_off_topic_empty_messages(self) -> None:
        """Off-topic работает с пустыми сообщениями."""
        state: ChatState = {"messages": []}

        result = await off_topic_node(state)

        assert "messages" in result
        assert len(result["messages"]) == 1

