---
name: pm-system-app-competitor-matrix
description: 面向手机系统 APP 与系统级功能的竞品矩阵分析 Skill。输入具体系统 APP、功能模块和调研主题后，基于证据完成产品定位、Feature 矩阵、竞品机制与界面明细、定量数据、可编辑竞品定位图，以及默认从 HarmonyOS 产品经理视角输出差异判断与后续发力方向。适用于图库/照片、云图库、文件管理、相机、备忘录、日历、浏览器、电话、短信、AI 助手、系统搜索、分享、备份、跨设备协同等系统软件课题。
---

# PM System APP Competitor Matrix

本 Skill 用于回答如下类型的产品经理问题：

> 针对一个具体的 **手机系统 APP + 功能模块 + 调研主题**，主流竞品分别怎么做、哪些能力可以借鉴、真正的差异在哪里、HarmonyOS 与竞品相比处于什么位置、下一步应该重点发力什么？

本 Skill 坚持 **证据优先（Evidence-first）**。任何没有被严格论证的结论，不得以确定事实呈现。

## 1. 适用范围与触发条件

当用户希望对手机操作系统中的系统 APP、系统服务或与其高度相关的功能进行结构化竞品分析时触发本 Skill。

典型对象包括：图库/照片、云图库、相机、文件管理、备忘录、日历、浏览器、电话、短信、AI 助手、系统搜索、系统分享、备份、跨设备协同、系统级 AI 能力等。

如果用户只是在做纯硬件参数对比、泛公司战略分析或单纯市场份额分析，且与系统 APP 具体功能课题无直接关系，则不应使用本 Skill。

## 2. 用户输入

将用户输入解析为 `ResearchContext`，结构见 `config/schemas.md`。

推荐输入顺序：

1. `purpose`（可选）：功能借鉴 / 差异化竞争 / 综合分析
2. `app`（必填）：系统 APP
3. `module`（必填）：功能模块
4. `topic`（必填）：调研主题
5. `specified_competitors`（可选）：用户指定竞品
6. `focus`（可选）：特别关注项

所有默认值统一读取 `config/constants.yaml`，主 Skill 不重复定义全局常量。

## 3. 核心工作流（Core Workflow）

每个主流程 Step 必须严格使用统一结构：**输入 → 执行子步骤 → 输出 → 约束 → Reference**。

### Step 1. 解析调研请求

**输入**
- 用户原始请求。

**执行子步骤**
1. 提取目的、系统 APP、功能模块、调研主题、指定竞品和特别关注项。
2. 对同义产品名、APP 名进行标准化，但不得改变用户原意。
3. 仅在 `config/constants.yaml` 允许的范围内应用默认值。

**输出**
- `ResearchContext`。

**约束**
- 不得无必要扩大用户原始调研范围。
- 不得臆造用户未指定的竞品或特别关注项。
- 地区、版本和输出格式不作为 `ResearchContext` 的用户输入字段；地区与版本仅在研究过程中作为证据属性记录，输出使用全局配置中的默认格式。

**参考文件（Reference）**
- `config/constants.yaml`
- `config/schemas.md`
- `templates/input-template.md`

### Step 2. 定义 Research Question

**输入**
- `ResearchContext`。

**执行子步骤**
1. 将用户调研主题转换为一个清晰、可支撑产品决策的核心 Research Question。
2. 判断本次重点要回答的是：是否支持、如何实现、实际效果、竞争定位，或上述组合。
3. 定义最终分析需要支撑的 `DecisionGoal`。

**输出**
- `ResearchQuestion`。
- `DecisionGoal`。

**约束**
- Research Question 必须直接对应用户指定的 APP / 模块 / 主题。
- 不得把一个窄课题扩展成整个 APP 的全量审计。

**参考文件（Reference）**
- `references/feature-decomposition.md`

### Step 3. 构建竞品集合

**输入**
- `ResearchContext`。
- `ResearchQuestion`。

