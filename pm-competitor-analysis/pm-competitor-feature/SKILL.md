---
name: competitor-app-feature-compare
description: "产品经理对系统 App 特定功能的竞品横向对比分析。支持精细到 L4 级别的功能规格对比，覆盖体验、设计思路、UX 菜单层级、文案、规格逻辑等多维度。信息来源以官方文档和官方营销材料为主。触发条件：用户提供功能场景描述（如「图库相册自定义排序」「设置存储数据清理」）。"
---

# 竞品 App 特性对比

产品经理对手机系统 App 特定功能的横向竞品对比分析。比拼的是**功能规格的精细度**（L4 级别），而非周报级的动态追踪。

## 适用场景

用户描述一个具体的手机系统 App 功能需求，例如：

- 「对比华为鸿蒙桌面卡片的形态与 iOS、小米、OPPO、vivo、荣耀的区别」
- 「图库 App 中相册自定义排序功能，各厂商怎么做的」
- 「设置存储中用户数据清理功能，各厂商的交互流程差异」
- 「系统相册的人像分类/面孔识别功能，入口层级和准确率对比」
- 「通知管理中的专注模式，各厂商的 UX 层级和可配置项对比」

**不适用于**：营销类文案生成、动态周报追踪、非系统 App 的竞品分析。

## 竞品范围

| # | 厂商 | 系统 | 备注 |
|---|------|------|------|
| 1 | Apple | iOS / iPadOS | 官方文档最完整，优先 developer.apple.com |
| 2 | Google | Android（原生/Pixel） | 作为 Android 基线参考 |
| 3 | 华为 | HarmonyOS / HarmonyOS NEXT | 中文官方文档为主 |
| 4 | 小米 | HyperOS | Xiaomi 官方社区/开发者文档 |
| 5 | OPPO | ColorOS | OPPO 官方开发者平台 |
| 6 | VIVO | OriginOS | VIVO 官方文档 |
| 7 | 荣耀 | MagicOS | 荣耀开发者文档 |
| 8 | 三星 | One UI | Samsung Developers |

> 用户可指定覆盖子集，默认全 8 家。

## 对比维度框架

每个竞品从以下 **6 个维度** 展开分析：

1. **规格逻辑** — 功能的核心机制：支持什么格式、数量上限、可配置项、触发条件、边界情况
2. **UX 菜单层级** — 功能入口路径（精确到几级菜单）、交互步骤数、操作反馈
3. **设计思路** — 该功能的设计哲学/定位差异，为什么这么做而不是那样做
4. **交互体验** — 关键交互细节：动画、手势、触控区域、加载策略、空状态/异常态处理
5. **文案** — 功能名称、操作按钮文案、提示文案、系统级 vs 第三方用语风格
6. **规格参数** — 支持数量、尺寸限制、格式要求、性能指标、兼容性约束

## 信息源优先级

获取信息时严格按以下优先级，**优先使用官方渠道**：

**第一优先级 — 官方开发文档：**
- Apple: https://developer.apple.com/documentation/
- Google: https://developer.android.com/docs
- 华为: https://developer.huawei.com/consumer/cn/doc/
- 小米: https://dev.mi.com/document/
- OPPO: https://open.oppomobile.com/
- VIVO: https://dev.vivo.com.cn/document
- 荣耀: https://developer.hihonor.com/
- 三星: https://developer.samsung.com/

