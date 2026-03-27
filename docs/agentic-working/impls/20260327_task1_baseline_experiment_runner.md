# 2026-03-27 Task 1 baseline 实验运行脚本说明

## 目标

- 为当前 baseline 提供一个正式的实验运行入口。
- 严格按照项目约定，将实验产物写入 `experiments/<exp>/` 子目录。
- 强制通过 `pixi` 环境运行，避免系统 Python 与项目环境漂移。

## 本次实现范围

- 新增 `scripts/run_baseline_experiment.py`。
- 新增 `pixi` task：`run-baseline-experiment`。
- 实验输出统一落在以下结构：
  - `configs/experiment_config.json`
  - `metrics/backtest/`
  - `metrics/prediction_summary.json`
  - `results/<baseline>_submission.csv`
  - `summary.json`

## 设计说明

### 实验目录

- 调用方显式传入 `--experiment-dir`。
- 目录命名应由外层命令按项目规则生成，例如 `MMDD_HHMMSS_<commit_hash_6>_<Remark>`。

### 运行内容

- 先对指定 baseline 跑一轮 rolling-origin backtest，并将指标写入实验目录下的 `metrics/backtest/`。
- 再基于全量训练数据和 `data/submit_example.csv` 的时间窗生成一份预测结果。
- 最终输出提交格式 CSV，列名严格为 `TIME,V`。

### 时间与预测输入

- 提交时间窗采用 `submit_example.csv` 作为模式源。
- 预测阶段只读取其中的 `TIME` 列，并转成未来时点列表。
- 未来行的 `V` 仅作为占位值，不参与真实监督信息输入。

## 后续建议

- 后续可把实验说明进一步补充到 `reports/` 或实验目录内的 markdown 总结中。
- 若后面支持多模型实验，可扩展为一次实验运行多个 baseline 并汇总对比。
