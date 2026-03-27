from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class FeatureSpec:
    target_column: str = "V"
    lag_steps: tuple[int, ...] = (1, 4, 96, 192, 288, 672)
    rolling_windows: tuple[int, ...] = (4, 8, 16, 32, 96)
    rolling_stats: tuple[str, ...] = ("mean", "min", "max")
    drop_incomplete_rows: bool = True


def quarter_slot(value: datetime) -> int:
    return value.hour * 4 + value.minute // 15


def weekday_slot_key(value: datetime) -> tuple[int, int]:
    return value.weekday(), quarter_slot(value)


def build_time_features(value: datetime) -> dict[str, int]:
    return {
        "hour": value.hour,
        "minute": value.minute,
        "quarter_slot": quarter_slot(value),
        "weekday": value.weekday(),
        "month": value.month,
        "day": value.day,
        "dayofyear": value.timetuple().tm_yday,
        "weekofyear": value.isocalendar().week,
        "is_weekend": int(value.weekday() >= 5),
    }


def _rolling_stat(values: list[float], stat_name: str) -> float:
    if stat_name == "mean":
        return statistics.fmean(values)
    if stat_name == "min":
        return min(values)
    if stat_name == "max":
        return max(values)
    raise ValueError(f"Unsupported rolling stat: {stat_name}")


def build_feature_rows(
    rows: list[dict[str, Any]],
    spec: FeatureSpec | None = None,
) -> list[dict[str, Any]]:
    feature_spec = FeatureSpec() if spec is None else spec
    target_column = feature_spec.target_column
    values = [float(row[target_column]) for row in rows]
    output_rows: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        row_time = row["TIME"]
        feature_row: dict[str, Any] = {
            "TIME": row_time,
            target_column: float(row[target_column]),
        }
        feature_row.update(build_time_features(row_time))

        is_complete = True

        for lag_step in feature_spec.lag_steps:
            feature_name = f"lag_{lag_step}"
            if index >= lag_step:
                feature_row[feature_name] = values[index - lag_step]
            else:
                feature_row[feature_name] = None
                is_complete = False

        for window in feature_spec.rolling_windows:
            if index >= window:
                history = values[index - window : index]
                for stat_name in feature_spec.rolling_stats:
                    feature_row[f"rolling_{window}_{stat_name}"] = _rolling_stat(
                        history, stat_name
                    )
            else:
                for stat_name in feature_spec.rolling_stats:
                    feature_row[f"rolling_{window}_{stat_name}"] = None
                is_complete = False

        if feature_spec.drop_incomplete_rows and not is_complete:
            continue
        output_rows.append(feature_row)

    return output_rows
