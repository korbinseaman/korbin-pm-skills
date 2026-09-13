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
        limitations.append("persons_summary.txt 仅用于披露样本构建背景，不能作为问卷发现、分群依据或单个回答的解释。")
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
    width, row_h, label_w, bar_w = 820, 40, 280, 420
    height = 26 + row_h * len(distribution)
    maximum = max(int(item.get("count", 0)) for item in distribution) or 1
    rows = []
    for index, item in enumerate(distribution):
        y = 12 + index * row_h
        count = int(item.get("count", 0))
        length = max(2, int(count / maximum * bar_w))
        rows.append(f'<text x="0" y="{y + 17}" class="axis">{esc(item.get("label"))}</text><rect x="{label_w}" y="{y}" width="{length}" height="24" rx="4" class="bar"/><text x="{label_w + length + 8}" y="{y + 17}" class="value">{count}（{float(item.get("percent", 0)):.1f}%）</text>')
    return f'<div class="chart"><svg viewBox="0 0 {width} {height}" role="img" aria-label="回答分布，分母 {base_n}">{"".join(rows)}</svg></div>'


def source_label() -> tuple[str, str]:
    return "合成模拟数据", "用于检查研究工具和形成待验证假设，不代表真实用户或市场总体。"


def render_report(analysis: dict[str, Any]) -> str:
    label, disclosure = source_label()
    sample = analysis.get("sample", {})
    context = analysis.get("research_context", {})
    goals = analysis.get("goal_coverage", [])
    themes = analysis.get("themes", [])
    segments = analysis.get("segment_observations", [])
    recommendations = analysis.get("recommendations", [])
    limitations = analysis.get("limitations", [])
    observations = analysis.get("qualitative_observations", [])
    cleaning = analysis.get("data_cleaning", {})
    cross_tabs = analysis.get("cross_tabulations", [])
    scale_quality = analysis.get("scale_quality", [])

    goal_rows = "".join(f'<tr><td>{esc(goal.get("goal_id"))}</td><td>{esc(goal.get("research_question"))}</td><td>{esc(", ".join(goal.get("question_ids", [])) or "无")}</td><td>{esc(goal.get("status"))}</td><td>{esc(goal.get("finding"))}</td></tr>' for goal in goals) or '<tr><td colspan="5">questionnaire-design.html 未提供可识别的研究目标。</td></tr>'

    charts = []
    for result in analysis.get("descriptive_results", []):
        if result.get("type") == "open_text":
            continue
        notes = []
        if result.get("multi_select"):
            notes.append("多选/排序的百分比合计可超过 100%")
        numeric = result.get("numeric_summary")
        if numeric:
            deviation = numeric.get("standard_deviation")
            notes.append(f"均值 {numeric.get('mean')}，标准差 {deviation if deviation is not None else '样本不足'}，中位数 {numeric.get('median')}")
        ranking = result.get("ranking") or []
        if ranking:
            ranked = sorted((item for item in ranking if item.get("selected_count")), key=lambda item: (-item.get("first_choice_count", 0), item.get("average_rank") or 99))
            notes.append("排序概览：" + "；".join(f"{item['label']} 首选 {item['first_choice_count']}，平均名次 {item['average_rank']}" for item in ranked[:3]))
        note_text = "；".join(notes)
        charts.append(f'<section class="evidence"><h3>{esc(result.get("question_id"))} · {esc(result.get("question"))}</h3><p>实际分母 <strong>{result.get("base_n", 0)}</strong>，完成样本中的空白/未作答 {result.get("missing_n", 0)}。{esc(note_text)}。只描述本批次。</p>{bar_svg(result.get("distribution", []), int(result.get("base_n", 0)))}</section>')
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
    evidence_rows = "".join(f'<tr><td>{esc(item.get("evidence_id"))}</td><td>{"模拟原话" if item.get("synthetic_quote") else "回答原文"}</td><td>{esc(item.get("kind"))}</td><td>{esc(item.get("text"))}</td></tr>' for item in observations) or '<tr><td colspan="4">没有开放回答或回答原因。</td></tr>'
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
    construction_note = f'<div class="note"><strong>样本构成说明：</strong>{"；".join(construction_bits) or "已读取 persons_summary.txt。"}。该文件只说明样本如何构建，不是回答证据、分群字段或市场比例。</div>' if construction else ""
    cross_rows = "".join(f"<tr><td>{esc(item.get('group_question_id'))}</td><td>{esc(item.get('target_question_id'))}</td><td>{esc(item.get('base_n'))}</td><td>{esc(item.get('finding'))}</td></tr>" for item in cross_tabs) or '<tr><td colspan="4">尚未形成满足样本量与研究目标要求的交叉分析。</td></tr>'
    scale_rows = "".join(f"<tr><td>{esc(item.get('scale_name') or item.get('question_ids'))}</td><td>{esc(item.get('method'))}</td><td>{esc(item.get('result'))}</td><td>{esc(item.get('interpretation'))}</td></tr>" for item in scale_quality) or '<tr><td colspan="4">没有满足同一构念、同一量表且样本条件足够的信效度检验。</td></tr>'

    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(analysis.get("title"))}</title>
