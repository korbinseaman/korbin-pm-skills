#!/usr/bin/env python3
"""Export a self-contained HTML VOC report and auditable XLSX raw-data workbook."""
from __future__ import annotations

import argparse
import html
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import xlsxwriter

from voc_store import connect, fetch_records, get_study, safe_file_stem


PLATFORM_LABELS = {"weibo": "微博", "xiaohongshu": "小红书", "coolapk": "酷安"}
XLSX_ROW_LIMIT = 900_000


def short_text(value: str, limit: int = 180) -> str:
    compact = " ".join(value.split())
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2).replace("</", "<\\/")


def state_label(value: str) -> str:
    labels = {
        "complete_under_current_interface": "当前接口下完整",
        "max_visible": "最大可见",
        "partial": "部分完成",
        "blocked": "受限阻断",
        "planned": "待执行",
        "in_progress": "执行中",
        "accessible": "可访问",
        "login_required": "需登录",
        "deleted": "已删除",
        "restricted": "受限",
    }
    return labels.get(value, value or "未标注")


def load_context(conn: sqlite3.Connection, study_id: str) -> dict[str, Any]:
    study = dict(get_study(conn, study_id))
    request = json.loads(study["request_json"])
    records = fetch_records(conn, study_id)
    tasks = [dict(row) for row in conn.execute("SELECT * FROM query_tasks WHERE study_id = ? ORDER BY platform, competitor, month_start", (study_id,))]
    gaps = [dict(row) for row in conn.execute("SELECT * FROM collection_gaps WHERE study_id = ? ORDER BY occurred_at", (study_id,))]
    return {"study": study, "request": request, "records": records, "tasks": tasks, "gaps": gaps}


def build_summary(context: dict[str, Any]) -> dict[str, Any]:
    records = context["records"]
    eligible = [record for record in records if record["analysis_eligible"]]
    by_platform = Counter(record["platform"] for record in records)
    by_competitor = Counter(record["competitor"] for record in eligible)
    theme_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in eligible:
        theme_groups[(record["competitor"], record["theme"] or "未编码", record["stance"] or "未标注")].append(record)
    themes = []
    for (competitor, theme, stance), group in sorted(theme_groups.items(), key=lambda item: (-len(item[1]), item[0])):
        platforms = sorted({record["platform"] for record in group})
        threads = {record["thread_url"] for record in group}
        themes.append({
            "competitor": competitor,
            "theme": theme,
            "stance": stance,
            "voice_count": len(group),
            "thread_count": len(threads),
            "platform_count": len(platforms),
            "platforms": [PLATFORM_LABELS.get(platform, platform) for platform in platforms],
            "latest_at": max((record["published_at"] or "" for record in group), default="") or None,
            "record_ids": [record["record_id"] for record in group],
            "examples": group[:3],
        })
    task_states = Counter(task["status"] for task in context["tasks"])
    coverage = defaultdict(lambda: Counter())
    for task in context["tasks"]:
        coverage[(task["platform"], task["competitor"])][task["status"]] += 1
    return {
        "record_count": len(records),
        "eligible_count": len(eligible),
        "platform_counts": {PLATFORM_LABELS.get(key, key): value for key, value in sorted(by_platform.items())},
        "competitor_counts": dict(sorted(by_competitor.items())),
        "themes": themes,
        "task_states": dict(sorted(task_states.items())),
        "coverage": [
            {"platform": PLATFORM_LABELS.get(platform, platform), "competitor": competitor, **dict(states)}
            for (platform, competitor), states in sorted(coverage.items())
        ],
    }


def to_excel_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None)
    except ValueError:
        return None


def excel_write_value(sheet: Any, row: int, col: int, header: str, value: Any, formats: dict[str, Any]) -> None:
    if value is None:
        sheet.write_blank(row, col, None, formats["cell"])
    elif header in {"原始公开地址", "所属原帖地址"} and isinstance(value, str) and value.startswith(("https://", "http://")):
        if len(value) <= 2079:
            sheet.write_url(row, col, value, formats["url"], string=value)
        else:
            sheet.write(row, col, value, formats["cell"])
    elif header in {"原始发布时间", "采集时间", "最后任务更新时间", "最后发生时间"}:
        parsed = to_excel_datetime(value)
        if parsed:
            sheet.write_datetime(row, col, parsed, formats["datetime"])
        else:
            sheet.write(row, col, value, formats["cell"])
    elif isinstance(value, bool):
        sheet.write_boolean(row, col, value, formats["cell"])
    elif isinstance(value, (int, float)):
        sheet.write_number(row, col, value, formats["cell"])
    else:
        sheet.write(row, col, value, formats["cell"])


