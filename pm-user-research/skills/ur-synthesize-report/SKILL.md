---
name: ur-synthesize-report
description: 直接分析 ur-user-simulator 生成的全量合成问卷工作簿，依次完成可追溯的数据清理、描述统计、交叉/量表检验、定性综合和可离线审计的 HTML 报告；不读取逐人画像或旁路质量报告，也不把合成样本推断为真实市场结论。
---

# 综合问卷数据并输出调研报告

把一批已完成的问卷回答转换成能回溯到题目和 Excel 原始行的报告。`questionnaire.md` 是题目文本的权威来源，`questionnaire-design.html` 是研究决策、目标和分析建议的权威来源，回答工作簿是所有回答与统计的唯一来源。

## 运行约定

- 把技能目录记为 `<SKILL_DIR>`，调用工作目录记为 `<WORK_DIR>`。
- 输出到 `<WORK_DIR>/用户调研/<YYYYMMDD><课题>/report_<run_id>/`，不同运行不得相互覆盖。
- 报告必须是 UTF-8 单文件 HTML，CSS、SVG 图表和必要数据全部内嵌，不依赖 CDN、远程字体或脚本。
- 所有中间和最终文件都写入调用者的任务目录，不写入 Skill 目录。

## 输入

先读 [references/io-contract.md](references/io-contract.md)，再收集以下文件；后续步骤只使用本节锁定的路径。

### 研究设计输入

- `<WORK_DIR>/用户调研/<YYYYMMDD><课题>/questionnaire.md`：必需；已由用户确认的正式问卷。
- `<WORK_DIR>/用户调研/<YYYYMMDD><课题>/questionnaire-design.html`：必需；提供产品决策、研究目标、逐题用途、分析建议和完整问卷附录。

从 `questionnaire.md` 的 Q 标题、题型标签、选项、量表端点、动态回填说明和逻辑提示解析完整问卷结构。题号重复、题型无法识别或 Excel 题目列与问卷不一致时停止分析。

### 回答批次输入

直接读取：

```text
<WORK_DIR>/用户调研/<YYYYMMDD><课题>/survey_response_data/survey_responses_<run_id>.xlsx
```

该文件是必需且唯一的回答批次输入，必须包含全量样本行、完成状态、实际模型、所有题目答案、条件性的回答原因和错误摘要。总样本、完成/失败、完成率、模型分布、缺失和问题摘要全部从工作簿直接计算。目录中存在多个工作簿时不得自行选择“最新”或跨批合并；使用用户指定的文件。

### 可选样本构成说明

- 默认不读取 `personas.json`、`persona_audit.json`、`persons/` 或任何逐人画像文件。
- 只有需要说明样本如何构建时，才可选读取 `<WORK_DIR>/用户调研/personas_data/persons_summary.txt`。
- `persons_summary.txt` 只提供批次级构建背景；不得当作问卷发现、分群字段、单个回答的解释、主题频次、用户原话或市场比例。

## 第一步：数据清理和准备

先对指定工作簿做初步检查。原始 Excel 保持不改写；清理后的分析样本和每条剔除理由写入 `analysis_summary.json.data_cleaning`，以便审计。

- 自动剔除可解析的结构性或逻辑无效完成回答：问卷外选项、重复排序、超过题目选择上限、非数值量表值、超出量表范围的值，以及违反“结束答题”、排他项跳题或明确显示条件的回答。
- 对照 `questionnaire.md` 的逻辑提示、`questionnaire-design.html` 的调研诉求和回答原文，人工识别逻辑不自洽、与本次调研对象/诉求明显不符的完成回答。每条人工剔除必须保留用户 ID 和具体理由；不能凭印象筛选。
- 带“错误摘要”的完成回答先列为人工复核，除非能说明其回答无效，否则不自动剔除。失败行不进入分析样本，但仍计入总样本、失败数和完成率。

运行准备脚本。需要人工剔除时可重复追加 `--exclude-response "<用户ID>:<清理理由>"`：

```bash
python "<SKILL_DIR>/scripts/generate_report.py" \
  --questionnaire "<QUESTIONNAIRE_MD>" \
  --design-doc "<DESIGN_DOC_HTML>" \
  --responses "<SURVEY_RESPONSES_XLSX>" \
  --exclude-response "<用户ID>:<清理理由>" \
  --output-dir "<REPORT_DIR>" \
  --prepare-only
```

如需披露样本构成，在命令中追加 `--persons-summary "<PERSONS_SUMMARY_TXT>"`。没有人工剔除时省略 `--exclude-response`。本技能固定处理合成模拟问卷，不接收真实或混合来源参数。

## 第二步：描述性统计分析

对清理后的可分析样本逐题统计；不得用总样本或清理前完成样本代替题目实际分母。准备阶段生成 `analysis_summary.json`，至少包含：

- 输入路径、`run_id`、合成数据标记和契约检查结果；
- 总行数、完成数、可分析数、失败数、完成率、缺失、质量等级和模型分布；
- 每题题干、题型、实际分母、缺失数、频数与百分比；
- 排序题的第一选择和平均名次，量表题的有效数和描述统计；
- 开放题回答及各题“回答原因”的原子文本，证据 ID 使用 `<用户ID>:<题号>` 或 `<用户ID>:<题号>:reason`；
- 从 `questionnaire-design.html` 提取的研究目标与题目映射；没有证据时明确写 `evidence_gap`。

