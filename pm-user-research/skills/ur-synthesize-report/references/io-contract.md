# 输入输出契约

本文件定义两种来源的输入适配、公共分析底稿与输出契约。两种来源共用主 SKILL.md 的五步执行流程；下面的固定目录、列与 CLI 命令只适用于合成模式。`ur-generate-personas` 的逐人产物不属于报告输入。

## 真实问卷输入适配

直接读取用户指定的 `.xlsx` 或 `.xls`，锁定实际工作表与原始答卷区域，记录列—题目映射、编码字典、量表方向、多选/矩阵拆列、缺失和跳题规则来源。无需模拟器命名或固定字段，不补造缺少的问卷、状态、模型、回答原因和采集信息。

有采集批次 ID 时保留；没有时生成本次分析运行 ID，并注明与采集批次不同。用匿名响应 ID 关联原文件、工作表和行号，身份映射仅保存在本地底稿。只有聚合数据时，不构造受访者行、筛选、原始答卷交叉或定性证据回溯。

真实数据与合成数据采用下面相同的分析字段职责，但 `data_source=real`；不存在或无法计算的状态/完成率/运行指标应省略或标为未知，不写成 0 或 100%。底稿记录实际采集信息和偏差，不要求模型分布。真实数据适配不代表现有合成 CLI 已支持任意 Excel。

## 合成问卷输入目录

```text
<WORK_DIR>/用户调研/<YYYYMMDD><课题>/
├── questionnaire.md                                      # 必需；题目文本权威来源
├── survey-design-desc.html                               # 必需；决策、目标、逐题用途、完整问卷
└── survey_response_data/
    └── survey_responses_<run_id>.xlsx                    # 必需；全量回答唯一来源

<WORK_DIR>/用户调研/personas_data/
└── persons_summary.html                                  # 可选；仅样本构建背景披露
```

目录中有多个回答工作簿时，调用方必须明确指定其中一个，不自行选择最新批次。报告目录使用所选工作簿文件名中的 `run_id`。

## 各输入的职责边界

| 文件 | 可读取内容 | 禁止用途 |
|---|---|---|
| `questionnaire.md` | 标题、题干、受访者看到的选项/量表、概念卡和逻辑提示 | 不从对话记忆补题目 |
| `survey-design-desc.html` | 产品决策、研究目标、逐题用途、分析建议和完整问卷附录 | 不把设计假设写成研究发现；题目结构仍以 `questionnaire.md` 为准 |
| 回答 Excel | 全量样本、回答、回答原因、状态、实际模型和错误摘要 | 不用外部画像或摘要填补空白答案 |
| `persons_summary.html` | 合成样本构建分布 | 不报告为问卷结果或市场比例 |

## questionnaire.md 前置要求

- 必须有一级标题，并以 `## Q编号 ｜ 题型` 定义每道题。
- 题号唯一；题型标签明确为单选、多选、排序、量表、NPS 或开放文本。
- 选择题选项、量表范围、最大选择数、动态回填来源和逻辑提示直接从 Markdown 解析。
- 研究目标只从 `survey-design-desc.html` 读取；`questionnaire.md` 不承担研究背景和分析计划。

## 回答 Excel

`survey_responses_<run_id>.xlsx` 只有一个“问卷回答”工作表，每个样本一行。固定列顺序为：

```text
任务ID | 用户ID | 姓名 | 实际模型 | 状态 | Q1 | [Q1_回答原因] | Q2 | ... | 错误摘要
```

