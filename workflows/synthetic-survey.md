# 工作流：完整合成定量问卷

## 目标

组合四个原子 Skill，完成问卷设计、画像生成、模拟作答和报告输出。

```text
ur-design-survey
    ↓
ur-generate-personas
    ↓
ur-user-simulator
    ↓
ur-synthesize-report
```

本工作流只定义 Skill 的调用顺序和交互关系。各阶段的业务逻辑、执行方式和质量规则，以对应 Skill 的 `SKILL.md` 为准。

## 任务目录

四个 Skill 共用一个正式任务目录：

```text
output/<YYYYMMDD><课题>/
```

Skill 之间只传递文件路径，不传递上一个 Skill 的对话内容。

## 跨 Skill 契约

| Skill | 工作流提供的输入 | 传给下游的输出 |
|---|---|---|
| `$ur-design-survey` | 用户的课题、材料和约束 | `shared_context.md` → 画像；`questionnaire.md` → 模拟与报告；`design-doc.md` → 报告 |
| `$ur-generate-personas` | `shared_context.md`、样本量和可选配额 | `persons_summary.txt`、`persons/` → 模拟 |
| `$ur-user-simulator` | `questionnaire.md`、`persons_summary.txt`、`persons/`、可选模型配置 | `survey_responses_<run_id>.xlsx` → 报告；质量报告 → 工作流门禁 |
| `$ur-synthesize-report` | `questionnaire.md`、`design-doc.md`、指定批次的回答 Excel；可选 `persons_summary.txt` | `report_<run_id>/` |

没有列入“传给下游”的文件由所属 Skill 自己管理，不自动成为其他 Skill 的输入。

## 执行

1. 在正式任务目录中调用 `$ur-design-survey`。用户确认问卷且该 Skill 完成自身检查后继续。
2. 把 `shared_context.md` 交给 `$ur-generate-personas`。画像产物通过该 Skill 自身检查后继续。
3. 把问卷和画像清单交给 `$ur-user-simulator`。该 Skill 完成一批模拟回答后，由工作流根据质量报告决定继续、复核或重跑。
4. 从可用回答批次中明确选择一个 `run_id`，把对应 Excel 连同问卷和设计文档交给 `$ur-synthesize-report`。
5. 报告输出沿用所选回答批次的 `run_id`。任一阶段失败时停止调用下游 Skill，回到失败阶段处理。

## 交互边界

- `$ur-generate-personas` 不接收问卷、研究假设或设计结论。
- `$ur-user-simulator` 只按画像清单逐人读取画像，不把不同人物放入同一作答上下文。
- `$ur-synthesize-report` 不读取逐人画像、个人答卷或模拟器质量报告；`persons_summary.txt` 只在需要说明样本构成时传入。
- 回答目录存在多个批次时，由调用方明确选择，不自动选择最新批次，不合并不同 `run_id`。

## 返工关系

| 变化 | 重跑范围 |
|---|---|
| 问卷或研究设计变化 | 模拟 → 报告 |
| 共享上下文或画像变化 | 画像 → 模拟 → 报告 |
| 新增回答批次 | 为新 `run_id` 生成报告 |

## 完成条件

- 四个 Skill 按顺序完成，并分别通过自身检查；
- 下游 Skill 只读取跨 Skill 契约中规定的文件；
- 回答批次和报告使用同一个 `run_id`，所有产物保存在同一正式任务目录。
