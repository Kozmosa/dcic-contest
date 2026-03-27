from __future__ import annotations

import statistics

from dcic_contest.baseline.base import ForecastContext
from dcic_contest.baseline.features import weekday_slot_key


class WeekdaySlotMeanForecaster:
    name = "weekday_slot_mean"

    def predict(self, context: ForecastContext) -> list[float]:
        grouped: dict[tuple[int, int], list[float]] = {}
        global_values: list[float] = []

        for row in context.train_rows:
            row_time = row["TIME"]
            key = weekday_slot_key(row_time)
            grouped.setdefault(key, []).append(float(row["V"]))
            global_values.append(float(row["V"]))

        global_mean = statistics.fmean(global_values)
        predictions: list[float] = []
        for row in context.future_rows:
            slot_values = grouped.get(weekday_slot_key(row["TIME"]))
            predictions.append(
                statistics.fmean(slot_values) if slot_values else global_mean
            )
        return predictions
