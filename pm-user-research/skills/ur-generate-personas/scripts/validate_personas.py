#!/usr/bin/env python3
"""Validate template-based persona content, output layout and consistency."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PERSONA_TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "persona_template.json"
REQUIRED_FIELDS = {
    "画像编号", "姓名", "年龄", "性别", "职业", "通用行为", "使用设备",
    "相关使用经验", "使用阶段", "系统App使用习惯",
}


def load_template_fields() -> set[str]:
    try:
        template = json.loads(PERSONA_TEMPLATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 persona_template.json：{exc}") from exc
    if not isinstance(template, dict) or not template:
        raise ValueError("persona_template.json 必须是非空 JSON 对象")
    fields = set(template)
    missing = sorted(REQUIRED_FIELDS - fields)
    if missing:
        raise ValueError(f"persona_template.json 缺少生成所需核心字段：{missing}")
    return fields


def issue(code: str, message: str, persona_id: str | None = None) -> dict[str, str]:
    result = {"code": code, "message": message}
    if persona_id:
        result["persona_id"] = persona_id
    return result


def validate_persona(persona: dict[str, Any], allowed_fields: set[str], blockers: list[dict[str, str]]) -> None:
    pid = str(persona.get("画像编号") or "")
    missing = sorted(REQUIRED_FIELDS - set(persona))
    extra = sorted(set(persona) - allowed_fields)
    if missing or extra:
        blockers.append(issue("persona_fields", f"画像字段不符合模板；缺少={missing}；多余={extra}", pid))
        return
    empty = [key for key, value in persona.items() if value in (None, "", "不适用")]
    if empty:
        blockers.append(issue("empty_optional_fields", f"画像不得输出空值、null 或“不适用”字段：{empty}", pid))
    age = persona["年龄"]
    role = str(persona["职业"])
    income = str(persona.get("月收入") or "")
    stage = persona["使用阶段"]
    if not isinstance(age, int) or not 18 <= age <= 80:
        blockers.append(issue("age_invalid", "年龄必须是 18–80 岁的整数", pid))
    if "学生" in role and (not isinstance(age, int) or age > 34 or income not in {"0–3000元", "3000元以下"}):
        blockers.append(issue("student_conflict", "学生年龄或收入设定不合理", pid))
    if "退休" in role and (not isinstance(age, int) or age < 50):
        blockers.append(issue("retirement_conflict", "退休人员年龄不能低于 50 岁", pid))
    if stage not in {"当前使用者", "曾经使用者", "潜在用户"}:
        blockers.append(issue("usage_stage", "使用阶段取值无效", pid))
    has_habit = "相关产品或功能使用习惯" in persona
    has_judgment = "判断" in persona
    if stage == "潜在用户":
        if has_habit or has_judgment:
            blockers.append(issue("invented_experience", "潜在用户不得输出使用习惯或判断字段", pid))
    elif not has_habit or not has_judgment:
        blockers.append(issue("experienced_content_missing", "有经验者必须包含使用习惯和判断", pid))


def validate_files(personas: list[dict[str, Any]], summary_path: Path, persons_dir: Path, blockers: list[dict[str, str]]) -> None:
    if not summary_path.exists():
        blockers.append(issue("summary_missing", f"缺少汇总文件：{summary_path.name}"))
    else:
        text = summary_path.read_text(encoding="utf-8")
        for heading in ("用户画像汇总", "画像总数", "全量用户ID", "用户群体分布", "性别分布", "年龄段分布", "相关经验分布", "使用阶段分布", "系统App使用习惯分布"):
            if heading not in text:
                blockers.append(issue("summary_structure", f"汇总文件缺少“{heading}”"))
        id_prefix = "全量用户ID："
        id_lines = [line for line in text.splitlines() if line.startswith(id_prefix)]
        if len(id_lines) != 1:
            blockers.append(issue("summary_ids_structure", "汇总文件必须且只能包含一行全量用户ID数组"))
        else:
            try:
                summary_ids = json.loads(id_lines[0][len(id_prefix):])
            except json.JSONDecodeError:
                blockers.append(issue("summary_ids_invalid", "全量用户ID必须使用合法的 JSON 数组格式"))
            else:
                expected_ids = [persona.get("画像编号") for persona in personas]
                if summary_ids != expected_ids:
                    blockers.append(issue("summary_ids_mismatch", "全量用户ID必须与 personas.json 中的画像顺序完全一致"))
    if not persons_dir.is_dir():
        blockers.append(issue("persons_dir_missing", f"缺少单人画像目录：{persons_dir.name}"))
        return
    files = sorted(persons_dir.glob("P*.txt"))
    if len(files) != len(personas):
        blockers.append(issue("persona_file_count", f"单人画像文件数 {len(files)} 与画像数 {len(personas)} 不一致"))
    file_map = {path.name.split("_", 1)[0]: path for path in files}
    for persona in personas:
        pid = persona.get("画像编号")
        path = file_map.get(pid)
        if not path:
            blockers.append(issue("persona_file_missing", "缺少单人画像文件", pid))
            continue
        text = path.read_text(encoding="utf-8")
        parsed: dict[str, str] = {}
        ordered_keys: list[str] = []
        for line in text.splitlines():
            if not line.strip():
                continue
            if "：" not in line:
                blockers.append(issue("persona_txt_structure", f"单人画像存在非键值行：{line}", pid))
                continue
            key, value = line.split("：", 1)
            ordered_keys.append(key)
            parsed[key] = value
        if ordered_keys != list(persona):
            blockers.append(issue("persona_txt_order", "单人画像字段或顺序与 persona_template.json 不一致", pid))
        for key, value in persona.items():
            if parsed.get(key) != str(value):
                blockers.append(issue("persona_txt_value", f"单人画像字段“{key}”与 JSON 不一致", pid))


def validate(data: dict[str, Any], summary_path: Path, persons_dir: Path) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []
    allowed_fields = load_template_fields()
    if data.get("schema_version") != "5.3":
        blockers.append(issue("schema_version", "schema_version 必须为 5.3"))
    personas = data.get("personas")
    if not isinstance(personas, list) or not personas:
        blockers.append(issue("personas_missing", "personas 必须是非空数组"))
        personas = []
    if data.get("sample_size") != len(personas):
        blockers.append(issue("sample_size_mismatch", "sample_size 与画像数量不一致"))
    ids = [p.get("画像编号") for p in personas if isinstance(p, dict)]
    if len(ids) != len(set(ids)):
        blockers.append(issue("duplicate_id", "画像编号重复"))
    for persona in personas:
        if isinstance(persona, dict):
            validate_persona(persona, allowed_fields, blockers)
        else:
            blockers.append(issue("persona_type", "persona 必须是对象"))

    groups = data.get("audience_groups") or []
    spec = data.get("generation_spec") or {}
    if spec.get("allocation_is_population_estimate") is not False:
        blockers.append(issue("allocation_claim", "构建配额不得标记为真实人口分布估计"))
    allocation = {
        item.get("audience_group"): item.get("count")
        for item in spec.get("group_allocation", [])
        if isinstance(item, dict)
    }
    if set(allocation) != set(groups) or sum(value for value in allocation.values() if isinstance(value, int)) != len(personas):
        blockers.append(issue("allocation_mismatch", "群体配额必须覆盖全部候选群体且合计等于画像数量"))
    stage_keys = {"当前使用者": "current", "曾经使用者": "lapsed", "潜在用户": "potential"}
    stages = Counter(stage_keys[p["使用阶段"]] for p in personas if isinstance(p, dict) and p.get("使用阶段") in stage_keys)
    if spec.get("usage_stage_allocation") != dict(stages):
        blockers.append(issue("usage_allocation", "使用阶段配额与实际画像不一致"))
    validate_files(personas, summary_path, persons_dir, blockers)
    if (summary_path.parent / "personas.txt").exists():
        blockers.append(issue("legacy_personas_txt", "不应保留合并版 personas.txt"))
    score = max(0, 100 - len(blockers) * 20)
    return {
        "passed": not blockers,
        "score": score,
        "grade": "excellent" if not blockers else "failed",
        "blockers": blockers,
        "warnings": [],
        "coverage": {
            "personas": len(personas),
            "audience_groups": allocation,
            "usage_stages": dict(stages),
            "shares_are_population_estimates": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="验证合成画像")
    parser.add_argument("input", type=Path)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--persons-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--write-back", action="store_true")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        result = validate(data, args.summary or args.input.parent / "persons_summary.txt", args.persons_dir or args.input.parent / "persons")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"审计失败：{exc}", file=sys.stderr)
        return 2
    if args.write_back:
        data["quality_check"] = result
        args.input.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