def write_table_sheet(workbook: xlsxwriter.Workbook, name: str, headers: list[str], rows: Iterable[list[Any]], widths: list[int] | None = None) -> None:
    sheet = workbook.add_worksheet(name[:31])
    formats = {
        "header": workbook.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#1F4E78", "border": 1, "text_wrap": True, "valign": "vcenter"}),
        "cell": workbook.add_format({"border": 1, "valign": "top", "text_wrap": True}),
        "url": workbook.add_format({"border": 1, "font_color": "#0563C1", "underline": 1, "valign": "top", "text_wrap": True}),
        "datetime": workbook.add_format({"border": 1, "num_format": "yyyy-mm-dd hh:mm", "valign": "top"}),
    }
    for col, header in enumerate(headers):
        sheet.write(0, col, header, formats["header"])
        width = widths[col] if widths and col < len(widths) else min(max(len(header) * 2, 12), 28)
        sheet.set_column(col, col, width)
    row_count = 0
    for row_count, row in enumerate(rows, start=1):
        for col, value in enumerate(row):
            excel_write_value(sheet, row_count, col, headers[col], value, formats)
    sheet.freeze_panes(1, 0)
    sheet.autofilter(0, 0, max(row_count, 1), len(headers) - 1)


def records_to_rows(records: list[dict[str, Any]]) -> tuple[list[str], list[list[Any]]]:
    headers = [
        "原声记录ID", "平台", "竞品", "产品/App", "功能路径", "原始用户文本", "内容类型", "观点倾向", "VOC主题",
        "评价原因", "使用场景", "痛点标签", "需求标签", "原始发布时间", "采集时间", "互动量快照", "匿名作者键",
        "原始公开地址", "所属原帖地址", "帖子ID", "评论ID", "父评论ID", "地址类型", "采集状态", "版本线索",
        "设备线索", "截图引用", "可进入分析", "排除原因", "需人工确认", "原文内容哈希", "备注",
    ]
    rows = []
    for record in records:
        rows.append([
            record["record_id"], PLATFORM_LABELS.get(record["platform"], record["platform"]), record["competitor"], record["product"], " > ".join(record["feature_path"]),
            record["original_text"], record["content_type"], record["stance"], record["theme"], "、".join(record["reason_tags"]),
            "、".join(record["scenario_tags"]), "、".join(record["pain_point_tags"]), "、".join(record["request_tags"]), record["published_at"], record["captured_at"],
            json.dumps(record["engagement"], ensure_ascii=False), record["author_hash"], record["source_url_raw"], record["thread_url"], record["source_content_id"],
            record["source_comment_id"], record["parent_comment_id"], record["address_type"], state_label(record["collection_status"]), record["observed_version"],
            record["observed_device"], record["screenshot_ref"], record["analysis_eligible"], record["exclusion_reason"], record["manual_confirmation"],
            record["content_hash"], record["notes"],
        ])
    return headers, rows


