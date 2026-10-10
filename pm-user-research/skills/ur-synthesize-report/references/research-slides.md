# 调研报告幻灯片：结论与后续工作输入

## 输入与底稿

使用已核对的 `research_context`、`goal_coverage`、`descriptive_results`、`themes`、`recommendations`、`limitations`；回答 Excel 是统计与引语的唯一证据。先在 `analysis_summary.json` 增加：

```json
{
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

`status` 取 `research_finding`、`product_hypothesis` 或 `to_verify`。每项至少给出可回溯的 `question_ids` 或 `evidence_ids`；证据不足时不填写为已证实的输入，把缺口写入页内“待补研究”。`evidence_ids` 使用已有的原始回答证据 ID，不放姓名或可识别原话。竞品名单可以是用户指定或下一步拟查对象，不能写成已核实的竞品能力。

## 页数与版式

- 第 1–2 页（结论）：每页最多 3 条目标对应结论。目标超过 3 个时分两页；超出 6 个时按决策相关性合并表达但保持目标映射。每条包括研究问题、直接答案、题号和关键数据 `n/N`、反例或限制；有匹配题目才放其图表，不能借用无关题的百分比。缺少正式目标时标注“探索性发现”，不得伪造目标。
- 后 2 页（工作输入）：一页为竞品分析 Brief，明确“要比较什么、为什么、核实什么、如何用于决策”；一页为体验定义 Brief，明确“谁在什么场景完成什么任务、要解决什么体验问题、通过什么原型验证”。每页最多 3 条，保留证据题号、发现/假设状态与待验证问题。
- 每页页脚标明数据来源、批次/运行 ID、图表有效分母及主要限制；合成数据注明只适合生成假设。图表使用可编辑形状与文字，避免仅截图。

## 产出与验收

按 `<YYYYMMDD><调研课题>_调研报告幻灯片.pptx` 输出至本次任务目录。合成 CLI 在完成结论底稿后生成独立 PPTX；真实 Excel 模式的适配流程也调用同一个幻灯片构建器，不把真实数据套入合成 CLI。HTML 的“调研分析结论”Tab 与浏览器 PPTX 下载使用同一组页内容。

逐页检查：研究目标被回答或标为缺口；竞品页没有虚构的竞品事实；体验页没有未经验证的解决方案承诺；题号、频数、百分比和分母与底稿一致；来源和限制可见；独立 PPTX 与 HTML 内容一致且文件能打开。缺少输入时显示待补项，不填充套话充数。
