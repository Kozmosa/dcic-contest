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

from dcic_contest.data_audit import AuditConfig, run_data_audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Task 1 data audit.")
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
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts" / "00_data_audit",
    )
    parser.add_argument(
        "--encoding",
        default="gb18030",
    )
    args = parser.parse_args()

    summary = run_data_audit(
        AuditConfig(
            input_csv=args.input_csv,
            submit_example_csv=args.submit_example_csv,
            output_dir=args.output_dir,
            encoding=args.encoding,
        )
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
