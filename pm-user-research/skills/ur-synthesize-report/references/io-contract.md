# 输入输出契约

本文件定义 `ur-synthesize-report` 从 `ur-design-survey` 和 `ur-user-simulator` 当前产物读取数据的文件契约；`ur-generate-personas` 的逐人产物不属于报告输入。

## 合成问卷输入目录

```text
<WORK_DIR>/用户调研/<YYYYMMDD><课题>/
├── shared_context.md                                      # 可选；只用于课题与受众披露
├── questionnaire.md                                      # 必需；题目文本权威来源
├── questionnaire-design.html                             # 必需；决策、目标、逐题用途、完整问卷
└── survey_response_data/
    └── survey_responses_<run_id>.xlsx                    # 必需；全量回答唯一来源

<WORK_DIR>/用户调研/personas_data/
└── persons_summary.txt                                   # 可选；仅样本构建背景披露
```

目录中有多个回答工作簿时，调用方必须明确指定其中一个，不自行选择最新批次。报告目录使用所选工作簿文件名中的 `run_id`。

## 各输入的职责边界

| 文件 | 可读取内容 | 禁止用途 |
|---|---|---|
| `questionnaire.md` | 标题、题干、受访者看到的选项/量表、概念卡和逻辑提示 | 不从对话记忆补题目 |
| `questionnaire-design.html` | 产品决策、研究目标、逐题用途、分析建议和完整问卷附录 | 不把设计假设写成研究发现；题目结构仍以 `questionnaire.md` 为准 |
| 回答 Excel | 全量样本、回答、回答原因、状态、实际模型和错误摘要 | 不用外部画像或摘要填补空白答案 |
| `persons_summary.txt` | 合成样本构建分布 | 不报告为问卷结果或市场比例 |

## questionnaire.md 前置要求

- 必须有一级标题，并以 `## Q编号 ｜ 题型` 定义每道题。
- 题号唯一；题型标签明确为单选、多选、排序、量表、NPS 或开放文本。
- 选择题选项、量表范围、最大选择数、动态回填来源和逻辑提示直接从 Markdown 解析。
- 研究目标只从 `questionnaire-design.html` 读取；`questionnaire.md` 不承担研究背景和分析计划。

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

本技能只处理 `ur-user-simulator` 生成的合成问卷，`analysis_summary.json.data_source` 固定为 `synthetic`。不接收真实或混合来源，也不读取 `personas.json`、`persona_audit.json` 或 `persons/`。

若调用方提供 `persons_summary.txt`，只可提取课题、画像总数和构建分布以披露样本如何构成。它不参与用户 ID 校验、统计、证据、分群或结论。

## analysis_summary.json

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
  "cross_tabulations": [],
  "scale_quality": [],
  "qualitative_observations": [],
  "themes": [],
  "segment_observations": [],
  "recommendations": [],
  "limitations": []
}
```

准备阶段只写可机械复核的统计和原子文本。研究者补写的主题、解释和建议必须保留证据 ID 与分母，不覆盖原始描述统计。

## 最终输出

```text
report_<run_id>/
├── analysis_summary.json
├── report.html
└── report_quality.md
```

- `analysis_summary.json`：图表、结论和证据索引的可复核底稿。
- `report.html`：UTF-8 单文件，内嵌 CSS、SVG 和必要数据，无外部依赖。
- `report_quality.md`：输入契约、Excel 统计抽查、证据回溯、来源披露、离线与视觉检查结果。

三个文件都是必需产物，并对应同一 `run_id`。
