"""Компонент чата: отображение истории сообщений и ввод."""

from datetime import datetime

import streamlit as st

from ui.config import ui_config
from ui.models.events import ChatMessage, MessageRole


def render_message(message: ChatMessage) -> None:
    """
    Отрисовать одно сообщение чата.

    Args:
        message: Модель сообщения для отображения
    """
    config = ui_config.chat

    # Получаем роль как строку (может быть enum или str после сериализации)
    role_str = message.role.value if isinstance(message.role, MessageRole) else message.role

    # Определяем аватар по роли
    is_user = role_str == MessageRole.USER.value
    avatar = config.user_avatar if is_user else config.assistant_avatar

    with st.chat_message(role_str, avatar=avatar):
        # Текст сообщения
        st.markdown(message.content)

        # Отображение вложения (изображения)
        if message.asset_url:
            st.image(message.asset_url, use_container_width=True)

        # Время сообщения
        time_str = message.timestamp.strftime("%H:%M")
        st.caption(time_str)


def render_chat_history(messages: list[ChatMessage]) -> None:
    """
    Отрисовать историю сообщений чата.

    Args:
        messages: Список сообщений для отображения
    """
    for message in messages:
        render_message(message)


def render_chat_input() -> str | None:
    """
    Отрисовать поле ввода сообщения.

    Returns:
        Введённый текст или None, если ничего не введено
    """
    config = ui_config.chat
    return st.chat_input(config.input_placeholder)


def create_user_message(content: str) -> ChatMessage:
    """
    Создать сообщение пользователя.

    Args:
        content: Текст сообщения

    Returns:
        Модель сообщения
    """
    return ChatMessage(
        role=MessageRole.USER,
        content=content,
        timestamp=datetime.now(),
    )


def create_assistant_message(
    content: str,
    asset_url: str | None = None,
) -> ChatMessage:
    """
    Создать сообщение ассистента.

    Args:
        content: Текст сообщения
        asset_url: URL вложения (опционально)

    Returns:
        Модель сообщения
    """
    return ChatMessage(
        role=MessageRole.ASSISTANT,
        content=content,
        timestamp=datetime.now(),
        asset_url=asset_url,
    )
