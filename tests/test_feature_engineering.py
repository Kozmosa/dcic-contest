from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from dcic_contest.baseline.features import (
    FeatureSpec,
    build_feature_rows,
    build_time_features,
)


def make_rows(
    start: datetime, values: list[float], step_minutes: int = 15
) -> list[dict]:
    return [
        {"TIME": start + timedelta(minutes=step_minutes * idx), "V": value}
        for idx, value in enumerate(values)
    ]


class TimeFeatureTest(unittest.TestCase):
    def test_build_time_features(self) -> None:
        features = build_time_features(datetime(2024, 1, 6, 13, 45))

        self.assertEqual(features["hour"], 13)
        self.assertEqual(features["minute"], 45)
        self.assertEqual(features["quarter_slot"], 55)
        self.assertEqual(features["weekday"], 5)
        self.assertEqual(features["month"], 1)
        self.assertEqual(features["day"], 6)
        self.assertEqual(features["is_weekend"], 1)


class FeatureRowBuilderTest(unittest.TestCase):
    def test_build_feature_rows_with_lag_and_rolling_features(self) -> None:
        rows = make_rows(datetime(2024, 1, 1, 0, 0), [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        spec = FeatureSpec(
            lag_steps=(1, 3),
            rolling_windows=(2, 4),
            rolling_stats=("mean", "min", "max"),
            drop_incomplete_rows=False,
        )

        feature_rows = build_feature_rows(rows, spec)
        target_row = feature_rows[4]

        self.assertEqual(target_row["lag_1"], 4.0)
        self.assertEqual(target_row["lag_3"], 2.0)
        self.assertEqual(target_row["rolling_2_mean"], 3.5)
        self.assertEqual(target_row["rolling_2_min"], 3.0)
        self.assertEqual(target_row["rolling_2_max"], 4.0)
        self.assertEqual(target_row["rolling_4_mean"], 2.5)
        self.assertEqual(target_row["rolling_4_min"], 1.0)
        self.assertEqual(target_row["rolling_4_max"], 4.0)

    def test_drop_incomplete_rows_keeps_only_fully_available_features(self) -> None:
        rows = make_rows(datetime(2024, 1, 1, 0, 0), [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        spec = FeatureSpec(
            lag_steps=(1, 3),
            rolling_windows=(2, 4),
            rolling_stats=("mean",),
            drop_incomplete_rows=True,
        )

        feature_rows = build_feature_rows(rows, spec)

        self.assertEqual(len(feature_rows), 2)
        self.assertEqual(feature_rows[0]["V"], 5.0)
        self.assertEqual(feature_rows[1]["V"], 6.0)

    def test_rejects_unsupported_rolling_stat(self) -> None:
        rows = make_rows(datetime(2024, 1, 1, 0, 0), [1.0, 2.0, 3.0])
        spec = FeatureSpec(
            lag_steps=(),
            rolling_windows=(2,),
            rolling_stats=("std",),
            drop_incomplete_rows=False,
        )

        with self.assertRaisesRegex(ValueError, "Unsupported rolling stat"):
            build_feature_rows(rows, spec)


if __name__ == "__main__":
    unittest.main()
