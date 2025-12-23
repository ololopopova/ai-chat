"""Тесты для conditional edges графа."""

from src.graph.edges import route_after_router
from src.graph.state import ChatState, Route


class TestRouteAfterRouter:
    """Тесты для функции route_after_router."""

    def test_route_to_generate(self) -> None:
        """Проверка маршрутизации к generate."""
        state: ChatState = {
            "messages": [],
            "route": Route.GENERATE,
        }
        result = route_after_router(state)
        assert result == "generate"

    def test_route_to_clarify(self) -> None:
        """Проверка маршрутизации к clarify."""
        state: ChatState = {
            "messages": [],
            "route": Route.CLARIFY,
        }
        result = route_after_router(state)
        assert result == "clarify"

    def test_route_to_off_topic(self) -> None:
        """Проверка маршрутизации к off_topic."""
        state: ChatState = {
            "messages": [],
            "route": Route.OFF_TOPIC,
        }
        result = route_after_router(state)
        assert result == "off_topic"

    def test_route_none_defaults_to_off_topic(self) -> None:
        """Проверка, что None route ведёт к off_topic."""
        state: ChatState = {
            "messages": [],
            "route": None,
        }
        result = route_after_router(state)
        assert result == "off_topic"

    def test_route_missing_defaults_to_off_topic(self) -> None:
        """Проверка, что отсутствующий route ведёт к off_topic."""
        state: ChatState = {
            "messages": [],
        }
        result = route_after_router(state)
        assert result == "off_topic"
