# 2026-03-27 Task 1 baseline 包实现说明

## 目标

- 在 `src/dcic_contest/baseline/` 下建立可扩展的 baseline 子包。
- 将规则型 baseline 从 `src/dcic_contest/evaluation.py` 中解耦，避免评估逻辑与模型逻辑继续耦合。
- 为后续 LightGBM baseline、特征工程和命令行选择模型打下统一接口基础。

## 本次实现范围

- 新增 `src/dcic_contest/baseline/` 子包。
- 新增统一预测上下文 `ForecastContext` 与 `BaselineForecaster` 协议。
- 新增 3 个规则 baseline：
  - `last_day_same_slot`
  - `last_7day_same_slot`
  - `weekday_slot_mean`
- 新增 baseline registry，用于集中管理默认模型与名称校验。
- 重构 `src/dcic_contest/evaluation.py`，改为通过 registry 调度 baseline。
- 更新 `scripts/run_backtest.py`，支持通过 `--models` 选择要运行的 baseline。

## 设计说明

### 接口层

- `ForecastContext` 封装 `train_rows`、`future_rows` 和 `horizon_steps`，保证各 baseline 拿到一致输入。
- `BaselineForecaster` 仅要求提供 `name` 和 `predict()`，保持最小抽象，便于后续接入更复杂模型。

### baseline 分类

- `naive.py` 放置直接基于历史序列复制或聚合的朴素基线。
- `seasonal.py` 放置带有周内季节性的规则基线。
- `features.py` 仅保留安全的时间辅助函数，当前只提供 `quarter_slot` 与 `weekday_slot_key`。

### 与数据审计结论的对齐

- 当前 baseline 仅使用 `TIME` 与历史 `V`。
- 未接入 `AVGV/MAXV/MAXT/MINV/MINT/AVGS/MAXS/MINS/SPAN`，避免引入按日汇总字段导致的未来信息泄漏。
- `weekday_slot_mean` 仅基于 `(weekday, 15min_slot)` 聚合，符合首版安全特征约束。

### 回测层调整

- `evaluation.py` 保留 `rmse`、fold 切分、结果落盘等职责。
- 具体模型预测改由 `build_forecasters()` 返回的实例执行。
- fold 指标表改为按实际运行模型动态展开列，避免未来新增 baseline 时继续手写字段。

## 当前收益

- baseline 逻辑与评估逻辑分层更清晰。
- 后续新增 LightGBM direct / recursive baseline 时，可以复用 registry 和回测主流程。
- 命令行已支持只跑某一部分 baseline，便于快速排查或比较。

## 后续建议

- 在 `tests/` 下补充 baseline 单测，覆盖最小历史长度校验与 `weekday_slot_mean` fallback 行为。
- 下一步可在该子包旁新增基于特征表的模型接口，而不是继续塞入 `evaluation.py`。
- 若后续要支持提交推理，可复用同一 registry 机制统一管理训练期与预测期模型构造。