- 所有 `questionnaire.md` 中的题号必须各有一个同名回答列，顺序与问卷一致。
- `<题号>_回答原因` 是条件列；某题无人填写原因时可以不存在。
- 不允许未知的 `Q...` 或 `Q..._回答原因` 列。
- 用户 ID 必须非空且唯一；不需要与 persona 文件做 ID 对应校验。
- 状态为完成/成功的行进入题目分析；失败行保留在批次总数、失败数和完成率中，回答不进入题目分母。
- 多选和排序使用中文分号 `；` 分隔；未作答为空单元格；数值和布尔值保持工作簿原类型。
- `任务ID` 应以 `<run_id>-` 开头。
- 总样本、完成/失败、完成率、模型分布、缺失和问题摘要均直接从这些行计算，不读取旁路汇总文件。
- 完成率低于 70% 时只生成质量诊断；任一“错误摘要”非空时标记 `needs_review`。
- 统计前先筛除可机械确认的无效完成回答：问卷外选项、重复排序、选择数超限、非数值量表值、超出量表范围的值，以及违反已解析的结束答题、排他项跳题或显示条件的回答。语义或研究诉求不符的人工剔除必须通过 `--exclude-response "<用户ID>:<理由>"` 记录；原始工作簿不改写。

## 合成数据与样本构成说明

合成模式及现有 `generate_report.py` CLI 处理 `ur-user-simulator` 生成的问卷，`analysis_summary.json.data_source` 为 `synthetic`。真实模式使用前述输入适配；两种来源不自动混合，也不读取 `personas.json`、`persona_audit.json` 或 `persons/`。

若调用方提供 `persons_summary.html`，只可读取其中 `persona-summary-data` JSON 的课题、画像总数和构建分布以披露样本如何构成。它不参与用户 ID 校验、统计、证据、分群或结论。

## analysis_summary.json

以下为现有合成 CLI 的示例。字段职责供两种模式复用，真实适配不能机械继承合成来源、模型和运行指标；未知值及未支持的交互需明确标记。

```json
{
  "schema_version": "2.0",
  "study_id": "survey_album_cloud_control",
  "run_id": "20260905_224909",
  "data_source": "synthetic",
  "inputs": {},
  "sample": {
    "total": 5,
    "completed": 5,
    "analyzable": 5,
    "failed": 0,
    "completion_rate": 1.0,
    "quality_grade": "excellent",
    "model_distribution": {}
  },
  "data_cleaning": {
    "completed_before_cleaning": 5,
    "analyzable_after_cleaning": 5,
    "excluded_count": 0,
    "excluded_records": [],
    "manual_review_records": []
  },
  "research_context": {
    "decision": "...",
    "research_goals": []
  },
  "goal_coverage": [],
  "descriptive_results": [],
  "interactive_data": {
    "questions": [{"id": "Q1", "question": "...", "type": "single_choice", "options": []}],
    "responses": [{"answers": {"Q1": "..."}}]
  },
  "cross_tabulations": [],
  "scale_quality": [],
  "qualitative_observations": [],
  "themes": [],
  "segment_observations": [],
  "recommendations": [],
  "limitations": []
}
```

准备阶段只写可机械复核的统计和原子文本。`interactive_data` 仅保存清理后可分析样本的匿名封闭题答案，供单文件 HTML 在本地按题目与选项筛选、重算描述统计、切换图表与交叉分析；禁止放入用户 ID、姓名、任务 ID、模型、开放回答或回答原因。研究者补写的主题、解释和建议必须保留证据 ID 与分母，不覆盖原始描述统计。

人工审计可在底稿的 `report_audit` 数组中记录：`{"check_id":"statistics","status":"passed","note":"抽查题目及原始行、结果与限制"}`。状态为 `passed`、`failed`、`pending` 或 `not_applicable`；未记录项默认待检查，不自动认证。检查 ID 为 `statistics`、`evidence`、`cleaning`、`privacy`、`desktop_mobile`、`filters`、`charts`、`cross`、`tabs`、`office`、`downloads`、`conclusions`。不要在公开审计说明中写入身份信息或敏感原文。

## 合成 CLI 调用

这是统一流程中步骤 1–2 与步骤 5 的执行工具，不是第二套分析流程。真实 Excel 不送入此 CLI；按主 Skill 的实现边界建立任务级输入/渲染适配。

准备并生成机械统计：

