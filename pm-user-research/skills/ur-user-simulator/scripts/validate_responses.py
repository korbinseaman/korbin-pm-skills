#!/usr/bin/env python3
"""Validate questionnaire Markdown, persona files, and per-user answer Markdown."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


QUESTION_HEADING = re.compile(r"^##\s+(Q[A-Za-z0-9_.-]+)\s*(?:[｜|]\s*(.+?))?\s*$")
ANSWER_HEADING = re.compile(r"^###\s+(Q[A-Za-z0-9_.-]+)\s*$")


def issue(code: str, severity: str, message: str, question_ids: list[str] | None = None,
          evidence: Any = None, suggestion: str = "", user_ids: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": code,
        "severity": severity,
        "question_ids": question_ids or [],
        "user_ids": user_ids or [],
        "evidence": evidence,
        "explanation": message,
        "suggestion": suggestion,
    }


def parse_persons_summary(path: Path) -> tuple[int, list[str]]:
    text = path.read_text(encoding="utf-8")
    total_match = re.search(r"画像总数\s*[：:]\s*(\d+)\s*人?", text)
    ids_match = re.search(r"全量用户ID\s*[：:]\s*(\[[^\r\n]+\])", text)
    if not total_match or not ids_match:
        raise ValueError("persons_summary.txt 必须包含画像总数和全量用户ID")
    try:
        user_ids = json.loads(ids_match.group(1))
    except json.JSONDecodeError as exc:
        raise ValueError("全量用户ID 必须是合法 JSON 数组") from exc
    if not isinstance(user_ids, list) or not user_ids or not all(isinstance(item, str) and item for item in user_ids):
        raise ValueError("全量用户ID 必须是非空字符串数组")
    total = int(total_match.group(1))
    if len(user_ids) != total:
        raise ValueError(f"画像总数为 {total}，但全量用户ID 有 {len(user_ids)} 个")
    if len(set(user_ids)) != len(user_ids):
        raise ValueError("全量用户ID 存在重复")
    return total, user_ids


def resolve_persona_files(persons_dir: Path, user_ids: list[str]) -> dict[str, Path]:
    persons_dir = persons_dir.resolve()
    if not persons_dir.is_dir():
        raise ValueError(f"单人画像目录不存在：{persons_dir}")
    resolved: dict[str, Path] = {}
    for user_id in user_ids:
        matches = sorted(persons_dir.glob(f"{user_id}_*.txt"))
        if len(matches) != 1:
            raise ValueError(f"用户 {user_id} 应恰好对应一个画像文件，实际找到 {len(matches)} 个")
        resolved[user_id] = matches[0].resolve()
    extra_ids = []
    for path in persons_dir.glob("*.txt"):
        candidate = path.name.split("_", 1)[0]
        if candidate not in resolved:
            extra_ids.append(candidate)
    if extra_ids:
        raise ValueError(f"persons/ 中存在未列入全量用户ID的文件：{', '.join(sorted(set(extra_ids)))}")
    return resolved


def parse_persona(path: Path, expected_user_id: str | None = None) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "：" not in line:
            continue
        key, value = line.split("：", 1)
        if key.strip() and value.strip():
            fields[key.strip()] = value.strip()
    user_id = fields.get("画像编号")
    if not user_id:
        raise ValueError(f"画像文件缺少画像编号：{path}")
    if expected_user_id and user_id != expected_user_id:
        raise ValueError(f"画像文件中的编号 {user_id} 与任务用户 {expected_user_id} 不一致")
    return fields


def _question_type(label: str) -> str:
    if "多选" in label:
        return "multi_choice"
    if "排序" in label:
        return "ranking"
    if "NPS" in label.upper():
        return "nps"
    if "量表" in label:
        return "likert_scale"
    if "开放" in label or "文本" in label:
        return "open_text"
    return "single_choice"


def parse_questionnaire(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    questions: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    body: list[str] = []

    def finish() -> None:
        nonlocal current, body
        if current is None:
            return
        nonempty = [line.strip() for line in body if line.strip()]
        prompt_lines = [line for line in nonempty if not line.startswith("-") and not line.startswith("【逻辑提示")]
        options = [line[2:].strip() for line in nonempty if line.startswith("- ")]
        current["question"] = " ".join(prompt_lines)
        current["logic_text"] = " ".join(line for line in nonempty if line.startswith("【逻辑提示"))
        dynamic = next((item for item in options if "动态回填" in item), "")
        if dynamic:
            source = re.search(r"Q[A-Za-z0-9_.-]+", dynamic)
            if source:
                current["options_from_question_id"] = source.group(0)
            options = [item for item in options if item != dynamic]
        if options and current["type"] in {"single_choice", "multi_choice", "ranking"}:
            current["options"] = options
        label = current["type_label"]
        max_match = re.search(r"(?:最多|选)\s*(\d+)\s*项", label)
        if max_match:
            current["max_choices"] = int(max_match.group(1))
        if current["type"] in {"likert_scale", "nps"}:
            scale_match = re.search(r"(\d+)\s*[–—-]\s*(\d+)", label)
            if scale_match:
                current["scale"] = {"min": float(scale_match.group(1)), "max": float(scale_match.group(2))}
            else:
                numeric_options = [re.match(r"(\d+(?:\.\d+)?)\s*=", item) for item in options]
                values = [float(match.group(1)) for match in numeric_options if match]
                if values:
                    current["scale"] = {"min": min(values), "max": max(values)}
        current["required"] = "选填" not in label and "可选" not in label
        questions.append(current)
        current, body = None, []

    for line in lines:
        match = QUESTION_HEADING.match(line.strip())
        if match:
            finish()
            label = (match.group(2) or "单选").strip()
            current = {"id": match.group(1), "type_label": label, "type": _question_type(label)}
            continue
        if current is not None:
            if line.startswith("## "):
                finish()
            else:
                body.append(line)
    finish()
    if not questions:
        raise ValueError("questionnaire.md 中没有识别到以“## Q...”开头的题目")
    ids = [question["id"] for question in questions]
    if len(set(ids)) != len(ids):
        raise ValueError("questionnaire.md 中存在重复题号")

    by_id = {question["id"]: question for question in questions}
    for index, question in enumerate(questions):
        logic = question.get("logic_text", "")
        if not logic:
            continue
        if "排他项" in logic:
            quoted = re.findall(r"「([^」]+)」", logic.split("排他项", 1)[0])
            if quoted:
                question["exclusive_options"] = quoted[-1:]
        if "结束答题" in logic:
            quoted = re.findall(r"「([^」]+)」", logic.split("结束答题", 1)[0])
            for later in questions[index + 1:]:
                later.setdefault("show_conditions", []).append({
                    "question_id": question["id"], "operator": "not_in", "value": quoted,
                })
        if "跳过" in logic:
            before, after = logic.split("跳过", 1)
            quoted = re.findall(r"「([^」]+)」", before)
            for target in re.findall(r"Q[A-Za-z0-9_.-]+", after):
                if target in by_id and quoted:
                    by_id[target].setdefault("show_conditions", []).append({
                        "question_id": question["id"], "operator": "not_contains", "value": quoted[-1],
                    })
        show_match = re.search(r"仅当\s*(Q[A-Za-z0-9_.-]+)\s*未选「([^」]+)」时显示", logic)
        if show_match:
            question.setdefault("show_conditions", []).append({
                "question_id": show_match.group(1), "operator": "not_contains", "value": show_match.group(2),
            })
    return questions


def answer_value(value: Any) -> Any:
    return value.get("value") if isinstance(value, dict) and "value" in value else value


def condition_matches(condition: dict[str, Any], answers: dict[str, Any]) -> bool:
    actual = answer_value(answers.get(str(condition.get("question_id"))))
    expected = condition.get("value")
    operator = condition.get("operator", "equals")
    if operator == "equals":
        return actual == expected
    if operator == "not_equals":
        return actual is not None and actual != expected
    if operator == "contains":
        return expected in actual if isinstance(actual, list) else isinstance(actual, str) and str(expected) in actual
    if operator == "not_contains":
        if actual is None:
            return False
        return expected not in actual if isinstance(actual, list) else str(expected) not in str(actual)
    if operator == "in":
        return actual in (expected or [])
    if operator == "not_in":
        return actual is not None and actual not in (expected or [])
    return False


def question_is_applicable(question: dict[str, Any], answers: dict[str, Any]) -> bool:
    return all(condition_matches(condition, answers) for condition in question.get("show_conditions", []))


def parse_model_json(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise
        value = json.loads(text[start:end + 1])
    if not isinstance(value, dict) or not isinstance(value.get("answers"), dict):
        raise ValueError("模型输出必须包含 answers 对象")
    notes = value.get("answer_notes", {})
    if notes is not None and not isinstance(notes, dict):
        raise ValueError("answer_notes 必须是对象")
    value["answer_notes"] = notes or {}
    return value


def _display_answer(value: Any) -> str:
    if value is None or value == "":
        return "未作答"
    if isinstance(value, list):
        return "；".join(str(item) for item in value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def write_answer_markdown(path: Path, *, run_id: str, user_id: str, persona: dict[str, str],
                          questionnaire_path: Path, provider: str, model: str,
                          questions: list[dict[str, Any]], result: dict[str, Any]) -> None:
    answers = result.get("answers", {})
    notes = result.get("answer_notes", {})
    lines = [
        f"任务ID：{run_id}-{user_id}",
        f"用户ID：{user_id}",
        f"姓名：{persona.get('姓名', '')}",
        f"问卷来源：{questionnaire_path.resolve()}",
        f"模型提供商：{provider}",
        f"实际模型：{model}",
        "合成回答：是",
        "",
    ]
    for question in questions:
        qid = question["id"]
        lines.extend([f"### {qid}", f"回答：{_display_answer(answers.get(qid))}"])
        note = notes.get(qid)
        if note not in (None, ""):
            lines.append(f"回答原因：{note}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    temporary.replace(path)


def _typed_answer(raw: str, question: dict[str, Any]) -> Any:
    if raw in {"", "未作答"}:
        return None
    qtype = question.get("type")
    if qtype in {"multi_choice", "ranking"}:
        return [item.strip() for item in raw.split("；") if item.strip()]
    if qtype in {"likert_scale", "nps"}:
        try:
            number = float(raw)
            return int(number) if number.is_integer() else number
        except ValueError:
            return raw
    if raw.lower() in {"true", "false"}:
        return raw.lower() == "true"
    return raw


def parse_answer_markdown(path: Path, questions: list[dict[str, Any]]) -> dict[str, Any]:
    qmap = {question["id"]: question for question in questions}
    headers: dict[str, str] = {}
    answers: dict[str, Any] = {}
    notes: dict[str, str] = {}
    current_qid: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        heading = ANSWER_HEADING.match(line)
        if heading:
            current_qid = heading.group(1)
            continue
        if current_qid and line.startswith("回答："):
            raw = line.split("：", 1)[1].strip()
            answers[current_qid] = _typed_answer(raw, qmap.get(current_qid, {"type": "open_text"}))
            continue
        if current_qid and line.startswith("回答原因："):
            notes[current_qid] = line.split("：", 1)[1].strip()
            continue
        if current_qid is None and "：" in line:
            key, value = line.split("：", 1)
            headers[key.strip()] = value.strip()
    if not headers.get("用户ID"):
        raise ValueError("个人答卷缺少用户ID")
    return {"headers": headers, "answers": answers, "answer_notes": notes}


def _resolved_options(question: dict[str, Any], answers: dict[str, Any]) -> list[str]:
    if question.get("options"):
        return [str(item) for item in question["options"]]
    source = question.get("options_from_question_id")
    source_value = answers.get(str(source))
    values = source_value if isinstance(source_value, list) else [source_value]
    return [str(item) for item in values if item not in (None, "")]


def validate_one(user_id: str, response: dict[str, Any], questions: list[dict[str, Any]],
                 persona: dict[str, str] | None = None) -> list[dict[str, Any]]:
    answers = response.get("answers", {})
    qmap = {question["id"]: question for question in questions}
    found: list[dict[str, Any]] = []
    for qid in answers:
        if qid not in qmap:
            found.append(issue("unknown_question", "error", "答卷包含未定义题号。", [qid], answers[qid], "删除未知题号。", [user_id]))
    for question in questions:
        qid = question["id"]
        applicable = question_is_applicable(question, answers)
        value = answer_value(answers.get(qid))
        present = value not in (None, "", [])
        if not applicable and present:
            found.append(issue("skip_logic_violation", "error", "不满足显示条件却作答。", [qid], value, "按问卷逻辑跳过该题。", [user_id]))
            continue
        if applicable and question.get("required", True) and not present:
            found.append(issue("missing_answer", "error", "适用题目缺少回答。", [qid], value, "重试该用户任务。", [user_id]))
            continue
        if not present:
            continue
        qtype = question.get("type")
        options = _resolved_options(question, answers)
        if qtype == "single_choice" and options and (isinstance(value, list) or value not in options):
            found.append(issue("invalid_option", "error", "单选回答不在选项中。", [qid], value, "只保留一个合法选项。", [user_id]))
        elif qtype in {"multi_choice", "ranking"}:
            if not isinstance(value, list):
                found.append(issue("invalid_option", "error", "多选或排序回答必须使用数组/分号分隔。", [qid], value, "返回合法选项列表。", [user_id]))
            else:
                unknown = [item for item in value if options and item not in options]
                if unknown:
                    found.append(issue("invalid_option", "error", "回答包含未知选项。", [qid], unknown, "移除未知选项。", [user_id]))
                max_choices = question.get("max_choices")
                if isinstance(max_choices, int) and len(value) > max_choices:
                    found.append(issue("too_many_choices", "error", "选择数量超过上限。", [qid], value, f"最多选择 {max_choices} 项。", [user_id]))
                exclusive = set(question.get("exclusive_options", []))
                if len(value) > 1 and exclusive.intersection(map(str, value)):
                    found.append(issue("exclusive_conflict", "error", "排他选项与其他选项同时出现。", [qid], value, "排他选项只能单独选择。", [user_id]))
        elif qtype in {"likert_scale", "nps"}:
            scale = question.get("scale") or ({"min": 0, "max": 10} if qtype == "nps" else {"min": 1, "max": 5})
            try:
                number = float(value)
                if number < float(scale["min"]) or number > float(scale["max"]):
                    raise ValueError
            except (TypeError, ValueError, KeyError):
                found.append(issue("out_of_range", "error", f"量表回答必须在 {scale.get('min')}–{scale.get('max')}。", [qid], value, "返回范围内数字。", [user_id]))

    joined = json.dumps(answers, ensure_ascii=False)
    if re.search(r"作为一名.{0,20}(用户|消费者|受访者)", joined):
        found.append(issue("template_language", "warning", "出现明显角色扮演模板句。", evidence="作为一名…", suggestion="调整提示后重试。", user_ids=[user_id]))
    if persona:
        age_match = re.search(r"我今年\s*(\d{1,3})\s*岁", joined)
        if age_match and persona.get("年龄") and age_match.group(1) != re.sub(r"\D", "", persona["年龄"]):
            found.append(issue("persona_conflict", "warning", "回答自述年龄与画像不一致。", evidence=age_match.group(0), suggestion="人工复核或重试。", user_ids=[user_id]))
    return found


def batch_authenticity(records: list[dict[str, Any]], questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    qtypes = {question["id"]: question.get("type") for question in questions}
    texts: list[tuple[str, str, str]] = []
    for record in records:
        user_id = record["user_id"]
        for qid, value in record.get("answers", {}).items():
            if qtypes.get(qid) == "open_text" and isinstance(value, str) and len(value) >= 30:
                texts.append((user_id, qid, re.sub(r"\s+", "", value)))
    found: list[dict[str, Any]] = []
    for index, left in enumerate(texts):
        for right in texts[index + 1:]:
            if left[1] != right[1]:
                continue
            ratio = difflib.SequenceMatcher(None, left[2], right[2]).ratio()
            if ratio >= 0.9:
                found.append(issue("cross_response_duplicate", "warning", "不同画像的长文本回答高度相似。", [left[1]], {"users": [left[0], right[0]], "similarity": round(ratio, 3)}, "人工抽查模板化风险。", [left[0], right[0]]))
    return found


def validate_answer_directory(questionnaire: Path, persons_summary: Path, persons_dir: Path,
                              answers_dir: Path, failures: dict[str, str] | None = None) -> dict[str, Any]:
    _, user_ids = parse_persons_summary(persons_summary)
    persona_files = resolve_persona_files(persons_dir, user_ids)
    questions = parse_questionnaire(questionnaire)
    failures = failures or {}
    records: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    models: Counter[str] = Counter()
    for user_id in user_ids:
        answer_path = answers_dir / f"{user_id}.md"
        if not answer_path.exists():
            issues.append(issue("missing_response", "error", failures.get(user_id, "没有生成有效个人答卷。"), user_ids=[user_id], suggestion="检查任务错误并重试。"))
            records.append({"user_id": user_id, "status": "failed", "answers": {}, "answer_notes": {}})
            continue
        try:
            parsed = parse_answer_markdown(answer_path, questions)
            if parsed["headers"].get("用户ID") != user_id:
                raise ValueError("答卷用户ID与文件名不一致")
            persona = parse_persona(persona_files[user_id], user_id)
            found = validate_one(user_id, parsed, questions, persona)
            issues.extend(found)
            provider = parsed["headers"].get("模型提供商", "unknown-provider")
            model = parsed["headers"].get("实际模型", "current-model")
            models[f"{provider}::{model}"] += 1
            records.append({"user_id": user_id, "status": "completed", **parsed, "issues": found})
        except (OSError, ValueError) as exc:
            issues.append(issue("invalid_response_file", "error", str(exc), user_ids=[user_id], suggestion="修复或重跑该用户任务。"))
            records.append({"user_id": user_id, "status": "failed", "answers": {}, "answer_notes": {}})
    batch_issues = batch_authenticity([record for record in records if record["status"] == "completed"], questions)
    issues.extend(batch_issues)
    completed = sum(record["status"] == "completed" for record in records)
    total = len(user_ids)
    if total == 0 or completed / total < 0.7:
        integrity = "poor"
    elif any(item["severity"] == "error" for item in issues):
        integrity = "needs_review"
    elif sum(item["severity"] == "warning" for item in issues) > max(1, total // 2):
        integrity = "good"
    else:
        integrity = "excellent"
    return {
        "total": total,
        "completed": completed,
        "failed": total - completed,
        "completion_rate": completed / total if total else 0.0,
        "data_integrity": integrity,
        "provider_distribution": dict(models),
        "issues": issues,
        "records": records,
        "question_ids": [question["id"] for question in questions],
    }


def quality_markdown(run_id: str, quality: dict[str, Any]) -> str:
    counts = Counter((item["type"], item["severity"]) for item in quality["issues"])
    issue_rows = []
    for (kind, severity), count in sorted(counts.items()):
        users = sorted({user for item in quality["issues"] if item["type"] == kind and item["severity"] == severity for user in item.get("user_ids", [])})
        issue_rows.append(f"| {kind} | {severity} | {count} | {', '.join(users) or '-'} |")
    model_rows = [f"- `{name}`：{count}" for name, count in sorted(quality["provider_distribution"].items())]
    review_rows = []
    for item in quality["issues"]:
        if item["severity"] in {"error", "warning"}:
            review_rows.append(f"- {','.join(item.get('user_ids') or ['批次'])} / {item['type']}：{item['explanation']}")
    decision = "可以进入后续分析" if quality["data_integrity"] in {"excellent", "good"} else "修复或复核后再进入后续分析"
    return f"""# 合成调研数据质量报告

