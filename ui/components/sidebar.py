"""Компонент боковой панели: логотип, управление, настройки, список диалогов."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import streamlit as st

from ui.config import ui_config

if TYPE_CHECKING:
    from ui.models.conversation import Conversation


def render_sidebar(
    conversations: dict[str, Conversation],
    current_thread_id: str | None = None,
    use_mock: bool = True,
) -> tuple[bool, bool, str | None]:
    """
    Отрисовать боковую панель приложения.

    Args:
        conversations: Словарь всех диалогов
        current_thread_id: ID текущего активного диалога
        use_mock: Текущее состояние переключателя Mock режима

    Returns:
        Кортеж (new_chat_clicked, use_mock_new_value, selected_thread_id)
    """
    config = ui_config.sidebar
    selected_thread_id: str | None = None

    with st.sidebar:
        # Логотип и название
        st.markdown(f"# {config.logo_text}")
        st.divider()

        # Кнопка "Новый диалог"
        new_chat_clicked = st.button(
            config.new_chat_button,
            type="primary",
            use_container_width=True,
        )

        # Список диалогов
        if conversations:
            st.divider()
            st.markdown("### 💬 Диалоги")

            # Сортируем по дате создания (новые сверху)
            sorted_convs = sorted(
                conversations.values(),
                key=lambda c: c.created_at,
                reverse=True,
            )

            for conv in sorted_convs:
                is_current = conv.thread_id == current_thread_id
                title = conv.get_title()

                # Кнопка для переключения на диалог
                button_type: Literal["primary", "secondary"] = (
                    "primary" if is_current else "secondary"
                )
                button_clicked = st.button(
                    f"{'▶ ' if is_current else ''}{title}",
                    key=f"conv_{conv.thread_id}",
                    type=button_type,
                    use_container_width=True,
                )
                if button_clicked and not is_current:
                    selected_thread_id = conv.thread_id

        st.divider()

        # Переключатель Mock/Real API
        st.markdown("### ⚙️ Настройки")
        use_mock_new = st.toggle(
            config.mock_mode_label,
            value=use_mock,
            help="Включить имитацию backend для разработки",
        )

        # Информация о текущем диалоге
        if current_thread_id:
            st.divider()
            st.markdown(f"**{config.thread_info_label}:**")
            st.code(current_thread_id[:8] + "...", language=None)

        # Информация о приложении
        st.divider()
        st.caption("AI Chat v0.1.0")
        st.caption("© 2024")

    return new_chat_clicked, use_mock_new, selected_thread_id


def render_timeline_in_sidebar(
    stages_html: str,
    progress_html: str | None = None,
) -> None:
    """
    Отрисовать timeline и прогресс в sidebar.

    Args:
        stages_html: HTML разметка стадий
        progress_html: HTML разметка прогресса (опционально)
    """
    with st.sidebar:
        st.divider()
        st.markdown(stages_html, unsafe_allow_html=True)

        if progress_html:
            st.divider()
            st.markdown(progress_html, unsafe_allow_html=True)
