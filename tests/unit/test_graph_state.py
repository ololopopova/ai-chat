"""Тесты для ChatState и state transitions."""

from langchain_core.messages import AIMessage, HumanMessage

from src.graph.state import ChatState, Route, Stage


class TestRoute:
    """Тесты для Route enum."""

    def test_route_values(self) -> None:
        """Проверка значений Route."""
        assert Route.GENERATE.value == "generate"
        assert Route.CLARIFY.value == "clarify"
        assert Route.OFF_TOPIC.value == "off_topic"

    def test_route_from_string(self) -> None:
        """Проверка создания Route из строки."""
        assert Route("generate") == Route.GENERATE
        assert Route("clarify") == Route.CLARIFY
        assert Route("off_topic") == Route.OFF_TOPIC


class TestStage:
    """Тесты для Stage enum."""

    def test_stage_values(self) -> None:
        """Проверка значений Stage."""
        assert Stage.ROUTER.value == "router"
        assert Stage.CLARIFY.value == "clarify"
        assert Stage.RETRIEVE.value == "retrieve"
        assert Stage.GENERATE.value == "generate"


class TestChatState:
    """Тесты для ChatState TypedDict."""

    def test_empty_state(self) -> None:
        """Проверка пустого состояния."""
        state: ChatState = {}
        assert state.get("messages") is None
        assert state.get("route") is None
        assert state.get("domain") is None

    def test_state_with_messages(self) -> None:
        """Проверка состояния с сообщениями."""
        state: ChatState = {
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi there!"),
            ],
        }
        assert len(state["messages"]) == 2
        assert state["messages"][0].content == "Hello"
        assert state["messages"][1].content == "Hi there!"

    def test_state_with_route(self) -> None:
        """Проверка состояния с маршрутом."""
        state: ChatState = {
            "messages": [],
            "route": Route.GENERATE,
            "domain": "marketing",
        }
        assert state["route"] == Route.GENERATE
        assert state["domain"] == "marketing"

    def test_state_with_stage(self) -> None:
        """Проверка состояния со стадией."""
        state: ChatState = {
            "messages": [],
            "stage": Stage.ROUTER,
        }
        assert state["stage"] == Stage.ROUTER

    def test_state_with_metadata(self) -> None:
        """Проверка состояния с метаданными."""
        state: ChatState = {
            "messages": [],
            "confidence": 0.85,
            "matched_domains": ["marketing", "product"],
        }
        assert state["confidence"] == 0.85
        assert state["matched_domains"] == ["marketing", "product"]

    def test_full_state(self) -> None:
        """Проверка полного состояния."""
        state: ChatState = {
            "messages": [HumanMessage(content="Test")],
            "route": Route.CLARIFY,
            "domain": None,
            "stage": Stage.CLARIFY,
            "confidence": 0.5,
            "matched_domains": ["marketing", "support"],
        }
        assert state["route"] == Route.CLARIFY
        assert state["stage"] == Stage.CLARIFY
        assert len(state["matched_domains"]) == 2

