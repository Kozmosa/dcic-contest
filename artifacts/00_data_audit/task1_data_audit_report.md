# Task 1 数据审计报告

## 审计范围

- 输入数据：`/Users/kozmosa/code/dcic-contest/data/A榜-充电站充电负荷训练数据.csv`
- 提交样例：`/Users/kozmosa/code/dcic-contest/data/submit_example.csv`
- 目标列：`V`
- 审计输出目录：`/Users/kozmosa/code/dcic-contest/artifacts/00_data_audit`

## 关键结论

- 训练数据共 29280 行，14 列，时间范围为 `2024/1/1 0:00` 至 `2024/10/31 23:45`。
- 原始文件为双表头 CSV，第 1 行中文表头，第 2 行英文表头；建议统一以英文表头作为正式字段名。
- 当前仅发现 1 个 `SENID`（1001-1012）与 1 个 `NAME`（电动汽车充电站），现阶段应按单对象长时序处理。
- 时间连续性检查通过：重复时间 0 条，异常间隔 0 条；每日记录数范围 96 到 96，满足 15 分钟粒度与每日 96 条要求。
- 提交样例窗口为 `2024/11/1 0:00` 至 `2024/12/31 23:45`，共 5856 行，列名模式为 `TIME,V`。

## 字段与读取约定

- 编码建议使用 `gb18030` 读取训练文件。
- `TIME/MAXT/MINT` 作为时间字段解析，`V/AVGV/MAXV/MINV/S/AVGS/MAXS/MINS/SPAN` 作为数值字段解析。
- `AVGV/MAXV/MAXT/MINV/MINT/AVGS/MAXS/MINS/SPAN` 在同一天内均表现为重复常量，更接近按日统计回填字段，而不是逐时点实时特征。

## 时间轴审计

- 预期间隔：15 分钟。
- 训练集起止：`2024/1/1 0:00` -> `2024/10/31 23:45`。
- 时间断点数：0。
- 重复主键数：0。
- 每日记录数最小值：96，最大值：96。

## 目标列 `V` 审计

- `V` 分布：最小值 1.210，中位数 5.400，最大值 9.850。
- 负值数量：0；零值数量：0。
- 相邻 15 分钟绝对变化的 99.9% 阈值约为 1.190，据此标记了 31 个“短时突变”候选点。

## 日级统计与一致性检查

- 日总负荷（按 `sum(V) * 0.25` 计算）的均值为 127.864 MWh，范围 112.272 到 163.125 MWh。
- 每日峰谷差均值为 7.174 MW。
- `AVGV` 与按日重算均值存在 0 天不一致；`AVGS` 与按日重算均值存在 0 天不一致。
- `MAXV/MINV/MAXT/MINT` 与按日重算结果整体一致，可用于交叉校验，但不建议直接作为预测时点特征。

## 特征可用性判断

- 安全可用：时间派生特征（`hour`、`weekday`、`15min_slot` 等）。
- 可作为标签历史构造：`V` 的 lag 与 rolling 统计。
- 待确认后再决定：`S`。
- 首版 baseline 禁用：`AVGV/MAXV/MAXT/MINV/MINT/AVGS/MAXS/MINS/SPAN`，原因是这些字段具有明显的按日汇总回填特征，存在未来信息泄漏风险。

## 对后续验证与 baseline 的建议

- rolling-origin backtest 可以按完整自然日切分，至少 3 folds，每 fold 预测未来 24 小时。
- Day 1 baseline 建议顺序：`last day same slot` -> `last 7 day same slot` -> `weekday-slot mean`。
- 第一版建模应仅依赖 `TIME` 派生特征和历史 `V`，先不要引入按日统计字段。
- 提交导出应严格复用 `submit_example.csv` 的时间格式与列名 `TIME,V`。

## 产物清单

- `tables/column_profile.csv`
- `tables/time_continuity.csv`
- `tables/time_gaps.csv`
- `tables/daily_load_stats.csv`
- `tables/slot_profile.csv`
- `tables/weekday_slot_profile.csv`
- `tables/anomaly_flags.csv`
- `tables/daily_consistency_checks.csv`
- `tables/feature_availability.csv`
- `figures/daily_energy.svg`
- `figures/daily_peak_gap.svg`
- `figures/slot_mean_load.svg`
- `summary.json`

## 审计结论

- 这份训练数据结构规整，可直接进入 Day 1 的 baseline 与 backtest 基础实现。
- 当前首要风险不是时间断点，而是错误使用按日汇总字段导致的特征泄漏，以及提交导出时偏离 `TIME,V` 模式。
- 后续如需更细粒度异常处理，可基于 `tables/anomaly_flags.csv` 对异常日和异常点做二次复核。
