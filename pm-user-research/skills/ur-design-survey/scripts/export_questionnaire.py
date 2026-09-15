#!/usr/bin/env python3
"""Generate AI-simulator and Wenjuanxing text exports from questionnaire.md."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


QUESTION = re.compile(r"^(Q\d+)【([^】]+)】（(必填|选填)）(.+)$")
CONFIG = re.compile(r"^-\s*(题目关联|跳题逻辑|选项关联|填写提示)：\s*(.+)$")
RULE_LABELS = {
    "题目关联": "显示条件",
    "跳题逻辑": "跳转规则",
    "选项关联": "动态选项",
    "填写提示": "作答提示",
}
WJX_TYPES = {
    "单选题": "单选题",
    "多选题": "多选题",
    "Top-N题": "多选题",
    "填空题": "填空题",
    "开放题": "填空题",
    "量表题": "量表题",
    "排序题": "排序题",
    "矩阵量表题": "矩阵量表题",
}


@dataclass
class Question:
    qid: str
    qtype: str
    required: str
    stem: str
    body: list[str]


@dataclass
class Survey:
    title: str
    preamble: list[str]
    questions: list[Question]
    closing: list[str]


def parse_source(path: Path) -> Survey:
    lines = path.read_text(encoding="utf-8").splitlines()
    title = next((line[2:].strip() for line in lines if line.startswith("# ")), path.stem)
    preamble: list[str] = []
    closing: list[str] = []
    questions: list[Question] = []
    current: Question | None = None
    in_closing = False

    for line in lines:
        match = QUESTION.match(line.strip())
        if match and not in_closing:
            if current:
                questions.append(current)
            current = Question(match.group(1), match.group(2), match.group(3), match.group(4), [])
            continue
        if current and line.startswith("## ") and ("结束语" in line or "提前结束" in line):
            questions.append(current)
            current = None
            in_closing = True
        if in_closing:
            closing.append(line)
        elif current:
            current.body.append(line)
        else:
            preamble.append(line)
    if current:
        questions.append(current)
    if not questions:
        raise ValueError("未识别到形如 Q1【单选题】（必填）题干 的题目")
    if len({item.qid for item in questions}) != len(questions):
        raise ValueError("问卷中存在重复题号")
    return Survey(title, preamble, questions, closing)


def respondent_description(preamble: list[str]) -> str:
    parts = []
    for line in preamble:
        stripped = line.strip()
        if stripped.startswith(">") and "配置注记" not in stripped:
            parts.append(stripped.lstrip("> "))
    return " ".join(parts)


def necessary_context(preamble: list[str]) -> list[str]:
    result: list[str] = []
    in_research_note = False
    for line in preamble:
        if line.strip() == "## 研究说明":
            in_research_note = True
            continue
        if in_research_note and line.startswith("## "):
            in_research_note = False
        stripped = line.strip()
        if in_research_note and stripped and not stripped.startswith(">"):
            result.append(stripped)
    return result


def split_question_body(body: list[str]) -> tuple[list[tuple[str, str]], list[str]]:
    rules: list[tuple[str, str]] = []
    content: list[str] = []
    for line in body:
        match = CONFIG.match(line.strip())
        if match:
            rules.append((RULE_LABELS[match.group(1)], match.group(2).strip()))
        else:
            content.append(line)
    while content and not content[0].strip():
        content.pop(0)
    while content and not content[-1].strip():
        content.pop()
    return rules, content


def simulator_markdown(survey: Survey) -> str:
    lines = [
        f"# {survey.title}",
        "",
        "> 仅依据用户画像、问卷材料和普通常识按题序作答；先执行题干后的规则，被隐藏或跳过的题目写“未作答”，不要猜测研究者期待的答案。",
    ]
    context = necessary_context(survey.preamble)
    if context:
        lines.extend(["", "## 必要背景", "", *context])
    for question in survey.questions:
        rules, content = split_question_body(question.body)
        lines.extend(["", f"{question.qid}【{question.qtype}】（{question.required}）{question.stem}", ""])
        for label, rule in rules:
            lines.append(f"> 【{label}】{rule}")
        if rules and content:
            lines.append("")
        lines.extend(content)
    lines.extend(["", "## 问卷结束"])
    return "\n".join(lines).rstrip() + "\n"


def top_level_options(body: list[str]) -> list[str]:
    options = []
    for line in body:
        stripped = line.strip()
        if CONFIG.match(stripped):
            continue
        if line.startswith("- ") and not re.match(r"^-\s*(评价对象|评价选项)：", line):
            options.append(line[2:].strip())
    return options


def matrix_parts(body: list[str]) -> tuple[list[str], list[str]]:
    rows: list[str] = []
    columns: list[str] = []
    target: list[str] | None = None
    for line in body:
        stripped = line.strip()
        if stripped == "- 评价对象：":
            target = rows
        elif stripped == "- 评价选项：":
            target = columns
        elif line.startswith("  - ") and target is not None:
            target.append(line[4:].strip())
        elif stripped and not line.startswith("  "):
            target = None
    return rows, columns


def scale_range(question: Question) -> str | None:
    match = re.search(r"(\d+)\s*[–—~-]\s*(\d+)\s*分", question.stem)
    return f"{match.group(1)}~{match.group(2)}" if match else None


def wenjuanxing_text(survey: Survey) -> tuple[str, list[str]]:
    description = respondent_description(survey.preamble)
    lines = [survey.title]
    if description:
        lines.append(description)
    lines.extend(["===", ""])
    warnings: list[str] = []

    for index, question in enumerate(survey.questions, start=1):
        wjx_type = WJX_TYPES.get(question.qtype)
        if not wjx_type:
            raise ValueError(f"{question.qid} 的题型“{question.qtype}”没有已验证的问卷星文本映射")
        lines.append(f"{index}. {question.stem} [{wjx_type}]")
        if question.qtype == "矩阵量表题":
            rows, columns = matrix_parts(question.body)
            if not rows or not columns:
                raise ValueError(f"{question.qid} 缺少“评价对象/评价选项”，无法生成矩阵量表题")
            lines.append("行：")
            lines.extend(f"- {item}" for item in rows)
            lines.append("列：")
            lines.extend(f"- {item}" for item in columns)
        elif question.qtype == "量表题":
            value_range = scale_range(question)
            if not value_range:
                raise ValueError(f"{question.qid} 量表题题干未提供可识别的数值范围")
            lines.append(value_range)
        elif wjx_type not in {"填空题"}:
            options = top_level_options(question.body)
            if not options:
                raise ValueError(f"{question.qid} 没有可导入的选项")
            lines.extend(f"{number}. {option}" for number, option in enumerate(options, start=1))
        rules, _ = split_question_body(question.body)
        if rules or question.required:
            warnings.append(f"{question.qid}：导入后复核必填状态及逻辑配置")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n", warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="从 questionnaire.md 生成模拟作答版和问卷星导入版")
    parser.add_argument("questionnaire", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    source = args.questionnaire.resolve()
    output_dir = (args.output_dir or source.parent).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    survey = parse_source(source)
    simulator = output_dir / "questionnaire_for_simulator.md"
    wenjuanxing = output_dir / "questionnaire_for_wenjuanxing.txt"
    simulator.write_text(simulator_markdown(survey), encoding="utf-8")
    wjx_text, warnings = wenjuanxing_text(survey)
    wenjuanxing.write_text(wjx_text, encoding="utf-8")
    print(json.dumps({
        "source": str(source),
        "question_count": len(survey.questions),
        "simulator": str(simulator),
        "wenjuanxing": str(wenjuanxing),
        "post_import_review": warnings,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
