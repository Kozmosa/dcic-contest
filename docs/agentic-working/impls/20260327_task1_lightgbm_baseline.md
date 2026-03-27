# 2026-03-27 Task 1 LightGBM baseline 接口实现说明

## 目标

- 在现有规则 baseline 与特征层之上，接入首个可扩展的 GBDT baseline 接口。
- 先实现 `lightgbm_recursive`，验证从训练样本构造、模型拟合到递归多步预测的数据流。
- 保持默认 backtest 仍只跑规则 baseline，避免在未装 `lightgbm` 的环境中影响现有主流程。

## 本次实现范围

- 新增 `src/dcic_contest/baseline/gbdt.py`。
- 新增 `LightGBMConfig` 与 `LightGBMRecursiveForecaster`。
- 在 `features.py` 中补充训练列名和递归推理特征构造函数。
- 将 `lightgbm_recursive` 接入 baseline registry，但不加入默认 baseline 列表。
- 新增 `tests/test_lightgbm_baseline.py`，用假模型覆盖训练矩阵构造和递归预测数据流。

## 设计说明

### 训练阶段

- `build_feature_rows()` 负责把原始时序数据转成监督学习样本。
- `LightGBMRecursiveForecaster._prepare_training_matrix()` 从特征行中抽取：
  - `X_train`：时间、lag、rolling 特征
  - `y_train`：目标列 `V`
- warm-up 区间因历史不足被自动剔除，避免不完整样本进入模型。

### 推理阶段

- 采用 recursive 多步预测。
- 每一步预测时，使用当前已有历史构造下一时点特征。
- 模型预测出的值会立即回写到 `history_rows`，再用于下一步 lag/rolling 特征构造。
- 这样可以与线上“未知未来真实值”的场景保持一致。

### 依赖策略

- `lightgbm` 在运行时延迟导入。
- 如果环境中未安装 `lightgbm`，仅在真正运行 `lightgbm_recursive` 时抛出清晰错误。
- 默认 baseline 列表仍为规则模型，因此现有 backtest 主流程不受影响。

## 当前局限

- 目前只实现 `recursive` 路线，尚未实现 `direct` 多模型版本。
- 参数仍使用首版保守默认值，尚未做时间序列场景调优。
- 尚未把该模型接入单独配置文件和正式实验目录输出。

## 后续建议

- 下一步可补 `LightGBM direct`，用每个 horizon 单独建模做对比。
- 可继续增加 `same weekday same slot`、更长窗口统计和节假日特征。
- 若确定使用 `pixi` 作为正式运行环境，应在环境依赖中补齐 `lightgbm` 并增加统一 task。
