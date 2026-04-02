from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class FeatureSpec:
    target_column: str = "V"
    lag_steps: tuple[int, ...] = (1, 4, 96, 192, 288, 672, 1344, 2688)
    rolling_windows: tuple[int, ...] = (4, 8, 16, 32, 96, 192)
    rolling_stats: tuple[str, ...] = ("mean", "min", "max", "std")
    same_slot_windows_days: tuple[int, ...] = (3, 7, 14, 28)
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
    if stat_name == "std":
        return statistics.pstdev(values) if len(values) > 1 else 0.0
    raise ValueError(f"Unsupported rolling stat: {stat_name}")


def _same_slot_history(
    values: list[float],
    index: int,
    horizon_steps: int,
    days: int,
) -> list[float] | None:
    offsets = [horizon_steps * day for day in range(1, days + 1)]
    if any(index < offset for offset in offsets):
        return None
    return [values[index - offset] for offset in offsets]


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

        for days in feature_spec.same_slot_windows_days:
            same_slot_values = _same_slot_history(values, index, 96, days)
            if same_slot_values is None:
                feature_row[f"same_slot_{days}d_mean"] = None
                feature_row[f"same_slot_{days}d_std"] = None
                feature_row[f"same_slot_{days}d_min"] = None
                feature_row[f"same_slot_{days}d_max"] = None
                is_complete = False
            else:
                feature_row[f"same_slot_{days}d_mean"] = _rolling_stat(
                    same_slot_values, "mean"
                )
                feature_row[f"same_slot_{days}d_std"] = _rolling_stat(
                    same_slot_values, "std"
                )
                feature_row[f"same_slot_{days}d_min"] = _rolling_stat(
                    same_slot_values, "min"
                )
                feature_row[f"same_slot_{days}d_max"] = _rolling_stat(
                    same_slot_values, "max"
                )

        if feature_spec.drop_incomplete_rows and not is_complete:
            continue
        output_rows.append(feature_row)

    return output_rows


def feature_column_names(spec: FeatureSpec | None = None) -> list[str]:
    feature_spec = FeatureSpec() if spec is None else spec
    columns = [
        "hour",
        "minute",
        "quarter_slot",
        "weekday",
        "month",
        "day",
        "dayofyear",
        "weekofyear",
        "is_weekend",
    ]
    columns.extend(f"lag_{lag_step}" for lag_step in feature_spec.lag_steps)
    for window in feature_spec.rolling_windows:
        for stat_name in feature_spec.rolling_stats:
            columns.append(f"rolling_{window}_{stat_name}")
    for days in feature_spec.same_slot_windows_days:
        columns.extend(
            [
                f"same_slot_{days}d_mean",
                f"same_slot_{days}d_std",
                f"same_slot_{days}d_min",
                f"same_slot_{days}d_max",
            ]
        )
    return columns


def build_prediction_features(
    history_rows: list[dict[str, Any]],
    prediction_time: datetime,
    spec: FeatureSpec | None = None,
) -> dict[str, Any]:
    feature_spec = FeatureSpec() if spec is None else spec
    target_column = feature_spec.target_column
    values = [float(row[target_column]) for row in history_rows]
    feature_row: dict[str, Any] = {"TIME": prediction_time}
    feature_row.update(build_time_features(prediction_time))

    for lag_step in feature_spec.lag_steps:
        if len(values) < lag_step:
            raise ValueError(f"Not enough history for lag feature lag_{lag_step}")
        feature_row[f"lag_{lag_step}"] = values[-lag_step]

    for window in feature_spec.rolling_windows:
        if len(values) < window:
            raise ValueError(f"Not enough history for rolling feature window {window}")
        history = values[-window:]
        for stat_name in feature_spec.rolling_stats:
            feature_row[f"rolling_{window}_{stat_name}"] = _rolling_stat(
                history, stat_name
            )

    for days in feature_spec.same_slot_windows_days:
        same_slot_values = _same_slot_history(values, len(values), 96, days)
        if same_slot_values is None:
            raise ValueError(
                f"Not enough history for same-slot feature window {days} days"
            )
        feature_row[f"same_slot_{days}d_mean"] = _rolling_stat(
            same_slot_values, "mean"
        )
        feature_row[f"same_slot_{days}d_std"] = _rolling_stat(
            same_slot_values, "std"
        )
        feature_row[f"same_slot_{days}d_min"] = _rolling_stat(
            same_slot_values, "min"
        )
        feature_row[f"same_slot_{days}d_max"] = _rolling_stat(
            same_slot_values, "max"
        )

    return feature_row
