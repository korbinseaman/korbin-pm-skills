# Research Evidence 证据检索规范

本文件是本 Skill 的核心 Reference。它定义 **查什么、怎么查、查到什么程度、什么证据可以支撑结论、什么时候必须停、什么时候必须标注“请人工确认”**。

所有全局常量、来源等级、人工确认文本、并行阈值等统一读取 `config/constants.yaml`，本文件不重复定义固定值。

## 1. 检索目标

Research Evidence 的目标不是“尽可能多搜资料”，而是围绕 `FeatureSchema` 为每个关键判断建立足够可信、可追溯的证据链。

证据检索必须服务于以下问题：

- 该竞品是否支持该 Feature？
- 如果支持，具体怎么实现？
- 用户从哪里进入、如何操作、能看到什么反馈？
- 是否存在版本、地区、账号、设备、会员等限制？
- 是否有真实界面截图或视频关键帧能直接证明？
- 是否存在能够增强说服力的定量数据？
- 不同来源是否存在冲突？

## 2. Research Scope：检索边界

`FeatureSchema` 是证据检索的主要边界。

### 必须控制的范围

- 只围绕当前 APP / Module / Topic / Feature 检索。
- 不得因为发现相关能力就无限扩展到整个产品。
- 区分当前版本与历史版本。
- 区分中国大陆版、海外版或其他区域差异。
- 区分正式发布能力、灰度能力、Beta/测试能力和概念演示。
- 区分系统 APP 自身能力与依赖其他 APP、网页端、账号后台或云服务实现的能力。
- 区分“官方宣称支持”和“用户实机观察到的实际行为”。

### 允许扩展检索的情况

只有以下情况可以短暂超出单个 Feature：

1. 需要理解一个底层机制才能判断当前 Feature。
2. 需要查找历史版本确认能力演进。
3. 需要验证地区/机型/账号差异。
4. 需要寻找行业标杆或可量化 Benchmark。
5. 用户目的为差异化竞争，需要确认某能力是否属于行业空白。

扩展检索完成后必须回到当前 Research Question，不得变成泛化行业研究。

## 3. Research Unit：最小检索单元

默认最小检索单元读取全局配置，通常为：

`Competitor × Feature`

例如：

- Apple × 是否支持按同步状态筛选
- Huawei × 是否支持按同步状态筛选
- Xiaomi × 是否支持按同步状态筛选

如果一个 Feature 内部包含无法拆开的复杂机制，可以在同一 Research Unit 内追加机制子问题，但不得因此改变 Feature Matrix 的结构。

### Research Unit 应携带的上下文

至少包括：

- competitor
- app
- module
- topic
- feature_id / feature_name
- region
- version
- priority

结构见 `config/schemas.md`。

## 4. 来源优先级

### Tier 1 — 官方一手资料

优先级最高，包括：

- 官方产品官网；
- 官方帮助文档 / Support；
- 官方用户指南；
- 官方技术文档；
- 官方开发者文档；
- 官方产品规格或正式公告。

适合证明：正式功能定义、限制条件、支持范围、版本、价格、规格等。

### Tier 2 — 官方演示与官方内容

包括：

- 官方发布会；
- 官方产品演示视频；
- 官方公众号；
- 官方社区公告；
- 官方应用商店页面与截图；
- 官方培训/教学材料。

适合证明：界面入口、交互流程、功能演示、产品定位和演进方向。

### Tier 3 — 高质量第三方实测

包括：

- 权威科技媒体；
- 专业评测机构；
- 高质量实机评测视频；
- 明确展示当前版本界面的实测文章或视频；
- 透明方法论的第三方 Benchmark。

适合补充：官方未写明的实际行为、操作路径、性能、限制和当前界面。

### Tier 4 — 用户与社区证据

包括：

- Reddit；
- 小红书；
- 微博；
- B站普通用户内容；
- 论坛/社区帖子；
- 用户评论与吐槽。

适合发现：边缘场景、真实问题、官方文档未覆盖的异常行为和用户认知。

Tier 4 通常不能单独支撑高可信事实结论。若只能依赖 Tier 4，应按人工确认规则处理。

