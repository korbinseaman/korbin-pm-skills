# 本地竞品 Changelog Schema

## 存储格式

使用 UTF-8 JSON Lines（`.jsonl`）：每行一个完整 JSON 对象，每个对象代表一条可去重的竞品变化。

选择 JSONL 的原因：

- 文件可持续增长，不需要把全部历史包进一个巨大 JSON 数组；
- 可使用 `rg`、`jq`、Python、DuckDB 等工具直接检索；
- 支持嵌套的功能分类、版本范围和来源字段，表达能力优于 CSV；
- 一条记录损坏不会导致整个历史文件不可读取。

默认目录：`workspace/竞品分析/changelog/`

每个厂商竞品与目标 App 一个文件：

```text
<竞品名称>_<应用名称>_changelog.jsonl
```

例如：

```text
Apple_照片_changelog.jsonl
华为_照片_changelog.jsonl
Google_备忘录_changelog.jsonl
```

文件名中的空格和 Windows 非法字符由脚本替换为 `_`。

## 输入记录

`scripts/changelog_store.py` 接收 JSON 数组，或包含 `findings` 数组的 JSON 对象。每条 finding 使用以下结构：

```json
{
  "competitor": {
    "name": "Apple",
    "platform": "iOS",
    "app_name": "Photos"
  },
  "app_name": "照片",
  "feature": {
    "path": ["编辑", "AI 编辑", "消除"],
    "name": "Clean Up",
    "tags": ["AI", "生成式编辑"]
  },
  "change": {
    "type": "feature_added",
    "title": "Clean Up 新增对象移除能力",
    "summary": "用户可在照片中移除干扰对象。",
    "details": null
  },
  "release": {
    "version": "iOS 27.0",
    "published_at": "2026-09-21",
    "regions": ["全球"],
    "models": []
  },
  "source": {
    "type": "official",
    "name": "Apple Support",
    "url": "https://support.apple.com/example",
    "language": "en"
  }
}
```

### 必填字段

- `competitor.name`：厂商或竞品名称；
- `competitor.app_name`：该厂商的实际 App 名；
- `app_name`：用户指定的统一应用名称；
- `feature.path`：从大类到具体能力的分类路径，至少一层；
- `feature.name`：具体功能或话题名称；
- `change.type`、`change.title`、`change.summary`；
- `release.published_at`：`YYYY-MM-DD`；
- `source.type`、`source.url`。

`change.type` 建议使用：

- `feature_added`：新增功能；
- `feature_changed`：已有功能调整；
- `fix`：修复；
- `rollout`：灰度或区域/机型扩展；
- `service_or_pricing`：服务、会员或价格变化；
- `user_feedback`：用户反馈主题；
- `news`：发布会、合作、专利等公开事件。

## 脚本生成的字段

写入 changelog 后，每条记录增加：

```json
{
  "schema_version": 1,
  "id": "稳定 SHA-256 摘要",
  "tracking": {
    "first_seen_at": "2026-09-22T09:00:00+08:00",
    "last_seen_at": "2026-09-22T09:00:00+08:00",
    "seen_count": 1,
    "run_ids": ["20260922-daily"],
    "modes_seen": ["daily"]
  }
}
```

稳定 ID 基于厂商、统一 App 名、功能路径、变更类型、版本、发布日期和规范化后的来源 URL 生成。相同 ID 再次出现时更新 `last_seen_at`、计数和最新字段，不追加重复记录。

## 检索示例

查找所有 AI 编辑变化：

```bash
rg 'AI 编辑' workspace/竞品分析/changelog/*_照片_changelog.jsonl
```

使用 `jq` 筛选新增功能：

```bash
jq -c 'select(.change.type == "feature_added")' workspace/竞品分析/changelog/Apple_照片_changelog.jsonl
```
