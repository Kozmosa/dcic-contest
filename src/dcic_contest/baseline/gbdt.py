from __future__ import annotations

# pyright: reportMissingImports=false

from dataclasses import dataclass, field
from typing import Any

from sklearn.multioutput import MultiOutputRegressor

from dcic_contest.baseline.base import ForecastContext
from dcic_contest.baseline.features import (
    FeatureSpec,
    build_feature_rows,
    build_prediction_features,
    feature_column_names,
)


@dataclass(frozen=True)
class LightGBMConfig:
    feature_spec: FeatureSpec = field(default_factory=FeatureSpec)
    params: dict[str, Any] = field(
        default_factory=lambda: {
            "n_estimators": 500,
            "learning_rate": 0.03,
            "num_leaves": 31,
            "min_child_samples": 48,
            "subsample": 0.85,
            "subsample_freq": 1,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
            "n_jobs": 1,
            "verbosity": -1,
        }
    )


class _LightGBMBaseForecaster:
    def __init__(self, config: LightGBMConfig | None = None) -> None:
        self.config = LightGBMConfig() if config is None else config

    def _build_regressor(self) -> Any:
        try:
            from lightgbm import LGBMRegressor
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "lightgbm is required for LightGBM baselines. "
                "Add it to the environment before running this baseline."
            ) from exc
        return LGBMRegressor(**self.config.params)

    def _build_dataframe(
        self,
        rows: list[dict[str, float]],
        columns: list[str],
    ) -> Any:
        try:
            import pandas as pd
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "pandas is required for LightGBM feature matrix construction. "
                "Add it to the environment before running this baseline."
            ) from exc
        return pd.DataFrame(rows, columns=columns).astype(float)

    def _prepare_training_matrix(
        self, train_rows: list[dict[str, Any]]
    ) -> tuple[Any, list[float], list[str]]:
        feature_rows = build_feature_rows(train_rows, self.config.feature_spec)
        columns = feature_column_names(self.config.feature_spec)
        target_column = self.config.feature_spec.target_column
        x_train = self._build_dataframe(feature_rows, columns)
        y_train = [float(row[target_column]) for row in feature_rows]
        if x_train.empty:
            raise ValueError("No training rows available after feature generation")
        return x_train, y_train, columns


class LightGBMRecursiveForecaster(_LightGBMBaseForecaster):
    name = "lightgbm_recursive"

    def predict(self, context: ForecastContext) -> list[float]:
        x_train, y_train, columns = self._prepare_training_matrix(context.train_rows)
        model = self._build_regressor()
        model.fit(x_train, y_train)

        history_rows = [dict(row) for row in context.train_rows]
        predictions: list[float] = []
        target_column = self.config.feature_spec.target_column

        for future_row in context.future_rows:
            feature_row = build_prediction_features(
                history_rows,
                future_row["TIME"],
                self.config.feature_spec,
            )
            x_future = self._build_dataframe(
                [{column: float(feature_row[column]) for column in columns}],
                columns,
            )
            predicted_value = float(model.predict(x_future)[0])
            predictions.append(predicted_value)
            history_rows.append(
                {"TIME": future_row["TIME"], target_column: predicted_value}
            )

        return predictions


