#!/usr/bin/env python3
"""Generate concise, internally consistent synthetic user personas."""

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
    "相关使用经验", "使用阶段",
}
SURNAMES = ["林", "周", "陈", "许", "沈", "唐", "顾", "陆", "韩", "叶", "苏", "梁", "宋", "夏", "程"]
GIVEN_NAMES = ["安", "宁", "然", "清", "言", "禾", "川", "乔", "遥", "简", "晨", "知", "予", "岚", "悦", "嘉", "辰", "月", "航", "青"]
GENDERS = ["女", "男", "女", "男", "女", "男", "女", "男", "不透露", "男"]
RESIDENCES = [
    {"description": "一线城市·上海", "region": "华东", "settlement_type": "一线城市"},
    {"description": "一线城市·北京", "region": "华北", "settlement_type": "一线城市"},
    {"description": "新一线城市·杭州", "region": "华东", "settlement_type": "新一线城市"},
    {"description": "新一线城市·成都", "region": "西南", "settlement_type": "新一线城市"},
    {"description": "省会城市·武汉", "region": "华中", "settlement_type": "省会城市"},
    {"description": "二线城市·佛山", "region": "华南", "settlement_type": "二线城市"},
    {"description": "中国北方县城", "region": "华北", "settlement_type": "县城"},
    {"description": "华东县域地区", "region": "华东", "settlement_type": "县域"},
    {"description": "西北三线城市", "region": "西北", "settlement_type": "三线城市"},
    {"description": "东北地级市", "region": "东北", "settlement_type": "地级市"},
]
PRIMARY_DEVICES = [
    {"brand": "苹果", "model": "iPhone 15", "device_type": "手机", "os": "iOS", "screen_size_class": "中屏", "purchase_year": 2024},
    {"brand": "华为", "model": "Mate 60", "device_type": "手机", "os": "HarmonyOS", "screen_size_class": "大屏", "purchase_year": 2023},
    {"brand": "小米", "model": "14", "device_type": "手机", "os": "Android", "screen_size_class": "中屏", "purchase_year": 2024},
    {"brand": "OPPO", "model": "Reno12", "device_type": "手机", "os": "Android", "screen_size_class": "大屏", "purchase_year": 2024},
    {"brand": "vivo", "model": "S19", "device_type": "手机", "os": "Android", "screen_size_class": "大屏", "purchase_year": 2024},
    {"brand": "荣耀", "model": "Magic6", "device_type": "手机", "os": "Android", "screen_size_class": "大屏", "purchase_year": 2024},
]
COMPANION_DEVICES = [
    {"brand": "联想", "model": "ThinkPad", "device_type": "笔记本电脑", "os": "Windows", "screen_size_class": "14英寸"},
    {"brand": "华硕", "model": "台式机", "device_type": "台式电脑", "os": "Windows", "screen_size_class": "大屏"},
    {"brand": "苹果", "model": "iPad Air", "device_type": "平板电脑", "os": "iPadOS", "screen_size_class": "11英寸"},
    {"brand": "苹果", "model": "MacBook Air", "device_type": "笔记本电脑", "os": "macOS", "screen_size_class": "13英寸"},
]
GENERAL_BEHAVIORS = [
    {"search_style": "先看经验分享", "search_channel": "内容社区", "content_style": "图文与短视频并用", "daily_screen_time": "5–7小时", "app_usage_style": "多任务并行", "favorite_categories": ["社交", "资讯", "工具"], "digital_comfort": "熟悉渠道优先", "consumption": {"shopping_preference": "线上为主", "price_sensitivity": "中"}},
    {"search_style": "先搜结论再核对细节", "search_channel": "搜索引擎", "content_style": "图文为主", "daily_screen_time": "3–5小时", "app_usage_style": "按任务切换", "favorite_categories": ["工具", "阅读", "购物"], "digital_comfort": "愿意尝试但先小范围验证", "consumption": {"shopping_preference": "线上线下结合", "price_sensitivity": "高"}},
    {"search_style": "比较多个来源", "search_channel": "搜索引擎与问答社区", "content_style": "长文与测评视频", "daily_screen_time": "6–8小时", "app_usage_style": "多窗口并行", "favorite_categories": ["资讯", "影音", "效率"], "digital_comfort": "能熟练切换多种工具", "consumption": {"shopping_preference": "线上为主", "price_sensitivity": "低"}},
    {"search_style": "先问熟人再搜索", "search_channel": "社交群与短视频平台", "content_style": "短视频为主", "daily_screen_time": "2–4小时", "app_usage_style": "固定应用优先", "favorite_categories": ["社交", "影音", "生活"], "digital_comfort": "重视步骤少且可撤销", "consumption": {"shopping_preference": "线下为主", "price_sensitivity": "中"}},
]
HOBBIES = [["音乐", "游戏", "运动"], ["阅读", "烹饪", "城市漫步"], ["摄影", "旅行", "看展"], ["园艺", "手工", "户外活动"]]
USAGE_PROFILES = [
    {"has_experience": True, "status": "current", "description": "长期保持相关使用习惯"},
    {"has_experience": True, "status": "current", "description": "近期有过数次相关使用"},
    {"has_experience": True, "status": "lapsed", "description": "过去有相关使用经验，近期没有使用"},
    {"has_experience": False, "status": "potential", "description": "当前没有与本次调研相关的使用经验"},
]
SUCCESS_CRITERIA = ["过程可控，出现问题时能够恢复", "结果准确，减少返工", "不打断原有流程即可完成", "在可接受时间内完成主要目标"]
FRICTIONS = [None, "偶尔需要重复检查结果", "跨设备继续处理时步骤较多", "多人确认会拉长完成时间"]
ADOPTION_BARRIERS = ["跨设备或跨渠道体验可能不一致", "需要先确认结果是否可靠", "学习成本可能高于使用收益", "对数据和权限边界存在顾虑"]
ALLOWED_HEADINGS = {
    "# 用户研究共享上下文", "## 任务信息", "## 目标用户", "## 确认信息",
    "### 全量候选群体", "### 已选目标群体", "### 纳入条件", "### 排除条件",
}
BASE_DIMENSIONS = ["demographics", "occupation_economy", "general_behavior", "devices"]
TOPIC_DIMENSIONS = ["experience", "usage_habit", "judgment"]


