#!/usr/bin/env python3
"""为“竞品 × Feature” Research Unit 生成确定性的检索 Query Set。

本脚本不直接调用搜索引擎，只负责生成与具体供应商无关的查询计划，
后续可由 Agent、浏览器工具或外部检索 Worker 执行。
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, List


def clean(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(x).strip() for x in value if str(x).strip())
    return str(value).strip()


def build_queries(unit: Dict) -> Dict[str, List[str]]:
    competitor = clean(unit.get("competitor"))
    app = clean(unit.get("app"))
    feature = clean(unit.get("feature_name") or unit.get("feature"))
    topic = clean(unit.get("topic"))
    region = clean(unit.get("region"))
    version = clean(unit.get("version"))

    suffix = " ".join(x for x in [region, version] if x)
    base = " ".join(x for x in [competitor, app, feature] if x)
    user_task = " ".join(x for x in [competitor, app, topic, feature] if x)

    # 不预置厂商 site: 域名，避免官方域名变化或不同地区域名导致漏检。
    # Query 中保留部分英文检索词，是为了覆盖国际厂商官方帮助与评测资料。
    return {
        "official": [
            f"{base} official support {suffix}".strip(),
            f"{base} user guide {suffix}".strip(),
        ],
        "user_task": [
            f"{user_task} how to {suffix}".strip(),
            f"{competitor} {feature} settings menu {suffix}".strip(),
        ],
        "ui": [
            f"{base} screenshot UI {suffix}".strip(),
            f"{base} demo video {suffix}".strip(),
        ],
        "negative": [
            f"{base} not supported limitation {suffix}".strip(),
            f"{base} cannot {feature} {suffix}".strip(),
        ],
        "quantitative": [
            f"{base} benchmark accuracy usage rate latency count {suffix}".strip(),
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="生成 Research Unit 的多类型检索 Query Set")
    parser.add_argument("--input", help="包含单个 ResearchUnit 的 JSON 文件；不传则从 stdin 读取。")
    parser.add_argument("--output", help="输出 JSON 文件；不传则输出到 stdout。")
    args = parser.parse_args()

    if args.input:
        unit = json.loads(open(args.input, "r", encoding="utf-8").read())
    else:
        unit = json.load(sys.stdin)

    result = dict(unit)
    result["query_sets"] = build_queries(unit)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        open(args.output, "w", encoding="utf-8").write(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
