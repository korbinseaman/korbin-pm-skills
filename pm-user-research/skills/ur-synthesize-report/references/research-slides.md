# 调研报告幻灯片：结论与后续工作输入

## 输入与底稿

使用已核对的 `research_context`、`goal_coverage`、`descriptive_results`、`themes`、`recommendations`、`limitations`；回答 Excel 是统计与引语的唯一证据。先在 `analysis_summary.json` 增加：

```json
{
  "conclusion_slides": [
    {
      "title": "一句话核心结论，直接回答研究问题",
      "research_question": "本页回答的目标问题",
      "goal_ids": ["G1"],
      "supporting_data": [
        {"question_id": "Q1", "option_label": "与原始统计完全一致的选项", "proves": "该数据证明了结论的哪一部分"},
        {"question_id": "Q2", "option_label": "另一项原始统计选项", "proves": "提供互补证据，而非重复数字"}
      ],
      "interpretation": "这些数据合起来意味着什么；不声称未经证明的因果关系",
      "product_implication": "对下一步产品工作的启示，非已验证方案",
      "counterevidence_or_limit": "反例、样本与题目口径限制"
    }
  ],
  "next_step_inputs": {
    "competitor_analysis": [
      {
        "input": "需比较的用户任务/场景及为什么要比较",
        "compare_dimensions": "拟比较的功能机制、流程或体验维度",
        "verification_question": "竞品事实尚待核实的具体问题",
        "decision_use": "结果将用于哪项产品决策",
        "question_ids": ["Q3"],
        "evidence_ids": [],
        "status": "research_finding"
      }
    ],
    "experience_design": [
      {
        "input": "有证据支持的目标用户与任务场景",
        "design_implication": "待设计的交互目标/体验原则及边界",
        "validation_question": "原型或后续研究需验证的问题",
        "question_ids": ["Q3"],
        "evidence_ids": [],
        "status": "product_hypothesis"
      }
    ]
  }
}
```

`conclusion_slides` 填写 2–3 项；`supporting_data` 每页恰有 2–3 项，`question_id` 与 `option_label` 必须能在 `descriptive_results` 精确定位。人数、比例和有效分母由底稿读取，不手填、猜测或用全样本替换题目有效分母。每项 `proves` 说明其支撑结论的哪部分；优先组合现状、对比、原因等不同角度，允许同题不同选项，但不能把同一统计拆分重复计数。数据与主张关系弱时应更换结论或补研究，不为满足数量门槛拼凑。用户原声可帮助解释，不算支撑数据；小样本、多选非互斥、选择性偏差和相反证据必须披露。

`status` 取 `research_finding`、`product_hypothesis` 或 `to_verify`。每项后续输入至少给出可回溯的 `question_ids` 或 `evidence_ids`；证据不足时不填写为已证实的输入，把缺口写入页内“待补研究”。`evidence_ids` 使用已有的原始回答证据 ID，不放姓名或可识别原话。竞品名单可以是用户指定或下一步拟查对象，不能写成已核实的竞品能力。

## 页数与版式

- 第 1–2/3 页（结论）：固定一页一个核心结论，共 2–3 页；标题就是结论，不用问卷题号或“调研结果”作标题。每页固定“结论 → 2–3 项数据证据 → 综合解释 → 产品含义/限制”，每项数据标明题号、选项、人数、百分比、有效分母、单/多选口径和 `proves`。图表只画这 2–3 项的对应统计，不能借用无关题的完整分布；不同题目的分母分别标注，不能误画成同一百分比构成。按调研目标组织，不按 Q1、Q2 顺序逐题汇报；正式目标缺失或不足两页可审定结论时报告证据缺口，停止正式幻灯片生成，不伪造目标或凑数。
- 后 2 页（工作输入）：一页为竞品分析 Brief，明确“要比较什么、为什么、核实什么、如何用于决策”；一页为体验定义 Brief，明确“谁在什么场景完成什么任务、要解决什么体验问题、通过什么原型验证”。每页最多 3 条，保留证据题号、发现/假设状态与待验证问题。
- 每页页脚标明数据来源、批次/运行 ID、图表有效分母及主要限制；合成数据注明只适合生成假设。图表使用可编辑形状与文字，避免仅截图。事实、综合判断和待验证产品假设分别标记；不把相关性写成因果，也不把产品建议写成调研事实。

## 产出与验收

按 `<YYYYMMDD><调研课题>_调研报告幻灯片.pptx` 输出至本次任务目录。合成 CLI 在完成结论底稿后生成独立 PPTX；真实 Excel 模式的适配流程也调用同一个幻灯片构建器，不把真实数据套入合成 CLI。HTML 的“调研分析结论”Tab 与浏览器 PPTX 下载使用同一组页内容。

逐页检查：结论页数 2–3、一页恰有一个核心结论且有 2–3 项不同的直接支撑数据；每项能准确说明 `proves`，并与原始 Excel 和底稿对应。研究目标被回答或标为缺口；竞品页没有虚构的竞品事实；体验页没有未经验证的解决方案承诺；题号、频数、百分比和分母与底稿一致；来源和限制可见；独立 PPTX、HTML 与浏览器下载内容一致且文件能打开。缺少输入时停止正式交付并说明待补项，不填充套话充数。
