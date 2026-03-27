from __future__ import annotations

from datetime import datetime


def quarter_slot(value: datetime) -> int:
    return value.hour * 4 + value.minute // 15


def weekday_slot_key(value: datetime) -> tuple[int, int]:
    return value.weekday(), quarter_slot(value)