**执行子步骤**
1. 加入全局配置中的默认手机厂商竞品。
2. 可选手机厂商竞品仅在用户明确指定时加入，除非后续全局常量另有调整。
3. 根据具体 APP、功能模块和调研主题，判断是否需要补充 2–3 个高度相关的头部互联网/专业产品。
4. 对每个动态增加的竞品记录纳入理由。

**输出**
- `CompetitorSet`。

**约束**
- 不得为了凑数量加入弱相关互联网产品。
- 竞品选择优先考虑研究价值，而不是品牌名单完整性。
- 最终矩阵必须保持可读性。

**参考文件（Reference）**
- `references/competitor-selection.md`
- `config/constants.yaml`

### Step 4. 构建 Feature Schema

**输入**
- `ResearchContext`。
- `ResearchQuestion`。
- `DecisionGoal`。

**执行子步骤**
1. 识别核心用户任务。
2. 按四层结构拆解：`User Task → Module → Feature → Feature Status`。
3. 必要时将 Feature 标记为功能型、机制型、体验型或数据型。
4. 合并重复项，移除与 Research Question 弱相关的维度。
5. 为每个 Feature 定义预期输出值类型，如状态、数字、时长、价格、文字机制等。

**输出**
- `FeatureSchema`。

**约束**
- Feature 必须由当前 APP、模块和课题动态生成。
- 禁止机械套用固定 Feature 清单。
- 复杂机制不得为了形成勾勾表而强行二值化为 ✓/×。
- 一个 Feature 尽量只承载一个可横向比较的判断。

**参考文件（Reference）**
- `references/feature-decomposition.md`

### Step 5. Research Evidence

**输入**
- `CompetitorSet`。
- `FeatureSchema`。
- `ResearchContext`。
- `ResearchQuestion`。

**执行子步骤**
1. 按全局配置的最小检索单元生成 Research Units。
2. 为每个检索单元生成 Query Set，覆盖官方术语、用户任务表达、界面/截图证据，以及必要的反向验证和冲突验证。
3. 同步检索与课题直接相关的官方产品定义、产品角色、演进方向和差异化依据；此阶段只记录证据，不提前形成产品定位结论。
4. 优先检索高优先级来源；仅在证据不足、版本不明或存在冲突时逐级扩展来源。
5. 对高优先级 Feature 尽可能获取真实竞品应用界面截图。
6. 将原始证据归一化、去重、冲突检测并赋予置信等级。
7. 当 Research Units 数量达到全局并行阈值或任务规模明显较大时，可使用 `scripts/research/` 的并行检索辅助流程提升效率。

**输出**
- `EvidenceRecords[]`。

**约束**
- “没有搜到”绝不等于“不支持”。
- 禁止生成、复刻、重绘竞品 UI 后将其作为真实证据。
- 必须遵守 `references/research-evidence.md` 定义的来源优先级、检索边界和停止条件。
- 证据不足或冲突未解决时，必须使用全局“请人工确认”标记。
- Research Evidence 完成前不得输出产品定位、竞品优势或差异化结论。

**参考文件（Reference）**
- `references/research-evidence.md`
- `scripts/research/`
- `config/constants.yaml`

### Step 6. 收集定量证据

**输入**
- `ResearchQuestion`。
- `FeatureSchema`。
- `EvidenceRecords[]`。

**执行子步骤**
1. 判断定量数据是否能够显著增强本课题的可信度和说服力。
2. 根据课题搜索相关指标，例如准确率/召回率、模板/资源数量、功能使用率、渗透率、响应时延、成功率、用户规模、价格/免费额度等。
3. 记录指标定义、时间、地区、版本、样本/测试条件、单位和来源。
4. 判断不同竞品之间的数据是否真正可比。

**输出**
- `QuantitativeEvidence[]`。

