from __future__ import annotations

# pyright: reportMissingImports=false

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from dcic_contest.baseline.base import ForecastContext
from dcic_contest.baseline.naive import (
    Last7DaySameSlotForecaster,
    LastDaySameSlotForecaster,
)
from dcic_contest.baseline.registry import (
    DEFAULT_BASELINE_NAMES,
    available_baselines,
    build_forecasters,
)
from dcic_contest.baseline.seasonal import WeekdaySlotMeanForecaster


def make_rows(
    start: datetime, values: list[float], step_minutes: int = 15
) -> list[dict]:
    return [
        {"TIME": start + timedelta(minutes=step_minutes * idx), "V": value}
        for idx, value in enumerate(values)
    ]


class LastDaySameSlotForecasterTest(unittest.TestCase):
    def test_returns_last_day_values(self) -> None:
        horizon_steps = 4
        train_rows = make_rows(
            datetime(2024, 1, 1, 0, 0), [1.0, 2.0, 3.0, 4.0, 9.0, 8.0, 7.0, 6.0]
        )
        future_rows = make_rows(datetime(2024, 1, 1, 2, 0), [0.0, 0.0, 0.0, 0.0])

        predictions = LastDaySameSlotForecaster().predict(
            ForecastContext(
                train_rows=train_rows,
                future_rows=future_rows,
                horizon_steps=horizon_steps,
            )
        )

        self.assertEqual(predictions, [9.0, 8.0, 7.0, 6.0])

    def test_raises_when_history_is_shorter_than_horizon(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "history length is shorter than horizon_steps"
        ):
            LastDaySameSlotForecaster().predict(
                ForecastContext(
                    train_rows=make_rows(datetime(2024, 1, 1, 0, 0), [1.0, 2.0, 3.0]),
                    future_rows=[],
                    horizon_steps=4,
                )
            )


class Last7DaySameSlotForecasterTest(unittest.TestCase):
    def test_returns_seven_day_same_slot_mean(self) -> None:
        horizon_steps = 2
        values: list[float] = []
        for day in range(7):
            values.extend([float(day), float(day + 10)])
        train_rows = make_rows(datetime(2024, 1, 1, 0, 0), values)
        future_rows = make_rows(datetime(2024, 1, 8, 0, 0), [0.0, 0.0])

        predictions = Last7DaySameSlotForecaster().predict(
            ForecastContext(
                train_rows=train_rows,
                future_rows=future_rows,
                horizon_steps=horizon_steps,
            )
        )

        self.assertEqual(predictions, [3.0, 13.0])

    def test_raises_when_history_is_shorter_than_seven_days(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "history length is shorter than seven days of slots"
        ):
            Last7DaySameSlotForecaster().predict(
                ForecastContext(
                    train_rows=make_rows(datetime(2024, 1, 1, 0, 0), [1.0] * 13),
                    future_rows=[],
                    horizon_steps=2,
                )
            )


class WeekdaySlotMeanForecasterTest(unittest.TestCase):
    def test_uses_weekday_slot_mean_for_seen_key(self) -> None:
        train_rows = [
            {"TIME": datetime(2024, 1, 1, 0, 0), "V": 2.0},
            {"TIME": datetime(2024, 1, 8, 0, 0), "V": 4.0},
            {"TIME": datetime(2024, 1, 2, 0, 15), "V": 8.0},
        ]
        future_rows = [{"TIME": datetime(2024, 1, 15, 0, 0), "V": 0.0}]

        predictions = WeekdaySlotMeanForecaster().predict(
            ForecastContext(
                train_rows=train_rows,
                future_rows=future_rows,
                horizon_steps=1,
            )
        )

        self.assertEqual(predictions, [3.0])

    def test_falls_back_to_global_mean_for_unseen_key(self) -> None:
        train_rows = [
            {"TIME": datetime(2024, 1, 1, 0, 0), "V": 2.0},
            {"TIME": datetime(2024, 1, 8, 0, 0), "V": 4.0},
        ]
        future_rows = [{"TIME": datetime(2024, 1, 2, 0, 15), "V": 0.0}]

        predictions = WeekdaySlotMeanForecaster().predict(
            ForecastContext(
                train_rows=train_rows,
                future_rows=future_rows,
                horizon_steps=1,
            )
        )

        self.assertEqual(predictions, [3.0])


class RegistryTest(unittest.TestCase):
    def test_build_forecasters_returns_default_order(self) -> None:
        forecasters = build_forecasters()

        self.assertEqual(
            [forecaster.name for forecaster in forecasters], DEFAULT_BASELINE_NAMES
        )

    def test_available_baselines_is_sorted(self) -> None:
        baselines = available_baselines()

        self.assertEqual(baselines, sorted(baselines))
        self.assertTrue(set(DEFAULT_BASELINE_NAMES).issubset(set(baselines)))

    def test_build_forecasters_rejects_unknown_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown baseline names"):
            build_forecasters(["unknown_model"])


if __name__ == "__main__":
    unittest.main()