class LightGBMDirectForecaster(_LightGBMBaseForecaster):
    name = "lightgbm_direct"

    def _prepare_direct_training_matrix(
        self, train_rows: list[dict[str, Any]], horizon_steps: int
    ) -> tuple[Any, list[list[float]], list[str]]:
        feature_rows = build_feature_rows(train_rows, self.config.feature_spec)
        columns = feature_column_names(self.config.feature_spec)
        target_column = self.config.feature_spec.target_column
        usable_rows = (
            feature_rows[:-horizon_steps] if horizon_steps > 0 else feature_rows
        )
        if not usable_rows:
            raise ValueError("No training rows available for direct multi-step targets")

        x_train = self._build_dataframe(usable_rows, columns)
        y_train: list[list[float]] = []
        for index in range(len(usable_rows)):
            target_vector = [
                float(feature_rows[index + step][target_column])
                for step in range(horizon_steps)
            ]
            y_train.append(target_vector)
        return x_train, y_train, columns

    def predict(self, context: ForecastContext) -> list[float]:
        horizon = len(context.future_rows)
        x_train, y_train, columns = self._prepare_direct_training_matrix(
            context.train_rows, horizon
        )
        future_feature = build_prediction_features(
            context.train_rows,
            context.future_rows[0]["TIME"],
            self.config.feature_spec,
        )
        x_future = self._build_dataframe(
            [{column: float(future_feature[column]) for column in columns}],
            columns,
        )
        model = self._build_regressor()
        multi_output_model = MultiOutputRegressor(model)
        multi_output_model.fit(x_train, y_train)
        predictions = multi_output_model.predict(x_future)[0]
        return [float(value) for value in predictions]


@dataclass(frozen=True)
class LightGBMRecursiveClippedConfig:
    base: LightGBMConfig = field(default_factory=LightGBMConfig)
    clip_history_days: int = 14
    clip_quantile_low: float = 0.0
    clip_quantile_high: float = 1.0


class LightGBMRecursiveClippedForecaster(LightGBMRecursiveForecaster):
    name = "lightgbm_recursive_clipped"

    def __init__(
        self, config: LightGBMRecursiveClippedConfig | None = None
    ) -> None:
        self.clip_config = (
            LightGBMRecursiveClippedConfig() if config is None else config
        )
        super().__init__(self.clip_config.base)

    def _clip_prediction(self, history_rows: list[dict[str, Any]], value: float) -> float:
        history_values = [float(row["V"]) for row in history_rows]
        clip_window = 96 * self.clip_config.clip_history_days
        recent_values = (
            history_values[-clip_window:] if len(history_values) >= clip_window else history_values
        )
        if not recent_values:
            return value
        sorted_values = sorted(recent_values)
        lower_index = int((len(sorted_values) - 1) * self.clip_config.clip_quantile_low)
        upper_index = int((len(sorted_values) - 1) * self.clip_config.clip_quantile_high)
        lower_bound = sorted_values[lower_index]
        upper_bound = sorted_values[upper_index]
        return min(max(value, lower_bound), upper_bound)

    def predict(self, context: ForecastContext) -> list[float]:
        x_train, y_train, columns = self._prepare_training_matrix(context.train_rows)
        model = self._build_regressor()
        model.fit(x_train, y_train)

        history_rows = [dict(row) for row in context.train_rows]
        predictions: list[float] = []
        target_column = self.config.feature_spec.target_column

        for future_row in context.future_rows:
            feature_row = build_prediction_features(
                history_rows,
                future_row["TIME"],
                self.config.feature_spec,
            )
            x_future = self._build_dataframe(
                [{column: float(feature_row[column]) for column in columns}],
                columns,
            )
            predicted_value = float(model.predict(x_future)[0])
            predicted_value = self._clip_prediction(history_rows, predicted_value)
            predictions.append(predicted_value)
            history_rows.append(
                {"TIME": future_row["TIME"], target_column: predicted_value}
            )

        return predictions


class LightGBMRecursiveClippedP95Forecaster(LightGBMRecursiveClippedForecaster):
    name = "lightgbm_recursive_clipped_p95"

    def __init__(self) -> None:
        super().__init__(
            LightGBMRecursiveClippedConfig(
                clip_history_days=14,
                clip_quantile_low=0.01,
                clip_quantile_high=0.99,
            )
        )


class LightGBMRecursiveClippedHardForecaster(LightGBMRecursiveClippedForecaster):
    name = "lightgbm_recursive_clipped_hard"

    def __init__(self) -> None:
        super().__init__(
            LightGBMRecursiveClippedConfig(
                clip_history_days=14,
                clip_quantile_low=0.0,
                clip_quantile_high=1.0,
            )
        )
