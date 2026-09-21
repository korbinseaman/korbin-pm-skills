---
name: competitor-system-app-tracker
description: >
  以日报或周报模式追踪八大手机厂商任意系统级应用（照片、备忘录、设置、相机等）的新版本发布、功能更新、社区反馈和重要新闻，生成竞品动态摘要并维护本地历史 changelog。
  覆盖竞品：Apple、Google、华为、小米、OPPO、VIVO、荣耀、三星。
  触发条件：(1) 用户提供系统应用名称并请求竞品分析，(2) 用户询问某系统APP在各厂商的最新动态。
  不适用于：非系统应用类竞品。
---

# 竞品系统应用动态追踪

追踪 8 大手机厂商的系统级应用每日或每周动态，输出结构化竞品日报/周报，并将历史发现写入本地 changelog。

## 前置条件

**用户必须指定要分析的系统应用名称**，例如：
- 照片 / 相册 / 图库
- 备忘录 / 笔记
- 相机
- 设置
- 计算器
- 时钟
- 天气
- 日历
- 文件管理
- 其他系统预装应用

如果用户未指定，先询问：「请问您要分析哪个系统应用？（如照片、备忘录、设置等）」

## 竞品范围

| # | 厂商 | 平台 | 应用命名参考 |
|---|-----|------|-------------|
| 1 | Apple | iOS / macOS | Apple Photos, Apple Notes, Settings 等 |
| 2 | Google | Android | Google Photos, Google Keep, Settings 等 |
| 3 | 华为 | HarmonyOS | 图库、备忘录、设置 等 |
| 4 | 小米 | HyperOS / Android | 相册、笔记、设置 等 |
| 5 | OPPO | ColorOS / Android | 相册、便签、设置 等 |
| 6 | VIVO | OriginOS / Android | 相册、笔记、设置 等 |
| 7 | 荣耀 | MagicOS / Android | 相册、笔记、设置 等 |
| 8 | 三星 | One UI / Android | Gallery, Samsung Notes, Settings 等 |

> 各厂商对同一功能的系统应用名称可能不同，分析时需根据用户指定的应用名对应到各厂商的实际应用名称。

## 追踪维度

1. **新版本/功能更新** — 官网、Changelog、博客、微博、微信公众号、小红书
2. **社区用户反馈** — 微博、小红书、抖音评论区、Reddit、Twitter/X、ProductHunt
3. **重要公开信息** — 发布会、新专利、战略合作、行业新闻

## 研究流程

### 步骤 0：确认应用名称

如果用户未在请求中明确指定系统应用名称，先询问并确认：
- 应用名称是什么？（如照片、备忘录、设置等）
- 是否有特定功能方向？（如 AI 功能、交互设计等）

确认后将应用名称记为 `{app_name}`，贯穿后续所有步骤。

同时确认运行模式：

- `daily`：默认模式，生成竞品日报；
- `weekly`：生成竞品周报；
- 用户未指定时使用 `daily`。

### 步骤 1：生成研究计划

运行辅助脚本获取所有信息源 URL：

```bash
python3 scripts/research_plan.py \
  --app "{app_name}" \
  --mode "{daily|weekly}" \
  --last-success-at "{可选：上次成功运行时间}"
```

脚本输出结构化 JSON，包含目标内容周期、带重叠的搜索窗口、厂商信息源和搜索关键词。如果脚本未内置该应用的信息源，则使用通用源模板，并通过 `web_search` 补充搜索各厂商 + 应用名称的最新动态链接。

时间范围规则：

- **日报**：内容周期为运行日前一个自然日；搜索窗口向前额外重叠 24 小时。
- **周报**：内容周期为上一个完整自然周（周一 00:00 至周日 23:59）；搜索窗口向前额外重叠 48 小时。
- 使用本地 changelog 稳定 ID 去重。目标周期外但本次首次发现的信息，日报最多补录最近 7 天、周报最多补录最近 14 天，并标注“补录”。
- 日报只推送本次新增或发生变化的记录；周报按功能分类汇总目标周内容。若同时设置日报和周报，周报做聚合总结，不逐条重复日报正文。

### 步骤 2：抓取信息源

每个厂商用 `web_fetch` 抓取 2–3 个关键信息源：
- **第一优先级**：官方博客/新闻页/更新日志 + 搜索到的针对性 URL
- **第二优先级**：社区论坛（Reddit、微博、产品论坛）
- **第三优先级**：科技媒体（36氪、少数派、9to5Google 等）

读取 `references/competitor-sources.json` 获取按优先级排列的厂商信息源和搜索词。若 JSON 中未收录该应用的专属来源，使用其中的 `fallback_search_queries` 和 `domestic_search_queries` 补充搜索，再抓取有效 URL。

### 步骤 3：综合发现

