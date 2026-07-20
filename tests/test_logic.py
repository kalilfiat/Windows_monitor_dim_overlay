from monitor_dim.logic import OverlayAction, OverlayIntent, dim_targets
from monitor_dim.models import AppMode


MONITORS = ["DISPLAY1", "DISPLAY2", "DISPLAY3"]


def test_cursor_and_active_modes_reveal_activity_monitor():
    targets = dim_targets(MONITORS, AppMode.CURSOR, "DISPLAY2", True, False)

    assert targets == {"DISPLAY1": True, "DISPLAY2": False, "DISPLAY3": True}


def test_manual_mode_dims_every_eligible_monitor():
    targets = dim_targets(MONITORS, AppMode.MANUAL, None, True, False)

    assert all(targets.values())


def test_disabled_or_peek_reveals_every_monitor():
    assert not any(dim_targets(MONITORS, AppMode.CURSOR, None, False, False).values())
    assert not any(dim_targets(MONITORS, AppMode.CURSOR, None, True, True).values())


def test_restore_delay_is_armed_only_once_during_repeated_polling():
    intent = OverlayIntent(desired_dimmed=True)
    assert intent.request(False, delayed=True) is OverlayAction.REVEAL
    assert intent.request(True, delayed=True) is OverlayAction.SCHEDULE_DIM

    for _ in range(20):
        assert intent.request(True, delayed=True) is OverlayAction.NONE

    assert intent.timer_expired() is OverlayAction.DIM_NOW
    assert intent.timer_expired() is OverlayAction.NONE


def test_reentering_monitor_cancels_pending_restore():
    intent = OverlayIntent(desired_dimmed=True)
    intent.request(False, delayed=True)
    intent.request(True, delayed=True)

    assert intent.request(False, delayed=True) is OverlayAction.REVEAL
    assert intent.timer_expired() is OverlayAction.NONE
