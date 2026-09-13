# pm-system-app-competitor-matrix

用于手机系统 APP 与系统级功能竞品分析的产品经理 Skill。

## 能输出什么

1. 产品定位 + Feature Matrix。
2. 带真实 UI 证据、机制说明和可选定量数据的竞品明细表。
3. 可编辑的竞品定位可视化，包括首版图片、原始数据和重生成脚本。
4. 竞品差异总结，以及默认从 HarmonyOS 产品经理视角给出的后续产品方向。

## 核心架构

- **瘦主 Skill**：`SKILL.md` 负责流程合同与关键硬规则。
- **Reference 负责判断逻辑**：竞品选择、Feature 拆解、证据检索、定量可比性、评分、战略判断等。
- **Config 负责全局常量**：默认竞品、状态符号、置信等级、数量上限、默认目标产品等。
- **Scripts 负责可重复/高成本执行**：Research 任务拆分、并行调度、证据归一化和图表重生成。
- **Templates 负责输出结构**。

## 安装

将整个目录复制到 Skill 目录中，并保持内部相对路径不变。运行时先加载 `SKILL.md`，再根据各 Workflow Step 按需读取对应 reference。

## 快速输入示例

```text
目的：差异化竞争
系统 APP：图库
功能模块：照片筛选
调研主题：云同步状态与存储位置筛选
指定竞品：
特别关注：多条件组合、状态反馈
```

## 图表重新生成

图表脚本支持雷达图用宽表 CSV，以及四象限图/矩阵定位图用 XY CSV。

```bash
python scripts/charts/generate_charts.py --input visualization_scores.csv --type radar --output-dir out
python scripts/charts/generate_charts.py --input visualization_xy.csv --type quadrant --output-dir out
python scripts/charts/generate_charts.py --input visualization_xy.csv --type matrix --output-dir out
python scripts/charts/generate_charts.py --input visualization_scores.csv --xy-input visualization_xy.csv --type all --output-dir out
```

数据结构见 `templates/visualization-data.md`。

## Research 辅助脚本

Research 辅助脚本不绑定具体检索供应商。在 `plan` 模式下，它负责生成 Query Set 和并行任务计划；如果运行环境提供外部搜索 Worker，可通过 `--worker-command` 接入。

```bash
python scripts/research/parallel_research.py \
  --input research_units.jsonl \
  --mode plan \
  --output research_plan.jsonl
```

脚本不会内置任何搜索厂商 API Key，也不会把“没有结果”判定为“不支持”。
