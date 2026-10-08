---
name: competitor-social-voice-insight
description: 从微博、小红书和酷安采集近两年可访问的竞品功能用户原声，保留真实来源地址，生成可追溯的 HTML VOC 报告和 XLSX 原始数据汇总。适用于消费级 App 的功能评价、痛点和需求洞察，不用于发布、互动或绕过平台访问限制。
---

# Competitor Social Voice Insight

面向消费级 App 的竞品功能 VOC 洞察。目标是获得并分析近两年内微博、小红书、酷安中**当前合法可访问且可发现**的用户原声，而非将样本声量误称为市场总体比例。研究请求可通过 `platforms` 选择其中的非空子集；不要为未选择的平台创建任务或报告覆盖结论。

## 必须交付

每次研究至少输出：

1. `竞品特性VOC报告-<课题>-<日期>.html`：离线可打开、可筛选的竞品功能 VOC 报告。
2. `竞品特性VOC原始数据-<课题>-<日期>.xlsx`：逐条保留原声、真实来源地址、平台定位和编码结果的工作簿。

仅当原声有真实平台地址时，才能进入正式证据集。平台没有评论直链时，保存原帖真实地址与评论 ID/回复 ID；不得伪造评论 URL。

## 运行模式

### 1. 创建研究与采集计划

要求用户给出目标产品、目标功能、竞品清单和特别关注问题。若没有明确竞品，先提出候选项并要求确认。

用 `scripts/create_study.py` 初始化 SQLite 研究库、生成 24 个月的查询计划。读取 [数据契约](references/data-contract.md) 确定请求格式和字段。

### 2. 获取平台内容

先读取 [采集与平台边界](references/collection-playbook.md)。

- 微博：优先使用用户已授权的微博官方 CLI/API；未提供权限时，使用用户已登录的可见浏览器补充公开页面。
- 小红书、酷安：使用用户已登录的可见浏览器采集页面当前可见内容。
- 登录、短信验证、验证码、风险提示均由用户接管。不要读取、存储密码或 Cookie；不要绕过平台限制；不要点赞、关注、评论、转发或发布。

按“平台 × 竞品 × 功能表达 × 自然月”执行任务。逐个获取候选原帖及其当前可见的一、二级评论，直到分页或“更多评论/回复”入口耗尽。每次页面读取后写入断点和覆盖状态。

### 3. 导入、编码与校验

把浏览器或官方接口获得的 JSONL 交给 `scripts/import_voice_records.py`。脚本会：

- 保存原始公开 URL 和原文；
- 生成仅用于去重的规范化 URL；
- 拒绝非三平台域名、缺失地址、空文本或包含疑似会话参数的记录；
- 对作者标识生成研究内匿名哈希，不输出原用户名；
- 写入 SQLite 并保留采集状态。

随后按 [VOC 分析规则](references/analysis-framework.md) 为记录补齐相关性、观点、主题、使用场景、痛点和需求。不能确认相关性的记录保留在原始库中，但标记为不进入分析。

### 4. 导出交付物

执行 `scripts/export_deliverables.py`。生成 HTML、XLSX、覆盖报告 JSON 和通用证据包 JSONL。报告与工作簿必须来自同一个 SQLite 数据库。

## 真实性与覆盖规则

- `source_url_raw` 必须保留平台实际提供的公开地址；`source_url_canonical` 仅用于去重。
- 无评论直链时，`source_url_raw` 保存真实原帖地址，`address_type` 标为 `parent_thread`，并保留评论定位字段。
- 输出 `complete_under_current_interface`、`max_visible`、`partial` 或 `blocked` 之一，不能将受限、删除或未验证内容称为全量。
- 单条社区原声只能证明该用户的陈述；跨平台主题结论必须注明样本范围、原声数量和来源链接。
- 报告中的每个主题必须能通过 `record_id` 回查到 XLSX 原声行。

## 参考资料

- 数据结构、输入和输出： [references/data-contract.md](references/data-contract.md)
- 平台采集、断点和失败处理： [references/collection-playbook.md](references/collection-playbook.md)
- 主题编码、结论边界和 HTML 报告规则： [references/analysis-framework.md](references/analysis-framework.md)

