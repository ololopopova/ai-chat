"""Тесты для ChatState (ReAct архитектура)."""

from langchain_core.messages import AIMessage, HumanMessage

from src.graph.state import ChatState, Stage


class TestStage:
    """Тесты для Stage enum (ReAct)."""

    def test_stage_values(self) -> None:
        """Проверка значений Stage для ReAct архитектуры."""
        assert Stage.THINKING.value == "thinking"
        assert Stage.CALLING_TOOL.value == "calling_tool"
        assert Stage.SYNTHESIZING.value == "synthesizing"
        assert Stage.COMPLETE.value == "complete"

    def test_stage_from_string(self) -> None:
        """Проверка создания Stage из строки."""
        assert Stage("thinking") == Stage.THINKING
        assert Stage("calling_tool") == Stage.CALLING_TOOL
        assert Stage("synthesizing") == Stage.SYNTHESIZING
        assert Stage("complete") == Stage.COMPLETE


class TestChatState:
    """Тесты для ChatState TypedDict (ReAct минималистичное состояние)."""

    def test_empty_state(self) -> None:
        """Проверка пустого состояния."""
        state: ChatState = {}
        assert state.get("messages") is None
        assert state.get("stage") is None

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

    def test_state_with_stage(self) -> None:
        """Проверка состояния со стадией."""
        state: ChatState = {
            "messages": [],
            "stage": Stage.THINKING,
        }
        assert state["stage"] == Stage.THINKING

    def test_state_full_react_cycle(self) -> None:
        """
        Проверка состояния через ReAct цикл.

        ReAct агент сам управляет messages:
        - HumanMessage: вопрос пользователя
        - AIMessage с tool_calls: агент решил вызвать инструмент
        - ToolMessage: результат от инструмента
        - AIMessage: финальный ответ
        """
        state: ChatState = {
            "messages": [
                HumanMessage(content="Что принимать для сна?"),
                # AIMessage с tool_calls (добавляется ReAct агентом)
                # ToolMessage с результатом (добавляется ReAct агентом)
                # AIMessage с финальным ответом
            ],
            "stage": Stage.COMPLETE,
        }
        assert len(state["messages"]) > 0
        assert state["stage"] == Stage.COMPLETE
