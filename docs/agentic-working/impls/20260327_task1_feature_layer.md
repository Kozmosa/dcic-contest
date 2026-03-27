# 2026-03-27 Task 1 基础特征层实现说明

## 目标

- 为后续 `LightGBM baseline` 准备一层可复用的监督学习特征生成逻辑。
- 首版只接入数据审计确认安全的时间派生特征、`V` 的 lag 特征和 rolling 特征。
- 保证所有统计仅使用当前预测时点之前的历史，避免时间泄漏。

## 本次实现范围

- 扩展 `src/dcic_contest/baseline/features.py`，新增 `FeatureSpec`。
- 新增 `build_time_features()`，统一生成基础时间特征。
- 新增 `build_feature_rows()`，将原始时序样本转换为可用于监督学习的特征行。
- 新增 `tests/test_feature_engineering.py`，覆盖时间特征、lag、rolling 与异常配置行为。

## 设计说明

### 时间特征

- 当前输出以下安全时间特征：
  - `hour`
  - `minute`
  - `quarter_slot`
  - `weekday`
  - `month`
  - `day`
  - `dayofyear`
  - `weekofyear`
  - `is_weekend`

这些特征均仅依赖 `TIME`，与数据审计结论一致，不会引入未来信息。

### lag 特征

- `build_feature_rows()` 支持任意 `lag_steps` 配置。
- 每个 lag 特征均严格使用 `index - lag_step` 位置的历史 `V`。
- 默认配置已覆盖近点、小时级和天级窗口，为后续 GBDT baseline 提供最小可用输入。

### rolling 特征

- rolling 统计只使用当前样本之前的窗口历史 `values[index - window:index]`。
- 当前默认支持 `mean`、`min`、`max`。
- 这层设计故意保持简单，先优先保证时序安全与可复用性，后续可再加 `std`、同 weekday 同 slot 统计等。

### 缺失策略

- 当某一行 lag 或 rolling 历史不足时，对应特征写为 `None`。
- 若 `drop_incomplete_rows=True`，则仅保留所有特征均齐全的样本。
- 这一策略便于后续训练前直接裁掉 warm-up 区间，也便于调试时保留未完成行检查特征情况。

## 与数据审计结论的对齐

- 仅使用 `TIME` 派生特征与历史 `V`。
- 未使用 `AVGV/MAXV/MAXT/MINV/MINT/AVGS/MAXS/MINS/SPAN` 等高泄漏风险字段。
- rolling 窗口全部以前视方式构造，不读取当前点之后的信息。

## 后续建议

- 下一步可在此基础上新增面向 GBDT 的训练样本切分与推理特征构造逻辑。
- 若后续引入节假日、天气等外部特征，可继续扩展到同一层统一拼接。
- `S` 字段在意义确认前不接入该特征层。