不得先把 Excel 转成另一份未定义的 `structured_data_*.json` 或 `raw_data_*.json`。统计从原工作簿直接产生，`analysis_summary.json` 是分析底稿，不是新的模拟器输出格式。

- 单选题：逐项频数、百分比和本题实际分母。
- 多选题：逐项选择人数与受访者百分比；明确百分比合计可超过 100%。需要比较两个问卷字段时使用多重响应交叉表，不把多个选择相加成互斥比例。
- 量表/NPS：逐项频数、均值、标准差、中位数、最小值和最大值。样本数不足 2 时标准差标记为“样本不足”。
- 排序题：第一选择频数、选择人数和平均名次。

## 第三步：高级与交叉分析

读取 [references/analysis-methods.md](references/analysis-methods.md) 的“交叉分析与量表检验”，只在条件满足时补全 `analysis_summary.json`：

1. `cross_tabulations`：仅按回答工作簿中可识别且与研究目标相关的分组题（例如问卷实际包含的年龄、性别或使用阶段题）交叉；每个单元格显示组内 `n` 与百分比，并保留空组、反例和小样本限制。
2. `scale_quality`：仅对同一构念、同方向、同量表的至少 3 个题项做内部一致性检验（如 Cronbach’s α）。效度只报告已有的题项—构念映射、样本条件和可执行的后续验证；样本或设计不满足条件时明确写“不适用”，不虚构 α、因子或效度结论。
3. 所有交叉和量表结论都只描述本次合成样本；不做显著性、总体推断、市场规模或真实人群差异声明。

## 第四步：完成定量与定性综合

读取 [references/analysis-methods.md](references/analysis-methods.md)，补全 `analysis_summary.json`：

1. `goal_coverage`：每个目标映射到题目、指标、证据或缺口，并写答案优先的 finding。
2. `themes`：只编码问卷开放回答和回答原因；先拆原子观察，再聚类主题。每个主题包含 `evidence_ids`、`n/N`、反例、替代解释和置信等级。
3. `segment_observations`：仅使用回答工作簿中明确存在的字段，标记 `source=response`；不得借用画像或样本构成汇总创建分群。
4. `recommendations`：按“证据 → 解释 → 产品含义 → 下一步验证”写，标注影响、证据强度、成本/风险和可逆性。
5. `limitations`：覆盖样本构建方式、缺失、运行质量、模型偏差、问卷设计限制和不能回答的问题。

按 [rules/evidence_rule.md](rules/evidence_rule.md) 控制表述。尤其注意：

- 合成数据中的发现最高为 `low` 置信度，只能用于工具测试和假设生成。
- 合成回答使用“模拟回答”或“模拟原话”，不能写“用户原话”。
- 百分比显示实际分母；多选题注明总和可超过 100%。
- 失败行保留在总样本和完成率中，但不进入题目分母；跳题和空白都计入本题缺失/未适用说明。
- 可选的样本构成说明、问卷回答比例和真实市场比例必须严格区分。

## 第五步：渲染、检查并交付报告

补全分析底稿后运行：

```bash
python "<SKILL_DIR>/scripts/generate_report.py" \
  --questionnaire "<QUESTIONNAIRE_MD>" \
  --design-doc "<DESIGN_DOC_HTML>" \
  --responses "<SURVEY_RESPONSES_XLSX>" \
  --exclude-response "<用户ID>:<清理理由>" \
  --analysis "<REPORT_DIR>/analysis_summary.json" \
  --output-dir "<REPORT_DIR>"
```

若第一步使用了人工清理参数，渲染时必须重复相同的 `--exclude-response` 参数；否则省略该行。按 [templates/report_outline.md](templates/report_outline.md) 输出 `report.html`。正文必须依次呈现数据清理、描述性统计、高级/交叉分析、回答中观察到的结果、研究者解释，以及仍需真实研究验证的假设。

按 [rules/report_quality_rule.md](rules/report_quality_rule.md) 检查，且必须：

- 打开最终 HTML 做视觉检查，不只检查源 JSON。
- 抽查至少 3 项统计，与 Excel 原行和题目列一致。
- 抽查至少 3 个证据 ID，能回到 Excel 的用户行和题目/回答原因列。
- 确认标题、研究目标结论、图表说明和限制中的来源披露一致。
- 确认 HTML 没有外部资源，移动端和桌面端都可读。

最终输出：

```text
report_<run_id>/
├── analysis_summary.json
├── report.html
└── report_quality.md
```

`report_quality.md` 是必需文件，记录输入契约、Excel 统计抽查、证据回溯、来源披露、离线和视觉检查结果。任一必检项失败，先修复再交付。

回复先给出报告路径和所分析的 `run_id`，再用 3–5 条概括关键发现与最重要限制。合成数据必须明确说明不能替代真实用户研究。

## 失败处理

- 输入不配套：保留原文件，列出缺失、错配和重复 run，不自行改名或合并。
- Excel 列与问卷不一致：生成字段错误清单并停止；不静默丢弃未知题号或缺少的题列。
- Excel 中完成率低于 70%：只保留 `analysis_summary.json` 中的数据质量诊断，不生成正式结论。
- 样本很小：报告计数与证据缺口，避免伪精确百分比和稳定分群结论。
- 引语或回答原因缺失：不补写；只报告现有结构化答案。
- HTML 审计失败：保留底稿，修复后重跑；不用聊天摘要替代报告。