def make_thread_rows(records: list[dict[str, Any]]) -> list[list[Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["thread_url"]].append(record)
    rows = []
    for url, group in sorted(grouped.items()):
        first = group[0]
        rows.append([
            PLATFORM_LABELS.get(first["platform"], first["platform"]), first["competitor"], first["product"], url,
            first["source_content_id"], min((item["published_at"] or "" for item in group), default="") or None,
            len(group), sum(1 for item in group if item["analysis_eligible"]), state_label(first["collection_status"]),
        ])
    return rows


def make_coverage_rows(tasks: list[dict[str, Any]]) -> list[list[Any]]:
    rows = []
    for task in tasks:
        rows.append([
            task["task_id"], PLATFORM_LABELS.get(task["platform"], task["platform"]), task["competitor"], task["query_text"], task["month_start"],
            task["month_end"], state_label(task["status"]), task["checkpoint_json"], task["last_error"], task["updated_at"],
        ])
    return rows


def write_workbook(context: dict[str, Any], summary: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = xlsxwriter.Workbook(str(path))
    workbook.set_properties({"title": f"竞品特性 VOC 原始数据 - {context['study']['subject']}", "comments": "来源地址由采集记录保留；请勿将其视作总体样本。"})
    try:
        info = [
            ["研究课题", context["study"]["subject"]], ["目标功能", context["study"]["feature_name"]],
            ["时间范围", f"{context['study']['start_date']} 至 {context['study']['end_date']}"], ["支持平台", "微博、小红书、酷安"],
            ["原声总数", summary["record_count"]], ["进入分析原声数", summary["eligible_count"]],
            ["数据口径", "近两年当前可访问、可发现且可读取的公开内容；不代表平台数据库全量或市场总体。"],
        ]
        write_table_sheet(workbook, "研究说明", ["字段", "值"], info, [18, 110])

        summary_headers = ["竞品", "VOC主题", "观点倾向", "有效原声数", "独立原帖数", "覆盖平台数", "平台", "最近出现时间", "代表原声记录ID"]
        summary_rows = [[item["competitor"], item["theme"], item["stance"], item["voice_count"], item["thread_count"], item["platform_count"], "、".join(item["platforms"]), item["latest_at"], "、".join(item["record_ids"][:10])] for item in summary["themes"]]
        write_table_sheet(workbook, "VOC汇总", summary_headers, summary_rows, [16, 24, 14, 12, 12, 12, 18, 18, 44])

        raw_headers, raw_rows = records_to_rows(context["records"])
        platform_rows: dict[str, list[list[Any]]] = defaultdict(list)
        for record, row in zip(context["records"], raw_rows):
            platform_rows[record["platform"]].append(row)
        for platform, rows in sorted(platform_rows.items()):
            label = PLATFORM_LABELS.get(platform, platform)
            for index in range(0, len(rows), XLSX_ROW_LIMIT):
                suffix = "" if len(rows) <= XLSX_ROW_LIMIT else f"_{index // XLSX_ROW_LIMIT + 1}"
                write_table_sheet(workbook, f"用户原声_{label}{suffix}", raw_headers, rows[index:index + XLSX_ROW_LIMIT], [18, 11, 14, 18, 20, 48, 12, 12, 20, 20, 20, 20, 20, 18, 18, 20, 24, 42, 42, 18, 18, 18, 14, 14, 16, 16, 22, 12, 20, 12, 64, 30])

        write_table_sheet(workbook, "帖子索引", ["平台", "竞品", "产品/App", "原帖真实地址", "帖子ID", "最早原声时间", "采集原声数", "有效VOC数", "采集状态"], make_thread_rows(context["records"]), [12, 16, 18, 42, 18, 18, 12, 12, 16])
        theme_rows = [[item["competitor"], item["theme"], item["stance"], item["voice_count"], item["thread_count"], "、".join(item["platforms"]), "、".join(item["record_ids"])] for item in summary["themes"]]
        write_table_sheet(workbook, "主题编码", ["竞品", "主题", "观点倾向", "原声数", "独立原帖数", "平台", "原声记录ID"], theme_rows, [16, 30, 14, 12, 14, 20, 58])
        write_table_sheet(workbook, "采集覆盖", ["任务ID", "平台", "竞品", "查询词", "月起始", "月结束", "任务状态", "断点", "最后错误", "最后任务更新时间"], make_coverage_rows(context["tasks"]), [56, 12, 16, 36, 14, 14, 18, 42, 30, 20])
        gap_rows = [[gap["gap_id"], PLATFORM_LABELS.get(gap["platform"], gap["platform"]), gap["competitor"], gap["month_start"], gap["stage"], gap["error_type"], gap["raw_url"], gap["detail"], gap["occurred_at"]] for gap in context["gaps"]]
        write_table_sheet(workbook, "采集缺口", ["缺口ID", "平台", "竞品", "月份", "阶段", "错误类型", "原始地址", "详情", "最后发生时间"], gap_rows, [50, 12, 16, 14, 16, 20, 42, 42, 20])
        field_rows = [
            ["原始公开地址", "source_url_raw", "采集时平台实际提供的公开地址；不得替换为搜索页或伪造链接。"],
            ["所属原帖地址", "thread_url", "没有评论直链时，用于定位原声的真实原帖地址。"],
            ["地址类型", "address_type", "direct_comment、parent_thread 或 thread。"],
            ["可进入分析", "analysis_eligible", "仅直接涉及目标竞品功能且具有真实来源的原声可进入正式分析。"],
            ["采集状态", "collection_status", "可访问、需登录、已删除、受限等采集时状态。"],
        ]
        write_table_sheet(workbook, "字段说明", ["工作簿字段", "机器字段", "说明"], field_rows, [20, 24, 80])
    finally:
        workbook.close()


def quote_link(record: dict[str, Any]) -> str:
    url = html.escape(record["source_url_raw"], quote=True)
    text = html.escape(short_text(record["original_text"]))
    location = "评论直链" if record["address_type"] == "direct_comment" else "原帖定位"
    return f'<a href="{url}" target="_blank" rel="noreferrer">{text}</a><span class="location">{location}</span>'


def write_html(context: dict[str, Any], summary: dict[str, Any], path: Path) -> None:
    study = context["study"]
    eligible = [record for record in context["records"] if record["analysis_eligible"]]
    cards = "".join(
        f'<article class="card"><span>{html.escape(label)}</span><strong>{count:,}</strong></article>'
        for label, count in [("原声总数", summary["record_count"]), ("进入分析", summary["eligible_count"]), ("VOC 主题", len(summary["themes"])), ("采集缺口", len(context["gaps"]))]
    )
    theme_rows = "".join(
        "<tr>"
        f"<td>{html.escape(item['competitor'])}</td><td>{html.escape(item['theme'])}</td><td>{html.escape(item['stance'])}</td>"
        f"<td>{item['voice_count']}</td><td>{item['thread_count']}</td><td>{html.escape('、'.join(item['platforms']))}</td>"
        f"<td>{html.escape(item['latest_at'] or '未标注')}</td><td>{html.escape('、'.join(item['record_ids'][:5]))}</td>"
        "</tr>"
        for item in summary["themes"]
    ) or '<tr><td colspan="8">暂无已编码的可分析原声。</td></tr>'
    evidence_rows = []
    for record in eligible:
        evidence_rows.append(
            f'<tr data-platform="{html.escape(record["platform"])}" data-competitor="{html.escape(record["competitor"])}" data-theme="{html.escape(record["theme"] or "未编码")}">'
            f'<td>{html.escape(record["record_id"][:12])}</td><td>{html.escape(PLATFORM_LABELS.get(record["platform"], record["platform"]))}</td>'
            f'<td>{html.escape(record["competitor"])}</td><td>{html.escape(record["theme"] or "未编码")}</td><td>{html.escape(record["stance"] or "未标注")}</td>'
            f'<td>{html.escape(record["published_at"] or "未标注")}</td><td>{quote_link(record)}</td></tr>'
        )
    platform_options = "".join(f'<option value="{key}">{html.escape(label)}</option>' for key, label in PLATFORM_LABELS.items())
    competitor_options = "".join(f'<option value="{html.escape(value)}">{html.escape(value)}</option>' for value in sorted({record["competitor"] for record in eligible}))
    coverage_rows = "".join(
        f"<tr><td>{html.escape(item['platform'])}</td><td>{html.escape(item['competitor'])}</td><td>{html.escape(json.dumps({state_label(key): value for key, value in item.items() if key not in {'platform', 'competitor'}}, ensure_ascii=False))}</td></tr>"
        for item in summary["coverage"]
    ) or '<tr><td colspan="3">尚未写入采集进度。</td></tr>'
    html_doc = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>竞品特性 VOC 报告 - {html.escape(study['subject'])}</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;margin:0;background:#f5f7fa;color:#172033;line-height:1.55}}main{{max-width:1400px;margin:auto;padding:32px}}h1{{margin:0 0 6px}}h2{{margin-top:36px}}.muted{{color:#617087}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin:24px 0}}.card{{background:white;border:1px solid #dce3ed;border-radius:10px;padding:16px}}.card span{{display:block;color:#617087;font-size:14px}}.card strong{{font-size:30px}}section{{background:white;border:1px solid #dce3ed;border-radius:10px;padding:20px;margin-top:18px;overflow:auto}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{border-bottom:1px solid #e5eaf0;text-align:left;vertical-align:top;padding:10px}}th{{background:#edf3fa;white-space:nowrap}}a{{color:#075cc7}}.location{{display:block;color:#617087;font-size:12px;margin-top:4px}}.filters{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px}}select,input{{padding:8px;border:1px solid #b9c5d4;border-radius:6px;background:white}}.method{{background:#fff9e8;border-left:4px solid #d99c00;padding:12px}}@media print{{body{{background:white}}main{{padding:0}}section{{break-inside:avoid;border:0}}}}
</style></head><body><main>
<header><h1>竞品特性 VOC 报告</h1><p class="muted">{html.escape(study['subject'])} · 目标功能：{html.escape(study['feature_name'])} · {html.escape(study['start_date'])} 至 {html.escape(study['end_date'])}</p></header>
<div class="cards">{cards}</div>
<section class="method"><strong>数据口径：</strong>本报告汇总微博、小红书、酷安中近两年当前可访问、可发现且可读取的公开内容。它反映本次采集样本中的用户原声，不代表平台数据库全量、市场份额或总体满意度。每条正式证据均可回查到原始公开地址。</section>
<section><h2>VOC 主题对比</h2><table><thead><tr><th>竞品</th><th>主题</th><th>观点</th><th>原声数</th><th>原帖数</th><th>平台</th><th>最近出现</th><th>代表记录</th></tr></thead><tbody>{theme_rows}</tbody></table></section>
<section><h2>采集覆盖</h2><table><thead><tr><th>平台</th><th>竞品</th><th>任务状态</th></tr></thead><tbody>{coverage_rows}</tbody></table></section>
<section><h2>用户原声证据</h2><div class="filters"><label>平台 <select id="platform"><option value="">全部</option>{platform_options}</select></label><label>竞品 <select id="competitor"><option value="">全部</option>{competitor_options}</select></label><label>主题 <input id="theme" placeholder="搜索主题"></label></div><table id="evidence"><thead><tr><th>记录ID</th><th>平台</th><th>竞品</th><th>主题</th><th>观点</th><th>发布时间</th><th>用户原声与真实地址</th></tr></thead><tbody>{''.join(evidence_rows) or '<tr><td colspan="7">暂无可分析原声。</td></tr>'}</tbody></table></section>
<section><h2>局限与缺口</h2><p>采集缺口共 {len(context['gaps'])} 条。链接失效、内容删除、登录限制、验证码、风控、分页差异及搜索未收录内容均不会被视为已覆盖。完整缺口明细位于原始数据工作簿的“采集缺口”表。</p></section>
</main><script>const f=()=>{{const p=document.querySelector('#platform').value,c=document.querySelector('#competitor').value,t=document.querySelector('#theme').value.trim().toLowerCase();document.querySelectorAll('#evidence tbody tr').forEach(r=>{{const ok=(!p||r.dataset.platform===p)&&(!c||r.dataset.competitor===c)&&(!t||r.dataset.theme.toLowerCase().includes(t));r.style.display=ok?'':'none'}})}};document.querySelectorAll('#platform,#competitor,#theme').forEach(e=>e.addEventListener(e.tagName==='INPUT'?'input':'change',f));</script></body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_doc, encoding="utf-8")


def write_coverage_json(context: dict[str, Any], summary: dict[str, Any], path: Path) -> None:
    payload = {"study_id": context["study"]["study_id"], "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"), "task_state_summary": summary["task_states"], "coverage": summary["coverage"], "gaps": context["gaps"]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_evidence_pack(records: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            if not record["analysis_eligible"]:
                continue
            payload = {
                "record_id": record["record_id"], "competitor": record["competitor"], "product": record["product"], "feature_path": record["feature_path"],
                "claim": record["theme"] or "未编码用户原声", "stance": record["stance"], "source_tier": 4, "source_type": "user_voice",
                "source_url": record["source_url_raw"], "thread_url": record["thread_url"], "published_at": record["published_at"],
                "quote_or_fact": record["original_text"], "confidence": "C", "manual_confirmation": True,
            }
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def export_deliverables(db_path: Path, study_id: str, out_dir: Path) -> dict[str, str]:
    conn = connect(db_path)
    try:
        context = load_context(conn, study_id)
    finally:
        conn.close()
    summary = build_summary(context)
    date_part = datetime.now().strftime("%Y-%m-%d")
    stem = safe_file_stem(context["study"]["subject"])[:72]
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"竞品特性VOC报告-{stem}-{date_part}.html"
    xlsx_path = out_dir / f"竞品特性VOC原始数据-{stem}-{date_part}.xlsx"
    coverage_path = out_dir / "coverage-report.json"
    evidence_path = out_dir / "evidence-pack.jsonl"
    write_html(context, summary, html_path)
    write_workbook(context, summary, xlsx_path)
    write_coverage_json(context, summary, coverage_path)
    write_evidence_pack(context["records"], evidence_path)
    return {"html": str(html_path.resolve()), "xlsx": str(xlsx_path.resolve()), "coverage": str(coverage_path.resolve()), "evidence_pack": str(evidence_path.resolve())}


def main() -> int:
    parser = argparse.ArgumentParser(description="导出竞品特性 VOC HTML 报告与 XLSX 原始数据")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--study-id", required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("workspace/竞品用户洞察/outputs"))
    args = parser.parse_args()
    try:
        print(json.dumps(export_deliverables(args.db, args.study_id, args.out_dir), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

