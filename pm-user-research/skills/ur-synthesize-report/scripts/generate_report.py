#!/usr/bin/env python3
"""Prepare and render an auditable report from the current survey artifacts."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import statistics
import sys
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree as ET


FIXED_COLUMNS = ["任务ID", "用户ID", "姓名", "实际模型", "状态"]
SUCCESS_STATUSES = {"completed", "complete", "success", "succeeded", "完成", "已完成", "成功"}
QUESTION_HEADING = re.compile(r"^##\s+(Q[A-Za-z0-9_.-]+)(?:\s*[｜|]\s*(.+))?$")
Q_COLUMN = re.compile(r"^(Q[A-Za-z0-9_.-]+)(?:_回答原因)?$")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} 顶层必须是对象")
    return data


def question_type(label: str) -> str:
    lowered = label.lower()
    if "nps" in lowered:
        return "nps"
    if "多选" in label:
        return "multi_choice"
    if "排序" in label:
        return "ranking"
    if "量表" in label:
        return "likert_scale"
    if "开放" in label or "文本" in label:
        return "open_text"
    return "single_choice"


def questionnaire_contract(path: Path) -> tuple[str, list[dict[str, Any]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    title = next((line[2:].strip() for line in lines if line.startswith("# ")), "")
    questions: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    body: list[str] = []

    def finish() -> None:
        nonlocal current, body
        if current is None:
            return
        content = [line.strip() for line in body if line.strip()]
        prompt = [line for line in content if not line.startswith("- ") and not line.startswith("【逻辑提示")]
        raw_options = [line[2:].strip() for line in content if line.startswith("- ")]
        dynamic = next((item for item in raw_options if "动态回填" in item), "")
        options = [item for item in raw_options if item != dynamic]
        current["question"] = " ".join(prompt)
        current["logic_text"] = " ".join(line for line in content if line.startswith("【逻辑提示"))
        if dynamic:
            source = re.search(r"Q[A-Za-z0-9_.-]+", dynamic)
            if source:
                current["options_from_question_id"] = source.group(0)
        if current["type"] in {"single_choice", "multi_choice", "ranking"} and options:
            current["options"] = options
        max_match = re.search(r"(?:最多|选)\s*(\d+)\s*项", current["type_label"])
        if max_match:
            current["max_choices"] = int(max_match.group(1))
        if current["type"] in {"likert_scale", "nps"}:
            scale_match = re.search(r"(\d+)\s*[–—-]\s*(\d+)", current["type_label"])
            if scale_match:
                labels = {}
                for option in options:
                    label_match = re.match(r"(\d+(?:\.\d+)?)\s*=\s*(.+)", option)
                    if label_match:
                        labels[label_match.group(1)] = label_match.group(2)
                current["scale"] = {"min": float(scale_match.group(1)), "max": float(scale_match.group(2)), "labels": labels}
        if "排他项" in current["logic_text"]:
            quoted = re.findall(r"「([^」]+)」", current["logic_text"].split("排他项", 1)[0])
            if quoted:
                current["exclusive_options"] = quoted[-1:]
        questions.append(current)
        current, body = None, []

    for line in lines:
        match = QUESTION_HEADING.match(line.strip())
        if match:
            finish()
            label = (match.group(2) or "单选").strip()
            current = {"id": match.group(1), "type_label": label, "type": question_type(label), "required": "选填" not in label and "可选" not in label}
        elif current is not None:
            if line.startswith("## "):
                finish()
            else:
                body.append(line)
    finish()
    if not title or not questions:
        raise ValueError("questionnaire.md 缺少标题或 Q 题目")
    ids = [question["id"] for question in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("questionnaire.md 中存在重复题号")
    return title, questions


def question_ids_in_text(text: str, ordered_ids: list[str]) -> list[str]:
    found: list[str] = []
    numeric = {int(match.group(1)): qid for qid in ordered_ids if (match := re.fullmatch(r"Q(\d+)", qid))}
    for match in re.finditer(r"Q(\d+)\s*[–—-]\s*Q?(\d+)", text):
        start, end = map(int, match.groups())
        for number in range(min(start, end), max(start, end) + 1):
            if number in numeric and numeric[number] not in found:
                found.append(numeric[number])
    for qid in re.findall(r"Q[A-Za-z0-9_.-]+", text):
        if qid in ordered_ids and qid not in found:
            found.append(qid)
    return sorted(found, key=ordered_ids.index)


def plain_html_text(fragment: str) -> str:
    without_tags = re.sub(r"(?is)<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def html_attribute(tag: str, name: str) -> str | None:
    match = re.search(rf"\b{re.escape(name)}\s*=\s*(['\"])(.*?)\1", tag, re.IGNORECASE | re.DOTALL)
    return html.unescape(match.group(2)).strip() if match else None


def html_data_field(text: str, name: str) -> str | None:
    match = re.search(
        rf"(?is)<[^>]*\bdata-field\s*=\s*(['\"]){re.escape(name)}\1[^>]*>(.*?)</[^>]+>",
        text,
    )
    return plain_html_text(match.group(2)) if match else None


def parse_design_html(text: str, question_ids: list[str]) -> dict[str, Any]:
    goals: list[dict[str, Any]] = []
    for match in re.finditer(
        r"(?is)(<article\b(?=[^>]*\bdata-goal-id\s*=)[^>]*>)(.*?)</article>",
        text,
    ):
        tag, body = match.groups()
        gid = html_attribute(tag, "data-goal-id")
        if not gid or any(goal["id"] == gid for goal in goals):
            continue
        statement = html_data_field(body, "goal-statement")
        if not statement:
            heading = re.search(r"(?is)<h[1-6][^>]*>(.*?)</h[1-6]>", body)
            statement = plain_html_text(heading.group(1)) if heading else gid
            statement = re.sub(rf"^{re.escape(gid)}\s*[·:：-]?\s*", "", statement)
        mapped = html_attribute(tag, "data-question-ids") or body
        goals.append({
            "id": gid,
            "question": statement,
            "question_ids": question_ids_in_text(mapped, question_ids),
        })
    advice_section = re.search(
        r"(?is)<section\b(?=[^>]*\bid\s*=\s*(['\"])analysis-advice\1)[^>]*>(.*?)</section>",
        text,
    )
    advice = [plain_html_text(item) for item in re.findall(r"(?is)<li[^>]*>(.*?)</li>", advice_section.group(2))] if advice_section else []
    return {
        "decision": html_data_field(text, "decision") or "未提供",
        "target_audience": html_data_field(text, "target-audience") or "未提供",
        "research_goals": goals,
        "analysis_advice": advice,
    }


def parse_design_doc(path: Path, question_ids: list[str]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".html", ".htm"} or re.match(r"(?is)^\s*<!doctype\s+html", text):
        return parse_design_html(text, question_ids)
    decision_match = re.search(r"(?m)^-\s*(?:产品决策|研究决策)：\s*(.+)$", text)
    audience_match = re.search(r"(?m)^-\s*目标用户(?:（[^）]*）)?：\s*(.+)$", text)
    goals: list[dict[str, Any]] = []
    for match in re.finditer(r"(?m)^-\s*(G[A-Za-z0-9_.-]+)：\s*(.+)$", text):
        gid, statement = match.groups()
        if not any(goal["id"] == gid for goal in goals):
            goals.append({"id": gid, "question": statement.strip()})
    if not goals:
        packed = re.search(r"(?m)^-\s*研究目标：\s*(.+)$", text)
        if packed:
            for gid, statement in re.findall(r"(G[A-Za-z0-9_.-]+)\s+([^；;]+)", packed.group(1)):
                goals.append({"id": gid, "question": statement.strip(" ：:")})
    for goal in goals:
        mapping = re.search(rf"(?m)^-\s*{re.escape(goal['id'])}：\s*(.+)$", text)
        candidates = []
        if mapping:
            candidates.extend(question_ids_in_text(mapping.group(1), question_ids))
        analysis_section = re.search(r"(?ms)^##\s+分析建议\s*$\n(.*?)(?=^##\s+|\Z)", text)
        if analysis_section:
            specific = re.search(rf"(?m)^-\s*{re.escape(goal['id'])}：\s*(.+)$", analysis_section.group(1))
            if specific:
                candidates.extend(question_ids_in_text(specific.group(1), question_ids))
        goal["question_ids"] = sorted(set(candidates), key=question_ids.index)
    advice_section = re.search(r"(?ms)^##\s+分析建议\s*$\n(.*?)(?=^##\s+|\Z)", text)
    advice = [line[2:].strip() for line in (advice_section.group(1).splitlines() if advice_section else []) if line.startswith("- ")]
    return {
        "decision": decision_match.group(1).strip() if decision_match else "未提供",
        "target_audience": audience_match.group(1).strip() if audience_match else "未提供",
        "research_goals": goals,
        "analysis_advice": advice,
    }


def column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference.upper())
    if not letters:
        return 0
    value = 0
    for char in letters.group(0):
        value = value * 26 + ord(char) - 64
    return value - 1


def parse_scalar(text: str | None) -> Any:
    if text in (None, ""):
        return None
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


def read_xlsx(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    rel_ns = {"p": "http://schemas.openxmlformats.org/package/2006/relationships"}
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        sheets = workbook.findall("m:sheets/m:sheet", ns)
        if len(sheets) != 1 or sheets[0].get("name") != "问卷回答":
            raise ValueError("回答 Excel 必须且只能包含一个名为“问卷回答”的工作表")
        rel_id = sheets[0].get(f"{{{ns['r']}}}id")
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = next((rel.get("Target") for rel in relationships.findall("p:Relationship", rel_ns) if rel.get("Id") == rel_id), None)
        if not target:
            raise ValueError("无法定位“问卷回答”工作表")
        sheet_path = str(PurePosixPath("xl") / target) if not target.startswith("/") and not target.startswith("xl/") else target.lstrip("/")
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.text or "" for node in item.findall(".//m:t", ns)) for item in root.findall("m:si", ns)]
        sheet = ET.fromstring(archive.read(sheet_path))
        matrix: list[list[Any]] = []
        for row in sheet.findall(".//m:sheetData/m:row", ns):
            values: dict[int, Any] = {}
            for cell in row.findall("m:c", ns):
                index = column_index(cell.get("r", "A1"))
                kind = cell.get("t")
                value_node = cell.find("m:v", ns)
                if kind == "inlineStr":
                    value = "".join(node.text or "" for node in cell.findall(".//m:is/m:t", ns))
                elif kind == "s" and value_node is not None:
                    value = shared[int(value_node.text or "0")]
                elif kind == "b" and value_node is not None:
                    value = value_node.text == "1"
                else:
                    value = parse_scalar(value_node.text if value_node is not None else None)
                values[index] = value
            width = max(values, default=-1) + 1
            matrix.append([values.get(index) for index in range(width)])
    if not matrix:
        raise ValueError("回答 Excel 没有数据")
    headers = [str(value).strip() if value is not None else "" for value in matrix[0]]
    if len(headers) != len(set(headers)):
        raise ValueError("回答 Excel 存在重复列名")
    records = []
    for raw in matrix[1:]:
        padded = raw + [None] * (len(headers) - len(raw))
        record = {header: padded[index] for index, header in enumerate(headers) if header}
        if any(value not in (None, "") for value in record.values()):
            records.append(record)
    return headers, records


def run_id_from_responses(responses: Path) -> str:
    match = re.fullmatch(r"survey_responses_(.+)\.xlsx", responses.name)
    if not match:
        raise ValueError("回答文件必须命名为 survey_responses_<run_id>.xlsx")
    return match.group(1)


def is_completed(value: Any) -> bool:
    return str(value or "").strip().lower() in SUCCESS_STATUSES


def split_choices(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in re.split(r"[；;]", str(value)) if item.strip()]


def validate_columns(headers: list[str], questions: list[dict[str, Any]]) -> None:
    missing_fixed = [column for column in FIXED_COLUMNS if column not in headers]
    if missing_fixed:
        raise ValueError(f"回答 Excel 缺少固定列：{', '.join(missing_fixed)}")
    qids = [str(item["id"]) for item in questions]
    missing = [qid for qid in qids if qid not in headers]
    if missing:
        raise ValueError(f"回答 Excel 缺少题目列：{', '.join(missing)}")
    present_qids = [header for header in headers if header in qids]
    if present_qids != qids:
        raise ValueError("回答 Excel 的题目列顺序与问卷不一致")
    unknown = [header for header in headers if Q_COLUMN.fullmatch(header) and header.removesuffix("_回答原因") not in qids]
    if unknown:
        raise ValueError(f"回答 Excel 含未知题目列：{', '.join(unknown)}")
def validate_records(records: list[dict[str, Any]], run_id: str) -> None:
    ids = [str(record.get("用户ID") or "") for record in records]
    if any(not user_id for user_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("回答 Excel 的用户 ID 必须非空且唯一")
    if any(not str(record.get("任务ID") or "").startswith(f"{run_id}-") for record in records):
        raise ValueError("回答 Excel 的任务 ID 必须以 run_id 开头")


def parse_manual_exclusions(values: list[str]) -> dict[str, str]:
    exclusions: dict[str, str] = {}
    for value in values:
        user_id, separator, reason = value.partition(":")
        user_id, reason = user_id.strip(), reason.strip()
        if not user_id or not separator or not reason:
            raise ValueError("--exclude-response 必须使用 <用户ID>:<清理理由> 格式")
        if user_id in exclusions:
            raise ValueError(f"用户 ID {user_id} 被重复列入清理名单")
        exclusions[user_id] = reason
    return exclusions


def response_issue(question: dict[str, Any], value: Any) -> str | None:
    if value in (None, ""):
        return None
    qtype = str(question.get("type"))
    options = {str(item) for item in question.get("options", [])}
    if qtype == "single_choice" and options and str(value) not in options:
        return "单选答案不在问卷选项中"
    if qtype in {"multi_choice", "ranking"}:
        choices = split_choices(value)
        if options and any(choice not in options for choice in choices):
            return "多选/排序答案含问卷外选项"
        if qtype == "ranking" and len(choices) != len(set(choices)):
            return "排序答案重复"
        maximum = question.get("max_choices")
        if isinstance(maximum, int) and len(choices) > maximum:
            return f"选择数超过上限 {maximum}"
    if qtype in {"likert_scale", "nps"} and question.get("scale"):
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return "量表答案不是数值"
        scale = question["scale"]
        if numeric < scale["min"] or numeric > scale["max"]:
            return f"量表答案超出 {scale['min']}–{scale['max']}"
    return None


def logic_issues(record: dict[str, Any], questions: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    for index, question in enumerate(questions):
        qid = str(question["id"])
        value = record.get(qid)
        choices = set(split_choices(value))
        logic = str(question.get("logic_text") or "")
        quoted = set(re.findall(r"「([^」]+)」", logic))
        if "结束答题" in logic and choices & quoted:
            answered_later = next((str(item["id"]) for item in questions[index + 1 :] if record.get(str(item["id"])) not in (None, "")), None)
            if answered_later:
                issues.append(f"{qid}：触发结束答题后仍回答 {answered_later}")
        if question.get("exclusive_options") and choices & set(question["exclusive_options"]):
            skipped = [target for target in re.findall(r"Q[A-Za-z0-9_.-]+", logic) if target != qid]
            answered_skipped = next((target for target in skipped if record.get(target) not in (None, "")), None)
            if answered_skipped:
                issues.append(f"{qid}：选择排他项后仍回答 {answered_skipped}")
        display_rule = re.search(r"仅当\s+(Q[A-Za-z0-9_.-]+)\s+未选「([^」]+)」时显示", logic)
        if display_rule and value not in (None, ""):
            source_qid, excluded_option = display_rule.groups()
            if excluded_option in split_choices(record.get(source_qid)):
                issues.append(f"{qid}：不满足显示条件仍有回答")
    return issues


def clean_completed_records(records: list[dict[str, Any]], questions: list[dict[str, Any]], manual_exclusions: dict[str, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    completed = [record for record in records if is_completed(record.get("状态"))]
    completed_ids = {str(record["用户ID"]) for record in completed}
    unknown_manual = set(manual_exclusions) - completed_ids
    if unknown_manual:
        raise ValueError(f"清理名单包含不存在或非完成的用户 ID：{', '.join(sorted(unknown_manual))}")
    kept: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    review: list[dict[str, str]] = []
    for record in completed:
        user_id = str(record["用户ID"])
        issues = [f"{question['id']}：{issue}" for question in questions if (issue := response_issue(question, record.get(str(question["id"]))))]
        issues.extend(logic_issues(record, questions))
        if user_id in manual_exclusions:
            issues.append(f"人工清理：{manual_exclusions[user_id]}")
        if issues:
            excluded.append({"user_id": user_id, "reason": "；".join(issues)})
            continue
        if record.get("错误摘要") not in (None, ""):
            review.append({"user_id": user_id, "reason": str(record["错误摘要"]).strip()})
        kept.append(record)
    return kept, {
        "completed_before_cleaning": len(completed),
        "analyzable_after_cleaning": len(kept),
        "excluded_count": len(excluded),
        "excluded_records": excluded,
        "manual_review_records": review,
    }


def persons_summary_context(path: Path) -> dict[str, Any]:
    """Extract only batch-level construction context, never individual persona data."""
    text = path.read_text(encoding="utf-8")
    payload_match = re.search(
        r'<script[^>]*id=["\']persona-summary-data["\'][^>]*>(.*?)</script>',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if payload_match:
        try:
            payload = json.loads(html.unescape(payload_match.group(1).strip()))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name} 的 persona-summary-data 不是有效 JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"{path.name} 的 persona-summary-data 必须是对象")
        return {
            "file": str(path.resolve()),
            "topic": payload.get("topic"),
            "declared_sample_size": payload.get("total"),
            "construction_summary": payload.get("construction_summary", []),
            "evidence_role": "construction_context_only",
        }
    total_match = re.search(r"画像总数：[：]?\s*(\d+)\s*人?", text)
    topic_match = re.search(r"调研课题：[：]?\s*(.+)", text)
    construction_lines = [line.strip().removeprefix("- ") for line in text.splitlines() if line.strip().startswith("-")]
    return {
        "file": str(path.resolve()),
        "topic": topic_match.group(1).strip() if topic_match else None,
        "declared_sample_size": int(total_match.group(1)) if total_match else None,
        "construction_summary": construction_lines,
        "evidence_role": "construction_context_only",
    }


def derive_batch_quality(records: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [record for record in records if is_completed(record.get("状态"))]
    failed = len(records) - len(completed)
    rate = len(completed) / len(records) if records else 0.0
    errors = Counter(str(record.get("错误摘要")).strip() for record in records if record.get("错误摘要") not in (None, ""))
    if not records or rate < 0.7:
        grade = "poor"
    elif errors:
        grade = "needs_review"
    elif failed:
        grade = "good"
    else:
        grade = "excellent"
    return {
        "completed_records": completed,
        "failed": failed,
        "completion_rate": rate,
        "quality_grade": grade,
        "issue_counts": dict(errors),
    }


def distribution_for(question: dict[str, Any], values: list[tuple[str, Any]]) -> dict[str, Any]:
    qtype = str(question.get("type", "open_text"))
    options = [str(item) for item in question.get("options", [])]
    result: dict[str, Any] = {}
    counts: Counter[str] = Counter()
    if qtype in {"multi_choice", "ranking"}:
        choices = [(user_id, split_choices(value)) for user_id, value in values]
        for _, selected in choices:
            counts.update(selected)
        if qtype == "ranking":
            first = Counter(selected[0] for _, selected in choices if selected)
            positions: dict[str, list[int]] = {}
            for _, selected in choices:
                for index, option in enumerate(selected, start=1):
                    positions.setdefault(option, []).append(index)
            result["ranking"] = [
                {"label": option, "first_choice_count": first.get(option, 0), "selected_count": len(positions.get(option, [])), "average_rank": round(statistics.mean(positions[option]), 2) if positions.get(option) else None}
                for option in options or sorted(positions)
            ]
    elif qtype != "open_text":
        counts.update(str(int(value)) if isinstance(value, float) and value.is_integer() else str(value) for _, value in values)
    order = options + [label for label in counts if label not in options]
    result["distribution"] = [
        {"label": label, "count": counts[label], "percent": round(counts[label] / len(values) * 100, 1) if values else 0.0}
        for label in order if counts[label]
    ]
    if qtype in {"likert_scale", "nps"}:
        numeric = [float(value) for _, value in values if isinstance(value, (int, float)) or re.fullmatch(r"-?\d+(?:\.\d+)?", str(value))]
        if numeric:
            result["numeric_summary"] = {
                "n": len(numeric),
                "mean": round(statistics.mean(numeric), 2),
                "standard_deviation": round(statistics.stdev(numeric), 2) if len(numeric) > 1 else None,
                "median": round(statistics.median(numeric), 2),
                "min": min(numeric),
                "max": max(numeric),
            }
    return result


def interactive_data(questions: list[dict[str, Any]], records: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the minimum anonymous answer payload needed for in-browser filtering."""
    closed_questions = [
        {
            "id": str(question["id"]),
            "question": question.get("question"),
            "type": question.get("type"),
            "options": [str(option) for option in question.get("options", [])],
        }
        for question in questions
        if question.get("type") != "open_text"
    ]
    qids = [question["id"] for question in closed_questions]
    return {
        "questions": closed_questions,
        "responses": [
            {
                "answers": {
                    qid: record.get(qid)
                    for qid in qids
                    if record.get(qid) not in (None, "")
                }
            }
            for record in records
        ],
    }


