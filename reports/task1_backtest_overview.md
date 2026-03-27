# Task 1 基线回测概览

本轮补齐了 Task 1 Day 1 所需的最小验证体系：`RMSE` 评估、3-fold rolling-origin backtest，以及 3 个时间序列 baseline。

## 已实现能力

- `src/dcic_contest/evaluation.py`
  - `rmse`
  - `last_day_same_slot_forecast`
  - `last_7day_same_slot_forecast`
  - `weekday_slot_mean_forecast`
  - `run_backtest`
- `scripts/run_backtest.py`
- `artifacts/01_backtest_baselines/`

## 当前回测设置

- 预测步长：96 个点，即未来 24 小时
- fold 数量：3
- 切分方式：rolling-origin，按完整未来一天做验证
- 输入数据：`data/A榜-充电站充电负荷训练数据.csv`

## 基线模型

- `last_day_same_slot`
- `last_7day_same_slot`
- `weekday_slot_mean`

## 统一运行方式

- 直接脚本入口：`python3 scripts/run_backtest.py`
- `pixi` 入口：在 `src/dcic_contest/` 目录下执行 `pixi run backtest-baselines`

## 产物位置

- `artifacts/01_backtest_baselines/summary.json`
- `artifacts/01_backtest_baselines/tables/fold_metrics.csv`
- `artifacts/01_backtest_baselines/tables/overall_metrics.csv`
