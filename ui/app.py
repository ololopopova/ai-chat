"""
Главное Streamlit приложение AI Chat.

Запуск: streamlit run ui/app.py
"""

import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH для корректных импортов
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from src.core.config import get_settings
from src.core.logging import get_logger
from ui.components.chat import (
    create_assistant_message,
    create_user_message,
    render_chat_history,
    render_chat_input,
)
from ui.components.progress import (
    complete_progress,
    create_progress_state,
    render_progress_inline,
    update_progress_state,
)
from ui.components.timeline import (
    complete_all_stages,
    render_timeline,
    update_stage,
)
from ui.models.events import (
    CompleteEvent,
    ErrorEvent,
    EventType,
    StageEvent,
    TokenEvent,
)
from ui.session import get_session_manager

logger = get_logger(__name__)


def process_message_streaming(user_input: str) -> None:
    """
    Обработать сообщение пользователя с синхронным стримингом.

    Использует синхронный WebSocket для реального стриминга в Streamlit.

    Args:
        user_input: Текст сообщения пользователя
    """
    session = get_session_manager()
    conversation = session.get_current_conversation()

    if not conversation:
        logger.warning("Нет активного диалога для обработки сообщения")
        return

    logger.info(f"Обработка сообщения: {user_input[:50]}...")

    # Сбрасываем стадии для нового запроса
    session._reset_processing_state()
    session.is_processing = True

    # Накапливаем ответ
    accumulated_content = ""
    asset_url: str | None = None

    # Placeholder для стриминга ответа
    response_placeholder = st.empty()

    try:
        # Используем СИНХРОННЫЙ метод для реального стриминга
        for event in session.api_client.send_message_sync(user_input):
            match event.type:
                case EventType.STAGE:
                    assert isinstance(event, StageEvent)
                    session.stages = update_stage(session.stages, event.stage_name)
                    session.active_message = event.message

                case EventType.TOKEN:
                    assert isinstance(event, TokenEvent)
                    accumulated_content += event.content
                    # Обновляем placeholder с новым контентом — это работает синхронно!
                    response_placeholder.markdown(accumulated_content + "▌")

                case EventType.ERROR:
                    assert isinstance(event, ErrorEvent)
                    logger.error(f"Ошибка от backend: {event.message}")
                    response_placeholder.error(f"❌ {event.message}")
                    session.is_processing = False
                    return

                case EventType.COMPLETE:
                    assert isinstance(event, CompleteEvent)
                    if event.asset_url:
                        asset_url = event.asset_url
                    # Используем финальный ответ если есть
                    if event.final_response and not accumulated_content:
                        accumulated_content = event.final_response
                    session.stages = complete_all_stages(session.stages)

                case _:
                    pass  # Игнорируем остальные события

        # Показываем финальный ответ (без курсора)
        response_placeholder.markdown(accumulated_content)

        # Добавляем финальное сообщение ассистента
        if accumulated_content:
            assistant_message = create_assistant_message(accumulated_content, asset_url)
            conversation.messages.append(assistant_message)
            logger.info("Сообщение успешно обработано")

    except Exception:
        logger.exception("Ошибка при обработке сообщения")
        response_placeholder.error("❌ Произошла непредвиденная ошибка.")
    finally:
        session.is_processing = False
        session.progress = None


def main() -> None:
    """Главная функция приложения."""
    settings = get_settings()

    # Настройка страницы
    st.set_page_config(
        page_title=settings.ui_title,
        page_icon=settings.ui_page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Инициализация сессии
    session = get_session_manager()

    # Боковая панель
    new_chat_clicked, use_mock_new, selected_thread_id = render_sidebar(
        conversations=session.conversations,
        current_thread_id=session.current_thread_id,
        use_mock=session.use_mock,
    )

    # Обработка действий sidebar
    if new_chat_clicked:
        session.create_new_conversation()
        logger.info("Создан новый диалог")
        st.rerun()

    if selected_thread_id:
        session.switch_conversation(selected_thread_id)
        logger.info(f"Переключение на диалог: {selected_thread_id[:8]}...")
        st.rerun()

    if use_mock_new != session.use_mock:
        session.use_mock = use_mock_new
        logger.info(f"Переключение режима Mock: {use_mock_new}")
        st.rerun()

    # Timeline в sidebar
    if session.stages:
        with st.sidebar:
            st.divider()
            render_timeline(session.stages, session.active_message)

    # Прогресс в sidebar
    if session.progress and session.progress.is_active:
        with st.sidebar:
            st.divider()
            render_progress_inline(
                session.progress.progress,
                session.progress.current_step,
            )

    # Основной контент
    st.title(f"{settings.ui_page_icon} {settings.ui_title}")

    # История чата
    conversation = session.get_current_conversation()
    if conversation:
        render_chat_history(conversation.messages)

    # Поле ввода
    user_input = render_chat_input(disabled=session.is_processing)

    if user_input and not session.is_processing:
        # Сразу показываем сообщение пользователя
        conversation = session.get_current_conversation()
        if conversation:
            user_message = create_user_message(user_input)
            conversation.messages.append(user_message)

        # Показываем сообщение в чате сразу
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)

        # Показываем ответ с реальным стримингом
        with st.chat_message("assistant", avatar="🤖"):
            # Синхронная функция — стриминг работает!
            process_message_streaming(user_input)

        st.rerun()


if __name__ == "__main__":
    main()
