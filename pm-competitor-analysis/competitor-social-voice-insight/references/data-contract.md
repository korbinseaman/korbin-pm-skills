# 数据契约

## StudyRequest

`create_study.py` 接收 JSON：

```json
{
  "study_id": "可选；未提供时自动生成",
  "subject": "目标产品或研究课题",
  "feature": {
    "name": "目标功能",
    "aliases": ["用户口语名称", "旧名称"]
  },
  "competitors": [
    {
      "name": "竞品公司或产品",
      "product": "对应 App 名称",
      "aliases": ["别名", "缩写"]
    }
  ],
  "focus": ["特别关注的问题"],
  "platforms": ["weibo", "xiaohongshu"],
  "start_date": "可选，YYYY-MM-DD",
  "end_date": "可选，YYYY-MM-DD"
}
```

未提供日期时，结束日期取运行日，开始日期取结束日期向前两个自然年。`platforms` 可选；省略时使用全部已支持平台 `weibo`、`xiaohongshu`、`coolapk`，提供时只能传其中的非空子集。

## VoiceRecord 输入

浏览器或官方接口的采集结果以 JSONL 传入。必填字段：

```json
{
  "platform": "weibo",
  "competitor": "Apple",
  "product": "Photos",
  "feature_path": ["编辑", "AI 消除"],
  "original_text": "用户原文",
  "source_url_raw": "https://...",
  "thread_url": "https://...",
  "address_type": "direct_comment",
  "published_at": "2026-08-12T10:00:00+08:00"
}
```

可选字段包括 `source_content_id`、`source_comment_id`、`parent_comment_id`、`author_handle`、`captured_at`、`engagement`、`content_type`、`observed_version`、`observed_device`、`screenshot_ref`、`collection_status`、`analysis_eligible`、`exclusion_reason`、`stance`、`theme`、`reason_tags`、`scenario_tags`、`pain_point_tags`、`request_tags`、`manual_confirmation` 和 `notes`。

`source_url_raw` 必须是平台真实公开地址。无评论直链时它可以与 `thread_url` 相同，但须使用 `address_type: "parent_thread"` 并提供可获得的评论 ID 或定位信息。

## 输出

- `social-voice.db`：内部 SQLite 真源，包含原始记录、采集任务、覆盖缺口和编码结果。
- `竞品特性VOC报告-*.html`：面向产品决策的离线报告。
- `竞品特性VOC原始数据-*.xlsx`：可筛选的原始数据及汇总。
- `coverage-report.json`：按平台、竞品、月份的覆盖状态。
- `evidence-pack.jsonl`：可由其他分析任务读取的、保留 `record_id` 和来源地址的主题证据。

