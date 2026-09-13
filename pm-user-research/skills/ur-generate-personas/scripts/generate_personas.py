#!/usr/bin/env python3
"""Render an LLM-authored persona JSON into the shared persona library.

This script deliberately does not invent people, behaviors, or research answers.
The calling LLM creates the persona objects; this utility only normalizes fields,
writes the three library artifacts, and prepares a deterministic summary.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "5.3"
PERSONA_TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "persona_template.json"
CORE_PERSONA_FIELDS = {
    "画像编号", "姓名", "年龄", "性别", "职业", "通用行为", "使用设备",
    "相关使用经验", "使用阶段", "系统App使用习惯",
}
EXPERIENCED_STAGES = {"当前使用者", "曾经使用者"}
VALID_STAGES = EXPERIENCED_STAGES | {"潜在用户"}


def load_template_fields() -> list[str]:
    try:
        template = json.loads(PERSONA_TEMPLATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 persona_template.json：{exc}") from exc
    if not isinstance(template, dict) or not template:
        raise ValueError("persona_template.json 必须是非空 JSON 对象")
    missing = sorted(CORE_PERSONA_FIELDS - set(template))
    if missing:
        raise ValueError(f"persona_template.json 缺少核心字段：{missing}")
    return list(template)


def normalize_persona(persona: Any, template_fields: list[str]) -> dict[str, Any]:
    if not isinstance(persona, dict):
        raise ValueError("personas 中的每一项必须是对象")
    missing = sorted(CORE_PERSONA_FIELDS - set(persona))
    extra = sorted(set(persona) - set(template_fields))
    if missing:
        raise ValueError(f"画像 {persona.get('画像编号', '<未知>')} 缺少字段：{missing}")
    if extra:
        raise ValueError(f"画像 {persona.get('画像编号', '<未知>')} 含有模板之外的字段：{extra}")
    empty = [key for key, value in persona.items() if value in (None, "", "不适用")]
    if empty:
        raise ValueError(f"画像 {persona.get('画像编号', '<未知>')} 含有空值字段：{empty}")
    if not isinstance(persona["年龄"], int) or not 18 <= persona["年龄"] <= 80:
        raise ValueError(f"画像 {persona.get('画像编号', '<未知>')} 的年龄必须是 18–80 岁整数")
    if persona["使用阶段"] not in VALID_STAGES:
        raise ValueError(f"画像 {persona.get('画像编号', '<未知>')} 的使用阶段无效")
    if persona["使用阶段"] == "潜在用户" and any(
        field in persona for field in ("相关产品或功能使用习惯", "判断")
    ):
        raise ValueError(f"潜在用户 {persona['画像编号']} 不得虚构产品使用习惯或判断")
    if persona["使用阶段"] in EXPERIENCED_STAGES and not {
        "相关产品或功能使用习惯", "判断",
    }.issubset(persona):
        raise ValueError(f"有经验用户 {persona['画像编号']} 必须包含使用习惯和判断")
    return {key: persona[key] for key in template_fields if key in persona}


def normalize_document(raw: Any, template_fields: list[str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("大模型输入必须是包含 personas 数组的 JSON 对象")
    required = {"schema_version", "topic", "audience_groups", "target_audience", "synthetic", "sample_size", "generation_spec", "personas", "limitations"}
    missing = sorted(required - set(raw))
    if missing:
        raise ValueError(f"大模型输出缺少顶层字段：{missing}")
    if raw["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"schema_version 必须为 {SCHEMA_VERSION}")
    if raw["synthetic"] is not True:
        raise ValueError("synthetic 必须为 true，画像必须明确标记为合成内容")
    if not isinstance(raw["audience_groups"], list) or not raw["audience_groups"]:
        raise ValueError("audience_groups 必须是非空数组")
    if not isinstance(raw["generation_spec"], dict):
        raise ValueError("generation_spec 必须是对象")
    allocation = raw["generation_spec"].get("group_allocation")
    if not isinstance(allocation, list) or not allocation:
        raise ValueError("generation_spec.group_allocation 必须由大模型提供")
    if not isinstance(raw["personas"], list) or not raw["personas"]:
        raise ValueError("personas 必须是非空数组")
    if raw["sample_size"] != len(raw["personas"]):
        raise ValueError("sample_size 必须等于 personas 数量")
    personas = [normalize_persona(item, template_fields) for item in raw["personas"]]
    ids = [item["画像编号"] for item in personas]
    if len(ids) != len(set(ids)):
        raise ValueError("画像编号不能重复")
    if set(ids) != {f"P{index:03d}" for index in range(1, len(ids) + 1)}:
        raise ValueError("画像编号必须从 P001 连续编号")
    normalized = {**raw, "personas": personas}
    normalized.setdefault("quality_check", {})
    return normalized


def age_band(age: int) -> str:
    if age <= 24:
        return "18–24岁"
    if age <= 34:
        return "25–34岁"
    if age <= 44:
        return "35–44岁"
    if age <= 54:
        return "45–54岁"
    return "55岁及以上"


def distribution_lines(title: str, counts: Counter[str], total: int) -> list[str]:
    lines = [title]
    for label, count in counts.items():
        lines.append(f"- {label}：{count}人（{count / total:.1%}）")
    return lines


def render_summary(data: dict[str, Any]) -> str:
    personas = data["personas"]
    total = len(personas)
    persona_ids = [persona["画像编号"] for persona in personas]
    group_counts = Counter({
        item["audience_group"]: item["count"]
        for item in data["generation_spec"]["group_allocation"]
    })
    gender_counts = Counter(persona["性别"] for persona in personas)
    age_counts = Counter(age_band(persona["年龄"]) for persona in personas)
    experience_counts = Counter(
        "无相关经验" if persona["使用阶段"] == "潜在用户" else "有相关经验"
        for persona in personas
    )
    stage_counts = Counter(persona["使用阶段"] for persona in personas)
    system_app_counts = Counter(persona["系统App使用习惯"] for persona in personas)
    experienced = [persona for persona in personas if persona["使用阶段"] in EXPERIENCED_STAGES]
    success = Counter(
        persona["判断"].split("；", 1)[0].removeprefix("看重“").removesuffix("”")
        for persona in experienced
    )
    barriers = Counter(persona["判断"].rsplit("采用顾虑：", 1)[-1] for persona in experienced)
    lines = [
        "用户画像汇总（合成）", "", f"调研课题：{data['topic']}", f"画像总数：{total}人",
        f"全量用户ID：{json.dumps(persona_ids, ensure_ascii=False)}",
        "说明：以下比例仅描述本次合成画像构成，不代表真实人口或产品用户分布。", "",
    ]
    sections = [
        ("一、用户群体分布", group_counts, total),
        ("二、性别分布", gender_counts, total),
        ("三、年龄段分布", age_counts, total),
        ("四、相关经验分布", experience_counts, total),
        ("五、使用阶段分布", stage_counts, total),
        ("六、系统App使用习惯分布", system_app_counts, total),
        ("七、判断标准分布（仅有经验者）", success, len(experienced) or 1),
        ("八、采用顾虑分布（仅有经验者）", barriers, len(experienced) or 1),
    ]
    for title, counts, denominator in sections:
        lines.extend(distribution_lines(title, counts, denominator))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def safe_filename(persona: dict[str, Any]) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "_", str(persona["姓名"]))
    return f"{persona['画像编号']}_{name}.txt"


def render_persona(persona: dict[str, Any]) -> str:
    return "\n".join(f"{key}：{value}" for key, value in persona.items()) + "\n"


def write_outputs(data: dict[str, Any], output_json: Path, summary_path: Path, persons_dir: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    persons_dir.mkdir(parents=True, exist_ok=True)
    for old in persons_dir.glob("P*.txt"):
        old.unlink()
    output_json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_path.write_text(render_summary(data), encoding="utf-8")
    for persona in data["personas"]:
        (persons_dir / safe_filename(persona)).write_text(render_persona(persona), encoding="utf-8")
    legacy = output_json.parent / "personas.txt"
    if legacy.exists():
        legacy.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="将大模型生成的画像 JSON 落盘为共享用户画像库")
    parser.add_argument("input", type=Path, help="大模型生成的 personas.json 临时文件")
    parser.add_argument("--output-dir", type=Path, help="共享画像库目录；默认使用输入文件所在目录")
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output", type=Path, help="兼容参数，等同 --output-json")
    parser.add_argument("--output-summary", type=Path)
    parser.add_argument("--persons-dir", type=Path)
    parser.add_argument("--replace-existing", action="store_true", help="明确允许重建已存在的全局画像库")
    args = parser.parse_args()
    try:
        if args.input.suffix.lower() != ".json":
            raise ValueError("输入必须是大模型生成的 JSON；不能直接把 shared_context.md 当作画像内容")
        template_fields = load_template_fields()
        raw = json.loads(args.input.read_text(encoding="utf-8"))
        data = normalize_document(raw, template_fields)
        explicit_json = args.output_json or args.output
        if args.output_dir and explicit_json:
            raise ValueError("--output-dir 与 --output-json/--output 只能选一个")
        output_json = (args.output_dir / "personas.json") if args.output_dir else (explicit_json or args.input)
        summary_path = args.output_summary or output_json.parent / "persons_summary.txt"
        persons_dir = args.persons_dir or output_json.parent / "persons"
        if output_json.exists() and not args.replace_existing and output_json.resolve() != args.input.resolve():
            raise ValueError(f"输出画像库已存在：{output_json}；如需重建请显式使用 --replace-existing")
        write_outputs(data, output_json, summary_path, persons_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"画像落盘失败：{exc}", file=sys.stderr)
        return 2
    print(output_json)
    print(summary_path)
    print(persons_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
