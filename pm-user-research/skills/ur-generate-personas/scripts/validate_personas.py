#!/usr/bin/env python3
"""Validate template-based persona content, output layout and consistency."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any


PERSONA_TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "persona_template.json"
REQUIRED_FIELDS = {
    "画像编号", "姓名", "年龄", "性别", "职业", "通用行为", "使用设备",
    "相关使用经验", "使用阶段", "系统App使用习惯",
}
COMPOUND_SURNAMES = (
    "欧阳", "司马", "上官", "诸葛", "夏侯", "东方", "皇甫", "尉迟",
    "公孙", "慕容", "令狐", "长孙",
)
POST_2000_STYLE_NAMES = {
    "梓轩", "子涵", "梓涵", "梓萱", "雨桐", "一诺", "诗涵",
    "沐宸", "沐阳", "若曦", "可馨", "欣妍", "语汐",
}
MID_CENTURY_STYLE_NAMES = {
    "建国", "国庆", "援朝", "跃进", "卫东", "红卫", "解放", "建军",
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


def chinese_given_name(name: str) -> str | None:
    normalized = name.strip()
    if not re.fullmatch(r"[\u3400-\u9fff]{2,4}", normalized):
        return None
    surname_length = 2 if any(normalized.startswith(surname) for surname in COMPOUND_SURNAMES) else 1
    given_name = normalized[surname_length:]
    return given_name or None


def name_age_band(age: int) -> str:
    if age <= 24:
        return "18–24岁"
    if age <= 34:
        return "25–34岁"
    if age <= 44:
        return "35–44岁"
    if age <= 54:
        return "45–54岁"
    if age <= 64:
        return "55–64岁"
    return "65–80岁"


def name_age_conflict(name: str, age: int) -> str | None:
    """Return only strong Chinese name/cohort conflicts; ambiguous cases stay human-reviewed."""
    given_name = chinese_given_name(name)
    if not given_name:
        return None
    birth_year = date.today().year - age
    if birth_year <= 1976 and given_name in POST_2000_STYLE_NAMES:
        return f"姓名“{name}”明显偏向 2000 年后命名风格，与约 {birth_year} 年出生的设定冲突"
    if birth_year >= 2000 and given_name in MID_CENTURY_STYLE_NAMES:
        return f"姓名“{name}”明显偏向 20 世纪中期命名风格，与约 {birth_year} 年出生的设定冲突"
    return None


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
    elif conflict := name_age_conflict(str(persona["姓名"]), age):
        blockers.append(issue("name_age_conflict", conflict, pid))
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


def validate_name_batch(
    personas: list[dict[str, Any]], spec: dict[str, Any], blockers: list[dict[str, str]],
) -> dict[str, Any]:
    names = [str(persona.get("姓名") or "").strip() for persona in personas if isinstance(persona, dict)]
    duplicates = sorted(name for name, count in Counter(names).items() if name and count > 1)
    if duplicates:
        blockers.append(issue("duplicate_name", f"批量画像不得重复完整姓名：{duplicates}"))

    chinese = [
        persona for persona in personas
        if isinstance(persona, dict) and re.fullmatch(r"[\u3400-\u9fff]{2,4}", str(persona.get("姓名") or "").strip())
    ]
    length_counts = Counter(len(str(persona["姓名"]).strip()) for persona in chinese)
    reported = spec.get("name_structure_allocation")
    actual_report = {f"{length}字全名": length_counts.get(length, 0) for length in (2, 3, 4)}
    if reported is not None and reported != actual_report:
        blockers.append(issue("name_structure_allocation", f"姓名结构配额与实际画像不一致：实际为 {actual_report}"))

    large_chinese_batch = len(personas) >= 50 and len(chinese) / len(personas) >= 0.9
    if large_chinese_batch:
        if reported is None:
            blockers.append(issue("name_structure_allocation_missing", "中文姓名为主的大批量画像必须记录 name_structure_allocation"))
        total = len(chinese)
        three_share = length_counts.get(3, 0) / total
        two_share = length_counts.get(2, 0) / total
        four_share = length_counts.get(4, 0) / total
        if not 0.70 <= three_share <= 0.80:
            blockers.append(issue("name_length_three_share", "三字全名应占中文姓名的 70%–80%"))
        if not 0.18 <= two_share <= 0.28:
            blockers.append(issue("name_length_two_share", "两字全名应占中文姓名的 18%–28%"))
        if not 0.01 <= four_share <= 0.03:
            blockers.append(issue("name_length_four_share", "四字全名应占中文姓名的 1%–3%"))
        for persona in chinese:
            name = str(persona["姓名"]).strip()
            if len(name) == 4 and not any(name.startswith(surname) for surname in COMPOUND_SURNAMES):
                blockers.append(issue("four_character_name_structure", f"四字姓名“{name}”缺少可识别的真实复姓结构", str(persona.get("画像编号") or "")))

        cohort_lengths: dict[str, list[int]] = {}
        for persona in chinese:
            age = persona.get("年龄")
            if isinstance(age, int):
                cohort_lengths.setdefault(name_age_band(age), []).append(len(str(persona["姓名"]).strip()))
        for band, lengths in cohort_lengths.items():
            if len(lengths) >= 10 and len(set(lengths)) < 2:
                blockers.append(issue("name_length_cohort_homogeneous", f"{band} 的姓名长度完全相同，存在批量模板痕迹"))

    return {
        "chinese_names": len(chinese),
        "lengths": actual_report,
    }


def validate_files(personas: list[dict[str, Any]], summary_path: Path, persons_dir: Path, blockers: list[dict[str, str]]) -> None:
    if not summary_path.exists():
        blockers.append(issue("summary_missing", f"缺少汇总文件：{summary_path.name}"))
    else:
        text = summary_path.read_text(encoding="utf-8")
        payload_match = re.search(
            r'<script[^>]*id=["\']persona-summary-data["\'][^>]*>(.*?)</script>',
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if payload_match:
            try:
                payload = json.loads(html.unescape(payload_match.group(1).strip()))
            except json.JSONDecodeError:
                blockers.append(issue("summary_ids_invalid", "persons_summary.html 的 persona-summary-data 不是合法 JSON"))
                payload = {}
            for heading in ("用户画像汇总", "画像总数", "全量用户ID", "用户群体分布", "性别分布", "年龄段分布", "相关经验分布", "使用阶段分布", "系统App使用习惯分布"):
                if heading not in text:
                    blockers.append(issue("summary_structure", f"HTML 汇总文件缺少“{heading}”"))
            summary_ids = payload.get("persona_ids")
            if not isinstance(summary_ids, list):
                blockers.append(issue("summary_ids_invalid", "persona-summary-data.persona_ids 必须是 JSON 数组"))
            else:
                expected_ids = [persona.get("画像编号") for persona in personas]
                if summary_ids != expected_ids:
                    blockers.append(issue("summary_ids_mismatch", "全量用户ID必须与 personas.json 中的画像顺序完全一致"))
        else:
            # Backward-compatible read for old fixtures; new output is HTML only.
            id_prefix = "全量用户ID："
            id_lines = [line for line in text.splitlines() if line.startswith(id_prefix)]
            if len(id_lines) != 1:
                blockers.append(issue("summary_ids_structure", "汇总文件必须包含 persona-summary-data 或旧版全量用户ID数组"))
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
    name_coverage = validate_name_batch(personas, spec, blockers)
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
            "names": name_coverage,
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
        result = validate(data, args.summary or args.input.parent / "persons_summary.html", args.persons_dir or args.input.parent / "persons")
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