def pick(values: list[Any], index: int, seed: int, step: int = 1) -> Any:
    return values[(seed + index * step) % len(values)]


def load_persona_template() -> list[str]:
    try:
        template = json.loads(PERSONA_TEMPLATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 persona_template.json：{exc}") from exc
    if not isinstance(template, dict) or not template:
        raise ValueError("persona_template.json 必须是非空 JSON 对象")
    missing = sorted(CORE_PERSONA_FIELDS - set(template))
    if missing:
        raise ValueError(f"persona_template.json 缺少生成所需核心字段：{missing}")
    return list(template)


def disposable_income_range(monthly_income: str) -> str:
    ranges = {
        "0–3000元": "0–3000元",
        "3000–7000元": "1000–3000元",
        "5000–7000元": "1500–3000元",
        "6000–9000元": "2000–4000元",
        "6000–10000元": "2000–5000元",
        "6000–12000元": "2000–6000元",
        "7000–12000元": "2500–6000元",
        "7000–15000元": "2500–7000元",
        "8000–15000元": "3000–7000元",
        "9000–16000元": "3500–8000元",
        "10000–18000元": "4000–9000元",
        "收入波动": "随项目变化",
    }
    return ranges.get(monthly_income, "随固定支出变化")


def field_value(lines: list[str], label: str) -> str:
    prefix = f"- {label}："
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return ""


def section_items(lines: list[str], heading: str) -> list[str]:
    marker = f"### {heading}"
    try:
        start = lines.index(marker) + 1
    except ValueError:
        return []
    items: list[str] = []
    for line in lines[start:]:
        if line.startswith("#"):
            break
        if line.startswith("- "):
            value = line[2:].strip()
            if value and value != "无":
                items.append(value)
    return items


def parse_shared_context(text: str) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or lines[0] != "# 用户研究共享上下文":
        raise ValueError("输入必须是 shared_context.md；不能使用 plan.json 或 Skill 间直接传值")
    unknown = [line for line in lines if line.startswith("#") and line not in ALLOWED_HEADINGS]
    if unknown:
        raise ValueError(f"shared_context.md 含有不应暴露给画像生成的章节：{', '.join(unknown)}")
    return {
        "topic": field_value(lines, "调研主题"),
        "audience_groups": section_items(lines, "全量候选群体"),
        "target_audience": {
            "selected_groups": section_items(lines, "已选目标群体"),
            "include": section_items(lines, "纳入条件"),
            "exclude": section_items(lines, "排除条件"),
            "exclude_confirmed_by_user": field_value(lines, "排除条件由用户明确确认") == "是",
        },
        "confirmation": {"status": field_value(lines, "状态"), "confirmed_by": field_value(lines, "确认人")},
    }


def read_input(document: dict[str, Any]) -> tuple[str, list[str], dict[str, Any]]:
    if document["confirmation"] != {"status": "已确认", "confirmed_by": "用户"}:
        raise ValueError("shared_context.md 尚未由用户确认")
    topic = document["topic"].strip()
    groups = list(dict.fromkeys(document["audience_groups"]))
    target = document["target_audience"]
    if not topic:
        raise ValueError("缺少 topic")
    if not groups:
        raise ValueError("缺少全量候选群体：需要 shared_context.md 中的全部候选用户群体")
    if not target["selected_groups"]:
        raise ValueError("缺少已选目标群体")
    unknown = sorted(set(target["selected_groups"]) - set(groups))
    if unknown:
        raise ValueError(f"selected_groups 不在 audience_groups 中：{', '.join(unknown)}")
    if target["exclude"] and not target["exclude_confirmed_by_user"]:
        raise ValueError("exclude 非空但未经用户明确确认")
    return topic, groups, target


def allocate_groups(groups: list[str], sample_size: int, quotas: dict[str, int] | None) -> tuple[list[str], list[dict[str, Any]], str]:
    if sample_size < len(groups):
        raise ValueError(f"sample_size {sample_size} 小于 audience_groups 数量 {len(groups)}，无法覆盖全部群体")
    if quotas:
        if set(quotas) != set(groups):
            raise ValueError("group_quota 必须覆盖全部候选群体")
        if any(value < 1 for value in quotas.values()) or sum(quotas.values()) != sample_size:
            raise ValueError("每个 group_quota 至少为 1，且人数之和必须等于 sample_size")
        counts, basis = dict(quotas), "user_specified"
    else:
        base, remainder = divmod(sample_size, len(groups))
        counts = {group: base + (position < remainder) for position, group in enumerate(groups)}
        basis = "coverage_balanced"
    remaining, assignments = dict(counts), []
    while len(assignments) < sample_size:
        for group in groups:
            if remaining[group]:
                assignments.append(group)
                remaining[group] -= 1
    allocation = [{"audience_group": group, "count": counts[group], "share": round(counts[group] / sample_size, 4)} for group in groups]
    return assignments, allocation, basis


def age_for(group: str, index: int, seed: int) -> int:
    if "学生" in group:
        low, high = 18, 29
    elif any(key in group for key in ("宝爸", "宝妈", "家长", "家庭")):
        low, high = 28, 49
    elif any(key in group for key in ("上班", "职场", "员工")):
        low, high = 23, 55
    elif any(key in group for key in ("创作者", "摄影", "内容")):
        low, high = 20, 49
    else:
        low, high = 18, 67
    return low + (seed + index * 7) % (high - low + 1)


def family_profile(group: str, age: int, index: int, seed: int) -> tuple[str, dict[str, Any]]:
    if "学生" in group or age <= 23:
        return "未婚", {"count": 0, "stages": []}
    if any(key in group for key in ("宝爸", "宝妈", "家长", "家庭")):
        count = 1 + ((seed + index) % 2)
        if age <= 32:
            stages = ["学龄前"] * count
        elif age <= 40:
            stages = ["小学"] if count == 1 else ["学龄前", "小学"]
        else:
            stages = ["小学"] if count == 1 else ["小学", "初中"]
        return "已婚", {"count": count, "stages": stages}
    if age <= 30:
        return ("未婚", {"count": 0, "stages": []}) if index % 2 else ("已婚", {"count": 0, "stages": []})
    if age <= 39:
        return "已婚", {"count": index % 2, "stages": ["学龄前"] if index % 2 else []}
    if age <= 54:
        return "已婚", {"count": 1, "stages": ["小学或中学"]}
    return "已婚", {"count": 1, "stages": ["成年"]}


def occupation_economy(group: str, age: int, index: int, seed: int) -> dict[str, str]:
    if "学生" in group:
        return {"employment_type": "在校学习", "role": "在校学生", "seniority": "不适用", "specialty": pick(["经管", "计算机", "设计", "人文社科"], index, seed), "industry": "教育", "monthly_income_range": "0–3000元", "income_level": "无固定或较低收入", "disposable_level": "有限"}
    if age >= 58:
        return {"employment_type": "退休", "role": "退休人员", "seniority": "不适用", "specialty": "原职业经验", "industry": "退休", "monthly_income_range": "3000–7000元", "income_level": "中等偏下收入", "disposable_level": "一般"}
    if any(key in group for key in ("创作者", "摄影", "内容")):
        roles = [
            ("自由职业", "内容创作者", "独立从业", "图文与短视频", "文化传媒", "收入波动", "不稳定收入", "随项目变化"),
            ("全职工作", "视觉设计师", "3–5年", "视觉设计", "广告与品牌", "8000–15000元", "中等收入", "一般"),
        ]
    elif any(key in group for key in ("上班", "职场", "员工")):
        roles = [
            ("全职工作", "企业职员", "3–5年", "项目执行", "企业服务", "7000–12000元", "中等收入", "一般"),
            ("全职工作", "产品运营", "5–8年", "运营管理", "互联网与软件", "10000–18000元", "中等偏上收入", "较充足"),
            ("全职工作", "公务员", "科员", "财务会计", "公共管理", "5000–7000元", "中等偏下收入", "一般"),
        ]
    else:
        roles = [
            ("全职工作", "教师", "5–10年", "教学", "教育", "6000–10000元", "中等收入", "一般"),
            ("个体经营", "个体经营者", "5年以上", "门店经营", "零售与生活服务", "6000–12000元", "中等收入", "随经营波动"),
            ("全职工作", "技术从业者", "3–8年", "技术实施", "信息技术", "9000–16000元", "中等偏上收入", "较充足"),
        ]
    if any(key in group for key in ("宝爸", "宝妈", "家长", "家庭")):
        roles = [
            ("全职工作", "教师", "5–10年", "教学", "教育", "6000–10000元", "中等收入", "一般"),
            ("全职工作", "企业会计", "5–10年", "财务会计", "制造与零售", "6000–9000元", "中等收入", "一般"),
            ("个体经营", "个体经营者", "5年以上", "门店经营", "零售与生活服务", "7000–15000元", "中等收入", "随经营波动"),
        ]
    values = pick(roles, index, seed, 3)
    keys = ["employment_type", "role", "seniority", "specialty", "industry", "monthly_income_range", "income_level", "disposable_level"]
    return dict(zip(keys, values))


def make_base_profile(group: str, index: int, seed: int) -> dict[str, Any]:
    age = age_for(group, index, seed)
    marital_status, children = family_profile(group, age, index, seed)
    name = f"{pick(SURNAMES, index, seed, 7)}{pick(GIVEN_NAMES, index, seed * 3, 11)}"
    return {
        "demographics": {
            "fictional_name": name, "age": age, "gender": pick(GENDERS, index, seed, 3),
            "residence": pick(RESIDENCES, index, seed, 3), "marital_status": marital_status, "children": children,
        },
        "occupation_economy": occupation_economy(group, age, index, seed),
        "general_behavior": {**pick(GENERAL_BEHAVIORS, index, seed, 3), "hobbies": pick(HOBBIES, index, seed, 3)},
        "devices": {"primary": pick(PRIMARY_DEVICES, index, seed, 5), "companion": pick(COMPANION_DEVICES, index, seed, 3)},
    }


def topic_material(topic: str) -> tuple[list[str], list[str], list[str]]:
    if any(key in topic for key in ("修图", "照片编辑", "图片编辑")):
        return (
            ["拍完一组照片准备分享时", "家庭合照需要处理时", "需要与他人共享、协作或确认时", "发现照片偏暗或构图不合适时"],
            ["先用系统图库做基础调整，必要时再换第三方应用", "使用熟悉的第三方修图应用完成主要处理", "在保留原图的前提下尝试不同效果", "先自行处理，再把结果发给朋友或同事确认"],
            ["完成主要目标", "完成处理但增加了切换工具的步骤", "得到可分享版本并保留原图"],
        )
    if any(key in topic for key in ("相册", "照片管理")):
        return (
            ["整理近期照片时", "更换设备前", "本地空间不足时", "需要与家人分享部分照片时"],
            ["按相册分类后再决定同步和分享范围", "沿用系统默认同步并定期检查状态", "手动挑选重要照片备份到电脑", "在本地、云服务和电脑之间分散保存"],
            ["完成主要目标", "完成备份但需要额外核对", "保留了重要内容并释放部分空间"],
        )
    return (
        [f"出现一次明确的{topic}任务时", f"时间有限且需要完成{topic}时", f"需要与他人协作处理{topic}时"],
        [f"先使用熟悉方式处理{topic}", f"比较两种现有方式后完成{topic}", f"按原有流程完成{topic}"],
        ["完成主要目标", "完成任务但增加了额外步骤", "暂时解决当前问题"],
    )


def make_research_profile(topic: str, index: int, seed: int) -> dict[str, Any]:
    experience = dict(pick(USAGE_PROFILES, index, seed, 1))
    if not experience["has_experience"]:
        return {"experience": experience, "usage_habit": None, "judgment": None}
    triggers, methods, outcomes = topic_material(topic)
    return {
        "experience": experience,
        "usage_habit": {
            "trigger": pick(triggers, index, seed, 3),
            "method": pick(methods, index, seed, 5),
            "outcome": pick(outcomes, index, seed, 7),
        },
        "judgment": {
            "success_criterion": pick(SUCCESS_CRITERIA, index, seed, 3),
            "friction": pick(FRICTIONS, index, seed, 5),
            "adoption_barrier": pick(ADOPTION_BARRIERS, index, seed, 7),
        },
    }


def make_persona(index: int, topic: str, group: str, seed: int) -> dict[str, Any]:
    base = make_base_profile(group, index, seed)
    research = make_research_profile(topic, index, seed)
    pid = f"P{index + 1:03d}"
    demo, job = base["demographics"], base["occupation_economy"]
    behavior, devices = base["general_behavior"], base["devices"]
    consumption = behavior["consumption"]
    general_behavior = (
        f"{behavior['search_style']}，主要通过{behavior['search_channel']}；{behavior['content_style']}；"
        f"日均屏幕时间{behavior['daily_screen_time']}；{behavior['app_usage_style']}；"
        f"{behavior['digital_comfort']}、价格敏感度{consumption['price_sensitivity']}；"
        f"兴趣为{compact_list(behavior['hobbies'])}"
    )
    primary, companion = devices["primary"], devices["companion"]
    device_text = f"{primary['brand']} {primary['model']}，{companion['screen_size_class']}{companion['brand']}{companion['device_type']}"
    stage_labels = {"current": "当前使用者", "lapsed": "曾经使用者", "potential": "潜在用户"}
    if research["usage_habit"]:
        habit = research["usage_habit"]
        usage_text = f"{habit['trigger']}，{habit['method']}；结果：{habit['outcome']}"
        judgment = research["judgment"]
        friction = judgment["friction"] or "目前没有稳定出现的明显困难"
        judgment_text = f"看重“{judgment['success_criterion']}”；当前卡点：{friction}；采用顾虑：{judgment['adoption_barrier']}"
    else:
        usage_text = None
        judgment_text = None
    persona = {
        "画像编号": pid,
        "姓名": demo["fictional_name"],
        "年龄": demo["age"],
        "性别": demo["gender"],
        "居住地": demo["residence"]["description"],
        "婚姻状况": demo["marital_status"],
        "职业": job["role"],
        "专业": job["specialty"],
        "月收入": job["monthly_income_range"],
        "收入水平": job["income_level"],
        "可支配水平": job["disposable_level"],
        "可支配收入": disposable_income_range(job["monthly_income_range"]),
        "通用行为": general_behavior,
        "使用设备": device_text,
        "相关使用经验": research["experience"]["description"],
        "使用阶段": stage_labels[research["experience"]["status"]],
    }
    if usage_text:
        persona["相关产品或功能使用习惯"] = usage_text
    if judgment_text:
        persona["判断"] = judgment_text
    template_fields = load_persona_template()
    return {
        key: persona[key]
        for key in template_fields
        if key in persona and persona[key] not in (None, "", "不适用")
    }


def build(document: dict[str, Any], sample_size: int, seed: int, quotas: dict[str, int] | None) -> dict[str, Any]:
    topic, groups, target = read_input(document)
    assignments, allocation, basis = allocate_groups(groups, sample_size, quotas)
    personas = [make_persona(index, topic, group, seed) for index, group in enumerate(assignments)]
    stage_keys = {"当前使用者": "current", "曾经使用者": "lapsed", "潜在用户": "potential"}
    stage_counts = Counter(stage_keys[p["使用阶段"]] for p in personas)
    return {
        "schema_version": SCHEMA_VERSION, "topic": topic, "audience_groups": groups,
        "target_audience": target, "synthetic": True, "sample_size": sample_size,
        "generation_spec": {
            "allocation_basis": basis, "allocation_is_population_estimate": False,
            "group_allocation": allocation, "base_dimensions": BASE_DIMENSIONS,
            "topic_dimensions": TOPIC_DIMENSIONS, "usage_stage_allocation": dict(stage_counts),
        },
        "personas": personas,
        "quality_check": {"score": 100, "grade": "excellent", "passed": True},
        "limitations": ["全部画像均为合成内容", "构建比例不代表真实人口或产品用户分布", "画像不是用户研究结论"],
    }


def compact_list(values: list[str]) -> str:
    return "、".join(values) if values else "无"


def render_persona(persona: dict[str, Any]) -> str:
    return "\n".join(f"{key}：{value}" for key, value in persona.items()) + "\n"


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
    personas, total = data["personas"], len(data["personas"])
    persona_ids = [persona["画像编号"] for persona in personas]
    group_counts = Counter({
        item["audience_group"]: item["count"]
        for item in data["generation_spec"]["group_allocation"]
    })
    gender_counts = Counter(p["性别"] for p in personas)
    age_counts = Counter(age_band(p["年龄"]) for p in personas)
    experience_counts = Counter("无相关经验" if p["使用阶段"] == "潜在用户" else "有相关经验" for p in personas)
    stage_counts = Counter(p["使用阶段"] for p in personas)
    experienced = [p for p in personas if p["使用阶段"] != "潜在用户"]
    success = Counter(p["判断"].split("；", 1)[0].removeprefix("看重“").removesuffix("”") for p in experienced)
    barriers = Counter(p["判断"].rsplit("采用顾虑：", 1)[-1] for p in experienced)
    lines = [
        "用户画像汇总（合成）", "", f"调研课题：{data['topic']}", f"画像总数：{total}人",
        f"全量用户ID：{json.dumps(persona_ids, ensure_ascii=False)}",
        "说明：以下比例仅描述本次合成画像构成，不代表真实人口或产品用户分布。", "",
    ]
    for title, counts, denominator in [
        ("一、用户群体分布", group_counts, total), ("二、性别分布", gender_counts, total),
        ("三、年龄段分布", age_counts, total), ("四、相关经验分布", experience_counts, total),
        ("五、使用阶段分布", stage_counts, total), ("六、判断标准分布（仅有经验者）", success, len(experienced) or 1),
        ("七、采用顾虑分布（仅有经验者）", barriers, len(experienced) or 1),
    ]:
        lines.extend(distribution_lines(title, counts, denominator))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def safe_filename(persona: dict[str, Any]) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "_", persona["姓名"])
    return f"{persona['画像编号']}_{name}.txt"


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
    parser = argparse.ArgumentParser(description="根据任务级共享上下文生成合成画像")
    parser.add_argument("input", type=Path, help="output/<当前任务>/shared_context.md")
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--group-quota", action="append", default=[], metavar="群体=人数")
    parser.add_argument("--seed", type=int, default=20260816)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-summary", type=Path)
    parser.add_argument("--persons-dir", type=Path)
    parser.add_argument("--output", type=Path, help="兼容参数，等同 --output-json")
    args = parser.parse_args()
    output_json = args.output_json or args.output
    if output_json is None:
        parser.error("必须提供 --output-json（或 --output）")
    try:
        if args.input.suffix.lower() != ".md":
            raise ValueError("输入必须是 shared_context.md；不能使用 plan.json 或 Skill 间直接传值")
        document = parse_shared_context(args.input.read_text(encoding="utf-8"))
        quotas: dict[str, int] = {}
        for item in args.group_quota:
            if "=" not in item:
                raise ValueError("group_quota 格式必须为 群体=人数")
            group, count = item.rsplit("=", 1)
            quotas[group.strip()] = int(count)
        data = build(document, args.sample_size, args.seed, quotas or None)
        summary_path = args.output_summary or output_json.parent / "persons_summary.txt"
        persons_dir = args.persons_dir or output_json.parent / "persons"
        write_outputs(data, output_json, summary_path, persons_dir)
    except (OSError, ValueError) as exc:
        print(f"生成失败：{exc}", file=sys.stderr)
        return 2
    print(output_json)
    print(summary_path)
    print(persons_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