**第二优先级 — 官方营销/UX 设计资源：**
- Apple: Human Interface Guidelines (https://developer.apple.com/design/human-interface-guidelines/)
- Google: Material Design Guidelines (https://m3.material.io/)
- 华为: HarmonyOS Design (https://developer.harmonyos.com/cn/design/)
- 各厂商发布会 Keynote、功能宣传页
- 各厂商官方社区（花粉俱乐部、小米社区等）

**第三优先级 — 权威科技媒体/评测：**
- 数字产品评测（重点关注功能交互拆解类的深度文章）
- 9to5Mac / 9to5Google / Android Authority 等

**第四优先级 — 社交平台实测/截图：**
- 微博、小红书、B站、YouTube 的实际操作截图/录屏

> ⚠️ **规则**：所有信息来源必须附上 URL 链接。如果信息来自多步推断（如从截图反推交互流程），必须在文中标注推断过程和证据链。

## 研究流程

### 步骤 0：澄清功能场景

确认用户需求，记录：
- `{app_name}` — 目标应用（如图库、设置、桌面、通知中心等）
- `{feature_name}` — 目标功能（如相册自定义排序、用户数据清理、桌面卡片形态等）
- `{scope}` — 对比范围（指定厂商子集 or 全 8 家）
- `{focus_dimensions}` — 重点维度（从 6 个维度中选择，默认全展开）
- `{feature_description}` — 功能场景的 L4 描述（用户提供的具体使用场景描述）

### 步骤 1：生成研究计划

根据 `{app_name}` + `{feature_name}` 生成研究计划：

1. 对每个厂商，明确要查找的 **官方文档页面类型**：
   - 该功能的 API / SDK 文档
   - UI 设计规范文档
   - 系统功能介绍页面
   - 发布会的相关功能介绍 slides
2. 生成每个厂商的核心搜索词（中英文）：

```bash
python3 scripts/research_plan.py --app "{app_name}" --feature "{feature_name}" --scope "{scope}"
```

脚本输出每个厂商的目标 URL 列表和搜索策略。

### 步骤 2：抓取信息源

按步骤 0 中的优先级顺序，对每个厂商执行：

**A. 官方文档搜索与抓取**

先尝试直接访问已知的官方文档 URL。如果不存在已知 URL，使用 `web_search` 搜索：

搜索词策略：
- 中英文各搜一次
- 例如对比桌面卡片：`HarmonyOS 桌面卡片 设计规范`、`iOS Widget Design Guidelines`、`HyperOS 桌面卡片 开发文档`
- 例如对比数据清理：`Android Storage Manager API`、`iOS 存储 清理 开发文档`

使用 `web_fetch` 抓取找到的官方页面内容。

**B. 官方营销材料搜索**

搜索词策略：
- 例如：`iOS 18 相册 更新 功能`、`HarmonyOS NEXT 图库 相册 自定义排序`
- 使用发布会/官网功能页作为来源

**C. 权威媒体补充**

针对官方文档覆盖不足的部分，搜索深度评测文章。

> **🔍 信息验证规则：**
> - 优先采用官方文档/官方宣传材料
> - 科技媒体信息需标注来源，并注明是否经过实测验证
> - 从截图/视频反推的交互细节必须标注「ⓘ 基于截图推断」
> - 任何无法验证的信息标注「⚠️ 待核实」
> - 每条信息必须附上原始来源链接，绝不允许无来源的信息条目

### 步骤 3：结构化对比分析

对每个厂商，按 6 个维度填充对比数据。处理流程：

1. **如果 `references/feature-maps/` 下已有该 `{feature_name}` 的预先研究记录**，先用它作为基础框架，再用 web 搜索补充最新细节。
2. **如果没有**，按步骤 2 获取信息后直接构建。

对比分析产出结构（每家厂商）：

```markdown
### Apple — iOS

**规格逻辑**
- 支持的格式/类型：...
- 配置上限：...
- 触发条件/执行时机：...

**UX 菜单层级**
- 入口：设置 > 通用 > ...
- 交互步骤数：从入口到完成共 N 步
- 操作反馈：...

**设计思路**
- Apple 的设计哲学：...
- 与竞品的差异化定位：...

**交互体验**
- 动画/过渡效果：...
- 手势支持：...
- 空状态/异常态处理：...

**文案**
- 功能名称：...
- 操作按钮文案：...
- 提示/引导文案：...

**规格参数**
- 数量限制：...
- 尺寸/格式要求：...
- 兼容性：...
```

### 步骤 4：生成横向对比总表

整合所有竞品数据，生成一个**核心对比矩阵**，放在报告开头：

| 维度 | Apple | Google | 华为 | 小米 | OPPO | VIVO | 荣耀 | 三星 |
|------|-------|--------|------|------|------|------|------|------|
| 入口深度 | 设置>... | 设置>... | ... | ... | ... | ... | ... | ... |
| 核心能力 | A | B | C | D | E | F | G | H |
| 数量上限 | N | N | N | N | N | N | N | N |
| 设计亮点 | ... | ... | ... | ... | ... | ... | ... | ... |
| ⚠️ 缺失项 | 不支持X | ... | ... | ... | ... | ... | ... | ... |

### 步骤 5：输出分析结论

在横向对比后产出分析结论：

1. **行业基线** — 大多数厂商都支持哪些能力（最小公分母）
2. **差异化亮点** — 某家独有的差异化功能/设计
3. **体验差距** — 各厂商在该功能上的体验梯度（领先/跟随/追赶）
4. **建议** — 如是为产品设计做参考，给出产品建议（可选，依赖用户要求）

### 步骤 6：生成 Markdown 报告

以 `assets/report-template.md` 为模板，填充所有内容。

保存到：`workspace/竞品特性对比/竞品对比报告-{app_name}-{feature_name}-{date}.md`

### 步骤 7：发布到飞书

1. 用 `feishu_create_doc` 创建飞书文档（标题：`竞品对比报告：{app_name} - {feature_name}`）
   - ⚠️ 如果返回 `application:application:self_manage` 权限错误，需在飞书开放平台后台给应用开通此权限
2. 用 `feishu_update_doc`（mode: overwrite）写入完整 Markdown 报告内容
   - ⚠️ 如果 create_doc 因权限失败，改用以下替代方案：通过飞书开放平台 REST API 直接创建文档
   ```bash
   # 获取 tenant_access_token
   TOKEN=$(curl -s -X POST 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal' \
     -H 'Content-Type: application/json' \
     -d '{"app_id":"<APP_ID>","app_secret":"<APP_SECRET>"}' | jq -r '.tenant_access_token')
   
   # 创建文档
   curl -s -X POST 'https://open.feishu.cn/open-apis/docx/v1/documents' \
     -H "Authorization: Bearer $TOKEN" \
     -H 'Content-Type: application/json' \
     -d '{"title":"竞品对比报告：{app_name} - {feature_name}"}'
   ```
3. 设置文档为互联网公开可读：
   - 获取 tenant_access_token 后调用飞书权限 API 设置 `anyone_readable`
4. 将文档链接发送给用户。如果飞书发布失败，将本地 Markdown 文件的路径告知用户。

> **飞书权限要求：** 应用在飞书开放平台需要开通以下权限：
> - `docx:document`（文档读写）
> - `drive:drive`（云空间管理）
> - `application:application:self_manage`（应用自管理，用于 create_doc）

## 输出规则

### 信息可靠性标注

每条信息需要标注可信度：
- **官方文档** — 默认无需标注（最高可信）
- **官方营销材料** — 标注「📢 官方营销材料」
- **权威媒体评测** — 标注来源名称
- **ⓘ 基于截图推断** — 非官方来源推测
- **⚠️ 待核实** — 无法确认的信息

### 来源链接规则

- **每条信息必须内联附上来源链接**
- 格式：`— [来源名称](URL)`
- 多个来源佐证的用 `·` 分隔：`— [Apple HIG](url) · [官方功能页](url)`
- 英文来源保持英文原文，中文来源保持中文原文
- 绝对不允许无来源的信息条目

### 对比格式

- 每家竞品一个独立章节
- 章节内按 6 个维度展开
- 横向总表放在报告顶部
- 分析结论放在报告底部

## 扩展

该 skill 支持通过 `references/feature-maps/` 目录积累常用功能的预先研究，避免重复抓取。如需预研新功能，只需补充一个 JSON/YAML 文件即可。
