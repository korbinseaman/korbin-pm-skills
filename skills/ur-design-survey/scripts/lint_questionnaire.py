#!/usr/bin/env python3
"""Lint a Markdown questionnaire for common wording and structure problems.

This is a heuristic checker, not a semantic validator. It flags risk signals
that a human reviewer should confirm; it never claims a question is invalid.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VAGUE_TIME = ("经常", "偶尔", "常常", "时不时", "通常")
LEADING = ("显然", "方便", "先进", "高效", "智能", "你是否同意", "你是否认为", "难道")
DOUBLE_BARREL = ("并且", "以及", "同时", "还有", "和")  # 仅作风险信号，需人工确认
ABSOLUTE = ("总是", "从不", "所有人", "一定", "绝对")
QUESTION_START = re.compile(r"^(?:#{2,4}\s*)?(Q\d+)(?:\s*[｜|]\s*.+|\s*【[^】]+】.+)\s*$")
INLINE_QUESTION = re.compile(r"^(Q\d+)【([^】]+)】\s*(.+?)\s*$")
REQUIREDNESS_MARKER = re.compile(r"^（(?:必填|选填)）")
EMPTY_CONFIGURATION = re.compile(
    r"(?m)^\s*-\s*(题目关联|跳题逻辑|选项关联|填写提示)\s*：\s*(?:无(?:[。（]|$)|不适用(?:[。（]|$))"
)


def issues_for(text: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for word in VAGUE_TIME:
        if word in text and not re.search(r"过去\s*\d+|最近一次|过去\d+天|过去\d+个月", text):
            found.append(("vague_time", f"出现模糊时间词「{word}」且未见明确时间窗"))
    for word in LEADING:
        if word in text:
            found.append(("leading_wording", f"出现诱导或暗示性措辞「{word}」"))
    for word in ABSOLUTE:
        if word in text:
            found.append(("absolute_wording", f"出现绝对化措辞「{word}」"))
    for word in DOUBLE_BARREL:
        if word in text:
            found.append(("possible_double_barrel", f"出现并列连词「{word}」，需确认是否一题多概念"))
    return found


def lint(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    question_ids = [match.group(1) for line in lines if (match := QUESTION_START.match(line))]
    question_blocks: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        match = QUESTION_START.match(line)
        if match:
            current = match.group(1)
            question_blocks.setdefault(current, [line])
        elif line.startswith("## "):
            current = None
        elif current:
            question_blocks[current].append(line)

    issues: list[dict] = []
    if not question_ids:
        issues.append({"type": "no_questions", "question_id": None, "message": "未发现 Q1… 编号的题目"})

    for qid in sorted(set(question_ids)):
        block_lines = question_blocks.get(qid, [])
        block = "\n".join(block_lines)
        inline = INLINE_QUESTION.match(block_lines[0]) if block_lines else None
        raw_stem = inline.group(3).strip() if inline else next((
            line.strip() for line in block_lines[1:]
            if line.strip()
            and not line.lstrip().startswith(("#", "-", "*", ">", "【", "["))
        ), "")
        stem = REQUIREDNESS_MARKER.sub("", raw_stem, count=1).strip()
        for code, message in issues_for(stem):
            issues.append({"type": code, "question_id": qid, "message": message})
        if not re.search(r"题型|类型|单选|多选|量表|排序|开放|填空", block):
            issues.append({"type": "missing_type", "question_id": qid, "message": "未标注题型"})
        if not stem:
            issues.append({"type": "missing_stem", "question_id": qid, "message": "缺少题干"})
        if not REQUIREDNESS_MARKER.match(raw_stem):
            issues.append({
                "type": "missing_required_marker",
                "question_id": qid,
                "message": "题干缺少“（必填）”或“（选填）”标记",
            })
        if re.search(r"(?m)^\s*-\s*是否必答\s*：", block):
            issues.append({
                "type": "separate_required_setting",
                "question_id": qid,
                "message": "不应单列“是否必答”，请将必填/选填标记放入题干",
            })
        for match in EMPTY_CONFIGURATION.finditer(block):
            issues.append({
                "type": "empty_configuration",
                "question_id": qid,
                "message": f"配置项「{match.group(1)}」没有实际内容，应直接省略",
            })

    if re.search(r"诱导|暗示", text):
        issues.append({"type": "leading_wording", "question_id": None, "message": "正文出现「诱导/暗示」类风险措辞"})

    passed = not any(
        item["type"] in {
            "no_questions",
            "missing_type",
            "missing_stem",
            "missing_required_marker",
            "separate_required_setting",
            "empty_configuration",
        }
        for item in issues
    )
    return {
        "file": str(path),
        "question_count": len(set(question_ids)),
        "issues": issues,
        "risk_count": len(issues),
        "passed": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 Markdown 问卷的常见措辞与结构问题")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = lint(args.input)
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(_render(result))
    return 0 if result["passed"] else 1


def _render(result: dict) -> str:
    lines = [
        f"问卷质量检查：{result['file']}",
        f"题目数：{result['question_count']}，风险信号：{result['risk_count']}",
    ]
    for item in result["issues"]:
        qid = item.get("question_id") or "-"
        lines.append(f"- [{item['type']}] {qid}: {item['message']}")
    lines.append("结论：" + ("通过（无结构阻断）" if result["passed"] else "不通过（存在结构缺失）"))
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
