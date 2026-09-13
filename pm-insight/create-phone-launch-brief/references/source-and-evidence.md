# Source and Evidence Rules

## Source hierarchy

Use sources in this order. Prefer the most direct source for each claim rather than citing a general event page for every statement.

1. Official event page, official newsroom release, official product page, specification page, and support documentation.
2. Official replay, official transcript, official subtitles, keynote chapters, and downloadable press material.
3. Official regional website and verified official brand accounts when they add market-specific availability or visuals.
4. User-supplied official files such as press releases, transcripts, screenshots, or decks.

5. Credible mainstream-media original reporting or hands-on reviews, permitted by default. Qualify the individual article: an identifiable outlet with editorial responsibility, a named author/editor or reporting desk, a publication date, and direct reporting, disclosed test methods or traceable primary evidence. A well-known outlet alone does not qualify rumors, sponsored copy or unattributed aggregation. Record the qualification basis; do not claim credibility from search rank.

Use official sources first for launch specifications, prices, compatibility and release commitments. Use qualified media to supplement reporting, explain observed interactions or document independent testing; identify the outlet and distinguish reporting, testing and editorial opinion. Do not generalize one test to all configurations. Exclude leaks, rumor pieces, anonymous social posts, retailer copy, reposted clips and unsupported summaries as claim evidence. Trace syndicated material to the original where accessible.

A media test can disagree with an official performance claim: preserve both attributions, test scope and dates rather than silently selecting one. Never label a media report as official.

Do not bypass authentication, paywalls, geographic controls, robots restrictions, or disabled downloads. If a replay cannot be accessed, continue with available official evidence and record the gap.

## Acquisition procedure

1. Record the event name, device family, event date, region, official host, and access time.
2. Search for the event page, newsroom index, device product pages, OS or software release pages, support pages, press kit, and official replay; supplement with qualified mainstream-media original coverage.
3. Prefer official transcript or captions. When only a replay exists and local transcription is permitted and feasible, transcribe it with timestamps. Keep the media URL and transcription method in notes.
4. Capture the smallest useful locator for every claim: section heading or paragraph for text, and `HH:MM:SS–HH:MM:SS` for video.
5. Save candidate official or qualified-media visuals with their source IDs and timestamps or page locations. Preserve original aspect ratio and do not remove source watermarks.
6. Recheck product and support pages before finalizing a 完整版 because official availability details may appear after the event.

## Evidence labels

Use one label per factual claim:

| Label | Meaning | Permitted wording |
| --- | --- | --- |
| `official-announcement` | Official text or speaker directly announces the capability | “官方宣布”“将支持” |
| `official-demo` | Official video visibly demonstrates the described interaction or result | “发布会演示显示” |
| `media-report` | A qualified mainstream outlet reports or explains the capability | “据 ×× 报道” |
| `media-test` | A qualified outlet directly tested the described behavior with stated conditions | “×× 实测显示，在……条件下” |

Never convert an announcement into a demo, or a demo into independent testing. Do not generate inference claims. Attribute sourced editorial assessments to their author/outlet, and keep them separate from factual specifications. An official subtitle alone establishes a spoken announcement, not that a visual demo was reviewed.

## Availability states

Normalize availability to one of these internal values and render the Chinese label in the deck:

| Internal value | Slide label | Use when |
| --- | --- | --- |
| `available` | 已上线 | Official material says the capability is currently available for the stated scope |
| `preview` | 预告 | Official material describes a future capability or gives a future release window |
| `phased-rollout` | 分批开放 | Availability varies by time, market, model, language, account, or staged rollout |
| `unknown` | 未知 | Official evidence does not establish release timing or scope |

Do not infer availability from a live demo alone.

## Feature ledger

Create one JSON object with `event`, `sources`, and `features`.

```json
{
  "event": {
    "brand": "Example",
    "name": "Example Launch Event",
    "date": "2026-09-01",
    "region": "中国",
    "edition": "速递版",
    "source_policy": "official-and-mainstream-media"
  },
  "sources": [
    {
      "source_id": "S1",
      "type": "newsroom",
      "title": "Official release title",
      "publisher": "Example",
      "url": "https://example.com/official-release",
      "published_at": "2026-09-01",
      "accessed_at": "2026-09-01T14:30:00+08:00",
      "region": "中国",
      "language": "zh-CN",
      "official": true,
      "source_class": "official",
      "event_relation": "same-event",
      "locator": "AI features, paragraph 3",
      "notes": ""
    }
  ],
  "features": [
    {
      "feature_id": "F1",
      "name": "Feature name",
      "category": "系统应用AI",
      "part": 3,
      "priority": "key",
      "claim": "Concise factual claim",
      "user_scenario": "The user need or moment",
      "entry": "Where the interaction starts",
      "steps": ["Step 1", "Step 2"],
      "result": "Observable user result",
      "availability_status": "phased-rollout",
      "applicable_devices": ["Model A"],
      "regions": ["中国"],
      "release_timing": "From 2026-10",
      "evidence_level": "official-demo",
      "source_refs": ["S1"],
      "text_locator": "AI features, paragraph 3",
      "video_timestamp": "00:42:10-00:43:05",
      "visual_source": "S1 product image 2"
    }
  ]
}
```

Allowed categories:

- Part 1: 新品硬件与价格
- Part 2: 操作系统与系统软件
- Part 3: 系统应用AI, 相机, 图库, 桌面与锁屏, 通信, 隐私与安全, 办公效率, 云服务, 跨设备协同, 其他软件能力

Set `part` to 1, 2 or 3. For each source use `source_class: official` with `official: true`, or `source_class: mainstream-media` with `official: false`. Media records require `credibility_basis` describing article-level qualification, plus `published_at`; a media test claim also needs `test_conditions`. Use `source_policy: official-only` if requested; otherwise use `official-and-mainstream-media`. Do not include legacy analysis or harmony_implication fields.

Use `priority: key` for substantial slide coverage and `supporting` for summary items. Hardware and OS facts belong in the same ledger and require citations; user scenario/result fields apply to key application features, not bare prices/specifications. Preserve currency/storage/market/price date inside price claims and predecessor/configuration inside upgrade claims. Keep fact-to-source mapping specific; split claims with differing evidence levels. Add `claim_event_relation` as `same-event`, `prior-announcement` or `post-event-update` when the source spans multiple events.

Unknown interaction steps may be omitted or explicitly marked unknown; never satisfy a schema with invented detail.

## Conflict handling

- Prefer a device-specific product or support page over broad keynote wording when it defines actual compatibility.
- Prefer the most recent official update for availability, while retaining the original event claim in the update record.
- When official regional pages disagree, state both scopes and do not merge them.
- When evidence is incomplete, use `unknown` and add a pending item.
- When a claimed feature appears only in a montage or marketing image, describe only what the visual establishes.

## Citation format

Use compact markers such as `[S1]` or `[S2 00:42:10]` next to claims. Put the full source title, publisher, publication date, URL, access date, region, and relevant locator in speaker notes and on the final source page. Keep external image citations with the slide that uses the image.
