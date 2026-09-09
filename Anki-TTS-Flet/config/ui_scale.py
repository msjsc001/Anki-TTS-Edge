from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MIN_UI_SCALE_PERCENT = 30
MAX_UI_SCALE_PERCENT = 200
DEFAULT_UI_SCALE_PERCENT = 100


def normalize_ui_scale_percent(value: Any) -> int:
    """Return an integer UI scale percentage within the supported range."""
    if isinstance(value, bool):
        return DEFAULT_UI_SCALE_PERCENT
    if isinstance(value, float) and not value.is_integer():
        return DEFAULT_UI_SCALE_PERCENT
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return DEFAULT_UI_SCALE_PERCENT

    if not MIN_UI_SCALE_PERCENT <= normalized <= MAX_UI_SCALE_PERCENT:
        return DEFAULT_UI_SCALE_PERCENT
    return normalized


@dataclass(frozen=True)
class UiScale:
    """Scale logical UI dimensions without changing the outer window size."""

    percent: int = DEFAULT_UI_SCALE_PERCENT

    def __post_init__(self) -> None:
        object.__setattr__(self, "percent", normalize_ui_scale_percent(self.percent))

    @property
    def factor(self) -> float:
        return self.percent / 100.0

    def px(self, value: int | float, *, minimum: int | float | None = None) -> int | float:
        scaled = round(float(value) * self.factor, 2)
        if minimum is not None:
            scaled = max(float(minimum), scaled)
        if isinstance(value, int) and scaled.is_integer():
            return int(scaled)
        return scaled

    def font(self, value: int | float) -> int | float:
        return self.px(value)
