from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from .models import AppMode


class OverlayAction(Enum):
    NONE = auto()
    REVEAL = auto()
    SCHEDULE_DIM = auto()
    DIM_NOW = auto()


@dataclass
class OverlayIntent:
    """Small deterministic state machine behind one overlay window."""

    desired_dimmed: bool = True
    restore_pending: bool = False

    def request(self, should_dim: bool, delayed: bool) -> OverlayAction:
        if should_dim == self.desired_dimmed:
            return OverlayAction.NONE
        self.desired_dimmed = should_dim
        self.restore_pending = should_dim and delayed
        if not should_dim:
            return OverlayAction.REVEAL
        return OverlayAction.SCHEDULE_DIM if delayed else OverlayAction.DIM_NOW

    def timer_expired(self) -> OverlayAction:
        if not self.desired_dimmed or not self.restore_pending:
            return OverlayAction.NONE
        self.restore_pending = False
        return OverlayAction.DIM_NOW

    def settle_after_preview(self) -> OverlayAction:
        self.restore_pending = False
        return OverlayAction.DIM_NOW if self.desired_dimmed else OverlayAction.REVEAL


def dim_targets(
    monitor_names: list[str],
    mode: AppMode,
    activity_monitor: str | None,
    enabled: bool,
    temporary_reveal: bool,
) -> dict[str, bool]:
    """Return whether each eligible monitor should currently be dimmed."""
    if not enabled or temporary_reveal:
        return {name: False for name in monitor_names}
    if mode is AppMode.MANUAL:
        return {name: True for name in monitor_names}
    return {name: name != activity_monitor for name in monitor_names}
