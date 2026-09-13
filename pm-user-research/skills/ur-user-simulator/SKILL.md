---
name: ur-user-simulator
description: 让合成用户画像在相互隔离的会话中回答定量问卷，支持当前模型或已配置的外部模型，并输出个人答卷、Excel 汇总和质量报告。本技能不处理访谈。
---

## 运行约定

- 把技能目录记为 `<SKILL_DIR>`，调用工作目录记为 `<WORK_DIR>`。
- 输出目录为 `<WORK_DIR>/用户调研/<YYYYMMDD><课题>/survey_response_data/`。
- 只从环境变量读取 API Key，不得把密钥写入配置、日志、答卷或回复。

## 第一步：读取问卷和全量用户清单

主任务只读取并核对：

1. `ur-design-survey` 已确认的 `questionnaire.md`。它必须包含完整题号、题干、选项、量表、概念卡和跳转/结束规则。
2. `<WORK_DIR>/用户调研/personas_data/persons_summary.txt`。这是跨课题复用的全局画像清单；从“画像总数”和“全量用户ID”取得人数 `N` 与有序 ID 数组。
3. 检查 `<WORK_DIR>/用户调研/personas_data/persons/` 中每个 ID 恰好对应一个 `<用户ID>_<姓名>.txt`，且没有额外文件。此时只确定文件路径，不读取所有画像内容；每个子任务执行时再读取自己的画像。

任一输入缺失、ID 重复、人数不一致或画像文件不能唯一匹配时，先停止分发并报告问题。

## 第二步：确定模型和任务配置

### 模型选择

检查用户提供的简洁 YAML，格式见 [`config/llm.example.yaml`](../../config/llm.example.yaml)，说明见 [references/llm-configuration.md](references/llm-configuration.md)。

- 配置中至少有一个“模型 ID 非空且对应 Key 环境变量存在”的项目：使用外部 API。多个可用模型按配置预置顺序轮询分配。
- 未提供配置，或全部配置项不可用：使用当前模型。子任务不指定模型覆盖，直接继承当前模型；无法取得准确模型 ID 时记录 `current-model`，不得猜测。
- 外部模型单次任务失败时，在同一模型上有限重试；仍失败则转给下一个可用模型。全部模型失败才把该用户记为失败。
- 遇到限流时降低并发并退避，不无限重试。并发上限和重试次数在分发前确定，执行中不临时增加模型。

### 任务配置

生成一个 `run_id`，并为每个用户设置：

- 任务 ID：`<run_id>-<用户ID>`
- 问卷绝对路径
- 该用户画像绝对路径
- 分配模型与调用方式
- 唯一输出路径：`<OUTPUT_DIR>/answers_<run_id>/<用户ID>.md`

一人只分配一个任务，不因模型数量增加答卷数。失败重试沿用原任务 ID。

## 第三步：并行分发、执行和同步结果

### 使用外部 API

运行：

```bash
python "<SKILL_DIR>/scripts/run_simulation.py" \
  --questionnaire "<QUESTIONNAIRE_MD>" \
  --persons-summary "<PERSONS_SUMMARY_TXT>" \
  --persons-dir "<PERSONS_DIR>" \
  --config "<LLM_YAML>" \
  --output-dir "<OUTPUT_DIR>"
```

脚本按全量用户 ID 创建独立并行任务。每个工作线程在开始作答时读取完整 `questionnaire.md`，然后只读取该用户的 TXT 画像；不读取其他画像或其他人的回答。若脚本返回 `fallback_current_model`，改用下面的当前模型流程。

### 使用当前模型

先运行：

```bash
python "<SKILL_DIR>/scripts/native_simulation.py" prepare \
  --questionnaire "<QUESTIONNAIRE_MD>" \
  --persons-summary "<PERSONS_SUMMARY_TXT>" \
  --persons-dir "<PERSONS_DIR>" \
  --output-dir "<OUTPUT_DIR>"
```

脚本只在标准输出返回待执行任务，不保存任务清单。将全部任务描述提交给平台的独立子任务并行执行；实际同时运行数量遵守平台限制。

每个子任务必须按以下顺序完成：

1. 完整读取任务指定的 `questionnaire.md`。
2. 只读取任务指定的 `<用户ID>_<姓名>.txt`，核对“画像编号”与任务用户 ID 一致。
3. 代入该画像按题序完成问卷，遵守显示、跳转、排他和结束规则；只能使用画像事实、题目材料和普通常识。
4. 将自己的答卷写入唯一输出路径，确认文件可重新读取后再返回完成状态。

