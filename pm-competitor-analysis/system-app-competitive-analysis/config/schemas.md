# 共享数据结构

以下结构名在 `SKILL.md`、`references/`、`templates/` 和脚本中保持一致。结构名和字段名属于技术标识，可保留英文；解释和规则统一使用中文。

## Workflow Step Contract

主流程中的每个 Step 统一使用以下五段：

- **输入（Input）**：该步骤消费的用户输入或上一步产物。
- **执行子步骤（Sub-steps）**：按顺序执行的工作。
- **输出（Output）**：该步骤必须生成的结构化产物。
- **约束（Constraints）**：硬边界、失败处理和禁止事项。
- **Reference**：仅在该步骤需要时加载的详细规则文件。

## ResearchContext

```yaml
purpose: 功能借鉴 | 差异化竞争 | 综合分析
app: string
module: string
topic: string
specified_competitors: [string]
focus: [string]
```

地区与版本不属于用户输入的 `ResearchContext`。如证据存在地区或版本差异，应在 `ResearchUnit`、`EvidenceRecord` 和 `QuantitativeEvidence` 中记录；输出格式使用全局默认值。

## ResearchQuestion

```yaml
question: string
decision_goal: string
comparison_modes:
  - support_coverage
  - mechanism
  - effectiveness
  - positioning
```

其中 `comparison_modes` 分别代表：功能覆盖、实现机制、实际效果、竞争定位。

## CompetitorSet

```yaml
default_device: [string]
optional_device: [string]
dynamic_internet: [string]
selection_rationale:
  competitor_name: string
```

## ProductPositioning

```yaml
dimensions:
  - id: string
    label: string
values:
  competitor_name:
    dimension_id:
      statement: string
      evidence_refs: [string]
      confidence: A | B | C
      manual_confirmation: bool
```

## FeatureSchema

```yaml
user_task: string
modules:
  - module_id: string
    module_name: string
    features:
      - feature_id: string
        feature_name: string
        feature_type: functional | mechanism | experience | quantitative
        expected_value_type: status | number | text | duration | price | ratio
        research_priority: high | medium | low
```

`feature_type`：
- `functional`：功能型。
- `mechanism`：机制型。
- `experience`：体验型。
- `quantitative`：数据型。

`expected_value_type`：
- `status`：支持状态。
- `number`：数量/性能数值。
- `text`：文字机制。
- `duration`：时间/有效期。
- `price`：价格/收费。
- `ratio`：比例/准确率/使用率等。

## ResearchUnit

默认最小检索单元为“一个竞品 × 一个 Feature”。

```yaml
unit_id: string
competitor: string
app: string
module: string
topic: string
feature_id: string
feature_name: string
region: string | null
version: string | null
priority: high | medium | low
```

## EvidenceRecord

```yaml
unit_id: string
competitor: string
feature_id: string
claim: string
support_direction: supports | contradicts | neutral
source_tier: 1 | 2 | 3 | 4
source_type: string
source_title: string
source_url: string | null
publisher: string | null
published_at: string | null
observed_version: string | null
observed_region: string | null
quote_or_fact: string | null
screenshot_path_or_ref: string | null
confidence: A | B | C
manual_confirmation: bool
notes: string | null
```

`support_direction`：支持该判断 / 与该判断冲突 / 中性信息。

## QuantitativeEvidence

```yaml
competitor: string
feature_id: string
metric_name: string
metric_definition: string
value: number | string
unit: string
sample_or_test_set: string | null
region: string | null
version: string | null
measured_at: string | null
source_ref: string
comparability: comparable | partially_comparable | not_comparable
manual_confirmation: bool
```

`comparability`：可直接横向比较 / 部分可比 / 不可直接比较。

## VisualizationRawData

雷达图使用宽表评分数据：

```yaml
competitor: string
<dimension_1>: number
<dimension_2>: number
...
```

四象限/矩阵定位图使用 XY 坐标数据：

```yaml
competitor: string
x: number
y: number
bubble: number | null
x_label: string
y_label: string
manual_confirmation: bool
```