## 5. Query Strategy：查询策略

每个重要 Research Unit 不应只执行单一关键词检索。根据需要组合以下 Query 类型。

### 5.1 官方术语 Query

目标：直接找到产品官方定义。

结构示例：

`竞品 + APP + Feature + official/support/user guide + 地区/版本`

例如：

`Apple Photos filter sync status official support`

如果已知官方域名，可进一步使用站点限定；如果官方域名未知，先发现官方来源，不要预设错误域名。

### 5.2 用户任务 Query

目标：避免因为官方功能命名不同而漏搜。

将 Feature 转换成用户真正想完成的动作，例如：

`Apple Photos how to find unsynced photos`

`Huawei Gallery filter cloud photos`

### 5.3 同义词/机制 Query

对同一概念使用不同表达，例如：

- synced / uploaded / backed up / cloud status；
- deleted / removed / trash / recently deleted；
- audit log / activity / history / operation record。

当中文与英文市场资料都可能存在时，必要时同时检索中英文关键词。

### 5.4 UI / Screenshot Query

目标：找到能够证明入口、界面状态和交互链路的真实 UI。

例如：

`Apple Photos filter menu screenshot`

`Huawei Gallery sync status filter UI`

`Xiaomi Gallery demo video filter`

### 5.5 反向验证 Query

当初步结论倾向于“不支持”、存在限制或官方资料未提及时必须使用。

例如：

`Apple Photos cannot filter unsynced photos`

`Apple Photos sync status filter not supported`

反向搜索用于减少“因为没找到就判定不支持”的错误。

### 5.6 冲突验证 Query

当两个来源结论不一致时，进一步组合：

- 产品名 + Feature + 当前版本；
- 产品名 + Feature + 地区；
- 产品名 + Feature + 旧版本/新版本；
- 产品名 + Feature + 具体机型或账号条件。

### 5.7 定量数据 Query

当课题适合数据支撑时追加：

`benchmark / accuracy / precision / recall / latency / usage rate / adoption / template count / price / quota`

具体定量规则见 `references/quantitative-evidence.md`。

## 6. 多阶段 Research 策略

默认采用逐步升级方式，避免每个 Research Unit 都执行高成本深搜。

### Pass 1 — 快速确认

目标：优先回答“是否支持/核心值是什么”。

动作：

1. 优先搜索 Tier 1。
2. 如果 Tier 1 直接且当前版本匹配，可形成高可信事实结论。
3. 如果官方资料没有覆盖，再进入 Pass 2 或 Pass 3。

### Pass 2 — 实现机制与界面证据

主要用于重点 Feature，继续查找：

- 功能入口；
- 操作流程；
- 关键文案和反馈状态；
- 真实 UI 截图；
- 限制条件；
- 与其他竞品有意义的机制差异。

### Pass 3 — 交叉验证 / 冲突消解

以下情况触发：

- 主要证据来自非官方来源；
- 当前版本与历史版本行为不确定；
- 初步判断倾向“不支持”；
- 不同来源相互冲突；
- 怀疑存在地区、账号、机型或系统版本差异。

每个 Research Unit 的最大 Pass 次数统一读取全局常量。

## 7. “不支持”的证明标准

这是硬边界：

> **搜索失败本身永远不能证明“不支持”。**

只有满足以下至少一项，才可以使用全局“不支持”状态：

1. 官方文档明确写明不支持、限制或不可用。
2. 当前且匹配版本/地区的官方完整能力定义能够合理排除该能力。
3. 多个独立、当前版本的高质量实机来源一致验证该能力不存在。
4. 已有明确的技术/产品限制，使指定场景下不可能支持。

如果以上条件均不满足，应使用全局“未知”状态，并附“请人工确认”。

## 8. Screenshot Acquisition：界面截图获取

对于高优先级 Feature，应尽可能获取真实 UI 证据，优先级如下：

1. 官方帮助文档截图；
2. 官方产品页截图；
3. 官方演示/发布会关键帧；
4. 官方应用商店截图；
5. 权威实机评测/视频关键帧；
6. 用户社区截图/视频关键帧。

