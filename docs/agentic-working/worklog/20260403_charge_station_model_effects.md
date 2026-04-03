# 2026-04-03 充电站负荷预测模型效果整理

## 统一评估口径

- `24h-window RMSE`
- `full-span RMSE`
- 当前 full-span 采用 `tail_proxy`，即使用训练集最后 `5856` 点代理提交区间。

## 当前主要结果

| 模型 | 路线 | 24h-window RMSE | full-span RMSE |
| --- | --- | ---: | ---: |
| `lightgbm_recursive` | 机器学习 | `0.160621` | `0.587075` |
| `timesfm_zero_shot_ctx4096` | foundation model | `0.227463` | `1.321150` |
| `weekday_slot_mean_recent_adjust_ultra_tight` | 统计 | `0.254742` | `0.339055` |
| `weekday_slot_mean` | 统计 | `0.276417` | `0.313367` |

## 当前判断

- 如果只看短窗回测，`lightgbm_recursive` 明显最佳。
- 如果更看重接近真实提交区间的长链稳定性，统计模型明显更强。
- `TimesFM` 当前不适合作为正式提交主候选。

## 后续方向

- 这个时序任务下一阶段不建议继续押注 zero-shot foundation model。
- 更值得投入的方向是：
  - `direct multi-horizon LightGBM`
  - 按 horizon 分桶或多头训练的 GBDT
  - 带更强时序归纳偏置的 encoder-decoder
- 实际筛选口径上，应把 `full-span RMSE` 作为主目标，`24h-window RMSE` 只做辅助参考。
