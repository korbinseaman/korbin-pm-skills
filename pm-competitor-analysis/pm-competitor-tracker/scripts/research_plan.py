#!/usr/bin/env python3
"""
竞品系统应用动态追踪 — 研究计划生成器

根据用户指定的系统应用名称，生成各厂商竞品的信息源 URL。

用法：
    python3 scripts/research_plan.py --app "{app_name}" [--week YYYY-WW]

示例：
    python3 scripts/research_plan.py --app "照片"
    python3 scripts/research_plan.py --app "备忘录"
    python3 scripts/research_plan.py --app "设置"

Agent 随后对每个 URL 执行 web_fetch 并用 web_search 补充搜索，综合发现。
"""

import argparse
import json
import sys
from datetime import datetime

# 厂商配置：通用基础源（适用于所有系统应用）
VENDOR_BASE_SOURCES = {
    "Apple": {
        "platform": "iOS / macOS",
        "base_sources": [
            ("Apple 新闻室", "https://www.apple.com/newsroom/", "产品/功能发布"),
            ("iOS/macOS 更新说明", "https://support.apple.com/en-us/HT201222", "系统级应用更新"),
            ("MacRumors", "https://www.macrumors.com/", "Apple 综合动态"),
        ],
        "search_keywords": [
            "Apple {app_name} update 2026",
            "Apple {app_name} new feature",
            "Apple {app_name} changes",
        ],
    },
    "Google": {
        "platform": "Android",
        "base_sources": [
            ("Google Blog", "https://blog.google/", "官方产品动态"),
            ("Android Authority", "https://www.androidauthority.com/", "Android 生态报道"),
            ("9to5Google", "https://9to5google.com/", "Google 产品报道"),
        ],
        "search_keywords": [
            "Google {app_name} update 2026",
            "Google {app_name} new feature",
            "Google {app_name} changelog",
        ],
    },
    "华为": {
        "platform": "HarmonyOS",
        "base_sources": [
            ("华为消费者官网", "https://consumer.huawei.com/cn/", "产品动态"),
            ("HarmonyOS 更新", "https://consumer.huawei.com/cn/support/harmonyos/", "系统版本更新"),
            ("花粉俱乐部", "https://club.huawei.com/", "用户反馈"),
        ],
        "search_keywords": [
            "华为 {app_name} 更新 2026",
            "HarmonyOS {app_name} 新功能",
            "华为 {app_name} 用户反馈",
        ],
    },
    "小米": {
        "platform": "HyperOS / Android",
        "base_sources": [
            ("小米社区", "https://www.xiaomi.cn/", "用户反馈"),
            ("HyperOS", "https://www.mi.com/hyperos", "系统更新"),
        ],
        "search_keywords": [
            "小米 {app_name} 更新 2026",
            "HyperOS {app_name} 新功能",
            "小米 {app_name} 社区讨论",
        ],
    },
    "OPPO": {
        "platform": "ColorOS / Android",
        "base_sources": [
            ("OPPO 社区", "https://www.oppo.cn/community/", "用户反馈"),
            ("ColorOS", "https://www.coloros.com/", "系统更新"),
        ],
        "search_keywords": [
            "OPPO {app_name} 更新 2026",
            "ColorOS {app_name} 新功能",
            "OPPO {app_name} 变化",
        ],
    },
    "VIVO": {
        "platform": "OriginOS / Android",
        "base_sources": [
            ("VIVO 社区", "https://community.vivo.com.cn/", "用户反馈"),
            ("OriginOS", "https://www.vivo.com.cn/originos", "系统更新"),
        ],
        "search_keywords": [
            "VIVO {app_name} 更新 2026",
            "OriginOS {app_name} 新功能",
            "VIVO {app_name} 社区",
        ],
    },
    "荣耀": {
        "platform": "MagicOS / Android",
        "base_sources": [
            ("荣耀俱乐部", "https://club.hihonor.com/cn/", "用户反馈"),
            ("MagicOS", "https://www.hihonor.com/cn/magic/", "系统更新"),
            ("荣耀官网", "https://www.hihonor.com/cn/", "综合动态"),
        ],
        "search_keywords": [
            "荣耀 {app_name} 更新 2026",
            "MagicOS {app_name} 新功能",
            "荣耀 {app_name} 用户反馈",
        ],
    },
    "三星": {
        "platform": "One UI / Android",
        "base_sources": [
            ("Samsung Newsroom", "https://news.samsung.com/", "官方新闻"),
            ("Samsung Members", "https://r1.community.samsung.com/", "用户社区"),
            ("One UI 支持", "https://www.samsung.com/us/support/mobile-support/", "系统更新"),
        ],
        "search_keywords": [
            "Samsung {app_name} update 2026",
            "Samsung {app_name} One UI",
            "Samsung {app_name} new feature",
        ],
    },
}


def generate_plan(app_name: str, week: str) -> dict:
    """生成针对指定系统应用的研究计划。"""
    vendors = {}
    for vendor_name, config in VENDOR_BASE_SOURCES.items():
        # 替换搜索关键词中的 {app_name}
        search_keywords = [kw.replace("{app_name}", app_name) for kw in config["search_keywords"]]

        # 生成应用特定的搜索 URL（用于 web_search 补充）
        search_urls = []
        for keyword in search_keywords:
            search_urls.append({
                "type": "web_search",
                "keyword": keyword,
                "purpose": f"搜索 {vendor_name} {app_name} 的最新动态",
            })

        vendors[vendor_name] = {
            "platform": config["platform"],
            "base_sources": [
                {"name": name, "url": url, "purpose": purpose}
                for name, url, purpose in config["base_sources"]
            ],
            "search_keywords": search_keywords,
        }

    return {
        "week": week,
        "app_name": app_name,
        "generated_at": datetime.now().isoformat(),
        "vendors": vendors,
        "instructions": [
            "1. 对每个 vendor 的 base_sources 执行 web_fetch 抓取",
            "2. 对每个 vendor 的 search_keywords 执行 web_search 补充搜索",
            "3. 综合所有发现，按 🆕/💬/📰 分类整理",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="竞品系统应用动态追踪 — 研究计划生成器")
    parser.add_argument("--app", required=True, help="系统应用名称，如：照片、备忘录、设置")
    parser.add_argument("--week", default=None, help="周数标识，如 2026-W17（默认当前周）")
    args = parser.parse_args()

    if args.week:
        week = args.week
    else:
        week = datetime.now().strftime("%Y-W%W")

    plan = generate_plan(args.app, week)
    print(json.dumps(plan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