子任务之间不得共享画像、提示、回答或研究者预期。提示边界见 [templates/survey_prompt.md](templates/survey_prompt.md)，执行约束见 [rules/simulation_rule.md](rules/simulation_rule.md)。

全部子任务结束后运行 `native_simulation.py finalize`，传入同一问卷、用户清单、画像目录、答卷目录、`run_id` 和质量报告路径。缺失答卷自动记为失败；已存在且用户 ID 正确的答卷用于中断恢复，不覆盖重做。

### 个人答卷格式

文件头记录任务 ID、用户 ID、姓名、问卷来源、模型提供商、实际模型和“合成回答”标识。每题只写：

```markdown
### Q1
回答：<用户答案；跳过或未作答时写“未作答”>
回答原因：<有则补充，无则省略整行>
```

不重复写入题目原文和选项。外部 API 返回 JSON 后，由脚本转换成相同的 Markdown 格式。

主任务同步每个用户的完成状态、实际模型和错误摘要，但不把任务清单或原始模型响应保存为最终文件。成功数加最终失败数必须等于 `N`。

## 第四步：校验回答

外部 API 脚本和当前模型的 `finalize` 都会调用 `validate_responses.py`。需要单独复核时运行：

```bash
python "<SKILL_DIR>/scripts/validate_responses.py" \
  --questionnaire "<QUESTIONNAIRE_MD>" \
  --persons-summary "<PERSONS_SUMMARY_TXT>" \
  --persons-dir "<PERSONS_DIR>" \
  --answers-dir "<ANSWERS_DIR>" \
  --quality-report "<QUALITY_REPORT_MD>" \
  --run-id "<RUN_ID>"
```

- 按 [rules/response_validation_rule.md](rules/response_validation_rule.md) 检查缺失、选项、量表、排他项和问卷中明确写出的跳转规则。
- 按 [rules/authenticity_rule.md](rules/authenticity_rule.md) 标记画像冲突、跨答卷长文本重复和模板化等风险。
- 问题分为 `error`、`warning`、`note`。风险信号不能用于证明回答真伪，也不能使用人口属性刻板推断态度或能力。

## 第五步：生成输出

### 1. 整理个人答卷

按 `persons_summary.txt` 的 ID 顺序检查 `answers_<run_id>/`。成功用户一人一个 `<用户ID>.md`；失败用户不生成默认答卷，其错误写入质量报告。

### 2. 生成 Excel

使用平台电子表格能力读取问卷、全量用户 ID、个人答卷和质量报告，生成 `survey_responses_<run_id>.xlsx`。结构与样式参考 [templates/survey_responses_example.xlsx](templates/survey_responses_example.xlsx)。

- 只创建“问卷回答”工作表，每个用户一行，按全量用户 ID 顺序排列。
- 固定列为“任务ID、用户ID、姓名、实际模型、状态”，之后按问卷顺序设置 `Q1、Q2…`，最后为“错误摘要”。
- 某题至少有一人填写回答原因时，在该题后增加 `<题号>_回答原因` 列；全部为空时不创建。
- 失败用户也保留一行，答案留空。多选答案用 `；` 分隔；数值和布尔值保持原类型；“未作答”在 Excel 中留空。
- 冻结首行、启用筛选、自动换行并设置可读列宽。导出后重新读取关键区域，检查行数、用户 ID、题号顺序和公式错误。

### 3. 完成质量报告和目录检查

质量报告至少包含总人数、完成数、失败数、完成率、模型分配、问题类型、严重度、涉及用户 ID、人工复核项和是否可进入后续分析。报告结构见 [templates/response_output.md](templates/response_output.md)。

最终目录只包含：

```text
survey_response_data/
├── answers_<run_id>/
│   ├── P001.md
│   └── ...
├── survey_responses_<run_id>.xlsx
└── quality_report_<run_id>.md
```

三项必须使用同一个 `run_id`。不得额外输出任务清单、原始 JSON 或结构化 JSON。详细格式见 [references/io-contract.md](references/io-contract.md)。

- `excellent/good`：可以进入后续分析，但仍保留合成数据限制。
- `needs_review`：先复核问题，再选择性重跑。
- `poor`：停止分析，修复高严重度问题后重跑。
