from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# pyright: reportMissingImports=false

from dcic_contest.baseline import build_forecasters
from dcic_contest.baseline.base import ForecastContext
from dcic_contest.data_audit import load_task1_training_data
from dcic_contest.evaluation import EvaluationConfig, run_backtest


def _read_submit_times(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [str(row["TIME"]).strip() for row in reader if row.get("TIME")]


def _read_submit_future_rows(path: Path) -> list[dict[str, Any]]:
    future_rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            time_text = str(row.get("TIME", "")).strip()
            if not time_text:
                continue
            future_rows.append(
                {
                    "TIME": datetime.strptime(time_text, "%Y/%m/%d %H:%M"),
                    "V": 0.0,
                }
            )
    return future_rows


def _ensure_dirs(experiment_dir: Path) -> dict[str, Path]:
    paths = {
        "root": experiment_dir,
        "configs": experiment_dir / "configs",
        "results": experiment_dir / "results",
        "metrics": experiment_dir / "metrics",
        "artifacts": experiment_dir / "artifacts",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _write_submission(path: Path, times: list[str], predictions: list[float]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["TIME", "V"])
        writer.writeheader()
        for time_text, prediction in zip(times, predictions):
            writer.writerow({"TIME": time_text, "V": round(prediction, 6)})


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_experiment(
    experiment_dir: Path,
    input_csv: Path,
    submit_example_csv: Path,
    baseline_name: str,
    encoding: str,
    horizon_steps: int,
    n_folds: int,
    fold_stride_steps: int,
) -> dict[str, Any]:
    dirs = _ensure_dirs(experiment_dir)

    config_payload = {
        "input_csv": str(input_csv),
        "submit_example_csv": str(submit_example_csv),
        "baseline_name": baseline_name,
        "encoding": encoding,
        "horizon_steps": horizon_steps,
        "n_folds": n_folds,
        "fold_stride_steps": fold_stride_steps,
        "experiment_dir": str(experiment_dir),
    }
    _write_json(dirs["configs"] / "experiment_config.json", config_payload)

    backtest_summary = run_backtest(
        EvaluationConfig(
            input_csv=input_csv,
            output_dir=dirs["metrics"] / "backtest",
            encoding=encoding,
            horizon_steps=horizon_steps,
            n_folds=n_folds,
            fold_stride_steps=fold_stride_steps,
            baseline_names=[baseline_name],
            submit_example_csv=submit_example_csv,
        )
    )

    bundle = load_task1_training_data(input_csv=input_csv, encoding=encoding)
    forecaster = build_forecasters([baseline_name])[0]
    submit_times = _read_submit_times(submit_example_csv)
    future_rows = _read_submit_future_rows(submit_example_csv)

    context = ForecastContext(
        train_rows=bundle.rows,
        future_rows=future_rows,
        horizon_steps=len(future_rows),
    )
    predictions = forecaster.predict(context)
    submission_path = dirs["results"] / f"{baseline_name}_submission.csv"
    _write_submission(submission_path, submit_times, predictions)

    prediction_summary = {
        "baseline_name": baseline_name,
        "prediction_count": len(predictions),
        "prediction_min": round(min(predictions), 6),
        "prediction_max": round(max(predictions), 6),
        "prediction_mean": round(sum(predictions) / len(predictions), 6),
        "submission_path": str(submission_path),
    }
    _write_json(dirs["metrics"] / "prediction_summary.json", prediction_summary)

    experiment_summary = {
        "config": config_payload,
        "backtest": backtest_summary,
        "prediction": prediction_summary,
    }
    _write_json(dirs["root"] / "summary.json", experiment_summary)
    return experiment_summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a baseline experiment under experiments/."
    )
    parser.add_argument("--experiment-dir", type=Path, required=True)
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=ROOT / "data" / "A榜-充电站充电负荷训练数据.csv",
    )
    parser.add_argument(
        "--submit-example-csv",
        type=Path,
        default=ROOT / "data" / "submit_example.csv",
    )
    parser.add_argument("--baseline-name", default="lightgbm_recursive")
    parser.add_argument("--encoding", default="gb18030")
    parser.add_argument("--horizon-steps", type=int, default=96)
    parser.add_argument("--n-folds", type=int, default=3)
    parser.add_argument(
        "--fold-stride-steps",
        type=int,
        default=96,
        help="Spacing between backtest windows in 15-minute steps. Use 96 for daily stride, 672 for weekly stride.",
    )
    args = parser.parse_args()

    summary = run_experiment(
        experiment_dir=args.experiment_dir,
        input_csv=args.input_csv,
        submit_example_csv=args.submit_example_csv,
        baseline_name=args.baseline_name,
        encoding=args.encoding,
        horizon_steps=args.horizon_steps,
        n_folds=args.n_folds,
        fold_stride_steps=args.fold_stride_steps,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
