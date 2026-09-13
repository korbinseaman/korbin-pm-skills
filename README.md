# Korbin PM Skills

面向产品经理工作流的 Agent Skills 集合，覆盖竞品分析、行业洞察、产品文案、演示材料和用户研究。每个 Skill 都以独立目录组织，包含 `SKILL.md`，并按需附带参考资料、模板、脚本、示例和 Agent 元数据。

本仓库适合在 Codex、Claude Code、OpenCode 等支持 Agent Skills 或可读取 Markdown 指令的环境中使用。

## 技能导航

### 竞品分析

| Skill | 适用场景 | 主要产物 |
|---|---|---|
| [`competitor-app-feature-compare`](pm-competitor-analysis/pm-competitor-feature/) | 对系统 App 的单个功能进行 L4 级横向对比 | 功能规格、体验、UX 层级、文案和机制对比 |
| [`competitor-system-app-tracker`](pm-competitor-analysis/pm-competitor-tracker/) | 按周追踪主流手机厂商系统应用动态 | 厂商动态、用户反馈、行业新闻和竞品周报 |
| [`pm-system-app-competitor-matrix`](pm-competitor-analysis/pm-system-app-competitor-matrix/) | 对系统 App 或系统级功能进行完整竞品矩阵分析 | 产品定位、Feature Matrix、证据明细、定量数据和定位图 |

### 产品洞察与表达

| Skill | 适用场景 | 主要产物 |
|---|---|---|
| [`create-phone-launch-brief`](pm-insight/create-phone-launch-brief/) | 基于官方材料和可信媒体整理手机新品发布会 | 中文新品速递 PPTX、功能卖点和证据索引 |
| [`pm-app-feature-copywriter`](pm-prd-and-ux/pm-app-feature-copywriter/) | 撰写或优化 App 功能文案 | Slogan、功能描述、微文案、版本说明和应用介绍 |

### 用户研究

[`pm-user-research`](pm-user-research/) 提供四个可独立使用、也可串联执行的原子 Skill：

| Skill | 职责 | 核心输出 |
|---|---|---|
| [`ur-design-survey`](pm-user-research/skills/ur-design-survey/) | 设计低偏差、可分析的定量问卷 | `questionnaire.md`、`questionnaire-design.html` |
| [`ur-generate-personas`](pm-user-research/skills/ur-generate-personas/) | 生成分层、可审计的合成用户画像 | `personas.json`、画像文件和审计结果 |
| [`ur-user-simulator`](pm-user-research/skills/ur-user-simulator/) | 让隔离的合成用户完成问卷 | 个人答卷、Excel 汇总和质量报告 |
| [`ur-synthesize-report`](pm-user-research/skills/ur-synthesize-report/) | 清理数据并综合定量与开放回答 | `analysis_summary.json`、离线 HTML 报告和质量报告 |

完整说明、数据契约和运行示例见 [`pm-user-research/README.md`](pm-user-research/README.md)。

## 目录结构

```text
korbin-pm-skills/
├── pm-competitor-analysis/    # 竞品功能对比、动态追踪和矩阵分析
├── pm-insight/                # 行业与新品洞察
├── pm-prd-and-ux/             # PRD、UX 与产品文案
├── pm-product-slides/         # 产品演示相关工作区
├── pm-user-research/          # 问卷、画像、模拟和研究报告
└── workspace/                 # 模板与工作素材
```

每个 Skill 的入口是其目录下的 `SKILL.md`。使用时应保持 Skill 内部目录结构不变，避免参考资料、模板或脚本的相对路径失效。

## 安装

### Codex

将需要的单个 Skill 目录复制或链接到 Codex 可发现的 skills 目录。例如，只安装用户研究技能时，应复制 `pm-user-research/skills/` 下对应的四个目录。

安装后可显式调用：

```text
$ur-design-survey 调研课题：图库 AI 修图；目标：识别高频任务和主要问题；问卷不超过 12 题。
```

### Claude Code / OpenCode

将 Skill 目录放入平台支持的 skills 目录；如果平台不支持 `$skill-name` 调用语法，可直接要求 Agent 读取对应的 `SKILL.md` 并执行其中流程。

## 使用示例

```text
$competitor-app-feature-compare 对比 Apple、Google、华为图库的相册自定义排序能力。
```

```text
$pm-system-app-competitor-matrix 分析图库照片筛选功能，重点关注云同步状态与存储位置筛选。
```

```text
$create-phone-launch-brief 基于官方发布会资料制作某款手机的中文新品速递。
```

```text
$pm-app-feature-copywriter 为系统图库的 AI 消除功能撰写功能介绍、入口文案和版本说明。
```

```text
$ur-design-survey 为“AI 帮接电话”设计关键假设验证问卷，最长作答路径不超过 15 题。
```

## 运行环境

- 大多数 Python 脚本只依赖 Python 3.10+ 标准库。
- 竞品矩阵图表脚本的额外依赖见 [`requirements.txt`](pm-competitor-analysis/pm-system-app-competitor-matrix/scripts/requirements.txt)。
- 需要外部模型时，请通过环境变量提供 API Key，并使用不会提交到 Git 的私有配置文件。
- 不要在 `*.example.yaml`、JSON、脚本、文档或测试数据中写入真实密钥。

## 验证

用户研究模块可在其目录下运行完整测试：

```bash
cd pm-user-research
python -m unittest discover -s tests -v
```

部分 Skill 还提供独立校验或生成脚本，使用前请先阅读对应 `SKILL.md` 和 `README.md`。

## 使用边界

- 合成画像和模拟回答用于验证问卷、数据管线与研究假设，不能替代真实用户研究，也不能用于估计真实市场比例、购买率或统计显著性。
- 竞品与行业结论应保留可核验来源，并区分事实、推断和产品建议。
- 运行产物应写入独立工作目录，不要覆盖 Skill 自身的模板、规则和参考资料。
- 提交前应检查 `.env`、私钥、访问令牌、密码和 API Key 等敏感信息。

## 贡献约定

新增或修改 Skill 时，建议至少确认：

1. `SKILL.md` 的名称、描述和触发条件清晰且不过度泛化。
2. 引用的 `references/`、`templates/`、`scripts/` 文件真实存在。
3. 示例不包含真实凭据、个人隐私或无法公开的业务数据。
4. 脚本具有明确输入、输出和失败提示，并可在干净环境中验证。
5. 对关键行为变更同步补充测试或评估用例。
