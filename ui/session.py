"""Менеджер сессии Streamlit — управление состоянием приложения."""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from src.core.config import get_settings
from ui.api_client import get_api_client
from ui.components.timeline import get_initial_stages
from ui.models.conversation import Conversation

if TYPE_CHECKING:
    from ui.api_client import BaseApiClient
    from ui.components.progress import ProgressState
    from ui.models.events import StageName, StageStatus


class SessionManager:
    """
    Менеджер для работы с Streamlit session_state.

    Инкапсулирует всю логику работы с состоянием сессии,
    обеспечивая типизацию и единую точку доступа.
    """

    def __init__(self) -> None:
        """Инициализация менеджера сессии."""
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        """Убедиться, что все ключи session_state инициализированы."""
        settings = get_settings()

        if "use_mock" not in st.session_state:
            st.session_state.use_mock = settings.use_mock_api

        if "conversations" not in st.session_state:
            st.session_state.conversations = {}

        if "current_thread_id" not in st.session_state:
            st.session_state.current_thread_id = None

        if "stages" not in st.session_state:
            st.session_state.stages = get_initial_stages()

        if "active_message" not in st.session_state:
            st.session_state.active_message = None

        if "progress" not in st.session_state:
            st.session_state.progress = None

        if "is_processing" not in st.session_state:
            st.session_state.is_processing = False

        if "api_client" not in st.session_state:
            st.session_state.api_client = get_api_client(use_mock=st.session_state.use_mock)

        # Создаём первый диалог, если нет ни одного
        if not st.session_state.conversations:
            self.create_new_conversation()

    # --- Свойства для доступа к состоянию ---

    @property
    def use_mock(self) -> bool:
        """Использовать ли mock API."""
        return bool(st.session_state.use_mock)

    @use_mock.setter
    def use_mock(self, value: bool) -> None:
        st.session_state.use_mock = value
        st.session_state.api_client = get_api_client(use_mock=value)

    @property
    def conversations(self) -> dict[str, Conversation]:
        """Словарь всех диалогов."""
        return st.session_state.conversations  # type: ignore[no-any-return]

    @property
    def current_thread_id(self) -> str | None:
        """ID текущего активного диалога."""
        return st.session_state.current_thread_id  # type: ignore[no-any-return]

    @current_thread_id.setter
    def current_thread_id(self, value: str | None) -> None:
        st.session_state.current_thread_id = value

    @property
    def stages(self) -> dict[StageName, StageStatus]:
        """Текущие стадии обработки."""
        return st.session_state.stages  # type: ignore[no-any-return]

    @stages.setter
    def stages(self, value: dict[StageName, StageStatus]) -> None:
        st.session_state.stages = value

    @property
    def active_message(self) -> str | None:
        """Сообщение активной стадии."""
        return st.session_state.active_message  # type: ignore[no-any-return]

    @active_message.setter
    def active_message(self, value: str | None) -> None:
        st.session_state.active_message = value

    @property
    def progress(self) -> ProgressState | None:
        """Текущий прогресс операции."""
        return st.session_state.progress  # type: ignore[no-any-return]

    @progress.setter
    def progress(self, value: ProgressState | None) -> None:
        st.session_state.progress = value

    @property
    def is_processing(self) -> bool:
        """Идёт ли обработка запроса."""
        return bool(st.session_state.is_processing)

    @is_processing.setter
    def is_processing(self, value: bool) -> None:
        st.session_state.is_processing = value

    @property
    def api_client(self) -> BaseApiClient:
        """API клиент."""
        return st.session_state.api_client  # type: ignore[no-any-return]

    # --- Методы для работы с диалогами ---

    def get_current_conversation(self) -> Conversation | None:
        """Получить текущий активный диалог."""
        thread_id = self.current_thread_id
        if thread_id and thread_id in self.conversations:
            return self.conversations[thread_id]
        return None

    def create_new_conversation(self) -> Conversation:
        """Создать новый диалог и сделать его активным."""
        thread_id = self.api_client.create_thread()

        conversation = Conversation(thread_id=thread_id)
        self.conversations[thread_id] = conversation
        self.current_thread_id = thread_id

        # Сбрасываем состояние обработки
        self._reset_processing_state()

        return conversation

    def switch_conversation(self, thread_id: str) -> bool:
        """
        Переключиться на другой диалог.

        Args:
            thread_id: ID диалога для переключения

        Returns:
            True если переключение успешно
        """
        if thread_id in self.conversations:
            self.current_thread_id = thread_id
            self._reset_processing_state()
            return True
        return False

    def _reset_processing_state(self) -> None:
        """Сбросить временное состояние обработки."""
        self.stages = get_initial_stages()
        self.active_message = None
        self.progress = None
        self.is_processing = False


# Глобальный экземпляр менеджера (создаётся при первом вызове)
def get_session_manager() -> SessionManager:
    """Получить менеджер сессии."""
    return SessionManager()
