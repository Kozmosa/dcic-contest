from __future__ import annotations

# pyright: reportMissingImports=false

from dataclasses import dataclass, field
from typing import Any

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
            "n_estimators": 300,
            "learning_rate": 0.05,
            "num_leaves": 31,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "random_state": 42,
            "verbosity": -1,
        }
    )


class LightGBMRecursiveForecaster:
    name = "lightgbm_recursive"

    def __init__(self, config: LightGBMConfig | None = None) -> None:
        self.config = LightGBMConfig() if config is None else config

    def _build_regressor(self) -> Any:
        try:
            from lightgbm import LGBMRegressor
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "lightgbm is required for lightgbm_recursive. "
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
                "pandas is required for lightgbm_recursive feature matrix construction. "
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
