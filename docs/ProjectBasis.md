# Project Basis

## Runtime And Tooling

- Python version: `3.11`
- Package and environment management: `pixi` + `uv`
- Virtual environment path: `src/dcic-contest/.venv`

## Code Quality

- Production code should include type annotations.
- Type checking strictness should target `standard`.
- Main workflows should be scriptable and should not rely on notebooks.

## Directory Conventions

- `artifacts/`: artifacts produced by formal runs.
- `conf/`: project configuration files in TOML format.
- `data/`: source and derived datasets required by the project.
- `docs/`: project documentation.
- `docs/agentic-working/`: markdown documents generated during agent-assisted work.
- `experiments/`: per-experiment working directories.
- `reports/`: markdown reports intended for release outputs.
- `scripts/`: CI, lint, and other project utility scripts.
- `src/`: project source code.
- `submissions/`: packaged deliverables for each release.
- `tests/`: unit and integration tests.

## Documentation Rules

- Shared project constraints should be maintained in `docs/ProjectBasis.md`.
- After each completed task at prompt granularity, append one line to that day's worklog at `docs/agentic-working/worklog/YYYYMMDD.md`.
- Each worklog line should use the format `HH:MM:SS <change summary>`.
- For large-scope changes, add a dedicated implementation note under `docs/agentic-working/impls/`.

## Large Change Criteria

Create an implementation note when a task includes one or more of the following:

- adding a new module or feature;
- refactoring that spans three or more files;
- changing shared data structures or configuration schema;
- changing the main training, validation, inference, or export workflow;
- changing externally consumed APIs or interfaces.

Small bug fixes, isolated single-file edits, documentation-only changes, test-only additions, and local parameter tuning do not require a dedicated implementation note.

## Submission Layout

Each release should be organized under `submissions/<release>/`, for example:

- reports: `submissions/0327v1/reports/`
- code: `submissions/0327v1/code/`
- artifacts: `submissions/0327v1/artifacts/`

## Experiment Layout

Each experiment root directory should use the naming rule:
Note: `<commit_hash_6>` means the 6 leftmost digits of current git commit when starting experiment.

- `MMDD_HHMMSS_<commit_hash_6>`
- `MMDD_HHMMSS_<commit_hash_6>_<Remark>`

Examples:

- `experiments/0327_144032_3fb635_LRSearch`
- `experiments/0327_144222_3fb635`

Each experiment directory may contain:

- root-level TOML config files;
- root-level experiment scripts;
- `logs/` for logs;
- `results/` for result files;
- `artifacts/` for experiment-produced models or artifacts;
- `metrics/` for recorded metrics and measurements.(usually json)
