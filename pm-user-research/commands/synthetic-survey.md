# 工作流：完整合成定量问卷

## 目标

组合四个原子 Skill，完成问卷设计、画像生成、模拟作答和报告输出。

```text
ur-design-survey
    ↓
检查预置用户画像 ── 数量不足时调用 ur-generate-personas
    ↓
ur-user-simulator
    ↓
ur-synthesize-report
```

本工作流只定义 Skill 的调用顺序和交互关系。各阶段的业务逻辑、执行方式和质量规则，以对应 Skill 的 `SKILL.md` 为准。

## 任务目录

问卷、模拟回答和报告使用当前课题目录；用户画像使用所有课题共用的全局目录：

```text
<WORK_DIR>/用户调研/<YYYYMMDD><课题>/
```

```text
<WORK_DIR>/用户调研/personas_data/
```

Skill 之间只传递文件路径，不传递上一个 Skill 的对话内容。

## 跨 Skill 契约

| Skill | 工作流提供的输入 | 传给下游的输出 |
|---|---|---|
| `$ur-design-survey` | 用户的课题、目标、问卷场景、材料和约束 | `questionnaire_for_simulator.md` → 模拟；`questionnaire.md` 与 `survey-design-desc.html` → 报告 |
| `$ur-generate-personas` | 仅在预置画像不足时接收用户直接确认的课题、全量候选用户群体、目标用户、所需画像数量和可选配额 | 大模型生成临时 `personas.json`，经脚本审计后写入全局 `用户调研/personas_data/` → 模拟 |
| `$ur-user-simulator` | `questionnaire_for_simulator.md`（缺失时回退 `questionnaire.md`）、本次选定的用户画像清单、对应的 `persons/`、可选模型配置 | `survey_responses_<run_id>.xlsx` → 报告；质量报告 → 工作流门禁 |
| `$ur-synthesize-report` | `questionnaire.md`、`survey-design-desc.html`、指定批次的回答 Excel；可选全局 `persons_summary.html` | `report_<run_id>/` |

没有列入“传给下游”的文件由所属 Skill 自己管理，不自动成为其他 Skill 的输入。

## 执行

1. 在正式任务目录中调用 `$ur-design-survey`。用户确认问卷且该 Skill 完成自身检查后继续。
2. 确定本次计划调用的用户数量 `N`，再检查全局 `用户调研/personas_data/` 中通过审计且文件完整的预置画像数量 `M`：
   - `M >= N`：直接从预置画像中选取 `N` 人作为本次调用清单，跳过 `$ur-generate-personas`，不得仅因课题变化重复生成画像；
   - `M < N`：调用 `$ur-generate-personas`，按 `N` 生成足量画像并通过该 Skill 的审计后，再形成 `N` 人调用清单；
   - 未指定 `N`：预置画像有效时默认使用其全部 `M` 人；没有有效预置画像时，采用 `$ur-generate-personas` 的默认数量。

   只有 `personas.json`、`persons_summary.html`、`persons/` 和 `persona_audit.json` 相互一致且审计通过，才计入预置画像数量。画像生成输入需由用户直接确认，不从问卷设计产物推导或传递。
3. 把问卷和本次选定的用户画像清单交给 `$ur-user-simulator`。该 Skill 完成一批模拟回答后，由工作流根据质量报告决定继续、复核或重跑。
4. 从可用回答批次中明确选择一个 `run_id`，把对应 Excel 连同问卷和设计文档交给 `$ur-synthesize-report`。
5. 报告输出沿用所选回答批次的 `run_id`。任一阶段失败时停止调用下游 Skill，回到失败阶段处理。

## 交互边界

- `$ur-generate-personas` 不接收问卷、研究假设或设计结论。
- `$ur-user-simulator` 只按本次选定的 `N` 人清单逐人读取画像，不把未选画像加入本批次，也不把不同人物放入同一作答上下文。
- `$ur-synthesize-report` 不读取逐人画像、已清理的临时答卷或模拟器质量报告；全局 `persons_summary.html` 只在需要说明样本构成时传入。
- 回答目录存在多个批次时，由调用方明确选择，不自动选择最新批次，不合并不同 `run_id`。

## 返工关系

| 变化 | 重跑范围 |
|---|---|
| 问卷或研究设计变化 | 模拟 → 报告 |
| 画像生成输入或画像变化 | 画像 → 模拟 → 报告 |
| 新增回答批次 | 为新 `run_id` 生成报告 |

## 完成条件

- 必需的 Skill 按顺序完成并分别通过自身检查；预置画像足够时允许跳过 `$ur-generate-personas`；
- 下游 Skill 只读取跨 Skill 契约中规定的文件；
- 回答批次和报告使用同一个 `run_id`，所有产物保存在同一正式任务目录。