```bash
python "<SKILL_DIR>/scripts/generate_report.py" \
  --questionnaire "<QUESTIONNAIRE_MD>" \
  --design-doc "<DESIGN_DOC_HTML>" \
  --responses "<SURVEY_RESPONSES_XLSX>" \
  --output-dir "<REPORT_DIR>" \
  --prepare-only
```

需要人工剔除时重复追加 `--exclude-response "<用户ID>:<具体理由>"`；需要披露样本构建时追加 `--persons-summary "<PERSONS_SUMMARY_HTML>"`，否则省略。按统一流程步骤 3–4 补全底稿，保留原有机械字段和目标映射，再渲染：

```bash
python "<SKILL_DIR>/scripts/generate_report.py" \
  --questionnaire "<QUESTIONNAIRE_MD>" \
  --design-doc "<DESIGN_DOC_HTML>" \
  --responses "<SURVEY_RESPONSES_XLSX>" \
  --analysis "<REPORT_DIR>/analysis_summary.json" \
  --output-dir "<REPORT_DIR>"
```

渲染必须重复准备阶段相同的人工剔除和可选样本构成参数，不能改变分析样本。用户指定底稿名称时，`--analysis` 使用实际路径；默认产物命名仍由现有脚本决定。

## 最终输出

```text
report_<run_id>/
├── analysis_summary.json
└── <YYYYMMDD><调研课题>_调研报告.html

```

- `analysis_summary.json`：图表、结论和证据 ID 的可复核底稿。
- `<YYYYMMDD><调研课题>_调研报告.html`：UTF-8 单文件，内嵌 CSS、SVG、匿名封闭题筛选数据与交互脚本，无外部依赖；支持按题目与选项多条件筛选、逐题独立表格/饼图/圆环/柱状/条形/折线切换、X 最多 2 题与 Y 最多 10 题的交叉分析，以及下载窗口内的真正 DOCX/PPTX/XLSX 导出和结论三页 PPT；保留 CSV 下载。筛选只重算封闭题描述统计、当前样本数与页面内交叉表。 “问卷质量报告”Tab 同时承载输入契约、统计/证据抽查、来源、隐私、离线、交互/导出和视觉检查记录。
不再单独生成 `report_quality.md`。结构检查与人工审计分别展示在 HTML 内；未检查项保持“待检查”，不能将控件存在等同于浏览器验收。

底稿和 HTML 为必需产物，对应同一 `run_id`；结论 PPT 由报告提供下载。HTML 日期默认使用生成日期，`--report-date YYYYMMDD` 可覆盖。课题名去重日期和问卷/报告后缀，并替换文件名非法字符。

## 交互统计与导出口径

- 同题多个选项按“任一满足”，不同题目按“同时满足”筛选；只基于 `interactive_data` 中的可分析样本。
- 交互工作台重算当前题目和交叉表；“调研分析结论”与“问卷质量报告”Tab 保留全批次口径，页面明确区分。
- 交叉表显示组人数、目标题有效分母、空白数、选项人数与有效分母百分比；空组百分比为 `—`，保留零频选项。多选/排序分组会重叠，目标题按“是否选择”统计，百分比合计可超过 100%。
- 饼图/圆环用于互斥题或排序题的第一选择；多选题允许切换，但图中比例按选择人次归一化，明确区别于表格的受访者比例；折线只表示按选项顺序排列的频数，不暗示时间趋势。
- 不提供 HTML 保存及 PNG/SVG 导出；结论页 PPTX 为2–3页（默认3页），含背景与目的、用户现状、诉求与痛点、关键结论及相关全批次百分比图表；CSV 包含当前交叉表的频数、有效分母与百分比。

当前报告交互要求：结论页提供2–3页 PPT（默认3页），依次呈现背景/目的与用户现状、用户诉求与痛点、目标对应的关键结论，并配相关题目图表、实际分母及来源限制。以证据支持现状与诉求，不补造未提供的背景、原因或研究目标。质量明细放入“问卷质量报告”Tab。普通分析图形按百分比绘制并标注；多选饼图/圆环按选择人次占比，其他图形按有效受访者占比。不提供保存报告及 PNG/SVG 导出。
