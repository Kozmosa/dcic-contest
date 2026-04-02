from __future__ import annotations

import csv
import json
import math
import statistics
from dataclasses import dataclass
from datetime import datetime
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
    fold_stride_steps: int = 96
    baseline_names: list[str] | None = None
    submit_example_csv: Path | None = None


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


def _read_submit_times(path: Path) -> list[datetime]:
    submit_times: list[datetime] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            time_text = str(row.get("TIME", "")).strip()
            if not time_text:
                continue
            submit_times.append(datetime.strptime(time_text, "%Y/%m/%d %H:%M"))
    if not submit_times:
        raise ValueError(f"No TIME rows found in submit example: {path}")
    return submit_times


def _build_folds(
    rows: list[dict[str, Any]],
    horizon_steps: int,
    n_folds: int,
    fold_stride_steps: int,
) -> list[tuple[int, int]]:
    rows_count = len(rows)
    min_train_steps = horizon_steps * 14
    if fold_stride_steps <= 0:
        raise ValueError("fold_stride_steps must be positive")
    folds: list[tuple[int, int]] = []
    for idx in range(n_folds, 0, -1):
        test_end = rows_count - fold_stride_steps * (idx - 1)
        test_start = test_end - horizon_steps
        train_end = test_start
        if train_end < min_train_steps:
            raise ValueError("Not enough data to build requested folds")
        folds.append((train_end, test_end))
    return folds


def _build_full_span_split(
    rows: list[dict[str, Any]],
    submit_times: list[datetime],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    submit_start = submit_times[0]
    submit_end = submit_times[-1]
    train_rows = [row for row in rows if row["TIME"] < submit_start]
    test_rows = [row for row in rows if submit_start <= row["TIME"] <= submit_end]
    if train_rows and len(test_rows) == len(submit_times):
        test_times = [row["TIME"] for row in test_rows]
        if test_times == submit_times:
            return train_rows, test_rows, {
                "mode": "calendar_aligned",
                "submit_window_start": submit_start.strftime("%Y/%m/%d %H:%M"),
                "submit_window_end": submit_end.strftime("%Y/%m/%d %H:%M"),
            }

    point_count = len(submit_times)
    if len(rows) <= point_count:
        raise ValueError("Not enough training rows to build full-span proxy split")
    proxy_test_rows = rows[-point_count:]
    proxy_train_rows = rows[:-point_count]
    return proxy_train_rows, proxy_test_rows, {
        "mode": "tail_proxy",
        "submit_window_start": submit_start.strftime("%Y/%m/%d %H:%M"),
        "submit_window_end": submit_end.strftime("%Y/%m/%d %H:%M"),
        "proxy_window_start": proxy_test_rows[0]["TIME"].strftime("%Y/%m/%d %H:%M"),
        "proxy_window_end": proxy_test_rows[-1]["TIME"].strftime("%Y/%m/%d %H:%M"),
        "reason": "submit_example dates are outside the available training period, so the last N training points are used as a full-span proxy",
    }


def run_backtest(config: EvaluationConfig) -> dict[str, Any]:
    dirs = _ensure_dirs(config.output_dir)
    bundle: Task1DataBundle = load_task1_training_data(
        config.input_csv, config.encoding
    )
    rows = bundle.rows
    folds = _build_folds(
        rows,
        config.horizon_steps,
        config.n_folds,
        config.fold_stride_steps,
    )
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

    full_span_summary: dict[str, Any] | None = None
    if config.submit_example_csv is not None:
        submit_times = _read_submit_times(config.submit_example_csv)
        train_rows, test_rows, split_info = _build_full_span_split(rows, submit_times)
        full_span_rows: list[dict[str, Any]] = []
        for model in forecasters:
            predictions = model.predict(
                ForecastContext(
                    train_rows=train_rows,
                    future_rows=test_rows,
                    horizon_steps=len(test_rows),
                )
            )
            y_true = [float(row["V"]) for row in test_rows]
            metric = rmse(y_true, predictions)
            full_span_rows.append(
                {
                    "model": model.name,
                    "point_count": len(test_rows),
                    "rmse": round(metric, 6),
                    "score": round(1.0 / (1.0 + metric), 6),
                    "submit_window_start": test_rows[0]["TIME"].strftime("%Y/%m/%d %H:%M"),
                    "submit_window_end": test_rows[-1]["TIME"].strftime("%Y/%m/%d %H:%M"),
                }
            )
        _write_csv(
            dirs["tables"] / "full_span_metrics.csv",
            list(full_span_rows[0].keys()),
            full_span_rows,
        )
        full_span_summary = {
            "submit_example_csv": str(config.submit_example_csv),
            "split_info": split_info,
            "point_count": len(test_rows),
            "window_start": test_rows[0]["TIME"].strftime("%Y/%m/%d %H:%M"),
            "window_end": test_rows[-1]["TIME"].strftime("%Y/%m/%d %H:%M"),
            "models": {
                row["model"]: {
                    "rmse": row["rmse"],
                    "score": row["score"],
                }
                for row in full_span_rows
            },
            "best_model_by_full_span_rmse": min(
                full_span_rows, key=lambda item: item["rmse"]
            )["model"],
        }

    summary = {
        "source_file": str(config.input_csv),
        "n_folds": config.n_folds,
        "horizon_steps": config.horizon_steps,
        "horizon_hours": config.horizon_steps / 4,
        "fold_stride_steps": config.fold_stride_steps,
        "fold_stride_hours": config.fold_stride_steps / 4,
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
        "window_metric_definition": {
            "window_rmse": "sqrt(mean((y_true - y_pred)^2)) over one 24h forecast window",
            "score": "1 / (1 + RMSE)",
        },
    }
    if full_span_summary is not None:
        summary["full_span_evaluation"] = full_span_summary
    (dirs["root"] / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary
