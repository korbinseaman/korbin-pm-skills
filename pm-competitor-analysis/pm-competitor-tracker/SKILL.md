---
name: competitor-system-app-tracker
description: >
  追踪八大手机厂商任意系统级应用（照片、备忘录、设置、相机等）的新版本发布、功能更新、社区反馈和重要新闻，生成竞品周报。
  覆盖竞品：Apple、Google、华为、小米、OPPO、VIVO、荣耀、三星。
  触发条件：(1) 用户提供系统应用名称并请求竞品分析，(2) 用户询问某系统APP在各厂商的最新动态。
  不适用于：非系统应用类竞品、非周报频率的请求。
---

# 竞品系统应用动态追踪

追踪 8 大手机厂商的系统级应用每周动态，输出结构化竞品分析报告。

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

### 步骤 1：生成研究计划

运行辅助脚本获取所有信息源 URL：

```bash
python3 scripts/research_plan.py --app "{app_name}"
```

脚本输出结构化 JSON，包含各厂商竞品信息源。如果脚本未内置该应用的信息源，则使用脚本提供的通用源模板，并通过 `web_search` 补充搜索各厂商 + 应用名称的最新动态链接。

### 步骤 2：抓取信息源

每个厂商用 `web_fetch` 抓取 2–3 个关键信息源：
- **第一优先级**：官方博客/新闻页/更新日志 + 搜索到的针对性 URL
- **第二优先级**：社区论坛（Reddit、微博、产品论坛）
- **第三优先级**：科技媒体（36氪、少数派、9to5Google 等）

若 `references/competitor-sources.md` 中未收录该应用的源，先用 `web_search` 搜索 `{厂商} {app_name} 更新` 类关键词获取有效 URL，再进行抓取。

### 步骤 3：综合发现

对每个厂商竞品，按以下分类整理发现：
- 🆕 **新功能/更新** — 版本号、功能新增
- 💬 **用户反馈** — 吐槽、好评、功能诉求（提炼主题）
- 📰 **新闻/事件** — 发布会、专利、合作

**🔍 信息验证（硬性规则）：**
- **时间校验 — 硬拦截**：
  - 每条信息必须确认发布时间，**只收录发布日期在追踪周期内（周一至周日）的信息**
  - 追踪周期外（包括上周、上月、更早）的内容一律排除，不得录入报告
  - 来源页面没有明确发布日期的信息，除非能通过 web_search 确认属于本周，否则不收录
  - 不得将「近期」「本月」「持续更新」等模糊时间描述当作有效时间——必须具体到日期
- **真实性校验**：优先采用官方公告、权威科技媒体报道；社区/自媒体信息需标注来源类型并交叉验证
- 如果无法确认发布时间或来源可疑，标注「⚠️ 待核实」

**🔗 每条发现必须附上原始信息来源链接**（官方公告、科技媒体报道、社区帖子等），方便用户点击鉴别真伪。**没有任何例外——即便是综合归纳性判断（如用户反馈提炼），也必须附上支撑该结论的 1–2 个来源链接。** 格式示例：`- iOS 26.4.2 安全修复发布 — [MacRumors](https://www.macrumors.com/2026/04/22/apple-releases-ios-26-4-2/)`

**如果确实无法找到对应来源，必须通过 `web_search` 搜索补充，绝不能省略链接。**

检查后无发现则标注「本周无重大更新」。

### 步骤 4：生成报告

以 `assets/report-template.md` 为模板，填充：
- `{app_name}` → 用户指定的系统应用名称
- `{date}` → `YYYY-MM-DD`（报告日期）
- `{week_start}` / `{week_end}` → 周一至周日
- `{generated_at}` → ISO 时间戳
- `{competitor_name}` → 各厂商在该应用上的实际名称
- `{content_or_none}` → 综合发现内容（格式见下方「输出格式规则」）
- `{summary}` → 1–2 句竞争格局观察

保存到：`workspace/竞品分析/竞品周报-{app_name}-{date}.md`

### 步骤 5：同步至飞书（创建 + 写入内容 + 设置公开权限）

1. 用 `feishu_doc`（action: create）创建飞书文档，获取 `doc_token`
2. **立即用 `feishu_doc`（action: write, doc_token=上一步返回值）将步骤 4 生成的完整 Markdown 报告内容写入文档**
   - ⚠️ 必须确认 write 返回 `success: true` 且 `blocks_added > 0`，否则重试或报错提醒用户
3. **设置文档为互联网公开可读（任何人无需登录即可浏览）**：
   - 从飞书配置中读取 `appId` 和 `appSecret`（位置：`~/.openclaw/config.yaml` → `channels.feishu`）
   - 先用 tenant_access_token 获取授权，再调用飞书权限 API 设置 `link_share_entity` 为 `anyone_readable`：
   ```bash
   APP_ID="<从config读取的appId>"
   APP_SECRET="<从config读取的appSecret>"
   DOC_TOKEN="<步骤1获取的doc_token>"
   # 获取 tenant_access_token
   TOK_RESP=$(curl -s -X POST 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal' \
     -H 'Content-Type: application/json' \
     -d "{\"app_id\":\"${APP_ID}\",\"app_secret\":\"${APP_SECRET}\"}")
   TOKEN=$(echo "$TOK_RESP" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('tenant_access_token','') or exit(1))")
   # 设置文档为公开可读
   curl -s -X PATCH "https://open.feishu.cn/open-apis/drive/v1/permissions/${DOC_TOKEN}/public?type=docx" \
     -H "Authorization: Bearer $TOKEN" \
     -H 'Content-Type: application/json' \
     -d '{"link_share_entity":"anyone_readable"}'
   ```
   - ⚠️ 必须确认返回 `"code": 0` 表示成功，否则报错提醒用户手动在飞书中设置「链接分享 → 互联网上获得链接的人可阅读」
4. 将报告链接发送给用户

## 输出格式规则

### 内容结构
- 每个厂商竞品一个独立章节，清晰分隔
- 使用**数字序号列表**逐条展示，每条包含：分类标签（🆕/💬/📰）+ 内容描述 + 信息来源链接
- **🔗 硬性要求：每一条信息（包括用户反馈的归纳性总结）都必须附上至少 1 个来源链接。绝对不允许出现没有链接的信息条目。**
- 如果用户反馈是通过多个来源综合提炼的，至少附上 1–2 个支撑该结论的来源链接
- 格式示例：
  ```
  1. 🆕 iOS 26.4.2 安全修复发布，修复 WebKit 漏洞。 — [MacRumors](https://www.macrumors.com/2026/04/22/apple-releases-ios-26-4-2/)
  2. 📰 Apple 宣布 iOS 26.5 开发者测试版已推送。 — [9to5Mac](https://9to5mac.com/...)
  3. 💬 Wardrobe 功能引发讨论，用户评价两极——创意新奇但实用性待验证。 — [9to5Google](https://9to5google.com/2026/04/29/google-photos-wardrobe/) · [IndiaTV](https://www.indiatvnews.com/technology/news/google-photos-gets-wardrobe-tool-how-the-new-ai-feature-helps-plan-outfits-easily-2026-04-30-1039463)
  ```
- 检查后无发现则标注「本周无重大更新」

### 语言规则
- **英文来源的内容直接显示英文原文**，不做翻译（如 Forbes、MacRumors、Android Authority 等）
- **中文来源的内容直接显示中文原文**（如 IT之家、什么值得买、花粉俱乐部等）
- 保持信息来源的原始语言，让用户看到第一手信息

### 本周观察
- 限 1–2 句，聚焦整体格局
- 如某厂商在该应用上有独特命名或差异化功能，在章节标题中标注
