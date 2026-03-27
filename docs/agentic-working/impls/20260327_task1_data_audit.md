# 2026-03-27 Task 1 数据审计实现说明

## 目标

- 为 Task 1 训练数据建立可复现、脚本化的数据审计流程。
- 将审计产物统一输出到 `artifacts/00_data_audit/`。
- 为 Day 1 后续的 baseline、backtest 与提交链路提供结构化输入。

## 本次实现范围

- 新增 Python 包入口：`src/dcic_contest/__init__.py`
- 新增审计核心模块：`src/dcic_contest/data_audit.py`
- 新增运行脚本：`scripts/run_data_audit.py`
- 新增默认配置：`conf/data_audit/task1_default.toml`
- 将数据审计流程接入 `src/dcic_contest/pixi.toml` 的 `data-audit` task
- 新增审计说明文档与产物输出

## 审计设计

### 读取规则

- 训练文件采用 `gb18030` 编码读取。
- 训练文件按双表头处理：
  - 第 1 行中文表头，仅作为字段语义参考
  - 第 2 行英文表头，作为正式字段名
- 提交样例采用 UTF-8 读取，并以 `TIME,V` 作为提交格式基准

### 审计覆盖项

- 字段概览：类型、缺失、唯一值、取值范围、样例值
- 时间完整性：
  - 时间范围
  - 重复时间与重复主键
  - 15 分钟连续性
  - 每日 96 条完整性
- 目标列 `V`：
  - 负值、零值
  - 分布统计
  - 相邻 15 分钟跳变候选点
- 日级统计：
  - 日总负荷
  - 峰值/谷值与峰谷差
- 一致性检查：
  - `AVGV/MAXV/MINV/AVGS/MAXS/MINS/SPAN`
  - `MAXT/MINT`
- 特征可用性判断：标出高泄漏风险字段

### 产物组织

- `artifacts/00_data_audit/summary.json`：核心摘要
- `artifacts/00_data_audit/task1_data_audit_report.md`：主报告
- `artifacts/00_data_audit/tables/*.csv`：结构化统计表
- `artifacts/00_data_audit/figures/*.svg`：核心图表

### 运行入口

- 直接运行：`python3 scripts/run_data_audit.py`
- 统一环境入口：在 `src/dcic_contest/` 目录下执行 `pixi run data-audit`

## 当前实现结论摘要

- 训练数据时间连续，无重复时间和断点。
- 每天完整覆盖 96 个 15 分钟点。
- 当前数据可直接支持 `last day same slot`、`last 7 day same slot` 和 `weekday-slot mean` baseline。
- 首版 baseline 应禁用 `AVGV/MAXV/MAXT/MINV/MINT/AVGS/MAXS/MINS/SPAN`，避免未来信息泄漏。
- 提交导出应严格遵循 `submit_example.csv` 的 `TIME,V` 模式。

## 后续建议

- 将该审计脚本纳入正式 CLI 主流程的前置步骤。
- 在 baseline 与 backtest 实现中直接复用 `artifacts/00_data_audit/tables/feature_availability.csv` 和 `summary.json`。
- 后续可扩展节假日分层统计、异常日复核与 weather 接入前的对齐审计。

## 后续集成进展

- 已新增 `scripts/run_backtest.py` 与 `src/dcic_contest/evaluation.py`，补齐 Day 1 所需的最小 `RMSE` 与 rolling-origin backtest 基线验证能力。
- 已新增 `pixi run backtest-baselines` 统一入口，便于在固定环境中复现 3-fold baseline 回测结果。
