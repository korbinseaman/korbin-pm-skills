# PM User Research Skills

面向产品经理的用户研究技能包：把问卷设计、合成画像、模拟作答和报告综合拆成四个原子技能，并提供可组合工作流。

> 合成用户和模拟回答适合检查问卷、数据管线和生成待验证假设；不能替代真实用户研究，也不能用于估计市场比例、购买率或显著性。

## 包含内容

| 技能 | 职责 | 核心输出 |
|---|---|---|
| `ur-design-survey` | 产品决策分析、定量问卷设计、质量审查 | `questionnaire.md`、`design-doc.md`、`quality-report.md` |
| `ur-generate-personas` | 生成基础 + 课题扩展画像，分层和配额审计 | `personas.json`、`persons_summary.txt`、单人画像、`persona_audit.json` |
| `ur-user-simulator` | 合成问卷作答、Excel 汇总、逻辑/模板化检查 | 个人答卷、`survey_responses_*.xlsx`、质量报告 |
| `ur-synthesize-report` | 定量问卷、开放回答、证据综合和离线图表报告 | `analysis_summary.json`、`report.html`、`report_quality.md` |

工作流：

- `workflows/survey-design.md`：完成调查问卷设计，只调用 `ur-design-survey`。
- `workflows/synthetic-survey.md`：组合四个原子 Skill，完成完整合成问卷调研。

## 目录

```text
pm-user-research-skills/
├── skills/
│   ├── ur-design-survey/
│   ├── ur-generate-personas/
│   ├── ur-user-simulator/
│   └── ur-synthesize-report/
├── workflows/
├── config/llm.example.yaml
├── output_example/20260815图库AI修图用户需求调研/
└── tests/
```

每个技能按实际需要包含 `SKILL.md`、`agents/openai.yaml`、`references/`、`templates/` 和 `scripts/`。

## 安装与平台兼容

技能遵循 Agent Skills 的 `SKILL.md` 目录形式，正文不依赖平台专用工具。

### Codex

把四个技能目录复制或链接到 Codex 可发现的 skills 目录。可显式调用：

```text
$ur-design-survey 为“图库 AI 修图”设计 12 题问卷
```

`agents/openai.yaml` 只提供 Codex UI 元数据，不影响其他平台。

### Claude Code / OpenCode

把技能目录放入平台支持的 skills 目录，或在任务中显式要求读取对应 `SKILL.md`。工作流文件使用 `$skill-name` 表示调用；若平台不支持该语法，就依次加载相应技能目录。

所有 Python 脚本只依赖 Python 3.10+ 标准库。

## 快速开始

### 1. 只设计研究方案

按 `workflows/survey-design.md` 调用 `ur-design-survey`。技能把产物写到当前工作目录：

```text
output/<YYYYMMDD><课题>/<课题>_Questionnaire/
```

### 2. 配置真实 LLM

复制 `config/llm.example.yaml` 到不会提交的私有位置：

1. 把计划使用的提供商的示例模型 ID 换成账号实际可用的模型 ID。
2. 在预置的对应环境变量中设置密钥，例如 `DASHSCOPE_API_KEY`、`DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY`。
3. 不要把密钥直接写进 JSON。

DeepSeek、智谱、Kimi、Qwen、MiniMax（中国区）和 OpenAI 的提供商 ID、接口类型、`base_url`、Key 环境变量名与启用状态均已内置。没有填写模型 ID 或没有设置 Key 的提供商会自动跳过。

提供商类型：

- `openai_compatible`：调用 `<base_url>/chat/completions`。
- `openai_responses`：调用 `<base_url>/responses`。
- `mock`：只用于自动测试，不得用于正式 pilot 或调研。

模型名称会变化，使用前应以供应商当前文档和账号权限为准；示例配置刻意不假定某个名称一定存在。

### 3. 运行模拟

调用 `$ur-user-simulator`，提供已确认的 `questionnaire.md`、`persons_summary.txt`、`persons/` 目录和可选 LLM 配置。Skill 并行完成全部用户任务，最终只输出个人答卷目录、Excel 汇总和质量报告。

### 4. 生成报告

选定一个明确的 `<run_id>`，先生成描述性分析草稿：

```bash
python "skills/ur-synthesize-report/scripts/generate_report.py" --questionnaire "output/<项目>/<课题>_Questionnaire/questionnaire.md" --design-doc "output/<项目>/<课题>_Questionnaire/design-doc.md" --responses "output/<项目>/survey_response_data/survey_responses_<run_id>.xlsx" --output-dir "output/<项目>/report_<run_id>" --prepare-only
```

脚本会自动筛除问卷外选项、排序重复/超限和量表越界等结构性无效回答。若人工确认某个完成回答与调研诉求不符或逻辑不自洽，在两次命令中都追加 `--exclude-response "<用户ID>:<具体理由>"`，使清理记录可追溯。由 `ur-synthesize-report` 完成交叉/量表检验、证据化主题和建议后渲染：

```bash
python "skills/ur-synthesize-report/scripts/generate_report.py" --questionnaire "output/<项目>/<课题>_Questionnaire/questionnaire.md" --design-doc "output/<项目>/<课题>_Questionnaire/design-doc.md" --responses "output/<项目>/survey_response_data/survey_responses_<run_id>.xlsx" --analysis "output/<项目>/report_<run_id>/analysis_summary.json" --output-dir "output/<项目>/report_<run_id>"
```

## 数据契约

技能之间只通过文件传递数据：

```text
shared_context.md ──→ personas.json + persons_summary.txt + persons/ + persona_audit.json
questionnaire.md + persons_summary.txt + persons/ ──→ answers_<run_id>/ + survey_responses_<run_id>.xlsx + quality_report_<run_id>.md
questionnaire.md + design-doc.md + survey_responses_<run_id>.xlsx [+ persons_summary.txt] ──→ analysis_summary.json + report.html + report_quality.md
```

`questionnaire.md` 是报告所需问卷结构的权威来源，`design-doc.md` 提供产品决策和研究目标。报告先对回答 Excel 执行可追溯清理，再计算逐题频数/百分比、量表均值/标准差以及满足条件的交叉或量表检验；仅在需要披露样本构成时可选读取 `persons_summary.txt`，且不将其视为回答证据。

## 输出位置

运行技能时始终以调用者当前工作目录为根创建 `output/`：

```text
output/<YYYYMMDD><课题>/
├── <课题>_Questionnaire/
├── personas_data/
├── survey_response_data/
│   ├── answers_<run_id>/
│   ├── survey_responses_<run_id>.xlsx
│   └── quality_report_<run_id>.md
└── report_<run_id>/
```

技能代码、模板和参考文档保持只读；运行数据不要写入技能目录。

## 验证

在项目根目录运行：

```bash
python -m unittest discover -s tests -v
```

验证范围包括：四个技能结构和 frontmatter、资源引用、方案审计、画像分配/审计、mock 并行记录链路、回答校验、HTML 离线图表和工作流引用。

`mock` 测试只能证明本地管线可运行；真实供应商测试需要用户自行提供 API 凭据，因此自动测试不会访问或消耗外部模型。
