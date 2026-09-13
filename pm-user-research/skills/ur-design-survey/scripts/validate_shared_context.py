#!/usr/bin/env python3
"""Validate the task-level user research shared context."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ALLOWED_HEADINGS = {
    "# 用户研究共享上下文", "## 任务信息", "## 目标用户", "## 确认信息",
    "### 全量候选群体", "### 已选目标群体", "### 纳入条件", "### 排除条件",
}


def field_value(lines: list[str], label: str) -> str:
    prefix = f"- {label}："
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return ""


def section_items(lines: list[str], heading: str) -> list[str]:
    try:
        start = lines.index(f"### {heading}") + 1
    except ValueError:
        return []
    items: list[str] = []
    for line in lines[start:]:
        if line.startswith("#"):
            break
        if line.startswith("- ") and line[2:].strip() not in {"", "无"}:
            items.append(line[2:].strip())
    return items


def parse(text: str) -> tuple[dict[str, Any], list[str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    issues: list[str] = []
    if not lines or lines[0] != "# 用户研究共享上下文":
        issues.append("文件标题必须为 用户研究共享上下文")
    unknown = [line for line in lines if line.startswith("#") and line not in ALLOWED_HEADINGS]
    if unknown:
        issues.append(f"包含非共享或可能造成画像偏差的章节: {', '.join(unknown)}")
    confirmed_exclusion = field_value(lines, "排除条件由用户明确确认")
    data = {
        "task_id": field_value(lines, "任务标识"),
        "topic": field_value(lines, "调研主题"),
        "audience_groups": section_items(lines, "全量候选群体"),
        "target_audience": {
            "selected_groups": section_items(lines, "已选目标群体"),
            "include": section_items(lines, "纳入条件"),
            "exclude": section_items(lines, "排除条件"),
            "exclude_confirmed_by_user": confirmed_exclusion == "是",
        },
        "confirmation": {"status": field_value(lines, "状态"), "confirmed_by": field_value(lines, "确认人")},
    }
    return data, issues


def validate(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not str(data.get("task_id") or "").strip():
        issues.append("task_id 不能为空")
    if not str(data.get("topic") or "").strip():
        issues.append("topic 不能为空")
    groups = data.get("audience_groups") or []
    if not isinstance(groups, list) or not groups:
        issues.append("audience_groups 必须是非空数组")
        groups = []
    target = data.get("target_audience") or {}
    selected = target.get("selected_groups") or []
    if not selected:
        issues.append("target_audience.selected_groups 不能为空")
    elif not set(selected).issubset(set(groups)):
        issues.append("selected_groups 必须属于 audience_groups")
    exclusions = target.get("exclude") or []
    if exclusions and target.get("exclude_confirmed_by_user") is not True:
        issues.append("非空 exclude 必须由用户明确确认")
    confirmation = data.get("confirmation") or {}
    if confirmation.get("status") != "已确认" or confirmation.get("confirmed_by") != "用户":
        issues.append("共享上下文必须由用户确认")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="校验任务级共享上下文")
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        if args.input.suffix.lower() != ".md":
            raise ValueError("输入文件必须是 shared_context.md")
        data, parse_issues = parse(args.input.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"passed": False, "issues": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2
    issues = parse_issues + validate(data)
    print(json.dumps({"passed": not issues, "issues": issues}, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
