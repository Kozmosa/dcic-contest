from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# pyright: reportMissingImports=false

from dcic_contest.evaluation import EvaluationConfig, run_backtest


def _parse_model_names(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    names = [item.strip() for item in raw.split(",") if item.strip()]
    return names or None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Task 1 rolling backtest baselines."
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=ROOT / "data" / "A榜-充电站充电负荷训练数据.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts" / "01_backtest_baselines",
    )
    parser.add_argument("--encoding", default="gb18030")
    parser.add_argument("--horizon-steps", type=int, default=96)
    parser.add_argument("--n-folds", type=int, default=3)
    parser.add_argument(
        "--models",
        default=None,
        help="Comma-separated baseline names to run. Defaults to all built-in baselines.",
    )
    args = parser.parse_args()

    summary = run_backtest(
        EvaluationConfig(
            input_csv=args.input_csv,
            output_dir=args.output_dir,
            encoding=args.encoding,
            horizon_steps=args.horizon_steps,
            n_folds=args.n_folds,
            baseline_names=_parse_model_names(args.models),
        )
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
