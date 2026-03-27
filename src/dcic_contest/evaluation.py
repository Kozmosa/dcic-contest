from __future__ import annotations

import csv
import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dcic_contest.baseline import build_forecasters
from dcic_contest.baseline.base import ForecastContext
from dcic_contest.data_audit import Task1DataBundle, load_task1_training_data


@dataclass
class EvaluationConfig:
    input_csv: Path
    output_dir: Path
    encoding: str = "gb18030"
    horizon_steps: int = 96
    n_folds: int = 3
    baseline_names: list[str] | None = None


def rmse(y_true: list[float], y_pred: list[float]) -> float:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    if not y_true:
        raise ValueError("y_true and y_pred must not be empty")
    squared_error = [(truth - pred) ** 2 for truth, pred in zip(y_true, y_pred)]
    return math.sqrt(sum(squared_error) / len(squared_error))


def _ensure_dirs(output_dir: Path) -> dict[str, Path]:
    paths = {
        "root": output_dir,
        "tables": output_dir / "tables",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_folds(
    rows: list[dict[str, Any]], horizon_steps: int, n_folds: int
) -> list[tuple[int, int]]:
    rows_count = len(rows)
    min_train_steps = horizon_steps * 14
    folds: list[tuple[int, int]] = []
    for idx in range(n_folds, 0, -1):
        test_end = rows_count - horizon_steps * (idx - 1)
        test_start = test_end - horizon_steps
        train_end = test_start
        if train_end < min_train_steps:
            raise ValueError("Not enough data to build requested folds")
        folds.append((train_end, test_end))
    return folds


def run_backtest(config: EvaluationConfig) -> dict[str, Any]:
    dirs = _ensure_dirs(config.output_dir)
    bundle: Task1DataBundle = load_task1_training_data(
        config.input_csv, config.encoding
    )
    rows = bundle.rows
    folds = _build_folds(rows, config.horizon_steps, config.n_folds)
    forecasters = build_forecasters(config.baseline_names)

    fold_rows: list[dict[str, Any]] = []
    all_metrics: dict[str, list[float]] = {model.name: [] for model in forecasters}

    for fold_index, (train_end, test_end) in enumerate(folds, start=1):
        train_rows = rows[:train_end]
        test_rows = rows[train_end:test_end]
        y_true = [float(row["V"]) for row in test_rows]

        context = ForecastContext(
            train_rows=train_rows,
            future_rows=test_rows,
            horizon_steps=config.horizon_steps,
        )
        metrics = {
            model.name: rmse(y_true, model.predict(context)) for model in forecasters
        }
        for model_name, metric in metrics.items():
            all_metrics[model_name].append(metric)

        fold_row: dict[str, Any] = {
            "fold": fold_index,
            "train_end_time": train_rows[-1]["TIME"].strftime("%Y/%m/%d %H:%M"),
            "test_start_time": test_rows[0]["TIME"].strftime("%Y/%m/%d %H:%M"),
            "test_end_time": test_rows[-1]["TIME"].strftime("%Y/%m/%d %H:%M"),
        }
        for model_name, metric in metrics.items():
            fold_row[f"{model_name}_rmse"] = round(metric, 6)
        fold_rows.append(fold_row)

    overall_rows = [
        {
            "model": model_name,
            "fold_count": len(values),
            "rmse_mean": round(statistics.fmean(values), 6),
            "rmse_std": round(statistics.pstdev(values) if len(values) > 1 else 0.0, 6),
            "rmse_min": round(min(values), 6),
            "rmse_max": round(max(values), 6),
        }
        for model_name, values in all_metrics.items()
    ]

    _write_csv(
        dirs["tables"] / "fold_metrics.csv", list(fold_rows[0].keys()), fold_rows
    )
    _write_csv(
        dirs["tables"] / "overall_metrics.csv",
        list(overall_rows[0].keys()),
        overall_rows,
    )

    summary = {
        "source_file": str(config.input_csv),
        "n_folds": config.n_folds,
        "horizon_steps": config.horizon_steps,
        "horizon_hours": config.horizon_steps / 4,
        "baseline_names": [model.name for model in forecasters],
        "models": {
            model_name: {
                "rmse_mean": round(statistics.fmean(values), 6),
                "rmse_std": round(
                    statistics.pstdev(values) if len(values) > 1 else 0.0, 6
                ),
            }
            for model_name, values in all_metrics.items()
        },
        "best_model_by_mean_rmse": min(
            all_metrics.items(), key=lambda item: statistics.fmean(item[1])
        )[0],
    }
    (dirs["root"] / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary
