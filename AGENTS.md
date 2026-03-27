# AGENTS

## Project Purpose

This repository supports the "数据中国-新能源汽车挑战赛" project, centered on the challenge "基于多源数据融合的电动汽车充电站协同优化挑战".

The competition defines three related tasks:

1. EV charging station load forecasting
2. V2G station operation strategy optimization
3. Vehicle-grid collaborative scheduling optimization

Unless a task explicitly says otherwise, agents should treat Task 1 as the default delivery priority during the current stage of the project, because the preliminary-round online submission is built around charging load prediction CSV outputs.

## Source Of Truth Priority

When requirements conflict or are incomplete, use the following priority order:

1. `docs/CommunicationBasis.md`
2. `docs/ProjectBasis.md`
3. `docs/数据中国-新能源汽车挑战赛.md`
4. Actual file formats and examples under `data/`
5. Existing project code and configs
6. Temporary notes or ad hoc assumptions

Do not invent contest rules, scoring details, submission formats, or data semantics when they can be grounded in the files above.

All user-facing interaction rules should be grounded in `docs/CommunicationBasis.md` when the task involves how the assistant should speak, restate, correct, or structure replies.

## Current Competition Focus

- Default active track: Task 1, charging load forecasting for the preliminary stage.
- Task 1 goal: forecast the next 24 hours of charging load at 15-minute granularity.
- Primary target field for Task 1: `V`.
- Primary online metric for the preliminary stage: `1 / (1 + RMSE)`.
- A valid submission should follow the two-column CSV pattern shown in `data/submit_example.csv`.
- Task 2 and Task 3 should be treated as research and extension tracks unless the user explicitly asks to work on them.

## Data Assets

Use the files under `data/` as the canonical local inputs.

- `data/A榜-充电站充电负荷训练数据.csv`: main Task 1 training data with time series load and derived statistics such as `V`, `AVGV`, `MAXV`, `MAXT`, `MINV`, `MINT`, `S`, and related fields.
- `data/submit_example.csv`: Task 1 submission example; use this as the first reference for output column names and time formatting.
- `data/附件1-V2G站向电网售电及从电网购电电价.csv`: Task 2 buy/sell electricity price schedule for V2G station optimization.
- `data/附件2-光伏典型出力.xlsx`: Task 2 photovoltaic generation reference input.
- `data/附件3 -EV用户充放电电价.csv`: Task 3 EV user charging/discharging price schedule.
- `data/附件4-线路基本参数.xlsx`: Task 3 network line parameter input.

Do not overwrite raw source files in `data/`. Any cleaned, transformed, joined, or feature-engineered outputs should be written as new derived artifacts in appropriate project locations.

## External Data Policy

The contest allows public external data, but does not allow non-public proprietary data.

Therefore:

- Public external data is allowed only when its source is documented and reproducible.
- Non-public, private, paid-only, or otherwise unverifiable data must not be introduced.
- Any pretrained model used in the project must be open-source and verifiable.
- When adding external data, document the source, access date, coverage window, and time-alignment method.

## Engineering Baseline

All engineering conventions from `docs/ProjectBasis.md` apply.

- Python version: `3.11`
- Package/environment management: `pixi` + `uv`
- Virtual environment path: `dcic-contest/.venv`
- Production code should include type annotations.
- Type checking target: `standard`
- Main workflows must be scriptable and must not depend on notebooks.

Agents should prefer building command-line, config-driven workflows over one-off exploratory notebooks.

Agents must follow `docs/ProjectBasis.md` for repository-wide engineering constraints, including runtime/tooling choices, directory conventions, documentation rules, worklog requirements, and implementation-note requirements.

## Communication Baseline

All communication conventions from `docs/CommunicationBasis.md` apply.

- If the user input contains Chinese, respond using the Chinese-mode interaction pattern defined in `docs/CommunicationBasis.md`.
- If the user input is pure English, first provide the minimally edited natural English version, then continue the substantive response in Chinese.
- If the user input mixes Chinese and English, treat it as Chinese-mode.
- Regardless of the user's input language, the assistant's substantive response should be in Chinese unless the user explicitly requests a language-editing task.
- Preserve technical literals such as code, commands, file paths, variable names, API names, and error messages accurately when restating or polishing.

## Directory Rules

Follow the repository directory conventions defined in `docs/ProjectBasis.md`.

- `artifacts/`: formal run artifacts
- `conf/`: TOML configs
- `data/`: source and derived datasets
- `docs/`: project documentation
- `docs/agentic-working/`: agent-generated working documents
- `experiments/`: per-experiment working directories
- `reports/`: release-oriented markdown reports
- `scripts/`: utility, CI, lint, and project scripts
- `src/`: source code
- `submissions/`: packaged deliverables by release
- `tests/`: unit and integration tests

For experiments, use the naming convention from `docs/ProjectBasis.md`:

- `MMDD_HHMMSS_<commit_hash_6>`
- `MMDD_HHMMSS_<commit_hash_6>_<Remark>`

## Task 1 Modeling Rules

When working on charging load forecasting, agents should follow these default rules unless the user explicitly requests another approach.

- Build a strong reproducible baseline before attempting complex models.
- Use time-aware validation only; never use random split validation for the main forecasting task.
- Prefer rolling-origin or other forward-chaining backtests with multiple folds.
- Evaluate with RMSE and keep validation logic aligned with the online target as closely as possible.
- Prevent time leakage in all feature engineering, aggregation, normalization, and post-processing.
- Validate submission files for nulls, negative values, malformed timestamps, duplicate timestamps, and wrong column names before export.

Recommended early baseline order:

1. last-day same-slot baseline
2. last-7-day same-slot baseline
3. weekday-slot historical mean baseline
4. GBDT baselines such as LightGBM, CatBoost, or XGBoost
5. deeper sequence models only after a stable offline validation pipeline exists

## Task 2 And Task 3 Working Rules

When the user explicitly asks to work on Task 2 or Task 3:

- Preserve a clear separation between forecasting, optimization, and reporting layers.
- Keep optimization assumptions explicit and reviewable.
- Ground price inputs in the provided attachment files before introducing any derived scenario logic.
- If power flow or scheduling constraints are added, document the mathematical assumptions and solver behavior.
- Write optimization outputs and reports in reproducible script form, not manual spreadsheets.

## Submission Rules

For preliminary-stage forecasting submissions:

- Use CSV output.
- Match the expected schema from `data/submit_example.csv`.
- Keep the time granularity at 15 minutes.
- Treat contest documentation as authoritative for any date-window changes between A leaderboard and B leaderboard stages.
- Add automated format checks before any export intended for ranking submission.

If the repository later supports multiple release packages, place deliverables under `submissions/<release>/` following the layout in `docs/ProjectBasis.md`.

## Agent Working Style

When contributing to this repository, agents should:

- read `docs/数据中国-新能源汽车挑战赛.md`, `docs/ProjectBasis.md`, and `docs/CommunicationBasis.md` before making non-trivial changes;
- keep the main workflow reproducible and command-line driven;
- prefer small, reviewable changes with explicit configs and output paths;
- avoid changing unrelated files;
- avoid destructive operations on raw data or existing experiment outputs unless explicitly requested;
- preserve compatibility with the project directory conventions;
- document any material assumption that affects scoring, validation, optimization behavior, or user-facing interaction behavior.

## Documentation And Worklog Requirements

After each completed task at prompt granularity:

- append one line to `docs/agentic-working/worklog/YYYYMMDD.md`;
- use the format `HH:MM:SS <change summary>`;
- keep the summary concise and specific.

Create a dedicated implementation note under `docs/agentic-working/impls/` when a task includes one or more of the following:

- adding a new module or feature;
- refactoring that spans three or more files;
- changing shared data structures or configuration schema;
- changing the main training, validation, inference, or export workflow;
- changing externally consumed APIs or interfaces.

## Practical Defaults

If the user does not specify a direction, prefer the following defaults:

- current main objective: Task 1 forecasting
- first metric to optimize offline: RMSE
- first deliverable: reproducible baseline plus legal submission export
- first model family to strengthen: GBDT
- first extension after baseline stability: external public weather data with documented provenance

## Non-Goals And Cautions

- Do not rely on notebooks as the only implementation of a formal workflow.
- Do not treat leaderboard movement as a substitute for stable offline validation.
- Do not mix unofficial assumptions into submission generation without documenting them.
- Do not use hidden future information when forecasting or constructing features.
- Do not introduce non-reproducible manual steps into training, validation, optimization, or export.
