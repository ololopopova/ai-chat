"""Тесты для компонента timeline."""

from ui.components.timeline import (
    STAGE_ORDER,
    complete_all_stages,
    get_initial_stages,
    update_stage,
)
from ui.models.events import StageName, StageStatus


class TestTimeline:
    """Тесты для функций timeline."""

    def test_stage_order_contains_all_stages(self) -> None:
        """STAGE_ORDER содержит все стадии."""
        assert (
            len(STAGE_ORDER) == 7
        )  # router, clarify, retrieve, generate, off_topic, tool_select, tool_execute
        assert StageName.ROUTER in STAGE_ORDER
        assert StageName.GENERATE in STAGE_ORDER
        assert StageName.OFF_TOPIC in STAGE_ORDER

    def test_get_initial_stages(self) -> None:
        """Начальное состояние — пустой словарь."""
        stages = get_initial_stages()
        assert stages == {}

    def test_update_stage_first(self) -> None:
        """Обновление первой стадии."""
        stages = update_stage({}, StageName.ROUTER)
        assert stages[StageName.ROUTER] == StageStatus.ACTIVE

    def test_update_stage_marks_previous_completed(self) -> None:
        """Предыдущие стадии становятся completed."""
        stages = {StageName.ROUTER: StageStatus.ACTIVE}
        stages = update_stage(stages, StageName.RETRIEVE)

        assert stages[StageName.ROUTER] == StageStatus.COMPLETED
        assert stages[StageName.RETRIEVE] == StageStatus.ACTIVE

    def test_update_stage_multiple(self) -> None:
        """Несколько последовательных обновлений."""
        stages: dict[StageName, StageStatus] = {}
        stages = update_stage(stages, StageName.ROUTER)
        stages = update_stage(stages, StageName.RETRIEVE)
        stages = update_stage(stages, StageName.GENERATE)

        assert stages[StageName.ROUTER] == StageStatus.COMPLETED
        assert stages[StageName.RETRIEVE] == StageStatus.COMPLETED
        assert stages[StageName.GENERATE] == StageStatus.ACTIVE

    def test_complete_all_stages(self) -> None:
        """Завершение всех активных стадий."""
        stages = {
            StageName.ROUTER: StageStatus.COMPLETED,
            StageName.RETRIEVE: StageStatus.ACTIVE,
        }
        completed = complete_all_stages(stages)

        assert completed[StageName.ROUTER] == StageStatus.COMPLETED
        assert completed[StageName.RETRIEVE] == StageStatus.COMPLETED
