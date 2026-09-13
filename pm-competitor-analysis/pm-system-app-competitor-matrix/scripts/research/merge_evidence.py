#!/usr/bin/env python3
"""对归一化证据按 Research Unit 分组/去重，并识别冲突与缺失。

本脚本刻意不负责最终判断产品是否支持某项能力；它只为上层推理准备证据摘要，
并标出需要人工复核或进一步检索的情况。
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from typing import Dict, List, Tuple


def read_jsonl(path: str) -> List[Dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def key(r: Dict) -> Tuple[str, str]:
    return str(r.get("competitor", "")), str(r.get("feature_id", ""))


def dedupe(records: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for r in records:
        sig = (
            r.get("source_url"), r.get("claim"), r.get("quote_or_fact"), r.get("support_direction")
        )
        if sig in seen:
            continue
        seen.add(sig)
        out.append(r)
    return out


def summarize(records: List[Dict]) -> Dict:
    records = dedupe(records)
    directions = {r.get("support_direction") for r in records if r.get("support_direction") in {"supports", "contradicts"}}
    conflict = directions == {"supports", "contradicts"}
    best_conf = "C"
    if any(r.get("confidence") == "A" for r in records):
        best_conf = "A"
    elif any(r.get("confidence") == "B" for r in records):
        best_conf = "B"
    return {
        "records": records,
        "record_count": len(records),
        "conflict": conflict,
        "best_confidence": best_conf,
        "manual_confirmation": conflict or best_conf in {"B", "C"},
    }


def main():
    p = argparse.ArgumentParser(description="合并/去重竞品证据，并识别冲突和缺失 Research Unit")
    p.add_argument("--input", required=True, help="已归一化的 EvidenceRecord JSONL")
    p.add_argument("--output", required=True, help="分组后的证据摘要 JSON")
    p.add_argument("--units", help="可选：ResearchUnit JSONL，用于识别没有返回证据的检索单元")
    args = p.parse_args()

    records = read_jsonl(args.input)
    grouped = defaultdict(list)
    for r in records:
        grouped[key(r)].append(r)

    result = {
        "groups": [],
        "missing_units": [],
    }
    for (competitor, feature_id), rs in sorted(grouped.items()):
        s = summarize(rs)
        result["groups"].append({"competitor": competitor, "feature_id": feature_id, **s})

    if args.units:
        units = read_jsonl(args.units)
        present = set(grouped.keys())
        for u in units:
            k = (str(u.get("competitor", "")), str(u.get("feature_id", "")))
            if k not in present:
                result["missing_units"].append({
                    "unit_id": u.get("unit_id"),
                    "competitor": u.get("competitor"),
                    "feature_id": u.get("feature_id"),
                })

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
