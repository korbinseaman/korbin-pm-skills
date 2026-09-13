#!/usr/bin/env python3
"""将结构不完全一致的原始证据 JSONL 归一化为 EvidenceRecord 风格的 JSONL。"""
from __future__ import annotations

import argparse
import json
from typing import Dict


def get(d: Dict, *keys, default=None):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def normalize(raw: Dict) -> Dict:
    confidence = str(get(raw, "confidence", default="C")).upper()
    if confidence not in {"A", "B", "C"}:
        confidence = "C"
    manual = get(raw, "manual_confirmation", default=None)
    if manual is None:
        manual = confidence in {"B", "C"}

    return {
        "unit_id": get(raw, "unit_id", "id"),
        "competitor": get(raw, "competitor"),
        "feature_id": get(raw, "feature_id"),
        "claim": get(raw, "claim", "summary", default=""),
        "support_direction": get(raw, "support_direction", default="neutral"),
        "source_tier": int(get(raw, "source_tier", default=4)),
        "source_type": get(raw, "source_type", default="unknown"),
        "source_title": get(raw, "source_title", "title", default=""),
        "source_url": get(raw, "source_url", "url"),
        "publisher": get(raw, "publisher"),
        "published_at": get(raw, "published_at", "date"),
        "observed_version": get(raw, "observed_version", "version"),
        "observed_region": get(raw, "observed_region", "region"),
        "quote_or_fact": get(raw, "quote_or_fact", "fact"),
        "screenshot_path_or_ref": get(raw, "screenshot_path_or_ref", "screenshot"),
        "confidence": confidence,
        "manual_confirmation": bool(manual),
        "notes": get(raw, "notes"),
    }


def main():
    p = argparse.ArgumentParser(description="将原始证据 JSONL 归一化为统一 EvidenceRecord 结构")
    p.add_argument("--input", required=True, help="原始证据 JSONL 文件")
    p.add_argument("--output", required=True, help="归一化后的 EvidenceRecord JSONL 文件")
    args = p.parse_args()

    with open(args.input, "r", encoding="utf-8") as fin, open(args.output, "w", encoding="utf-8") as fout:
        for line_no, line in enumerate(fin, 1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit(f"第 {line_no} 行不是合法 JSONL：{e}")
            fout.write(json.dumps(normalize(raw), ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
