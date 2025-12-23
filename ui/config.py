"""Конфигурация UI компонентов."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChatConfig:
    """Конфигурация компонента чата."""

    user_avatar: str = "👤"
    assistant_avatar: str = "🤖"
    user_bg_color: str = "#e3f2fd"
    assistant_bg_color: str = "#f5f5f5"
    max_message_height: int = 500
    input_placeholder: str = "Введите сообщение..."


@dataclass(frozen=True)
class TimelineConfig:
    """Конфигурация компонента timeline."""

    pending_icon: str = "○"
    active_icon: str = "●"
    completed_icon: str = "✓"
    pending_color: str = "#9e9e9e"
    active_color: str = "#2196f3"
    completed_color: str = "#4caf50"


@dataclass(frozen=True)
class ProgressConfig:
    """Конфигурация компонента прогресса."""

    bar_color: str = "#4caf50"
    bar_bg_color: str = "#e0e0e0"
    cancel_button_text: str = "Отменить"


@dataclass(frozen=True)
class SidebarConfig:
    """Конфигурация боковой панели."""

    logo_text: str = "🤖 AI Ассистент"
    new_chat_button: str = "🔄 Новый диалог"
    mock_mode_label: str = "Mock режим"
    thread_info_label: str = "Thread ID"


@dataclass
class UIConfig:
    """Главная конфигурация UI."""

    chat: ChatConfig = field(default_factory=ChatConfig)
    timeline: TimelineConfig = field(default_factory=TimelineConfig)
    progress: ProgressConfig = field(default_factory=ProgressConfig)
    sidebar: SidebarConfig = field(default_factory=SidebarConfig)


# Глобальная конфигурация UI
ui_config = UIConfig()