def prepare_analysis(args: argparse.Namespace) -> dict[str, Any]:
    title, questions = questionnaire_contract(args.questionnaire)
    qids = [str(item["id"]) for item in questions]
    context = parse_design_doc(args.design_doc, qids)
    headers, records = read_xlsx(args.responses)
    run_id = run_id_from_responses(args.responses)
    validate_columns(headers, questions)
    validate_records(records, run_id)
    sample_construction = persons_summary_context(args.persons_summary) if args.persons_summary else None
    manual_exclusions = parse_manual_exclusions(args.exclude_response)

    batch_quality = derive_batch_quality(records)
    completed_records, cleaning = clean_completed_records(records, questions, manual_exclusions)
    descriptive: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    source_by_user = {str(record["用户ID"]): "synthetic" for record in completed_records}
    for question in questions:
        qid = str(question["id"])
        qtype = str(question.get("type", "open_text"))
        values = [(str(record["用户ID"]), record.get(qid)) for record in completed_records if record.get(qid) not in (None, "")]
        result = {
            "question_id": qid,
            "question": question.get("question"),
            "type": qtype,
            "base_n": len(values),
            "missing_n": len(completed_records) - len(values),
            "multi_select": qtype in {"multi_choice", "ranking"},
            **distribution_for(question, values),
        }
        descriptive.append(result)
        if qtype == "open_text":
            for user_id, value in values:
                observations.append({"evidence_id": f"{user_id}:{qid}", "response_id": user_id, "question_id": qid, "kind": "answer", "text": str(value), "synthetic_quote": source_by_user[user_id] == "synthetic"})
        reason_column = f"{qid}_回答原因"
        if reason_column in headers:
            for record in completed_records:
                reason = record.get(reason_column)
                if reason not in (None, ""):
                    user_id = str(record["用户ID"])
                    observations.append({"evidence_id": f"{user_id}:{qid}:reason", "response_id": user_id, "question_id": qid, "kind": "answer_reason", "text": str(reason), "synthetic_quote": source_by_user[user_id] == "synthetic"})

    goals = context.get("research_goals", [])
    goal_coverage = [
        {"goal_id": goal["id"], "research_question": goal["question"], "question_ids": goal.get("question_ids", []), "status": "covered" if goal.get("question_ids") else "evidence_gap", "finding": "待根据描述统计和主题编码补充"}
        for goal in goals
    ]
    model_distribution = Counter(str(record.get("实际模型") or "未记录") for record in completed_records)
    limitations = [
        "合成回答只能用于检查研究工具和形成待真实研究验证的假设，不能代表真实用户或市场总体。",
    ]
    if sample_construction:
        limitations.append("persons_summary.html 仅用于披露样本构建背景，不能作为问卷发现、分群依据或单个回答的解释。")
    if cleaning["excluded_count"]:
        limitations.append(f"数据清理剔除了 {cleaning['excluded_count']} 个完成回答；具体用户 ID 与理由保留在 data_cleaning 中。")
    if cleaning["manual_review_records"]:
        limitations.append(f"仍有 {len(cleaning['manual_review_records'])} 个完成回答带错误摘要，未自动剔除，需在决策前人工复核。")
    if len(completed_records) < 10:
        limitations.append(f"可分析样本仅 {len(completed_records)} 个，只报告描述性观察，不解释为稳定分群差异。")
    if batch_quality["failed"]:
        limitations.append(f"本批次有 {batch_quality['failed']} 个失败样本；失败行不进入各题分母。")
    if batch_quality["quality_grade"] == "needs_review":
        limitations.append("回答表中存在错误摘要，相关样本必须在决策前复核。")
    topic = title
    report_title = f"{topic.removesuffix('问卷')}报告"
    return {
        "schema_version": "2.0",
        "study_id": f"questionnaire_{hashlib.sha256(title.encode('utf-8')).hexdigest()[:12]}",
        "run_id": run_id,
        "title": report_title,
        "topic": topic.removesuffix("问卷"),
        "data_source": "synthetic",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "inputs": {
            "questionnaire": str(args.questionnaire.resolve()),
            "design_doc": str(args.design_doc.resolve()),
            "responses": str(args.responses.resolve()),
            "persons_summary": str(args.persons_summary.resolve()) if args.persons_summary else None,
        },
        "contract_checks": {"questionnaire_parse": "passed", "responses_filename": "passed", "xlsx_columns": "passed", "xlsx_rows": "passed", "data_cleaning": "passed", "persons_summary": "passed" if sample_construction else "not_provided"},
        "sample": {
            "total": len(records),
            "completed": len(batch_quality["completed_records"]),
            "analyzable": len(completed_records),
            "failed": batch_quality["failed"],
            "completion_rate": round(batch_quality["completion_rate"], 4),
            "quality_grade": batch_quality["quality_grade"],
            "model_distribution": dict(model_distribution),
            "issue_counts": batch_quality["issue_counts"],
        },
        "research_context": context,
        "sample_construction": sample_construction,
        "data_cleaning": cleaning,
        "goal_coverage": goal_coverage,
        "descriptive_results": descriptive,
        "interactive_data": interactive_data(questions, completed_records),
        "qualitative_observations": observations,
        "cross_tabulations": [],
        "scale_quality": [],
        "themes": [],
        "segment_observations": [],
        "recommendations": [],
        "limitations": limitations,
    }


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def bar_svg(distribution: list[dict[str, Any]], base_n: int) -> str:
    if not distribution:
        return '<p class="empty">本题没有可绘制的封闭题数据。</p>'
    width, label_w, bar_w = 920, 310, 450
    maximum = max(int(item.get("count", 0)) for item in distribution) or 1
    rows = []
    y = 12
    for item in distribution:
        label = str(item.get("label", ""))
        lines = [label[start:start + 21] for start in range(0, len(label), 21)] or [""]
        count = int(item.get("count", 0))
        length = max(2, int(count / maximum * bar_w)) if count else 0
        label_svg = "".join(f'<tspan x="0" dy="{0 if index == 0 else 22}">{esc(line)}</tspan>' for index, line in enumerate(lines))
        rows.append(f'<text x="0" y="{y + 17}" class="axis">{label_svg}</text><rect x="{label_w}" y="{y}" width="{length}" height="24" rx="6" class="bar"/><text x="{label_w + length + 8}" y="{y + 17}" class="value">{count}（{float(item.get("percent", 0)):.1f}%）</text>')
        y += max(42, len(lines) * 22 + 14)
    height = y + 12
    return f'<div class="chart"><svg viewBox="0 0 {width} {height}" role="img" aria-label="回答分布，分母 {base_n}">{"".join(rows)}</svg></div>'


