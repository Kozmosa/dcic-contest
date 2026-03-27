# Task 1 数据审计概览

本轮已完成 Task 1 训练数据的首版脚本化审计，正式产物统一输出到 `artifacts/00_data_audit/`。

## 结果概览

- 训练数据 `data/A榜-充电站充电负荷训练数据.csv` 共 29280 行、14 列。
- 时间范围为 `2024/1/1 0:00` 至 `2024/10/31 23:45`，严格 15 分钟粒度。
- 数据当前表现为单对象长时序，仅包含 1 个 `SENID=1001-1012`。
- 时间连续性检查通过：无重复时间、无断点、每天完整 96 条。
- `V` 无缺失、无负值、无零值；相邻 15 分钟变化的 99.9% 阈值约为 1.19，已标记 31 个突变候选点。
- 日级汇总字段与按日重算结果一致，但这些字段仍应视为高泄漏风险字段，首版 baseline 禁用。

## 产物位置

- 主报告：`artifacts/00_data_audit/task1_data_audit_report.md`
- 摘要：`artifacts/00_data_audit/summary.json`
- 结构化表：`artifacts/00_data_audit/tables/`
- 图表：`artifacts/00_data_audit/figures/`
- 实现说明：`docs/agentic-working/impls/20260327_task1_data_audit.md`

## 运行方式

- 直接脚本入口：`python3 scripts/run_data_audit.py`
- 统一 `pixi` 入口：在 `src/dcic_contest/` 目录下执行 `pixi run data-audit`

## 直接结论

- 数据已经具备 Day 1 baseline 与 rolling-origin backtest 的基础条件。
- 首轮建模建议仅使用 `TIME` 派生特征和历史 `V`，不要直接使用 `AVGV/MAXV/MAXT/MINV/MINT/AVGS/MAXS/MINS/SPAN`。
- 提交链路应严格按 `data/submit_example.csv` 的 `TIME,V` 模式实现。
