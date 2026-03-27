# dcic_contest pixi workspace

该目录保存 `pixi` 工作区文件，用于统一项目环境与任务入口。

## 当前可用任务

- `pixi run data-audit`：运行 Task 1 数据审计，输出到仓库根目录 `artifacts/00_data_audit/`
- `pixi run backtest-baselines`：运行 Task 1 的最小验证体系与 3 个基线回测，输出到 `artifacts/01_backtest_baselines/`

## 说明

- 代码主仓库根目录位于当前目录上两级。
- `data-audit` task 通过设置 `PYTHONPATH=../..` 调用仓库根目录下的 `scripts/run_data_audit.py`。
