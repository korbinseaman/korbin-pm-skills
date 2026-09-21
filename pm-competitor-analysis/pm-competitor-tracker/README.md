# 竞品系统应用动态追踪

面向产品经理的系统应用竞品追踪 Skill。它可以按日报或周报模式，持续追踪 Apple、Google、华为、小米、OPPO、vivo、荣耀和三星的系统应用动态，并同时产出：

- 适合在飞书、WeLink、钉钉等通讯工具中阅读的竞品更新摘要；
- 可长期检索、去重和按功能分类的本地 JSONL Changelog。

适用于照片/图库、备忘录/笔记、相机、设置、时钟、天气、日历、文件管理等系统预装应用。

## 快速开始

### 1. 在 AI Agent 中安装 Skill

将本 Skill 安装到 OpenClaw 或其他支持 Agent Skills 的 AI Agent。安装方式见下方“安装”章节。

安装后，在会话中发送：

```text
请使用 $competitor-system-app-tracker 开始配置竞品追踪。
```

在 OpenClaw Control UI 中也可以输入 `$`，从技能列表中选择 `competitor-system-app-tracker`。

### 2. 告诉 Agent 你关注的系统应用

如果没有在第一条消息中指定应用，Agent 会询问：

```text
你希望追踪哪个系统应用？例如照片、备忘录、设置或时钟。
```

直接回答即可：

```text
我关注照片/图库应用，重点看 AI 编辑、搜索和云同步。
```

Agent 默认使用日报模式；也可以明确要求周报，或指定只关注某些功能方向。

### 3. 在 Agent 中设置定时任务

首次执行结果符合预期后，可以直接让 Agent 创建定时任务。例如：

```text
请为这个 Skill 创建定时任务：
- 应用：照片/图库
- 模式：日报
- 时间：每个工作日上午 9:00
- 时区：Asia/Shanghai
- 推送渠道：飞书
- 推送目标：当前群聊
- 每次保存完整历史 Changelog，只推送本次新增或变化的摘要
```

周报示例：

```text
每周一上午 9:30 运行 $competitor-system-app-tracker，生成上一自然周的“备忘录/笔记”竞品周报，推送到当前会话，并将完整记录持续写入本地 Changelog。
```