def source_label() -> tuple[str, str]:
    return "合成模拟数据", "用于检查研究工具和形成待验证假设，不代表真实用户或市场总体。"


def conclusion_deck(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """Three evidence-led slides; missing authored findings remain explicit gaps."""
    goals = analysis.get("goal_coverage", [])
    themes = analysis.get("themes", [])
    context = analysis.get("research_context", {})
    results = [item for item in analysis.get("descriptive_results", []) if item.get("type") != "open_text" and item.get("base_n")]
    linked_ids = [qid for goal in goals for qid in goal.get("question_ids", [])]
    results.sort(key=lambda item: (item.get("question_id") not in linked_ids, linked_ids.index(item["question_id"]) if item.get("question_id") in linked_ids else 999))
    findings = [f'{goal.get("research_question", "研究目标")}：{goal.get("finding") or "尚未形成证据支持的结论"}' for goal in goals]
    lines = [
        ["背景：" + str(context.get("background") or "未提供独立背景说明；以下以已提供的产品决策作为分析起点。"),
         "目的：" + str(context.get("decision") or "未提供产品决策或正式调研目的。"),
         "用户现状：" + str(goals[0].get("finding") or "尚未形成现状分析，不能将人口属性或概念意愿当作实际行为。") if goals else "用户现状：未提供目标对应的现状结论。"],
        [str(theme.get("insight") or theme.get("name") or theme.get("theme_id")) + "；证据：" + ", ".join(theme.get("evidence_ids", [])) for theme in themes] or ["未形成用户诉求与痛点的证据编码；不能由选项分布补造原因或用户原话。"],
        findings or ["未提供正式研究目标；当前仅有描述统计，无法形成目标对应的关键结论。"],
    ]
    slides = []
    for index, title in enumerate(["调研背景、目的与用户现状", "用户诉求与痛点", "调研目标与关键结论"]):
        goal = goals[min(index, len(goals) - 1)] if goals else {}
        candidates = [item for item in results if item.get("question_id") in goal.get("question_ids", [])]
        if index == 0:
            candidates.sort(key=lambda item: (bool(re.search("年龄|性别|品牌", item.get("question", ""))), not bool(re.search("频率|过去|近期|付费|使用", item.get("question", "")))))
        result = (candidates or results or [{}])[0]
        items = result.get("distribution", [])
        if result.get("ranking"):
            items = [{"label": row["label"], "count": row.get("first_choice_count", 0), "percent": row.get("first_choice_count", 0) / result["base_n"] * 100} for row in result["ranking"]]
        items = sorted(items, key=lambda row: -row.get("percent", 0))
        note = f'全批次；实际分母 n={result.get("base_n", 0)}；空白/未作答 {result.get("missing_n", 0)}。'
        if result.get("type") == "multi_choice":
            note += "多选为受访者占比，比例合计可超过100%。"
        if result.get("type") == "ranking":
            note += "按第一选择统计。"
        if len(items) > 6:
            note += "展示占比最高的6项，完整选项见普通分析。"
        slides.append({"title": title, "lines": lines[index][:4], "chart": {"title": f'{result.get("question_id", "")} · {result.get("question", "暂无题目统计")}', "note": note, "items": items[:6]}})
    return slides


def report_filename(analysis: dict[str, Any], report_date: str | None = None) -> str:
    """Build a safe, stable dated filename without renaming input artifacts."""
    if report_date:
        date = datetime.strptime(report_date, "%Y%m%d").strftime("%Y%m%d")
        if date != report_date:
            raise ValueError("报告日期必须为 YYYYMMDD")
    else:
        try:
            date = datetime.fromisoformat(str(analysis.get("generated_at", ""))).strftime("%Y%m%d")
        except ValueError:
            date = datetime.now().strftime("%Y%m%d")
    topic = str(analysis.get("topic") or analysis.get("title") or "未命名调研")
    topic = topic.removesuffix("_调研报告").removesuffix("报告").removesuffix("问卷")
    topic = re.sub(r"^\d{8}", "", topic).strip()
    topic = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", topic).strip(" .") or "未命名调研"
    return f"{date}{topic}_调研报告.html"


def render_quality_audit(analysis: dict[str, Any], problems: list[str] | None) -> str:
    """Keep structural checks distinct from researcher/browser verification."""
    checks = analysis.get("contract_checks", {})
    names = {"questionnaire_parse": "正式问卷解析", "responses_filename": "回答批次标识", "xlsx_columns": "Excel 题目列", "xlsx_rows": "Excel 样本行", "data_cleaning": "数据清理", "persons_summary": "可选样本构建说明"}
    labels = {"passed": "通过", "failed": "失败", "pending": "待检查", "not_provided": "未提供", "not_applicable": "不适用"}
    contract_rows = "".join(f'<tr><td>{esc(names.get(key, key))}</td><td>{esc(labels.get(str(value), value))}</td></tr>' for key, value in checks.items()) or '<tr><td colspan="2">未提供输入契约检查记录</td></tr>'
    structural = [
        ("离线资源", ["HTML 包含外部资源"]),
        ("SVG 图表", ["有封闭题数据但没有 SVG 图表"]),
        ("筛选、分析与导出控件结构", ["HTML 缺少筛选、分析或报告下载控件", "HTML 缺少本地筛选所需的匿名答卷数据"]),
        ("批次标识披露", ["HTML 未显示 run_id"]),
        ("数据来源披露", ["合成数据披露不足"]),
    ]
    automatic_rows = "".join(f'<tr><td>{esc(name)}</td><td>{"待检查" if problems is None else "失败" if any(issue in problems for issue in issues) else "通过"}</td></tr>' for name, issues in structural)
    manual_checks = [
        ("statistics", "统计与 Excel 原始行抽查（至少3项，不足时全部）"),
        ("evidence", "已有证据回溯及引语脱敏（至少3项，不足时全部）"),
        ("cleaning", "剔除理由、缺失和待复核记录"),
        ("privacy", "身份信息、稀有组合与重识别风险"),
        ("desktop_mobile", "桌面与窄屏视觉、长文本及图表可读性"),
        ("filters", "题目/选项筛选及统计实时重算"),
        ("charts", "逐题六种视图及百分比口径"),
        ("cross", "X/Y 添加、移除、交换及交叉分母"),
        ("tabs", "四个 Tab 切换、键盘导航及导出隔离"),
        ("office", "DOCX/PPTX/XLSX 与结论 PPT 可重新打开"),
        ("downloads", "实际浏览器报告、结论 PPT 及 CSV 下载"),
        ("conclusions", "目标对应结论、来源限制及未回答问题"),
    ]
    records = {item.get("check_id"): item for item in analysis.get("report_audit", [])}
    manual_rows = []
    for check_id, name in manual_checks:
        record = records.get(check_id, {})
        status = record.get("status", "pending")
        if status not in {"passed", "failed", "pending", "not_applicable"}:
            status = "pending"
        manual_rows.append(f'<tr><td>{esc(name)}</td><td>{labels[status]}</td><td>{esc(record.get("note") or "尚未记录检查结果")}</td></tr>')
    result = "结构检查待完成" if problems is None else "结构检查失败" if problems else "结构检查通过"
    issues = "；".join(problems or []) or "无已记录结构问题"
    return f'<div id="report-audit"><h3>报告检查与交付审计</h3><p>{esc(result)}；人工审计以各项记录为准。自动结构检查不等于浏览器交互、文件下载或视觉验收。</p><details class="data-details"><summary>输入契约检查</summary><div class="table-wrap"><table><thead><tr><th>检查项</th><th>结果</th></tr></thead><tbody>{contract_rows}</tbody></table></div></details><details class="data-details" open><summary>自动结构检查</summary><div class="table-wrap"><table><thead><tr><th>检查项</th><th>结果</th></tr></thead><tbody>{automatic_rows}</tbody></table></div><p>{esc(issues)}</p></details><details class="data-details" open><summary>人工检查及修订记录</summary><div class="table-wrap"><table><thead><tr><th>检查项</th><th>状态</th><th>记录 / 限制</th></tr></thead><tbody>{"".join(manual_rows)}</tbody></table></div></details></div>'


def render_report(analysis: dict[str, Any], machine_problems: list[str] | None = None) -> str:
    label, disclosure = source_label()
    sample = analysis.get("sample", {})
    context = analysis.get("research_context", {})
    goals = analysis.get("goal_coverage", [])
    themes = analysis.get("themes", [])
    segments = analysis.get("segment_observations", [])
    recommendations = analysis.get("recommendations", [])
    limitations = analysis.get("limitations", [])
    cleaning = analysis.get("data_cleaning", {})
    cross_tabs = analysis.get("cross_tabulations", [])
    scale_quality = analysis.get("scale_quality", [])
    quality_audit = render_quality_audit(analysis, machine_problems)
    interactive_payload = json.dumps({**analysis.get("interactive_data", {}), "conclusion_deck": conclusion_deck(analysis)}, ensure_ascii=False).replace("</", "<\\/")

    goal_rows = "".join(f'<tr><td>{esc(goal.get("goal_id"))}</td><td>{esc(goal.get("research_question"))}</td><td>{esc(", ".join(goal.get("question_ids", [])) or "无")}</td><td>{esc(goal.get("status"))}</td><td>{esc(goal.get("finding"))}</td></tr>' for goal in goals) or '<tr><td colspan="5">survey-design-desc.html 未提供可识别的研究目标。</td></tr>'

    charts = []
    for result in analysis.get("descriptive_results", []):
        if result.get("type") == "open_text":
            continue
        notes = []
        if result.get("type") == "multi_choice":
            notes.append("多选题的百分比合计可超过 100%")
        numeric = result.get("numeric_summary")
        if numeric:
            deviation = numeric.get("standard_deviation")
            notes.append(f"均值 {numeric.get('mean')}，标准差 {deviation if deviation is not None else '样本不足'}，中位数 {numeric.get('median')}")
        ranking = result.get("ranking") or []
        if ranking:
            ranked = sorted((item for item in ranking if item.get("selected_count")), key=lambda item: (-item.get("first_choice_count", 0), item.get("average_rank") or 99))
            notes.append("排序概览：" + "；".join(f"{item['label']} 首选 {item['first_choice_count']}，平均名次 {item['average_rank']}" for item in ranked[:3]))
        distribution = result.get("distribution", [])
        if ranking:
            notes.append("图表按第一选择人数统计")
            distribution = [{"label": item["label"], "count": item.get("first_choice_count", 0), "percent": round(item.get("first_choice_count", 0) / result["base_n"] * 100, 1) if result.get("base_n") else 0} for item in ranking]
        note_text = "；".join(notes)
        charts.append(f'<section class="evidence"><h3>{esc(result.get("question_id"))} · {esc(result.get("question"))}</h3><p>实际分母 <strong>{result.get("base_n", 0)}</strong>，可分析样本中的空白/未作答 {result.get("missing_n", 0)}。{esc(note_text)}。只描述本批次。</p>{bar_svg(distribution, int(result.get("base_n", 0)))}</section>')
    if not charts:
        charts.append('<p class="empty">没有可绘制的封闭题结果。</p>')

    theme_cards = []
    for theme in themes:
        frequency = theme.get("frequency", {})
        theme_cards.append(f'<article class="card"><h3>{esc(theme.get("insight") or theme.get("name") or theme.get("theme_id"))}</h3><p><span class="pill">{esc(theme.get("confidence", "未评级"))}</span> 本批次出现 {esc(frequency.get("n", "?"))}/{esc(frequency.get("N", "?"))}。</p><p><strong>证据：</strong>{esc(", ".join(theme.get("evidence_ids", [])) or "未附证据")}</p><p><strong>反例：</strong>{esc("；".join(theme.get("counterevidence", [])) or "未记录")}</p><p><strong>替代解释：</strong>{esc("；".join(theme.get("alternative_explanations", [])) or "未记录")}</p></article>')
    if not theme_cards:
        theme_cards.append('<p class="empty">尚未完成开放回答与回答原因的主题编码。</p>')
    segment_rows = "".join(f'<tr><td>{esc(item.get("segment"))}</td><td>{esc(item.get("source"))}</td><td>{esc(item.get("n"))}</td><td>{esc(item.get("observation") or item.get("finding"))}</td><td>{esc(item.get("limitation"))}</td></tr>' for item in segments) or '<tr><td colspan="5">未形成可报告的分群观察。</td></tr>'
    rec_items = "".join(f'<li><strong>{esc(item.get("action") or item.get("recommendation"))}</strong><br>{esc(item.get("rationale", ""))}<br><small>证据强度：{esc(item.get("evidence_strength", "未评级"))}；成本/风险：{esc(item.get("cost_risk", "待补充"))}；下一步：{esc(item.get("validation", "待补充"))}</small></li>' for item in recommendations) or '<li>尚未形成证据支持的建议。</li>'
    model_items = "".join(f"<li><code>{esc(name)}</code>：{count}</li>" for name, count in sample.get("model_distribution", {}).items()) or "<li>未记录</li>"
    issue_items = "".join(f"<li><code>{esc(name)}</code>：{count}</li>" for name, count in sample.get("issue_counts", {}).items()) or "<li>无已记录问题</li>"
    cleaned_rows = "".join(f"<li><code>{esc(item.get('user_id'))}</code>：{esc(item.get('reason'))}</li>" for item in cleaning.get("excluded_records", [])) or "<li>无自动或人工确认的剔除记录</li>"
    review_rows = "".join(f"<li><code>{esc(item.get('user_id'))}</code>：{esc(item.get('reason'))}</li>" for item in cleaning.get("manual_review_records", [])) or "<li>无待人工复核记录</li>"
    limit_items = "".join(f"<li>{esc(item)}</li>" for item in limitations) or "<li>未记录限制；正式交付前必须补充。</li>"
    construction = analysis.get("sample_construction") or {}
    construction_bits = []
    if construction.get("topic"):
        construction_bits.append(f"课题：{esc(construction['topic'])}")
    if construction.get("declared_sample_size") is not None:
        construction_bits.append(f"画像汇总声明样本：{esc(construction['declared_sample_size'])} 人")
    construction_note = f'<div class="note"><strong>样本构成说明：</strong>{"；".join(construction_bits) or "已读取 persons_summary.html。"}。该文件只说明样本如何构建，不是回答证据、分群字段或市场比例。</div>' if construction else ""
    cross_rows = "".join(f"<tr><td>{esc(item.get('group_question_id'))}</td><td>{esc(item.get('target_question_id'))}</td><td>{esc(item.get('base_n'))}</td><td>{esc(item.get('finding'))}</td></tr>" for item in cross_tabs) or '<tr><td colspan="4">尚未形成满足样本量与研究目标要求的交叉分析。</td></tr>'
    scale_rows = "".join(f"<tr><td>{esc(item.get('scale_name') or item.get('question_ids'))}</td><td>{esc(item.get('method'))}</td><td>{esc(item.get('result'))}</td><td>{esc(item.get('interpretation'))}</td></tr>" for item in scale_quality) or '<tr><td colspan="4">没有满足同一构念、同一量表且样本条件足够的信效度检验。</td></tr>'
    templates_dir = Path(__file__).resolve().parents[1] / "templates"
    office_js = (templates_dir / "report-office.js").read_text(encoding="utf-8")
    analysis_js = (templates_dir / "report-analysis.js").read_text(encoding="utf-8")
    interactive_script = '<script id="report-interactive-data" type="application/json">' + interactive_payload + '</script><script>' + office_js + '</script><script>' + analysis_js + '</script>'

    report_css = (Path(__file__).resolve().parents[1] / "templates" / "report.css").read_text(encoding="utf-8")
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(analysis.get("title"))}</title><style>{report_css}</style></head>
<body data-run-id="{esc(analysis.get("run_id"))}"><main>
<div class="topbar"><div class="brand"><span class="brand-mark" aria-hidden="true">▥</span>研究报告</div><div class="top-actions" data-export-exclude><button id="open-export" class="primary" type="button">下载报告</button></div></div>
<header class="report-header"><div class="eyebrow">RESEARCH REPORT</div><h1>{esc(analysis.get("title"))}</h1><div class="meta"><span class="source-tag">{esc(label)}</span><span>批次 {esc(analysis.get("run_id"))}</span><span>{esc(analysis.get("generated_at"))}</span></div><div class="disclosure"><strong>数据边界</strong><span>{esc(disclosure)}</span></div></header>{construction_note}
<div class="metrics"><div class="metric"><span>总样本</span><b>{sample.get("total", 0)}</b><small>完成 {sample.get("completed", 0)} · 失败 {sample.get("failed", 0)}</small></div><div class="metric"><span>可分析样本</span><b>{sample.get("analyzable", 0)}</b><small>清理后有效回答</small></div><div class="metric"><span>完成率</span><b>{float(sample.get("completion_rate", 0)):.1%}</b><small>完成回答 / 总样本</small></div><div class="metric"><span>清理剔除</span><b>{cleaning.get("excluded_count", 0)}</b><small>原始工作簿保持不变</small></div></div>
<div class="workspace">
<aside id="sample-filters" class="filters" data-export-exclude><div class="filter-heading"><h2>样本筛选</h2><button id="clear-filters" class="text-button" type="button">重置</button></div><label>筛选题目<select id="filter-question"></select></label><div class="field-label">筛选选项<span>可多选</span></div><select id="filter-value" multiple hidden aria-label="筛选选项"></select><div id="filter-options" class="filter-options"></div><button id="add-filter" class="primary apply-button" type="button">应用筛选</button><div id="active-filters" class="filter-chips"></div><p class="filter-caption">同一题满足任一选项；不同题同时满足条件。两个分析页共用筛选。</p></aside>
<section class="analysis-area"><div class="analysis-top"><div class="analysis-tabs" role="tablist" aria-label="分析类型" data-export-exclude><button id="tab-ordinary" type="button" role="tab" aria-selected="true" aria-controls="panel-ordinary" tabindex="0">普通分析</button><button id="tab-cross" type="button" role="tab" aria-selected="false" aria-controls="panel-cross" tabindex="-1">交叉分析</button><button id="tab-conclusions" type="button" role="tab" aria-selected="false" aria-controls="panel-conclusions" tabindex="-1">调研分析结论</button><button id="tab-quality" type="button" role="tab" aria-selected="false" aria-controls="panel-quality" tabindex="-1">问卷质量报告</button></div><p id="filter-status" class="sample-status"></p></div><p id="view-context" class="view-context"></p>
<article id="panel-ordinary" role="tabpanel" aria-labelledby="tab-ordinary"><div hidden><select id="chart-question"></select><select id="chart-type"></select></div><div id="ordinary-questions"></div></article>
<article id="panel-cross" class="cross-panel" role="tabpanel" aria-labelledby="tab-cross" hidden><div class="cross-builder"><h3>我的交叉分析</h3><div class="cross-grid" data-export-exclude><div><label>自变量 X <small>分组题目，最多 2 题</small><select id="cross-group"></select></label><button id="add-cross-group" type="button">＋ 添加自变量</button><div id="cross-groups" class="filter-chips"></div></div><button id="swap-cross" type="button" aria-label="交换 X 与 Y">⇄</button><div><label>因变量 Y <small>分析题目，最多 10 题</small><select id="cross-target"></select></label><button id="add-cross-target" type="button">＋ 添加因变量</button><div id="cross-targets" class="filter-chips"></div></div></div><div class="cross-actions" data-export-exclude><button id="calculate-cross" class="primary" type="button">交叉分析</button><button id="export-cross-csv" type="button">下载交叉表 CSV</button></div><p id="cross-note" class="helper">可添加多个 X、Y 题目；未添加时使用下拉框当前题目。筛选条件同时适用于交叉分析。</p></div><div id="cross-table"></div></article>
<article id="panel-conclusions" class="report-body" role="tabpanel" aria-labelledby="tab-conclusions" hidden>
<div class="conclusion-heading"><div><h2>调研分析结论</h2><p class="helper">从背景与目的出发，分析现状、诉求与痛点，再形成目标对应的关键结论。</p></div><button id="download-conclusion-ppt" class="primary" type="button">下载结论 PPT（3页）</button></div><div id="conclusion-slides"></div>
<p class="conclusion-context">以下为清理后全批次的研究分析结论，不随普通分析或交叉分析中的筛选条件变化。</p>



