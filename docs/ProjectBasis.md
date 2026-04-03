# 项目基础约束

## 运行时与工具链

- Python 版本：`3.11`
- 包与环境管理：`pixi` + `uv`
- 虚拟环境路径：`src/dcic-contest/.venv`

## 代码质量

- 生产代码应包含类型注解。
- 类型检查严格度目标应为 `standard`。
- 主流程应支持脚本化执行，不应依赖 notebook。
- 编写代码时，尽量遵循代码仓库原本规划的结构，禁止随意修改仓库目录结构。
- 集成进入仓库时，执行最小侵入式修改并作原子提交，便于发生问题时回退。


## 目录约定

- `artifacts/`：正式运行产生的工件。
- `conf/`：项目配置文件，采用 TOML 格式。
- `data/`：项目所需的原始数据与派生数据。
- `docs/`：项目文档。
- `docs/agentic-working/`：agent 协作过程中生成的 markdown 文档。
- `experiments/`：按实验划分的工作目录。
- `reports/`：面向发布输出的 markdown 报告。
- `scripts/`：CI、lint 及其他项目工具脚本。
- `src/`：项目源代码。
- `submissions/`：各个 release 的交付物目录。
- `tests/`：单元测试与集成测试。
- `autoresearches/`: 基于 Karparthy autoresearch 框架的自动实验目录, 包含的每个子目录都是自洽的 autoresearch project.

## 文档规则

- 共享项目约束应维护在 `docs/ProjectBasis.md` 中。
- 每次完成一个 prompt 粒度的任务后，都要在当天的 worklog `docs/agentic-working/worklog/YYYYMMDD.md` 中追加一行记录。
- 每条 worklog 应采用 `HH:MM:SS <change summary>` 格式。
- 对于范围较大的改动，应在 `docs/agentic-working/impls/` 下补充专门的实现说明文档。

## 大改动判定标准

当任务包含以下任一情况时，应新增 implementation note：

- 新增模块或功能；
- 跨三个及以上文件的重构；
- 修改共享数据结构或配置 schema；
- 修改主训练、验证、推理或导出流程；
- 修改对外暴露的 API 或接口。

以下情况通常不需要单独的 implementation note：小型 bug 修复、单文件孤立修改、纯文档更新、仅新增测试、局部参数调优。

## 提交物目录布局

每个 release 应组织在 `submissions/<release>/` 下，例如：

- 报告：`submissions/0327v1/reports/`
- 代码：`submissions/0327v1/code/`
- 工件：`submissions/0327v1/artifacts/`

## 实验目录布局

每个实验根目录应遵循以下命名规则：
说明：`<commit_hash_6>` 表示启动实验时当前 git commit 的前 6 位。

- `MMDD_HHMMSS_<commit_hash_6>`
- `MMDD_HHMMSS_<commit_hash_6>_<Remark>`

示例：

- `experiments/0327_144032_3fb635_LRSearch`
- `experiments/0327_144222_3fb635`

每个实验目录中可以包含：

- 根目录级 TOML 配置文件；
- 根目录级实验脚本；
- `logs/`：日志文件；
- `results/`：结果文件；
- `artifacts/`：实验产出的模型或其他工件；
- `metrics/`：记录指标与测量结果，通常为 json。

## Git 提交信息约定

- commit 首行使用 Conventional Commits，使用英文简要描述主要变更。
- 建议格式：`feat: ...` / `fix: ...` / `refactor: ...` / `docs: ...` / `chore: ...`。
- commit message 正文使用中文，说明本次修改细节、影响范围与必要的背景。
- 正文必须使用 Markdown 无序列表（`- `）分点描述，优先说明“为什么改”和“改了什么”。
- 整个 commit message 应按 Markdown 书写，并尽量减少格式使用；除纯文本与无序列表外，尽量少用或不用加粗、斜体等格式。
- 需要换行时，使用多个 `-m` 参数或 heredoc 方式提交；不要在字符串中写字面量 `\n` 作为换行。

## 变更维护原则

- 修改工程约定时，优先更新本文件。
- 修改 `AGENTS.md` 或本文件时，应检查两者是否发生漂移，并保持环境、文档和提交约定一致。
- 新增长期有效规范时，在 `docs/LLM-Working/` 下新增对应主题文档，并在本文件中补充索引。
- 每次会话结束建议同步当天 `YYYYMMDD.md`，保证进度连续可追踪。

## 计算资源与执行约束

- 参考 `ComputeMachine.md`