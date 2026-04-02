# 2026-04-02 ML-only Progress

## Context

- 用户要求后续方案只能使用机器学习方法，统计学方案全部放弃。
- 当前线上高分来自 `weekday_slot_mean`，但该路线已按用户要求停用。
- 后续验证主口径：
  - `24h-window RMSE`
  - `full-span RMSE`
- `full-span RMSE` 使用 `submit_example.csv` 的长度做整段代理验证。
  - 由于训练数据只到 `2024/10/31 23:45`，提交样例从 `2024/11/01 00:00` 开始，
    当前离线 full-span 使用训练集最后 `5856` 点作为 `tail_proxy`。

## Today completed

- 已接入双口径验证体系，回测输出同时包含 `24h-window RMSE` 和 `full-span RMSE`。
- 已实现纯 ML 的 `lightgbm_recursive_clipped_p95` 与 `lightgbm_recursive_clipped_hard`。
- 已跑过 CNN / GRU challenger，但当前结果明显落后于 LightGBM。

## Key offline results already known

- `weekday_slot_mean`
  - `full-span RMSE = 0.313367`
- `lightgbm_recursive`
  - `24h-window RMSE = 0.160621`
  - `full-span RMSE = 0.587075`
- `timesfm_zero_shot_ctx4096`
  - `full-span RMSE = 1.321150`

## 2026-04-02 Evening update

- `lightgbm_recursive_clipped_p95`
  - `24h-window RMSE = 0.158931`
  - `full-span RMSE = 0.587181`
- `lightgbm_recursive_clipped_hard`
  - `24h-window RMSE = 0.158916`
  - `full-span RMSE = 0.587049`

## Current judgement

- clipped LightGBM 对原始 LightGBM 只有极小幅度改善，不足以作为下一阶段主增益方向。
- 后续更值得尝试：
  - `direct multi-horizon LightGBM`
  - 按 horizon 分桶训练的多头 GBDT
  - 带更强时序归纳偏置的 encoder-decoder，而不是当前轻量 CNN/GRU