</article>
<article id="panel-quality" class="report-body" role="tabpanel" aria-labelledby="tab-quality" hidden>
<section class="report-section"><div class="section-heading"><span class="section-index">01</span><h2>分群与研究者分析</h2></div><p>以下内容基于全批次，与上方筛选统计区分。</p><details class="data-details"><summary>分群观察与反例</summary><div class="table-wrap"><table><thead><tr><th>分群</th><th>来源</th><th>n</th><th>观察</th><th>限制</th></tr></thead><tbody>{segment_rows}</tbody></table></div></details><details class="data-details"><summary>预设交叉分析与量表检验</summary><div class="table-wrap"><table><thead><tr><th>分组题</th><th>目标题</th><th>有效样本</th><th>观察</th></tr></thead><tbody>{cross_rows}</tbody></table><table><thead><tr><th>量表 / 题项</th><th>方法</th><th>结果</th><th>解释</th></tr></thead><tbody>{scale_rows}</tbody></table></div></details></section>
<section class="report-section"><div class="section-heading"><span class="section-index">02</span><h2>全批次描述统计</h2></div><p>清理后全批次结果保留原口径，不随上方筛选变化。</p><details class="data-details"><summary>展开全部题目图表</summary><div id="full-batch-charts">{"".join(charts)}</div></details></section>
<section class="report-section"><div class="section-heading"><span class="section-index">03</span><h2>数据质量与清理记录</h2></div><p>质量等级：{esc(sample.get("quality_grade"))} · 完成回答清理前 {cleaning.get("completed_before_cleaning", 0)} · 清理后 {cleaning.get("analyzable_after_cleaning", 0)}</p><details class="data-details"><summary>查看清理与运行明细</summary><div class="method-grid"><div><h3>清理剔除记录</h3><ul>{cleaned_rows}</ul></div><div><h3>待人工复核</h3><ul>{review_rows}</ul></div><div><h3>实际模型</h3><ul>{model_items}</ul></div><div><h3>已记录问题</h3><ul>{issue_items}</ul></div></div></details>{quality_audit}</section>
<section class="report-section"><div class="section-heading"><span class="section-index">04</span><h2>限制与未回答问题</h2></div><ul>{limit_items}</ul></section></article></section></div>
<dialog id="export-dialog" data-export-exclude><div class="dialog-heading"><h2>下载报告</h2><button id="close-export" type="button" aria-label="关闭">×</button></div><label>选择文档格式<select id="export-format"><option value="docx">Word 文档（.docx）</option><option value="pptx">PowerPoint 演示文稿（.pptx）</option><option value="xlsx">Excel 工作簿（.xlsx）</option></select></label><label>Word 纸张大小<select id="export-paper"><option>A4</option><option>A3</option></select></label><p class="helper">导出当前分析 Tab 与当前筛选结果，并附报告正文的文字说明。研究结论保持全批次口径。Word/Excel 使用可编辑统计表，PowerPoint 使用可编辑条形图与统计表。结论页 PowerPoint 导出为三页结论与图表。</p><p id="export-error" role="alert"></p><div class="dialog-footer"><span>离线生成，不上传数据</span><button id="confirm-export" type="button" class="primary">下载报告</button></div></dialog>
<p id="download-status" data-export-exclude>筛选、分析与导出均在本地完成。</p>
<footer class="page-footer"><span>合成模拟数据 · 用于假设验证与研究工具检查</span><span>结论 PPT 使用全批次数据</span></footer>
</main>{interactive_script}</body></html>'''


def validate_analysis(base: dict[str, Any], analysis: dict[str, Any]) -> None:
    protected = ["schema_version", "study_id", "run_id", "data_source", "sample", "data_cleaning", "descriptive_results", "interactive_data", "qualitative_observations"]
    for key in protected:
        if analysis.get(key) != base.get(key):
            raise ValueError(f"analysis_summary.json 不得修改机械生成字段：{key}")
    base_goals = [(item.get("goal_id"), item.get("research_question"), item.get("question_ids")) for item in base.get("goal_coverage", [])]
    new_goals = [(item.get("goal_id"), item.get("research_question"), item.get("question_ids")) for item in analysis.get("goal_coverage", [])]
    if base_goals != new_goals:
        raise ValueError("analysis_summary.json 不得修改研究目标或题目映射")
    invalid = [item for item in analysis.get("themes", []) if item.get("confidence") in {"medium", "high"}]
    if invalid:
        raise ValueError("合成数据主题的置信等级最高只能为 low")


def machine_quality(report: str, analysis: dict[str, Any]) -> list[str]:
    problems = []
    if re.search(r"(?:src|href)=[\"']https?://", report, flags=re.I):
        problems.append("HTML 包含外部资源")
    if "<svg" not in report and any(item.get("distribution") for item in analysis.get("descriptive_results", [])):
        problems.append("有封闭题数据但没有 SVG 图表")
    if str(analysis.get("run_id")) not in report:
        problems.append("HTML 未显示 run_id")
    if "合成模拟数据" not in report or "不代表真实用户或市场总体" not in report:
        problems.append("合成数据披露不足")
    required_controls = ('id="filter-question"', 'id="filter-value"', 'id="ordinary-questions"', 'id="tab-conclusions"', 'id="panel-conclusions"', 'id="tab-quality"', 'id="panel-quality"', 'id="cross-group"', 'id="cross-target"', 'id="add-cross-group"', 'id="add-cross-target"', 'id="calculate-cross"', 'id="open-export"', 'id="export-dialog"', 'id="export-format"', 'id="confirm-export"', 'id="export-cross-csv"', 'id="download-conclusion-ppt"', 'id="conclusion-slides"')
    if any(control not in report for control in required_controls):
        problems.append("HTML 缺少筛选、分析或报告下载控件")
    if "report-interactive-data" not in report:
        problems.append("HTML 缺少本地筛选所需的匿名答卷数据")
    if not analysis.get("limitations"):
        problems.append("缺少限制")
    return problems




def main() -> int:
    parser = argparse.ArgumentParser(description="直接从全量问卷 Excel 生成离线 HTML 调研报告")
    parser.add_argument("--questionnaire", type=Path, required=True)
    parser.add_argument("--design-doc", type=Path, required=True)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--persons-summary", type=Path, help="可选；只读取样本构建汇总，不读取逐人画像")
    parser.add_argument("--exclude-response", action="append", default=[], metavar="用户ID:理由", help="可重复；清理研究诉求不符或逻辑不自洽的完成回答")
    parser.add_argument("--analysis", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--report-date", help="可选；输出文件日期，格式 YYYYMMDD，默认使用报告生成日期")
    args = parser.parse_args()
    try:
        base = prepare_analysis(args)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        analysis_path = args.output_dir / "analysis_summary.json"
        if args.analysis:
            analysis = load_json(args.analysis)
            validate_analysis(base, analysis)
        else:
            analysis = base
        analysis_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.prepare_only:
            print(analysis_path)
            return 0
        if analysis.get("sample", {}).get("quality_grade") == "poor":
            raise ValueError("回答质量为 poor：已保留 analysis_summary.json，但不生成正式报告")
        report = render_report(analysis)
        problems = machine_quality(report, analysis)
        report_path = args.output_dir / report_filename(analysis, args.report_date)
        report_path.write_text(render_report(analysis, problems), encoding="utf-8")
        print(json.dumps({"report": str(report_path), "analysis": str(analysis_path), "quality_panel": "#panel-quality", "machine_checks_passed": not problems, "problems": problems}, ensure_ascii=False, indent=2))
        return 0 if not problems else 1
    except (OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile, ET.ParseError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    sys.exit(main())
