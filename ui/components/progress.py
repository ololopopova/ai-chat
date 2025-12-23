"""Компонент прогресса: отображение хода долгих операций."""

from dataclasses import dataclass

import streamlit as st

from ui.config import ui_config


@dataclass
class ProgressState:
    """Состояние прогресса операции."""

    job_id: str
    progress: int  # 0-100
    current_step: str
    is_active: bool = True
    is_cancelled: bool = False


def render_progress(state: ProgressState | None) -> bool:
    """
    Отрисовать прогресс-бар с информацией о текущем шаге.

    Args:
        state: Состояние прогресса или None, если нет активной операции

    Returns:
        True, если была нажата кнопка отмены
    """
    if state is None or not state.is_active:
        return False

    config = ui_config.progress

    st.markdown("### ⏳ Выполняется операция")

    # Прогресс-бар
    st.progress(state.progress / 100, text=f"{state.progress}%")

    # Текущий шаг
    st.info(f"📌 {state.current_step}")

    # Кнопка отмены
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        if st.button(config.cancel_button_text, key=f"cancel_{state.job_id}", type="secondary"):
            return True

    return False


def render_progress_inline(progress: int, current_step: str) -> None:
    """
    Отрисовать компактный прогресс-бар (без кнопки отмены).

    Args:
        progress: Процент выполнения (0-100)
        current_step: Описание текущего шага
    """
    st.progress(progress / 100)
    st.caption(f"⏳ {current_step} ({progress}%)")


def create_progress_state(job_id: str) -> ProgressState:
    """
    Создать начальное состояние прогресса.

    Args:
        job_id: Идентификатор задачи

    Returns:
        Начальное состояние прогресса
    """
    return ProgressState(
        job_id=job_id,
        progress=0,
        current_step="Подготовка...",
        is_active=True,
    )


def update_progress_state(
    state: ProgressState,
    progress: int,
    current_step: str,
) -> ProgressState:
    """
    Обновить состояние прогресса.

    Args:
        state: Текущее состояние
        progress: Новый процент выполнения
        current_step: Новый текущий шаг

    Returns:
        Обновлённое состояние
    """
    return ProgressState(
        job_id=state.job_id,
        progress=progress,
        current_step=current_step,
        is_active=state.is_active,
        is_cancelled=state.is_cancelled,
    )


def complete_progress(state: ProgressState) -> ProgressState:
    """
    Завершить прогресс операции.

    Args:
        state: Текущее состояние

    Returns:
        Завершённое состояние
    """
    return ProgressState(
        job_id=state.job_id,
        progress=100,
        current_step="Завершено",
        is_active=False,
        is_cancelled=state.is_cancelled,
    )


def cancel_progress(state: ProgressState) -> ProgressState:
    """
    Отменить операцию.

    Args:
        state: Текущее состояние

    Returns:
        Отменённое состояние
    """
    return ProgressState(
        job_id=state.job_id,
        progress=state.progress,
        current_step="Отменено",
        is_active=False,
        is_cancelled=True,
    )
