from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ForecastContext:
    train_rows: list[dict[str, Any]]
    future_rows: list[dict[str, Any]]
    horizon_steps: int


class BaselineForecaster(Protocol):
    name: str

    def predict(self, context: ForecastContext) -> list[float]: ...