对每个厂商竞品，按以下分类整理发现：
- 🆕 **新功能/更新** — 版本号、功能新增
- 💬 **用户反馈** — 吐槽、好评、功能诉求（提炼主题）
- 📰 **新闻/事件** — 发布会、专利、合作

**🔍 信息验证（硬性规则）：**
- **时间校验 — 硬拦截**：
  - 每条信息必须确认发布时间，优先收录发布日期在本次内容周期内的信息
  - 仅允许按步骤 1 的补录规则收录周期外信息，并明确标注“补录”
  - 来源页面没有明确发布日期的信息，除非能通过 web_search 确认属于本次内容周期，否则不收录
  - 不得将「近期」「本月」「持续更新」等模糊时间描述当作有效时间——必须具体到日期
- **真实性校验**：优先采用官方公告、权威科技媒体报道；社区/自媒体信息需标注来源类型并交叉验证
- 如果无法确认发布时间或来源可疑，标注「⚠️ 待核实」

**🔗 每条发现必须附上原始信息来源链接**（官方公告、科技媒体报道、社区帖子等），方便用户点击鉴别真伪。**没有任何例外——即便是综合归纳性判断（如用户反馈提炼），也必须附上支撑该结论的 1–2 个来源链接。** 格式示例：`- iOS 26.4.2 安全修复发布 — [MacRumors](https://www.macrumors.com/2026/04/22/apple-releases-ios-26-4-2/)`

**如果确实无法找到对应来源，必须通过 `web_search` 搜索补充，绝不能省略链接。**

检查后无发现则标注「本期无重大更新」。

### 步骤 4：生成竞品日报

读取 [references/output-formats.md](references/output-formats.md) 的“通讯工具摘要”规则，以 `assets/communication-digest-template.md` 生成供用户浏览的精简 Markdown。日报模式展示当日新增、更新和补录；周报模式展示目标周聚合结果。填充：

- `{app_name}` → 用户指定的系统应用名称
- `{updated_at_m_d}` → `M/D` 格式的生成日期
- `{period_line}` → 日报留空；周报填入 `> 周报范围：M/D–M/D`
- `{vendor_icon_markdown_or_fallback}` → 使用研究计划输出的 `icon_path` 生成 Logo Markdown；渠道不支持图片时使用 `🏢`
- `{vendor_display_name}` → 用户熟悉的厂商中文名
- `{updates_or_none}` → 最多 3 条精选更新，或 `暂无更新`
- `{changelog_directory}` → 步骤 5 的本地 Changelog 目录

可将本次推送载荷保存到：

- 日报：`workspace/竞品分析/outbox/竞品日报-{app_name}-{date}.md`
- 周报：`workspace/竞品分析/outbox/竞品周报-{app_name}-{week_end}.md`

该 Markdown 是本次通讯消息的载荷，不承担历史存储职责。

### 步骤 5：写入本地竞品 Changelog

使用 UTF-8 JSONL 保存全部历史发现。每个厂商竞品与目标 App 一个文件：

```text
workspace/竞品分析/changelog/<竞品名称>_<应用名称>_changelog.jsonl
```

先将本次发现整理为符合 [references/changelog-schema.md](references/changelog-schema.md) 的 JSON，再执行：

```bash
python3 scripts/changelog_store.py \
  --input "{本次 findings.json}" \
  --output-dir "workspace/竞品分析/changelog" \
  --run-id "{run_id}" \
  --mode "{daily|weekly}" \
  --seen-at "{generated_at}"
```

脚本按稳定 ID 更新或追加记录，返回每个文件的 `added`、`updated` 和 `total`。JSONL 的功能分类使用 `feature.path`，可按“一级功能 → 子功能 → 具体能力”检索。全部有效发现都写入 Changelog，包括因通讯摘要篇幅限制而未展示的记录。

### 步骤 6：推送今日竞品日报

本步骤只在用户配置了通讯工具或定时任务时执行：

1. 读取步骤 4 生成的通讯摘要文件；
2. 按用户配置调用对应推送 CLI，渠道可为飞书、WeLink、钉钉或其他工具；
3. CLI 至少接收 `channel`、`target` 和 `input`，成功后返回消息 ID 或可访问链接；
4. 未配置推送目标时跳过，不影响日报生成与本地 changelog。

周报模式若需要推送，复用相同逻辑并传入周报文件。具体 CLI、鉴权和定时频率由创建自动化任务时指定，本 Skill 不内置渠道凭据。

## 输出定义

每次执行产生两个逻辑输出：

1. **通讯工具摘要**：面向用户阅读的精简 Markdown，由步骤 4 生成并由步骤 6 推送；
2. **本地历史 Changelog**：面向长期存储和检索的 JSONL，由步骤 5 写入。

两类输出的边界、格式和对应关系见 [references/output-formats.md](references/output-formats.md)。Changelog 字段定义见 [references/changelog-schema.md](references/changelog-schema.md)。