<style>:root{{--ink:#172033;--muted:#596274;--line:#dce2ec;--soft:#f5f7fb;--brand:#3157d5;--warn:#934800;--warnbg:#fff4e8}}*{{box-sizing:border-box}}body{{margin:0;background:#edf1f6;color:var(--ink);font:16px/1.65 system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif}}main{{max-width:1020px;margin:32px auto;background:#fff;padding:48px;border-radius:16px;box-shadow:0 10px 34px #18213a18}}h1{{font-size:34px;line-height:1.2;margin:0 0 8px}}h2{{margin-top:44px;border-bottom:2px solid var(--line);padding-bottom:8px}}h3{{margin-bottom:6px}}.banner{{padding:16px 18px;background:var(--warnbg);border-left:5px solid #df8427;border-radius:8px;margin:20px 0}}.banner strong{{color:var(--warn)}}.note{{padding:14px 16px;background:#eef4ff;border-radius:8px;margin:16px 0}}.metrics{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}}.metric{{background:var(--soft);padding:13px;border-radius:10px}}.metric b{{display:block;font-size:23px}}table{{width:100%;border-collapse:collapse;margin:14px 0;font-size:14px}}th,td{{text-align:left;vertical-align:top;border:1px solid var(--line);padding:9px}}th{{background:var(--soft)}}.evidence,.card{{border:1px solid var(--line);border-radius:12px;padding:18px;margin:18px 0}}.chart{{overflow-x:auto}}svg{{width:100%;min-width:680px}}.bar{{fill:var(--brand)}}.axis{{font-size:13px;fill:var(--ink)}}.value{{font-size:13px;fill:var(--muted)}}.pill{{display:inline-block;padding:2px 8px;border-radius:99px;background:#e8edff;color:#2544a2;font-size:13px}}.empty,small{{color:var(--muted)}}code{{background:var(--soft);padding:2px 5px;border-radius:4px}}@media(max-width:760px){{main{{margin:0;padding:24px;border-radius:0}}.metrics{{grid-template-columns:repeat(2,1fr)}}h1{{font-size:28px}}}}</style></head><body><main>
<h1>{esc(analysis.get("title"))}</h1><p>批次：<code>{esc(analysis.get("run_id"))}</code> · 生成时间：{esc(analysis.get("generated_at"))}</p><div class="banner"><strong>{esc(label)}</strong><br>{esc(disclosure)}</div>{construction_note}
<h2>研究目标与证据覆盖</h2><p><strong>产品决策：</strong>{esc(context.get("decision", "未提供"))}</p><p><strong>目标用户：</strong>{esc(context.get("target_audience", "未提供"))}</p><table><thead><tr><th>ID</th><th>研究目标</th><th>题目</th><th>状态</th><th>当前结论</th></tr></thead><tbody>{goal_rows}</tbody></table>
<h2>样本、清理与数据质量</h2><div class="metrics"><div class="metric"><span>总样本</span><b>{sample.get("total", 0)}</b></div><div class="metric"><span>完成</span><b>{sample.get("completed", 0)}</b></div><div class="metric"><span>可分析</span><b>{sample.get("analyzable", 0)}</b></div><div class="metric"><span>失败</span><b>{sample.get("failed", 0)}</b></div><div class="metric"><span>完成率</span><b>{float(sample.get("completion_rate", 0)):.1%}</b></div></div><p>回答质量：<strong>{esc(sample.get("quality_grade"))}</strong>；完成回答清理前 {cleaning.get("completed_before_cleaning", 0)}，清理后 {cleaning.get("analyzable_after_cleaning", 0)}，剔除 {cleaning.get("excluded_count", 0)}。</p><h3>清理剔除记录</h3><ul>{cleaned_rows}</ul><h3>待人工复核</h3><ul>{review_rows}</ul><h3>实际模型</h3><ul>{model_items}</ul><h3>已记录问题</h3><ul>{issue_items}</ul>
<h2>封闭题描述统计</h2><p>每张图使用本题实际回答分母；失败行不进入题目分母。</p>{"".join(charts)}
<h2>高级与交叉分析</h2><h3>交叉分析</h3><table><thead><tr><th>分组题</th><th>目标题</th><th>有效样本</th><th>观察</th></tr></thead><tbody>{cross_rows}</tbody></table><h3>量表信效度</h3><table><thead><tr><th>量表/题项</th><th>方法</th><th>结果</th><th>解释</th></tr></thead><tbody>{scale_rows}</tbody></table>
<h2>主题、痛点与需求</h2>{"".join(theme_cards)}
<h2>分群观察与反例</h2><table><thead><tr><th>分群</th><th>来源</th><th>n</th><th>观察</th><th>限制</th></tr></thead><tbody>{segment_rows}</tbody></table>
<h2>建议与下一步验证</h2><ol>{rec_items}</ol>
<h2>限制与未回答问题</h2><ul>{limit_items}</ul>
<h2>证据索引</h2><table><thead><tr><th>证据 ID</th><th>披露</th><th>类型</th><th>文本</th></tr></thead><tbody>{evidence_rows}</tbody></table>
</main></body></html>'''


def validate_analysis(base: dict[str, Any], analysis: dict[str, Any]) -> None:
    protected = ["schema_version", "study_id", "run_id", "data_source", "sample", "data_cleaning", "descriptive_results", "qualitative_observations"]
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
    if not analysis.get("limitations"):
        problems.append("缺少限制")
    return problems


def quality_markdown(analysis: dict[str, Any], problems: list[str]) -> str:
    checks = analysis.get("contract_checks", {})
    contract_rows = "\n".join(f"| {key} | {value} |" for key, value in checks.items())
    result = "自动检查通过" if not problems else "自动检查失败"
    return f"""# 报告质量检查

## 批次

- run_id：`{analysis.get('run_id')}`
- 数据来源：`{analysis.get('data_source')}`
- 结果：**{result}**

## 输入契约

| 检查项 | 结果 |
|---|---|
{contract_rows}

## 自动检查

- 离线资源：{'通过' if 'HTML 包含外部资源' not in problems else '失败'}
- SVG 图表：{'通过' if '有封闭题数据但没有 SVG 图表' not in problems else '失败'}
- run_id 披露：{'通过' if 'HTML 未显示 run_id' not in problems else '失败'}
- 数据来源披露：{'通过' if '合成数据披露不足' not in problems else '失败'}
- 数据清理：完成行清理前 `{analysis.get('data_cleaning', {}).get('completed_before_cleaning', 0)}`，可分析 `{analysis.get('data_cleaning', {}).get('analyzable_after_cleaning', 0)}`，剔除 `{analysis.get('data_cleaning', {}).get('excluded_count', 0)}`。
- 问题：{'无' if not problems else '；'.join(problems)}

## 交付前人工审计

- [ ] 至少 3 项统计已与 Excel 原行核对
- [ ] 至少 3 个证据 ID 已回到 Excel 用户行与题目/回答原因列
- [ ] 已复核数据清理清单；所有人工剔除均有研究相关或逻辑不自洽的书面理由
- [ ] 已打开 HTML 检查桌面和窄屏布局
- [ ] 标题、图表、表格和长文本无明显截断或重叠
- [ ] 研究目标结论、主题和建议已完成，或明确标为描述性底稿
"""


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
        report_path = args.output_dir / "report.html"
        report_path.write_text(report, encoding="utf-8")
        quality_path = args.output_dir / "report_quality.md"
        quality_path.write_text(quality_markdown(analysis, problems), encoding="utf-8")
        print(json.dumps({"report": str(report_path), "analysis": str(analysis_path), "quality": str(quality_path), "machine_checks_passed": not problems, "problems": problems}, ensure_ascii=False, indent=2))
        return 0 if not problems else 1
    except (OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile, ET.ParseError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    sys.exit(main())
