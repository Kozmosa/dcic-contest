from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class FeatureSpec:
    target_column: str = "V"
    lag_steps: tuple[int, ...] = (1, 4, 96, 192, 288, 672)
    rolling_windows: tuple[int, ...] = (4, 8, 16, 32, 96)
    rolling_stats: tuple[str, ...] = ("mean", "min", "max")
    same_weekday_slot_windows: tuple[int, ...] = (4, 8, 16)
    same_slot_day_windows: tuple[int, ...] = (7, 14, 28)
    drop_incomplete_rows: bool = True


HOLIDAY_DATES = {
    date(2024, 1, 1),
    date(2024, 2, 10),
    date(2024, 2, 11),
    date(2024, 2, 12),
    date(2024, 2, 13),
    date(2024, 2, 14),
    date(2024, 2, 15),
    date(2024, 2, 16),
    date(2024, 2, 17),
    date(2024, 4, 4),
    date(2024, 4, 5),
    date(2024, 4, 6),
    date(2024, 5, 1),
    date(2024, 5, 2),
    date(2024, 5, 3),
    date(2024, 5, 4),
    date(2024, 5, 5),
    date(2024, 6, 8),
    date(2024, 6, 9),
    date(2024, 6, 10),
    date(2024, 9, 15),
    date(2024, 9, 16),
    date(2024, 9, 17),
    date(2024, 10, 1),
    date(2024, 10, 2),
    date(2024, 10, 3),
    date(2024, 10, 4),
    date(2024, 10, 5),
    date(2024, 10, 6),
    date(2024, 10, 7),
}

MAKEUP_WORKDAY_DATES = {
    date(2024, 2, 4),
    date(2024, 2, 18),
    date(2024, 4, 7),
    date(2024, 4, 28),
    date(2024, 5, 11),
    date(2024, 9, 14),
    date(2024, 9, 29),
    date(2024, 10, 12),
}


def quarter_slot(value: datetime) -> int:
    return value.hour * 4 + value.minute // 15


def weekday_slot_key(value: datetime) -> tuple[int, int]:
    return value.weekday(), quarter_slot(value)


def build_time_features(value: datetime) -> dict[str, int]:
    day = value.date()
    is_holiday = int(day in HOLIDAY_DATES)
    is_makeup_workday = int(day in MAKEUP_WORKDAY_DATES)
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
        "is_holiday": is_holiday,
        "is_makeup_workday": is_makeup_workday,
        "is_workday": int(
            not is_holiday and (value.weekday() < 5 or is_makeup_workday)
        ),
        "is_pre_holiday": int(day + timedelta(days=1) in HOLIDAY_DATES),
        "is_post_holiday": int(day - timedelta(days=1) in HOLIDAY_DATES),
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
    same_weekday_slot_history: dict[tuple[int, int], list[float]] = {}
    same_slot_day_history: dict[int, list[float]] = {}

    for index, row in enumerate(rows):
        row_time = row["TIME"]
        slot_key = quarter_slot(row_time)
        weekday_slot = weekday_slot_key(row_time)
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

        weekday_slot_values = same_weekday_slot_history.get(weekday_slot, [])
        for window in feature_spec.same_weekday_slot_windows:
            feature_name = f"same_weekday_slot_mean_{window}"
            if len(weekday_slot_values) >= window:
                feature_row[feature_name] = statistics.fmean(
                    weekday_slot_values[-window:]
                )
            else:
                feature_row[feature_name] = None
                is_complete = False

        same_slot_values = same_slot_day_history.get(slot_key, [])
        for window in feature_spec.same_slot_day_windows:
            feature_name = f"same_slot_mean_{window}d"
            if len(same_slot_values) >= window:
                feature_row[feature_name] = statistics.fmean(same_slot_values[-window:])
            else:
                feature_row[feature_name] = None
                is_complete = False

        if feature_spec.drop_incomplete_rows and not is_complete:
            same_weekday_slot_history.setdefault(weekday_slot, []).append(
                float(row[target_column])
            )
            same_slot_day_history.setdefault(slot_key, []).append(
                float(row[target_column])
            )
            continue
        output_rows.append(feature_row)
        same_weekday_slot_history.setdefault(weekday_slot, []).append(
            float(row[target_column])
        )
        same_slot_day_history.setdefault(slot_key, []).append(float(row[target_column]))

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
        "is_holiday",
        "is_makeup_workday",
        "is_workday",
        "is_pre_holiday",
        "is_post_holiday",
    ]
    columns.extend(f"lag_{lag_step}" for lag_step in feature_spec.lag_steps)
    for window in feature_spec.rolling_windows:
        for stat_name in feature_spec.rolling_stats:
            columns.append(f"rolling_{window}_{stat_name}")
    for window in feature_spec.same_weekday_slot_windows:
        columns.append(f"same_weekday_slot_mean_{window}")
    for window in feature_spec.same_slot_day_windows:
        columns.append(f"same_slot_mean_{window}d")
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
    history_before_prediction = [
        row for row in history_rows if row["TIME"] < prediction_time
    ]
    weekday_slot_values = [
        float(row[target_column])
        for row in history_before_prediction
        if weekday_slot_key(row["TIME"]) == weekday_slot_key(prediction_time)
    ]
    same_slot_values = [
        float(row[target_column])
        for row in history_before_prediction
        if quarter_slot(row["TIME"]) == quarter_slot(prediction_time)
    ]

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

    for window in feature_spec.same_weekday_slot_windows:
        feature_name = f"same_weekday_slot_mean_{window}"
        if len(weekday_slot_values) < window:
            raise ValueError(
                f"Not enough history for same weekday slot feature window {window}"
            )
        feature_row[feature_name] = statistics.fmean(weekday_slot_values[-window:])

    for window in feature_spec.same_slot_day_windows:
        feature_name = f"same_slot_mean_{window}d"
        if len(same_slot_values) < window:
            raise ValueError(
                f"Not enough history for same slot feature window {window}"
            )
        feature_row[feature_name] = statistics.fmean(same_slot_values[-window:])

    return feature_row
