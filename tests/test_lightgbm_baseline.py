from __future__ import annotations

# pyright: reportMissingImports=false

import importlib.util
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from dcic_contest.baseline.base import ForecastContext
from dcic_contest.baseline.features import FeatureSpec
from dcic_contest.baseline.gbdt import (
    LightGBMConfig,
    LightGBMDirectForecaster,
    LightGBMRecursiveForecaster,
)
from dcic_contest.baseline.registry import build_forecasters


def make_rows(
    start: datetime, values: list[float], step_minutes: int = 15
) -> list[dict]:
    return [
        {"TIME": start + timedelta(minutes=step_minutes * idx), "V": value}
        for idx, value in enumerate(values)
    ]


class FakeRegressor:
    def __init__(self) -> None:
        self.fit_x: Any = None
        self.fit_y: list[float] | None = None
        self.last_seen_values: list[float] = []

    def fit(self, x_train: Any, y_train: list[float]) -> None:
        self.fit_x = x_train
        self.fit_y = y_train

    def predict(self, x_future: Any) -> list[float]:
        self.last_seen_values.append(float(x_future.iloc[0, 0]))
        if self.fit_y and isinstance(self.fit_y[0], list):
            horizon = len(self.fit_y[0])
            return [[100.0 + offset for offset in range(1, horizon + 1)]]
        return [100.0 + len(self.last_seen_values)]


@unittest.skipUnless(
    importlib.util.find_spec("pandas") is not None,
    "pandas is required for LightGBM baseline tests",
)
class LightGBMRecursiveForecasterTest(unittest.TestCase):
    def test_prepare_training_matrix_builds_supervised_rows(self) -> None:
        rows = make_rows(datetime(2024, 1, 1, 0, 0), [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        forecaster = LightGBMRecursiveForecaster(
            LightGBMConfig(
                feature_spec=FeatureSpec(
                    lag_steps=(1, 2),
                    rolling_windows=(2,),
                    rolling_stats=("mean",),
                )
            )
        )

        x_train, y_train, columns = forecaster._prepare_training_matrix(rows)

        self.assertEqual(columns[0], "hour")
        self.assertEqual(columns[-1], "rolling_2_mean")
        self.assertEqual(len(x_train), 4)
        self.assertEqual(y_train, [3.0, 4.0, 5.0, 6.0])

    def test_predict_uses_recursive_history_updates(self) -> None:
        train_rows = make_rows(
            datetime(2024, 1, 1, 0, 0),
            [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        )
        future_rows = make_rows(datetime(2024, 1, 1, 1, 30), [0.0, 0.0])
        forecaster = LightGBMRecursiveForecaster(
            LightGBMConfig(
                feature_spec=FeatureSpec(
                    lag_steps=(1,),
                    rolling_windows=(2,),
                    rolling_stats=("mean",),
                )
            )
        )
        fake_regressor = FakeRegressor()

        with patch.object(forecaster, "_build_regressor", return_value=fake_regressor):
            predictions = forecaster.predict(
                ForecastContext(
                    train_rows=train_rows,
                    future_rows=future_rows,
                    horizon_steps=2,
                )
            )

        self.assertEqual(predictions, [101.0, 102.0])
        self.assertEqual(fake_regressor.fit_y, [3.0, 4.0, 5.0, 6.0])
        self.assertEqual(fake_regressor.last_seen_values[0], 1.0)
        self.assertEqual(fake_regressor.last_seen_values[1], 1.0)

    def test_registry_builds_lightgbm_forecaster(self) -> None:
        forecasters = build_forecasters(["lightgbm_recursive", "lightgbm_direct"])

        self.assertEqual(len(forecasters), 2)
        self.assertEqual(forecasters[0].name, "lightgbm_recursive")
        self.assertEqual(forecasters[1].name, "lightgbm_direct")


@unittest.skipUnless(
    importlib.util.find_spec("pandas") is not None,
    "pandas is required for LightGBM baseline tests",
)
class LightGBMDirectForecasterTest(unittest.TestCase):
    def test_predict_returns_horizon_length_predictions(self) -> None:
        train_rows = make_rows(
            datetime(2024, 1, 1, 0, 0),
            [float(idx) for idx in range(1, 40)],
            step_minutes=24 * 60,
        )
        future_rows = make_rows(
            datetime(2024, 2, 9, 0, 0),
            [0.0, 0.0],
            step_minutes=24 * 60,
        )
        forecaster = LightGBMDirectForecaster(
            LightGBMConfig(
                feature_spec=FeatureSpec(
                    lag_steps=(1, 7),
                    rolling_windows=(2, 4),
                    rolling_stats=("mean",),
                    same_weekday_slot_windows=(2,),
                    same_slot_day_windows=(7, 14),
                )
            )
        )
        fake_regressor = FakeRegressor()

        with patch.object(forecaster, "_build_regressor", return_value=fake_regressor):
            predictions = forecaster.predict(
                ForecastContext(
                    train_rows=train_rows,
                    future_rows=future_rows,
                    horizon_steps=2,
                )
            )

        self.assertEqual(predictions, [101.0, 102.0])


if __name__ == "__main__":
    unittest.main()