OpenClaw 使用 Automations 管理定时任务；创建后可让 Agent 列出任务、立即试运行一次或修改推送目标。参见 [OpenClaw Automations 文档](https://docs.openclaw.ai/automation/cron-jobs)。

## Prompt 示例

### 立即生成一份日报

```text
使用 $competitor-system-app-tracker 生成“时钟”应用的竞品日报。关注闹钟、睡眠、计时器和跨设备同步；结果保存到本地 Changelog，并把精简摘要回复在当前会话。
```

### 生成周报

```text
使用 $competitor-system-app-tracker 汇总“照片/图库”应用上一自然周的竞品动态，重点关注 AI 编辑、相册管理、搜索和云服务。周报不要逐条重复已经发送过的日报。
```

### 只关注特定能力

```text
追踪各手机厂商“设置”应用的隐私、权限管理和显示设置变化，日报模式；没有新增内容的厂商显示“暂无更新”。
```

### 创建日报定时任务

```text
请创建一个定时任务：每天上午 8:45 使用 $competitor-system-app-tracker 追踪“备忘录/笔记”，时区 Asia/Shanghai；将摘要推送到我的 WeLink，完整历史保存在本地。创建后先试运行一次。
```

### 创建周报定时任务

```text
请创建一个定时任务：每周一上午 10:00 汇总“相机”应用上一自然周的竞品更新，推送到钉钉产品群；只发送聚合后的周报，历史明细继续写入 JSONL。
```

## 数据源

信息源统一配置在 [`references/competitor-sources.json`](references/competitor-sources.json)，覆盖 8 家厂商，并按以下优先级使用：

| 优先级 | 来源类型 | 示例 |
|---|---|---|
| 1 | 厂商官方来源 | 官方更新说明、支持页面、新闻室、开发者公告、官方账号 |
| 2 | 社区与用户反馈 | 厂商社区、Reddit、酷安、知乎等 |
| 3 | 科技媒体 | 9to5Mac、9to5Google、Android Authority、IT之家等 |

执行时不会只依赖预置入口。Agent 会根据目标应用名称继续搜索该 App、对应 OS 版本、关联服务和具体功能页面，例如：

```text
Apple Photos update 2026
华为 图库 更新 2026
site:ithome.com 小米 相册 更新
```

每条进入摘要或 Changelog 的信息都必须保留原始来源链接，并确认具体发布日期。社区或媒体信息会标注来源类型；能够找到官方证据时优先使用官方页面。

8 家厂商 Logo 已作为本地 SVG 预置在 [`assets/vendor-icons/`](assets/vendor-icons/)，生成通讯摘要时无需临时下载图标。

## 安装

Skill 目录必须保持完整，不能只复制 `SKILL.md`。`assets/`、`references/` 和 `scripts/` 中包含模板、图标、数据源和持久化逻辑。

### 方式一：手动复制到 OpenClaw Skills 目录

从仓库下载 [`pm-competitor-tracker`](https://github.com/korbinseaman/korbin-pm-skills/tree/main/pm-competitor-analysis/pm-competitor-tracker) 完整目录，然后复制为：

```text
<OpenClaw 工作区>/skills/competitor-system-app-tracker/
```

目录结构至少应为：

```text
<OpenClaw 工作区>/skills/competitor-system-app-tracker/
├── SKILL.md
├── assets/
├── references/
└── scripts/
```

如果希望所有本地 OpenClaw Agent 都能使用，可以复制到：

```text
~/.openclaw/skills/competitor-system-app-tracker/
```

OpenClaw 默认会监测 Skills 目录变化；如果当前会话没有刷新出新 Skill，请新建会话或重启 Gateway。目录发现和加载优先级见 [OpenClaw Skills 文档](https://docs.openclaw.ai/tools/skills)。

### 方式二：在 Agent 会话中下载并安装

向具备文件和网络访问能力的 Agent 发送：

```text
请从下面地址下载完整 Skill：
https://github.com/korbinseaman/korbin-pm-skills/tree/main/pm-competitor-analysis/pm-competitor-tracker

检查 SKILL.md 和脚本后，将完整目录安装到当前 Agent 可发现的 skills 目录，目录名使用 competitor-system-app-tracker。不要遗漏 assets、references、scripts 和 tests。安装后检查 Skill 是否可用，并告诉我安装位置和检查结果。
```

Agent 在执行下载或安装前可能会请求授权；确认目标目录和源码地址无误后再批准。

### 方式三：使用命令行安装

本 Skill 位于仓库子目录，因此先克隆仓库，再使用 OpenClaw 的本地目录安装命令：

```bash
git clone --depth 1 https://github.com/korbinseaman/korbin-pm-skills.git

openclaw skills install \
  ./korbin-pm-skills/pm-competitor-analysis/pm-competitor-tracker \
  --as competitor-system-app-tracker

openclaw skills check
```

上面的命令默认安装到当前 OpenClaw 工作区。若要让所有本地 Agent 共用，在安装命令末尾增加 `--global`：

```bash
openclaw skills install \
  ./korbin-pm-skills/pm-competitor-analysis/pm-competitor-tracker \
  --as competitor-system-app-tracker \
  --global
```

OpenClaw 的 `skills install`、`--global` 和本地目录安装行为见 [Skills CLI 文档](https://docs.openclaw.ai/cli/skills)。其他 AI Agent 请将完整 Skill 目录放到其可发现的 Skills 目录；如果不支持 `$skill-name` 语法，可以直接要求 Agent 读取该目录下的 `SKILL.md` 并执行。

## 工作原理

1. **确认任务**：确定目标系统应用、日报或周报模式、重点功能和推送渠道。
2. **计算时间窗口**：日报统计前一个自然日并重叠查询 24 小时；周报统计上一完整自然周并重叠查询 48 小时。
3. **检索信息**：先查询厂商官网，再补充社区和科技媒体；搜索词根据目标应用动态生成。
4. **验证与分类**：确认发布日期和来源链接，按功能更新、用户反馈、新闻事件及功能层级分类。
5. **去重与持久化**：为每条发现生成稳定 ID，写入每个厂商独立的 JSONL Changelog，重复发现只更新追踪信息。
6. **生成通讯摘要**：每家厂商最多展示 3 条重要更新，没有更新时显示“暂无更新”，末尾附历史目录。
7. **按需推送**：定时任务调用用户配置的飞书、WeLink、钉钉或其他通讯渠道；未配置渠道时只生成本地结果。

## 输出

### 通讯工具摘要

使用 [`assets/communication-digest-template.md`](assets/communication-digest-template.md)：

```markdown
📰 **AI 精选竞品更新摘要 · 时钟**（更新于 9/20）

![苹果 Logo](assets/vendor-icons/apple.svg) **苹果**

- iOS 新增工作日（含调休）闹钟能力。— [来源](https://example.com/...)

![华为 Logo](assets/vendor-icons/huawei.svg) **华为**

暂无更新

历史更新日志：`workspace/竞品分析/changelog`
```

### 本地历史 Changelog

完整历史使用 UTF-8 JSONL，按厂商和应用拆分：

```text
workspace/竞品分析/changelog/<竞品名称>_<应用名称>_changelog.jsonl
```

例如：

```text
Apple_照片_changelog.jsonl
华为_照片_changelog.jsonl
Google_备忘录_changelog.jsonl
```

输出边界见 [`references/output-formats.md`](references/output-formats.md)，字段结构和检索示例见 [`references/changelog-schema.md`](references/changelog-schema.md)。

## 运行要求

- 支持 Agent Skills 或能够读取 `SKILL.md` 的 AI Agent；
- 网页访问和搜索能力；
- Python 3.10+，用于研究计划和 Changelog 写入脚本；
- 如需自动推送，需要在 Agent 或定时任务中配置对应通讯渠道。

## 许可证

MIT
