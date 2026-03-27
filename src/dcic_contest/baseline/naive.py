from __future__ import annotations

import statistics

from dcic_contest.baseline.base import ForecastContext


class LastDaySameSlotForecaster:
    name = "last_day_same_slot"

    def predict(self, context: ForecastContext) -> list[float]:
        history = [float(row["V"]) for row in context.train_rows]
        if len(history) < context.horizon_steps:
            raise ValueError("history length is shorter than horizon_steps")
        return history[-context.horizon_steps :]


class Last7DaySameSlotForecaster:
    name = "last_7day_same_slot"

    def predict(self, context: ForecastContext) -> list[float]:
        history = [float(row["V"]) for row in context.train_rows]
        required = context.horizon_steps * 7
        if len(history) < required:
            raise ValueError("history length is shorter than seven days of slots")

        predictions: list[float] = []
        for slot in range(context.horizon_steps):
            slot_values = [
                history[-required + slot + day * context.horizon_steps]
                for day in range(7)
            ]
            predictions.append(statistics.fmean(slot_values))
        return predictions
