---
name: create-phone-launch-brief
description: Create or update a source-grounded Chinese smartphone launch PPTX from official materials and credible mainstream media. Organize hardware and pricing, operating-system and software upgrades, then key AI, camera, gallery, desktop and communication features. Use for “XX 手机新品发布会速递”, 手机发布会总结, 软件功能卖点复盘, or updating a launch deck with new evidence. Exclude rumor roundups and general technology news.
---

# Create Phone Launch Brief

Create a shareable `《XX 手机新品发布会速递》.pptx` for software product managers. Deliver the deck; keep evidence ledgers and research notes temporary unless requested.

## Apply the defaults

- Write in Simplified Chinese for a China-market audience; cover any smartphone brand.
- Organize the body in order: **Part 1 手机新品概览**, **Part 2 操作系统与系统软件升级**, **Part 3 重点应用与功能特性**.
- Give Part 1 substantive hardware coverage: models, launch prices, storage, chip, display, camera lenses, battery/charging, design and documented upgrades. Do not restrict hardware to software dependencies.
- Use Part 2 for the OS version, system-wide changes, software selling points and rollout. Use Part 3 for detailed AI, camera, gallery, desktop/lock-screen and communication experiences, adding other announced system apps where relevant.
- Allocate the most space to Part 3. Start around 12 slides, usually 10–16 including cover and sources; adjust to the evidence and requested length. Do not pad missing categories.
- Do not output HarmonyOS watchpoints, competitor implications, follow-up recommendations or original strategic analysis. An audience described as “鸿蒙产品经理” does not request these additions.
- Ground every factual statement, upgrade comparison and selling point in an official source or a credible mainstream-media original report/review. Do not invent scenarios, interaction steps, benefits, metrics, or trend conclusions. Attribute media observations and editorial opinions explicitly.

Honor explicit language, market, audience, scope, slide count and template requests. Keep external analysis outside the default briefing unless separately requested.

## Load the guidance

Read these references before producing a deck:

- [references/source-and-evidence.md](references/source-and-evidence.md): acquisition, source qualification, evidence labels, citations and ledger.
- [references/analysis-framework.md](references/analysis-framework.md): three-part classification, experience extraction and selection.
- [references/slide-blueprint.md](references/slide-blueprint.md): page structure, visuals and acceptance checks.

Use the Presentations skill to create and visually verify the final editable PPTX.

## Resolve scope and edition

Establish the event, device family, date, market and information cutoff. Use supplied links/files as seeds; otherwise search official event, newsroom, product/specification, OS and support pages, replay/transcript, then qualified media reports for gaps or hands-on detail. Ask only if unresolved event ambiguity materially changes the result.

Distinguish this event's announcements from earlier OS previews, inherited features and post-event updates. Label each boundary; do not present a prior feature as newly announced. Separate launch pricing from later promotions and current availability from availability at the event.

- **速递版**: Use when material is incomplete. Include supported claims and record coverage gaps and update status.
- **完整版**: Use when replay/transcript or equivalent detailed evidence supports the key features. Add interactions, applicability and direct locators. Never imply that the full video was reviewed when only selected segments were checked.

Keep the same three-part structure in both editions.

## Build and validate the evidence

Build a temporary JSON ledger covering hardware, pricing, OS and application claims using `source-and-evidence.md`. Include source provenance, event relation, feature applicability, evidence level, locators and visual provenance. Leave unsupported information unknown or omit it.

Run the bundled validator before creating slides:

```bash
python3 <skill-root>/scripts/validate_feature_ledger.py <ledger.json> --mode rapid
```

Use `--mode verified` for 完整版. Fix errors and address warnings or retain the corresponding limitation in the PPT. The validator checks structure and evidence references; manually check whether cited material actually supports the wording.

## Produce and deliver

1. Acquire official and qualified mainstream-media evidence without bypassing access controls.
2. Extract claims and source-supported selling points; preserve model, region, version, language, account, network, release timing and test conditions.
3. Organize all three parts with `analysis-framework.md`; plan sufficient hardware detail and focused application pages with `slide-blueprint.md`.
4. Create editable slides with concise Chinese copy, sourced images and claim-level source markers. Put full citations in notes and the source appendix.
5. Render all slides and fix overflow, weak hierarchy, unreadable citations, distorted images and unsupported wording.
6. Deliver the PPTX, mentioning only material coverage limitations.

## Preserve evidence boundaries

- Official announcement, official demo, media report and media hands-on test are different evidence levels. Never upgrade one into another.
- Mark availability as 已上线, 预告, 分批开放 or 未知 and preserve scope.
- Cite the original article/page or video, not search results, aggregators or unattributed reposts.
- Prefer official visuals; use a qualified media outlet's original screenshots with attribution when needed. Do not fabricate announced UI or strip watermarks.
- Keep the source index, available video timestamps, material gaps and version record inside the PPTX.

## Example requests

- “整理 iPhone XX 发布会，按硬件概览、系统升级和重点应用特性输出速递 PPT。”
- “根据直播、新闻稿和主流媒体实测整理 XX 发布会，重点看 AI、相机与图库，逐页标注来源。”
- “更新昨天的速递完整版，补价格配置、桌面和通信特性及适用条件。”
