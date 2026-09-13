#!/usr/bin/env python3
"""
竞品 App 特性对比 — 研究计划生成器

为指定的 App + 功能生成各竞品厂商的目标 URL 和搜索策略。
输出结构化 JSON，供 SKILL.md 步骤 2 使用。

用法:
  python3 scripts/research_plan.py --app "图库" --feature "相册自定义排序"
  python3 scripts/research_plan.py --app "设置" --feature "用户数据清理" --scope "apple,google,华为,小米"
"""

import json
import argparse

# 各厂商的官方文档基 URL 和搜索词模板
VENDORS = {
    "apple": {
        "name": "Apple",
        "system": "iOS",
        "doc_base": "https://developer.apple.com/documentation/",
        "hig_base": "https://developer.apple.com/design/human-interface-guidelines/",
        "search_template": {
            "en": "site:developer.apple.com {app_en} {feature_en}",
            "zh": "Apple iOS {app_zh} {feature_zh} 功能设计",
        },
    },
    "google": {
        "name": "Google",
        "system": "Android",
        "doc_base": "https://developer.android.com/docs",
        "design_base": "https://m3.material.io/",
        "search_template": {
            "en": "site:developer.android.com {app_en} {feature_en}",
            "zh": "Android {app_zh} {feature_zh} 功能",
        },
    },
    "华为": {
        "name": "华为",
        "system": "HarmonyOS",
        "doc_base": "https://developer.huawei.com/consumer/cn/doc/",
        "design_base": "https://developer.harmonyos.com/cn/design/",
        "search_template": {
            "en": "site:developer.huawei.com {app_en} {feature_en}",
            "zh": "HarmonyOS {app_zh} {feature_zh} 设计规范",
        },
    },
    "小米": {
        "name": "小米",
        "system": "HyperOS",
        "doc_base": "https://dev.mi.com/document/",
        "community_base": "https://www.xiaomi.cn/",
        "search_template": {
            "zh": "HyperOS {app_zh} {feature_zh} 设计 开发",
        },
    },
    "OPPO": {
        "name": "OPPO",
        "system": "ColorOS",
        "doc_base": "https://open.oppomobile.com/",
        "search_template": {
            "zh": "ColorOS {app_zh} {feature_zh} 功能",
        },
    },
    "VIVO": {
        "name": "VIVO",
        "system": "OriginOS",
        "doc_base": "https://dev.vivo.com.cn/document",
        "search_template": {
            "zh": "OriginOS {app_zh} {feature_zh} 功能 设计",
        },
    },
    "荣耀": {
        "name": "荣耀",
        "system": "MagicOS",
        "doc_base": "https://developer.hihonor.com/",
        "search_template": {
            "zh": "MagicOS {app_zh} {feature_zh} 功能",
        },
    },
    "三星": {
        "name": "三星",
        "system": "One UI",
        "doc_base": "https://developer.samsung.com/",
        "search_template": {
            "en": "site:developer.samsung.com {app_en} {feature_en} One UI",
            "zh": "三星 One UI {app_zh} {feature_zh}",
        },
    },
}

# 预置常用 App 名称映射（中英对照）
APP_NAME_MAP = {
    "图库": {"zh": "图库", "en": "gallery photos"},
    "相册": {"zh": "相册", "en": "gallery album"},
    "照片": {"zh": "照片", "en": "photos"},
    "桌面": {"zh": "桌面", "en": "home screen launcher"},
    "桌面卡片": {"zh": "桌面卡片", "en": "home screen widget"},
    "设置": {"zh": "设置", "en": "settings"},
    "通知": {"zh": "通知", "en": "notifications"},
    "相机": {"zh": "相机", "en": "camera"},
    "日历": {"zh": "日历", "en": "calendar"},
    "备忘录": {"zh": "备忘录", "en": "notes memo"},
    "时钟": {"zh": "时钟", "en": "clock"},
}

# 预置常用功能关键词（与固定场景匹配）
FEATURE_MAP = {
    "桌面卡片": {"zh": "桌面卡片", "en": "widget home screen card"},
    "相册自定义排序": {"zh": "相册自定义排序", "en": "album custom sort order"},
    "用户数据清理": {"zh": "用户数据清理", "en": "storage cleanup user data"},
    "人像分类": {"zh": "人像分类 面孔识别", "en": "portrait face recognition album"},
    "专注模式": {"zh": "专注模式", "en": "focus mode do not disturb"},
    "动态照片": {"zh": "动态照片 live photo", "en": "live photo motion photo"},
}


def generate_plan(app, feature, scope=None):
    app_info = APP_NAME_MAP.get(app, {"zh": app, "en": app})
    feature_info = FEATURE_MAP.get(feature, {"zh": feature, "en": feature})

    vendors = VENDORS
    if scope:
        scope_list = [s.strip() for s in scope.split(",")]
        vendors = {k: v for k, v in vendors.items() if k in scope_list}

    plan = {
        "meta": {
            "app": app,
            "feature": feature,
            "app_zh": app_info["zh"],
            "app_en": app_info["en"],
            "feature_zh": feature_info["zh"],
            "feature_en": feature_info["en"],
        },
        "vendors": {},
    }

    for key, v in vendors.items():
        searches = []
        for lang, template in v["search_template"].items():
            query = template.format(
                app_zh=app_info["zh"],
                app_en=app_info["en"],
                feature_zh=feature_info["zh"],
                feature_en=feature_info["en"],
            )
            searches.append({"lang": lang, "query": query})

        vendor_plan = {
            "name": v["name"],
            "system": v["system"],
            "doc_base": v.get("doc_base", ""),
            "design_base": v.get("design_base", ""),
            "community_base": v.get("community_base", ""),
            "searches": searches,
        }
        plan["vendors"][key] = vendor_plan

    return plan


def main():
    parser = argparse.ArgumentParser(description="竞品特性对比研究计划生成器")
    parser.add_argument("--app", required=True, help="应用名称（如 图库、设置、桌面）")
    parser.add_argument("--feature", required=True, help="功能名称（如 桌面卡片、相册自定义排序）")
    parser.add_argument("--scope", default=None, help="限定厂商子集（逗号分隔，如 apple,华为,小米）")
    parser.add_argument("--output", default=None, help="输出文件路径（可选）")

    args = parser.parse_args()
    plan = generate_plan(args.app, args.feature, args.scope)

    output = json.dumps(plan, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"研究计划已保存到: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
