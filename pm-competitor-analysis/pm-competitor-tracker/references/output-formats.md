# 输出格式

本 Skill 产生两类用途不同的输出。不要用通讯摘要代替历史存储，也不要把完整 JSONL 直接发送给用户。

## 1. 通讯工具摘要

用途：发送到飞书、WeLink、钉钉等通讯工具，供用户快速浏览本次新增或发生变化的竞品动态。

格式：UTF-8 Markdown，使用 `assets/communication-digest-template.md`。

内容规则：

- 标题使用 `📰 AI 精选竞品更新摘要 · <系统应用名称>`，并显示 `M/D` 格式的更新时间。
- 日报的 `period_line` 留空；周报使用 `> 周报范围：M/D–M/D`。
- 厂商按 Apple、Google、华为、小米、OPPO、VIVO、荣耀、三星排列。
- 厂商标题由 Logo 图标和加粗厂商名组成。图标从 `competitor-sources.json` 的 `icon_path` 读取；研究计划会将其解析为本地绝对路径。
- 生成本地 Markdown 时，`vendor_icon_markdown_or_fallback` 使用 `![厂商 Logo](绝对路径)`。推送到通讯工具前，由 CLI 上传本地 SVG；渠道只接受位图时先转为 PNG，再替换成渠道素材引用。渠道完全不支持图片时使用 `🏢`，不要输出失效图片。
- 每条更新只保留一个结论句，结尾附原始来源链接；不要在消息正文展开长背景。
- 更新结论使用用户请求的语言，产品名和功能专有名词可保留原文。
- 每个厂商默认最多展示 3 条最重要更新，排序为官方更新、功能变化、重要反馈或新闻。更多记录保留在 Changelog。
- 没有新增或变化时写 `暂无更新`。
- 末尾显示本地 Changelog 目录的原始路径。该路径用于定位历史文件，不承诺在远程通讯工具中可直接打开。
- 日报只展示本次新增、更新或补录记录；周报展示目标周的分类汇总，不逐条重发已发送的日报正文。

预置图标：

| 厂商 | 显示名 | Skill 内路径 |
|---|---|---|
| Apple | 苹果 | `assets/vendor-icons/apple.svg` |
| Google | 谷歌 | `assets/vendor-icons/google.svg` |
| 华为 | 华为 | `assets/vendor-icons/huawei.svg` |
| 小米 | 小米 | `assets/vendor-icons/xiaomi.svg` |
| OPPO | OPPO | `assets/vendor-icons/oppo.svg` |
| VIVO | vivo | `assets/vendor-icons/vivo.svg` |
| 荣耀 | 荣耀 | `assets/vendor-icons/honor.svg` |
| 三星 | 三星 | `assets/vendor-icons/samsung.svg` |

更新条目格式：

```markdown
- {一句话更新结论} — [{source_name}]({source_url})
```

同一结论由多个来源支撑时：

```markdown
- {一句话更新结论} — [{source_1}]({url_1}) · [{source_2}]({url_2})
```

完整示例：

```markdown
📰 **AI 精选竞品更新摘要 · 时钟**（更新于 9/20）

![苹果 Logo]({apple_icon_absolute_path}) **苹果**

- iOS 17 系统新增工作日（含调休）闹钟功能，可在调休日自动调整。— [9to5Mac](https://9to5mac.com/...)

🏢 **华为**

暂无更新

历史更新日志：`workspace/竞品分析/changelog`
```

## 2. 本地历史 Changelog

用途：保存全部历史发现，用于去重、检索、按功能特性分类和后续分析。

格式：UTF-8 JSONL，每个竞品与应用一个文件：

```text
workspace/竞品分析/changelog/<竞品名称>_<应用名称>_changelog.jsonl
```

字段、分类和写入规则见 `references/changelog-schema.md`。通讯摘要中的每一条更新都必须能对应到至少一条 Changelog 记录；Changelog 可以包含因篇幅限制而未进入通讯摘要的记录。