### 截图选择原则

- 截图必须能够证明当前 Feature，而不是随便放一张 APP 首页。
- 一张图不能解释完整流程时，可以使用 1–3 张关键帧。
- 优先包含入口、关键设置、结果状态、重要文案。
- 可做不改变含义的裁剪以聚焦 Feature，但不得修改界面内容。

### 截图记录信息

尽量记录：

- 来源；
- 产品/系统版本；
- 地区；
- 发布时间或截图获取日期；
- 该截图具体证明什么。

如果没有可靠界面截图，使用全局配置中的兜底文本。

**禁止生成、复刻、重绘、推断竞品 UI 后将其当成真实竞品截图。**

## 9. Confidence 与人工确认

置信等级统一读取 `config/constants.yaml`。

典型判断方式：

- **A**：当前版本匹配的官方一手证据；或多个强独立来源一致且无实质冲突。
- **B**：单一可靠非一手来源、当前实机证据，或基于强事实形成的分析判断。
- **C**：仅社区证据、间接推断、版本部分不匹配或仍存在明显不确定性。

是否必须展示“请人工确认”统一服从全局配置，不在本文件重复定义文本。

## 10. 冲突处理

当来源冲突时，按以下顺序处理：

1. 先检查发布时间与系统/应用版本。
2. 检查地区、账号、设备型号、会员状态等条件差异。
3. 对“官方定义的正式能力”，优先当前版本官方一手资料。
4. 对“实际观察行为”，即使官方没有写，也要保留可信实机证据，不能简单丢弃。
5. 如果冲突仍无法消解，不得强行合并成一个确定事实；使用全局冲突标记，并在表 2 说明不同证据分别是什么。

## 11. 停止条件

一个 Research Unit 满足以下任一条件即可停止继续检索：

### Condition A

找到一个与版本/地区匹配的 Tier 1 来源，能够直接、清楚地解决当前事实判断或数值。

### Condition B

找到两个相互独立的 Tier 2/3 来源，结论一致，且不存在更强的相反证据。

### Condition C

已经执行完全局配置允许的最大检索 Pass，仍没有可靠证据。

处理：`未知 + 请人工确认`。

### Condition D

经过版本、地区、设备等维度的冲突排查后仍不能消解。

处理：使用全局冲突标记 + 人工确认，并在表 2 保留冲突详情。

当判断已经足够明确时，不要为了“搜得更多”无限继续检索。

## 12. 并行执行边界

Research Unit 之间通常高度独立，因此大规模任务适合并行。

当 Research Unit 数量达到 `config/constants.yaml` 的并行阈值，或任务明显属于大规模矩阵检索时，可启用并行辅助流程。

推荐流水线：

`FeatureSchema → ResearchUnits → QuerySets → 并行检索 → RawEvidence → 归一化 → 去重/合并 → 冲突检测 → EvidenceRecords`

### 脚本可以做什么

- 生成 Research Units；
- 生成 Query Sets；
- 批量分组与并发调度；
- 调用用户或运行环境提供的搜索 Worker；
- 将返回结果归一化为统一 JSON；
- 去重、聚合同一 Feature 的多个证据；
- 标出冲突、缺失 Research Unit 和待人工确认项。

### 脚本不得假设什么

- 不得强绑定某一家专有搜索供应商；
- 不得内置 API Key；
- 不得把“无搜索结果”解释为“不支持”；
- 不得认为一个 URL 本身就足以证明某个 Claim；
- 不得替代主 Agent 对最终来源质量和 Claim 的判断。

## 13. Research Scripts

- `scripts/research/query_builder.py`：根据 Research Unit 生成确定性的多类型 Query Set。
- `scripts/research/parallel_research.py`：与供应商无关的任务分批/并发 Worker 调度器。
- `scripts/research/evidence_normalizer.py`：把原始 JSONL 归一化成 `EvidenceRecord`。
- `scripts/research/merge_evidence.py`：去重、按 Unit 聚合、检查冲突和缺失。

脚本的目标是减少重复编排和提升大规模检索效率，**不是绕过证据判断**。