> 此批次为合成数据；真实性检查只能识别风险信号。

## 执行概览

- run_id：`{run_id}`
- 样本数：{quality['total']}
- 完成：{quality['completed']}
- 失败：{quality['failed']}
- 完成率：{quality['completion_rate']:.1%}
- 数据质量：**{quality['data_integrity']}**

## 模型分配

{chr(10).join(model_rows) or '- 无成功任务'}

## 问题统计

| 类型 | 严重度 | 数量 | 涉及用户ID |
|---|---|---:|---|
{chr(10).join(issue_rows) or '| 无 | - | 0 | - |'}

## 需要人工复核

{chr(10).join(review_rows) or '- 无'}

## 结论与是否可进入分析

{decision}。合成结果不能替代真实用户研究或用于估计总体比例。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="校验个人问卷答卷并生成质量报告")
    parser.add_argument("--questionnaire", type=Path, required=True)
    parser.add_argument("--persons-summary", type=Path, required=True)
    parser.add_argument("--persons-dir", type=Path, required=True)
    parser.add_argument("--answers-dir", type=Path, required=True)
    parser.add_argument("--quality-report", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--failure", action="append", default=[], metavar="USER_ID=ERROR")
    args = parser.parse_args()
    failures = {}
    for value in args.failure:
        if "=" not in value:
            parser.error("--failure 必须使用 USER_ID=ERROR 格式")
        user_id, message = value.split("=", 1)
        failures[user_id] = message
    try:
        quality = validate_answer_directory(
            args.questionnaire.resolve(), args.persons_summary.resolve(), args.persons_dir.resolve(),
            args.answers_dir.resolve(), failures,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    args.quality_report.parent.mkdir(parents=True, exist_ok=True)
    args.quality_report.write_text(quality_markdown(args.run_id, quality), encoding="utf-8")
    print(json.dumps({key: quality[key] for key in ("total", "completed", "failed", "completion_rate", "data_integrity")}, ensure_ascii=False, indent=2))
    return 0 if quality["data_integrity"] in {"excellent", "good"} else 1


if __name__ == "__main__":
    sys.exit(main())