**约束**
- 没有可靠数据时不得为了填表而编造数据。
- 口径不可比的数据不得强行排名。
- 估算值、口径不一致数据或弱证据数据必须标注“请人工确认”。

**参考文件（Reference）**
- `references/quantitative-evidence.md`

### Step 7. 分析产品定位

**输入**
- `CompetitorSet`。
- `ResearchQuestion`。
- `EvidenceRecords[]`。
- `QuantitativeEvidence[]`。

**执行子步骤**
1. 基于已归一化的证据，识别与本课题直接相关的产品定义/产品角色。
2. 基于已归一化的证据，识别与本课题相关的产品演进思路/战略方向。
3. 基于已归一化的证据，识别与本课题相关的核心竞争力/差异化能力。
4. 从上述内容中选择不超过全局配置上限的定位维度。
5. 为每条定位判断绑定 `evidence_refs`、置信等级和人工确认状态。

**输出**
- `ProductPositioning`。

**约束**
- 禁止在 Research Evidence 和定量证据收集完成前推测或预设产品定位。
- 禁止使用“创新、体验好、功能丰富”等泛化品牌评价替代真正的产品定位。
- 产品定位必须能够解释已发现的 Feature、机制、体验或定量差异。
- 没有充分证据支撑的判断不得作为确定性定位；如仍有分析价值，必须标记“请人工确认”。

**参考文件（Reference）**
- `references/output-spec.md`
- `references/research-evidence.md`
- `references/quantitative-evidence.md`

### Step 8. 判定 Feature 状态并生成两张核心表

**输入**
- `ProductPositioning`。
- `FeatureSchema`。
- `EvidenceRecords[]`。
- `QuantitativeEvidence[]`。

**执行子步骤**
1. 根据证据为每个“竞品 × Feature”判定结果，可使用全局状态符号，也可在复杂场景下使用简短文字或数值。
2. 生成 Output 1：结论型标题、两句话关键结论、产品定位、Feature Matrix、优势场景、不足。
3. 生成 Output 2：详细机制、真实 UI 证据、入口/流程、定量证据、限制条件、关键差异和证据状态。

**输出**
- `Table1`。
- `Table2`。

**约束**
- 表 1 必须易于快速扫读，复杂机制放到表 2 展开。
- 比 `✓/×` 更准确时，可直接填写“30 天”“仅云端”“仅会员”等文字。
- “优势场景”和“不足”没有可靠结论时可以留空。
- 必须保留证据层传递下来的“请人工确认”标记。

**参考文件（Reference）**
- `references/output-spec.md`
- `templates/table-1-feature-matrix.md`
- `templates/table-2-detail-analysis.md`

### Step 9. 生成竞品高层定位可视化

**输入**
- `Table1`。
- `Table2`。
- `QuantitativeEvidence[]`。

**执行子步骤**
1. 根据课题动态选择 4–6 个大颗粒评分维度。
2. 使用全局评分范围对重点竞品打分，并记录每个分数的评分依据。
3. 从雷达图、四象限图、矩阵定位图中选择最适合的一种作为首版图；只有确有价值时才增加其他图。
4. 输出首版图表图片。
5. 同时输出可编辑的原始评分/坐标数据表。
6. 提供并使用图表重生成脚本，支持用户修改数据后通过快捷指令重新生成雷达图、四象限图、矩阵定位图或全部图表。

**输出**
- `Visualization`。
- `VisualizationRawData`。
- `ScoringRationale`。
- `RegenerationCommand`。

**约束**
- 所有评分必须能够追溯到前面的 Feature、机制、界面或数据证据。
- 低置信评分必须标注“请人工确认”。
- 避免在单张雷达图中堆叠过多竞品。
- 用户只修改原始数据即可重新生成图表，不应要求重新执行整套 Research。

**参考文件（Reference）**
- `references/scoring-framework.md`
- `templates/visualization-data.md`
- `scripts/charts/`

### Step 10. 生成竞品结论与 HarmonyOS 发力方向

