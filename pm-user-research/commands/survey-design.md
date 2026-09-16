# 工作流：调查问卷设计

## 目标

调用 `$ur-design-survey` 完成调研课题梳理、问卷设计和质量检查，产出可直接配置的调查问卷。

本工作流只负责调用和停止条件；具体设计方法、题目规则、确认过程和质量标准均以该 Skill 的 `SKILL.md` 为准。

## 调用关系

```text
用户需求
    ↓
ur-design-survey
    ↓
问卷设计交付
```

## 输入

把用户提供的调研课题、调研目标和问卷场景完整交给 `$ur-design-survey`；问卷场景必须是原始需求洞察、关键假设验证、产品方案选择或满意度调查之一。目标用户、产品背景、题量、材料及其他约束按需附加；必填项缺失时由该 Skill 在 Step 1 要求补充。

## 任务目录

使用 `$ur-design-survey` 规定的默认目录：

```text
<WORK_DIR>/用户调研/<YYYYMMDD><课题>/
```

## 执行

1. 调用 `$ur-design-survey`，传入用户需求和已有材料。
2. 按该 Skill 的交互要求完成研究设计确认和必要修改。
3. 等待该 Skill 生成并检查全部问卷设计文件。
4. 向用户交付结果并停止工作流。

## 输出

直接交付 `$ur-design-survey` 生成的文件：

- `questionnaire.md`
- `survey-design-desc.html`
- `questionnaire_for_simulator.md`
- `questionnaire_for_userclub.txt`
- `questionnaire_for_wenjuanxing.txt`

## 工作流边界

- 不调用其他三个原子 Skill。
- 不生成用户画像，不模拟填写问卷，不分析回答数据，不输出调研报告。
- 用户确认问卷后即完成；如用户要求继续开展合成问卷调研，另行调用 `commands/synthetic-survey.md`。

## 完成条件

- `$ur-design-survey` 已通过自身检查；
- 五份问卷设计文件已保存到同一任务目录；
- 已向用户说明题量、最长答题路径、预计时长、质量结果和剩余限制。
