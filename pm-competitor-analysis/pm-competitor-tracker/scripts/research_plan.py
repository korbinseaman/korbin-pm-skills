#!/usr/bin/env python3
"""根据 JSON 信息源配置生成竞品系统应用研究计划。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES_PATH = SKILL_ROOT / "references" / "competitor-sources.json"


def load_source_config(path: Path = DEFAULT_SOURCES_PATH) -> dict:
    """读取信息源 JSON；仅校验研究计划依赖的顶层结构。"""
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    if not isinstance(config.get("vendors"), dict) or not config["vendors"]:
        raise ValueError("competitor-sources.json must contain a non-empty vendors object")
    return config


def _parse_datetime(value: str | None, tz: ZoneInfo) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed.astimezone(tz)


def calculate_time_window(
    mode: str,
    run_at: datetime,
    last_success_at: datetime | None = None,
) -> dict:
    """计算目标统计周期和带重叠的搜索窗口。"""
    tz = run_at.tzinfo
    day_start = datetime.combine(run_at.date(), time.min, tzinfo=tz)

    if mode == "daily":
        period_end_exclusive = day_start
        period_start = period_end_exclusive - timedelta(days=1)
        overlap = timedelta(hours=24)
        late_backfill_days = 7
    elif mode == "weekly":
        current_week_start = day_start - timedelta(days=run_at.weekday())
        period_end_exclusive = current_week_start
        period_start = current_week_start - timedelta(days=7)
        overlap = timedelta(hours=48)
        late_backfill_days = 14
    else:
        raise ValueError("mode must be 'daily' or 'weekly'")

    search_start = period_start - overlap
    if last_success_at:
        catchup_start = max(
            last_success_at - overlap,
            run_at - timedelta(days=late_backfill_days),
        )
        search_start = min(search_start, catchup_start)

    return {
        "run_id": f"{run_at.strftime('%Y%m%dT%H%M%S%z')}-{mode}",
        "mode": mode,
        "period_start": period_start.isoformat(),
        "period_end": (period_end_exclusive - timedelta(microseconds=1)).isoformat(),
        "query_start": search_start.isoformat(),
        "query_end": run_at.isoformat(),
        "overlap_hours": int(overlap.total_seconds() // 3600),
        "late_backfill_days": late_backfill_days,
        "inclusion_rule": (
            "收录目标周期内发布的信息；历史 changelog 中不存在、但本次首次发现且发布时间不早于"
            f"最近 {late_backfill_days} 天的信息可作为补录。"
        ),
        "delivery_rule": (
            "通过 changelog 稳定 ID 去重；日报只推送本次新增/更新，周报按功能分类汇总目标周内容。"
        ),
    }


def _render_query(template: str, vendor: str, app_name: str, year: int) -> str:
    return template.format(vendor=vendor, app_name=app_name, year=year)


def generate_plan(
    app_name: str,
    mode: str,
    run_at: datetime,
    last_success_at: datetime | None = None,
    source_config: dict | None = None,
) -> dict:
    """生成针对指定系统应用的研究计划。"""
    config = source_config or load_source_config()
    vendors = {}
    fallback_templates = config.get("fallback_search_queries", [])
    domestic_templates = config.get("domestic_search_queries", [])

    for vendor_name, vendor_config in config["vendors"].items():
        query_templates = vendor_config.get("search_queries") or fallback_templates
        search_keywords = [
            _render_query(template, vendor_name, app_name, run_at.year)
            for template in query_templates
        ]
        sources = sorted(
            vendor_config.get("sources", []),
            key=lambda source: (source.get("priority", 99), source.get("name", "")),
        )
        icon_path = vendor_config.get("icon_path")
        resolved_icon_path = str((SKILL_ROOT / icon_path).resolve()) if icon_path else None
        vendors[vendor_name] = {
            "platform": vendor_config.get("platform"),
            "display_name": vendor_config.get("display_name", vendor_name),
            "icon_path": resolved_icon_path,
            "base_sources": sources,
            "search_keywords": search_keywords,
        }

    time_window = calculate_time_window(mode, run_at, last_success_at)
    return {
        "run_id": time_window["run_id"],
        "mode": mode,
        "time_window": time_window,
        "app_name": app_name,
        "generated_at": run_at.isoformat(),
        "source_config": str(DEFAULT_SOURCES_PATH),
        "vendors": vendors,
        "shared_sources": sorted(
            config.get("shared_sources", []),
            key=lambda source: (source.get("priority", 99), source.get("name", "")),
        ),
        "fallback_search_keywords": [
            _render_query(template, "{vendor}", app_name, run_at.year)
            for template in fallback_templates
        ],
        "domestic_search_keywords": [
            _render_query(template, "{vendor}", app_name, run_at.year)
            for template in domestic_templates
        ],
        "instructions": [
            "1. 按 priority 从低到高选择每个 vendor 的 base_sources，优先抓取官方来源",
            "2. 对每个 vendor 的 search_keywords 执行 web_search 补充搜索",
            "3. 按 time_window 查询，并用本地 changelog 的稳定 ID 去重",
            "4. 综合所有发现，按 🆕/💬/📰 分类整理",
        ],
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="竞品系统应用动态追踪 — 研究计划生成器")
    parser.add_argument("--app", required=True, help="系统应用名称，如：照片、备忘录、设置")
    parser.add_argument("--mode", choices=["daily", "weekly"], default="daily", help="日报或周报模式")
    parser.add_argument("--run-at", default=None, help="运行时间 ISO 8601；默认当前时间")
    parser.add_argument("--last-success-at", default=None, help="上次成功运行时间 ISO 8601")
    parser.add_argument("--timezone", default="Asia/Shanghai", help="IANA 时区，默认 Asia/Shanghai")
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES_PATH, help="信息源 JSON 路径")
    args = parser.parse_args()

    try:
        tz = ZoneInfo(args.timezone)
        run_at = _parse_datetime(args.run_at, tz) or datetime.now(tz)
        last_success_at = _parse_datetime(args.last_success_at, tz)
        plan = generate_plan(
            args.app,
            args.mode,
            run_at,
            last_success_at,
            load_source_config(args.sources),
        )
        plan["source_config"] = str(args.sources.resolve())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
