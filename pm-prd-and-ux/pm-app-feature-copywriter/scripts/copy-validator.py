#!/usr/bin/env python3
"""手机系统应用文案质量检查脚本

检查项：
1. 字数限制
2. 禁用词检测
3. 格式规范
4. 术语一致性
"""

import sys
import re


# 禁用词列表
FORBIDDEN_WORDS = [
    "史上最强", "颠覆性", "遥遥领先", "革命性", "颠覆",
    "史上最佳", "绝无仅有", "天下第一",
]

# 建议用词（提示性，非强制替换）
SUGGESTED_TERMS = {
    "云盘": "云服务 / 云备份",
    "插件": "小组件 / Widget",
    "推送": "通知 / 提醒",
    "小程序": "轻应用 / 快速应用",
}

# 中英文混排检查：英文前后应有空格
MIXED_PATTERN = re.compile(r'([a-zA-Z])([\u4e00-\u9fff])|([\u4e00-\u9fff])([a-zA-Z])')


def check_length(text, max_chars=None, min_chars=None):
    """检查字数"""
    length = len(text)
    issues = []
    if max_chars and length > max_chars:
        issues.append(f"⚠️ 字数超限：当前 {length} 字，限制 {max_chars} 字以内")
    if min_chars and length < min_chars:
        issues.append(f"⚠️ 字数不足：当前 {length} 字，建议 {min_chars} 字以上")
    return issues


def check_forbidden_words(text):
    """检查禁用词"""
    issues = []
    for word in FORBIDDEN_WORDS:
        if word in text:
            issues.append(f"❌ 包含禁用词：「{word}」")
    return issues


def check_terminology(text):
    """检查术语使用"""
    issues = []
    for wrong, suggestion in SUGGESTED_TERMS.items():
        if wrong in text:
            issues.append(f"💡 建议替换：「{wrong}」→ {suggestion}")
    return issues


def check_mixed_spacing(text):
    """检查中英文混排空格"""
    issues = []
    matches = MIXED_PATTERN.findall(text)
    if matches:
        examples = []
        for m in matches:
            parts = [p for p in m if p]
            if len(parts) == 2:
                examples.append(f"「{parts[0]}{parts[1]}」")
        if examples:
            issues.append(f"💡 中英文混排建议加空格，例如：{', '.join(examples[:3])}")
    return issues


def validate(text, max_chars=None, min_chars=None):
    """完整检查"""
    all_issues = []
    all_issues.extend(check_length(text, max_chars, min_chars))
    all_issues.extend(check_forbidden_words(text))
    all_issues.extend(check_terminology(text))
    all_issues.extend(check_mixed_spacing(text))
    return all_issues


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python copy-validator.py <文本> [最大字数] [最小字数]")
        print("示例: python copy-validator.py '智能修图，一触即达' 20")
        sys.exit(0)

    text = sys.argv[1]
    max_chars = int(sys.argv[2]) if len(sys.argv) > 2 else None
    min_chars = int(sys.argv[3]) if len(sys.argv) > 3 else None

    issues = validate(text, max_chars, min_chars)

    if issues:
        print("检查结果：")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("✅ 检查通过，未发现明显问题。")
