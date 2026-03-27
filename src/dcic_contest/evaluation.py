from __future__ import annotations

import csv
import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dcic_contest.data_audit import Task1DataBundle, load_task1_training_data


@dataclass
class EvaluationConfig:
    input_csv: Path
    output_dir: Path
    encoding: str = "gb18030"
    horizon_steps: int = 96
    n_folds: int = 3


def rmse(y_true: list[float], y_pred: list[float]) -> float:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    if not y_true:
        raise ValueError("y_true and y_pred must not be empty")
    squared_error = [(truth - pred) ** 2 for truth, pred in zip(y_true, y_pred)]
    return math.sqrt(sum(squared_error) / len(squared_error))


def last_day_same_slot_forecast(
    history: list[float], horizon_steps: int
) -> list[float]:
    if len(history) < horizon_steps:
        raise ValueError("history length is shorter than horizon_steps")
    return history[-horizon_steps:]


def last_7day_same_slot_forecast(
    history: list[float], horizon_steps: int
) -> list[float]:
    required = horizon_steps * 7
    if len(history) < required:
        raise ValueError("history length is shorter than seven days of slots")
    predictions: list[float] = []
    for slot in range(horizon_steps):
        slot_values = [
            history[-required + slot + day * horizon_steps] for day in range(7)
        ]
        predictions.append(statistics.fmean(slot_values))
    return predictions


def weekday_slot_mean_forecast(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
) -> list[float]:
    grouped: dict[tuple[int, int], list[float]] = {}
    global_values: list[float] = []
    for row in train_rows:
        row_time = row["TIME"]
        weekday = row_time.weekday()
        slot = row_time.hour * 4 + row_time.minute // 15
        grouped.setdefault((weekday, slot), []).append(float(row["V"]))
        global_values.append(float(row["V"]))
    global_mean = statistics.fmean(global_values)
    predictions: list[float] = []
    for row in test_rows:
        row_time = row["TIME"]
        weekday = row_time.weekday()
        slot = row_time.hour * 4 + row_time.minute // 15
        slot_values = grouped.get((weekday, slot))
        predictions.append(
            statistics.fmean(slot_values) if slot_values else global_mean
        )
    return predictions


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

    fold_rows: list[dict[str, Any]] = []
    all_metrics: dict[str, list[float]] = {
        "last_day_same_slot": [],
        "last_7day_same_slot": [],
        "weekday_slot_mean": [],
    }

    for fold_index, (train_end, test_end) in enumerate(folds, start=1):
        train_rows = rows[:train_end]
        test_rows = rows[train_end:test_end]
        history = [float(row["V"]) for row in train_rows]
        y_true = [float(row["V"]) for row in test_rows]

        preds_last_day = last_day_same_slot_forecast(history, config.horizon_steps)
        preds_last_7day = last_7day_same_slot_forecast(history, config.horizon_steps)
        preds_weekday_slot = weekday_slot_mean_forecast(train_rows, test_rows)

        metrics = {
            "last_day_same_slot": rmse(y_true, preds_last_day),
            "last_7day_same_slot": rmse(y_true, preds_last_7day),
            "weekday_slot_mean": rmse(y_true, preds_weekday_slot),
        }
        for model_name, metric in metrics.items():
            all_metrics[model_name].append(metric)

        fold_rows.append(
            {
                "fold": fold_index,
                "train_end_time": train_rows[-1]["TIME"].strftime("%Y/%m/%d %H:%M"),
                "test_start_time": test_rows[0]["TIME"].strftime("%Y/%m/%d %H:%M"),
                "test_end_time": test_rows[-1]["TIME"].strftime("%Y/%m/%d %H:%M"),
                "last_day_same_slot_rmse": round(metrics["last_day_same_slot"], 6),
                "last_7day_same_slot_rmse": round(metrics["last_7day_same_slot"], 6),
                "weekday_slot_mean_rmse": round(metrics["weekday_slot_mean"], 6),
            }
        )

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
