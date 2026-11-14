"""Injectable clock so overdue logic and tests are deterministic.

Datetimes are naive, matching the contract types and the seed data.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now()


class FixedClock:
    def __init__(self, at: datetime) -> None:
        self._at = at

    def now(self) -> datetime:
        return self._at

    def advance(self, **kwargs: float) -> None:
        self._at += timedelta(**kwargs)