**输入**
- `Table1`。
- `Table2`。
- `Visualization`。
- `ResearchContext.purpose`。

**执行子步骤**
1. 总结行业共识/行业 Baseline。
2. 总结主要竞品路线与核心差异。
3. 识别标杆能力与行业空白。
4. 使用全局战略判断标签评估 HarmonyOS 所处位置。
5. 在有证据支撑时，分别给出短期补齐、中期强化和长期差异化方向。
6. 根据用户目的调整建议重心：功能借鉴更关注成熟方案与最佳实践；差异化竞争更关注行业空白、竞争壁垒和可形成独特价值的方向。

**输出**
- `CompetitiveSummary`。
- `HarmonyOSGap`。
- `RecommendedDirections`。

**约束**
- 每条战略建议必须可追溯到前文证据，或明确标识为分析判断。
- 不得因为竞品支持某项能力就默认建议 HarmonyOS 跟进。
- 必须区分行业基础能力、竞品优势能力和推测性机会。

**参考文件（Reference）**
- `references/harmonyos-perspective.md`
- `references/output-spec.md`

## 4. 关键硬规则

1. **先证据，后结论。** 证据缺失时，不得静默转化为事实性“×”。
2. **严格执行人工确认机制。** 任何未被充分论证的判断，必须使用全局配置中的“请人工确认”标记。
3. **Feature 动态拆解。** 分析维度必须由当前 APP、模块和调研主题决定，模板只提供结构，不替代分析。
4. **只使用真实 UI 证据。** 禁止生成或复刻竞品界面并作为截图证据。
5. **先检查数据可比性，再做定量结论。** 指标定义、样本、版本、地区或测试条件不同的数据不得直接排名。
6. **结论必须区分研究目的。** 功能借鉴与差异化竞争必须体现不同的建议重心。
7. **默认 HarmonyOS 视角。** 用户未指定其他目标产品时，战略结论使用全局配置中的目标产品视角。

## 5. 输出定义

Markdown 与 Word 两种格式必须保持相同的信息结构，共包含四类逻辑输出：

1. **Output 1 — 产品定位 + Feature Matrix**
   - 一句能够概览整体结果的结论型标题。
   - 恰好两句话关键结论。
   - 产品定位，行数不超过全局配置上限。
   - Feature Matrix。
   - 各竞品优势场景。
   - 各竞品不足。

2. **Output 2 — 竞品机制与证据明细**
   - Feature / 机制具体实现。
   - 能获取到可靠证据时，提供真实竞品应用界面截图。
   - 功能入口 / 交互流程。
   - 有价值且可靠时，加入定量数据。
   - 限制条件、关键差异、证据状态。

3. **Output 3 — 竞品高层定位可视化**
   - 首版图表图片。
   - 可编辑原始数据表。
   - 评分依据。
   - 支持雷达图、四象限图、矩阵定位图或全部图表的重生成脚本/命令。

4. **Output 4 — 竞品差异结论与 HarmonyOS 方向**
   - 行业共识。
   - 竞品差异。
   - 标杆能力。
   - 行业空白。
   - HarmonyOS 所处位置与 Gap。
   - 后续优先发力方向。

## 6. Reference 索引

按当前 Step 按需读取对应文件，避免一次性加载全部 reference。

- 全局常量：`config/constants.yaml`
- 共享数据结构：`config/schemas.md`
- 竞品选择：`references/competitor-selection.md`
- Feature 拆解：`references/feature-decomposition.md`
- 证据检索：`references/research-evidence.md`
- 定量证据：`references/quantitative-evidence.md`
- 评分与可视化：`references/scoring-framework.md`
- 输出规范：`references/output-spec.md`
- HarmonyOS 视角：`references/harmonyos-perspective.md`
- 输出模板：`templates/`
- Research 辅助脚本：`scripts/research/`
- 图表重生成脚本：`scripts/charts/`
