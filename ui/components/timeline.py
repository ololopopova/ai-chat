"""Компонент timeline: отображение стадий обработки запроса."""

import streamlit as st

from ui.config import ui_config
from ui.models.events import STAGE_LABELS, StageName, StageStatus

# Порядок стадий обработки (используется для сортировки и определения завершённых)
STAGE_ORDER: list[StageName] = [
    StageName.ROUTER,
    StageName.CLARIFY,
    StageName.RETRIEVE,
    StageName.GENERATE,
    StageName.OFF_TOPIC,
    StageName.TOOL_SELECT,
    StageName.TOOL_EXECUTE,
]


def render_stage_item(
    stage: StageName,
    status: StageStatus,
    message: str | None = None,
) -> None:
    """
    Отрисовать один элемент стадии.

    Args:
        stage: Название стадии
        status: Статус стадии
        message: Дополнительное сообщение (опционально)
    """
    config = ui_config.timeline

    # Определяем иконку и цвет по статусу
    match status:
        case StageStatus.PENDING:
            icon = config.pending_icon
            color = config.pending_color
        case StageStatus.ACTIVE:
            icon = config.active_icon
            color = config.active_color
        case StageStatus.COMPLETED:
            icon = config.completed_icon
            color = config.completed_color

    # Получаем русское название стадии
    label = STAGE_LABELS.get(stage, stage.value)

    # Стилизованный текст
    st.markdown(
        f"<span style='color: {color}; font-weight: "
        f"{'bold' if status == StageStatus.ACTIVE else 'normal'};'>"
        f"{icon} {label}</span>",
        unsafe_allow_html=True,
    )

    # Дополнительное сообщение для активной стадии
    if message and status == StageStatus.ACTIVE:
        st.caption(message)


def render_timeline(
    stages: dict[StageName, StageStatus],
    active_message: str | None = None,
) -> None:
    """
    Отрисовать timeline стадий обработки.

    Args:
        stages: Словарь стадий и их статусов
        active_message: Сообщение для активной стадии
    """
    st.markdown("### 📋 Стадии обработки")

    for stage in STAGE_ORDER:
        if stage in stages:
            status = stages[stage]
            message = active_message if status == StageStatus.ACTIVE else None
            render_stage_item(stage, status, message)


def get_initial_stages() -> dict[StageName, StageStatus]:
    """
    Получить начальное состояние стадий (все pending).

    Returns:
        Словарь стадий с начальными статусами
    """
    return {}


def update_stage(
    stages: dict[StageName, StageStatus],
    new_stage: StageName,
) -> dict[StageName, StageStatus]:
    """
    Обновить статусы стадий при переходе на новую.

    Все предыдущие стадии помечаются completed,
    новая стадия становится active.

    Args:
        stages: Текущие стадии
        new_stage: Новая активная стадия

    Returns:
        Обновлённый словарь стадий
    """
    updated = {}

    # Находим индекс новой стадии
    try:
        new_index = STAGE_ORDER.index(new_stage)
    except ValueError:
        new_index = -1

    # Все стадии до новой - completed, новая - active
    for i, stage in enumerate(STAGE_ORDER):
        if stage in stages or stage == new_stage:
            if i < new_index:
                updated[stage] = StageStatus.COMPLETED
            elif stage == new_stage:
                updated[stage] = StageStatus.ACTIVE
            elif stage in stages:
                updated[stage] = stages[stage]

    return updated


def complete_all_stages(stages: dict[StageName, StageStatus]) -> dict[StageName, StageStatus]:
    """
    Пометить все активные стадии как завершённые.

    Args:
        stages: Текущие стадии

    Returns:
        Обновлённый словарь стадий
    """
    return {
        stage: StageStatus.COMPLETED if status == StageStatus.ACTIVE else status
        for stage, status in stages.items()
    }
