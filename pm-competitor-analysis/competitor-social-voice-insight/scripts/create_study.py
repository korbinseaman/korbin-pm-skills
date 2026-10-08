#!/usr/bin/env python3
"""Initialise a two-year, three-platform VOC study and emit its query task plan."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from voc_store import PLATFORMS, connect, initialize_schema, json_text, make_study_id, now_iso, require_text, safe_file_stem, stable_hash


OPINION_TERMS = ["好用", "不好用", "体验", "问题", "建议", "希望", "不能用", "失效", "卡顿"]


def two_years_before(value: date) -> date:
    try:
        return value.replace(year=value.year - 2)
    except ValueError:
        return value.replace(year=value.year - 2, month=2, day=28)


def parse_date(value: str | None, fallback: date) -> date:
    if not value:
        return fallback
    return date.fromisoformat(value)


def months_between(start: date, end: date) -> list[tuple[date, date]]:
    current = start.replace(day=1)
    months = []
    while current <= end:
        next_month = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        month_end = min(end, next_month - timedelta(days=1))
        months.append((max(start, current), month_end))
        current = next_month
    return months


def load_request(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("study request must be a JSON object")
    return data


def build_query_texts(competitor: dict[str, Any], feature: dict[str, Any]) -> list[str]:
    name = require_text(competitor.get("name"), "competitors[].name")
    product = require_text(competitor.get("product"), "competitors[].product")
    competitor_terms = [name, product, *[str(item).strip() for item in competitor.get("aliases", []) if str(item).strip()]]
    feature_terms = [require_text(feature.get("name"), "feature.name"), *[str(item).strip() for item in feature.get("aliases", []) if str(item).strip()]]
    queries = set()
    for vendor in competitor_terms:
        for feature_term in feature_terms:
            for opinion in OPINION_TERMS:
                queries.add(f"{vendor} {feature_term} {opinion}")
    return sorted(queries)


def create_study(request: dict[str, Any], db_path: Path) -> dict[str, Any]:
    subject = require_text(request.get("subject"), "subject")
    feature = request.get("feature")
    if not isinstance(feature, dict):
        raise ValueError("feature must be an object")
    feature_name = require_text(feature.get("name"), "feature.name")
    competitors = request.get("competitors")
    if not isinstance(competitors, list) or not competitors:
        raise ValueError("competitors must be a non-empty array")
    if not all(isinstance(item, dict) for item in competitors):
        raise ValueError("competitors must contain objects")
    end_date = parse_date(request.get("end_date"), date.today())
    start_date = parse_date(request.get("start_date"), two_years_before(end_date))
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")
    study_id = str(request.get("study_id") or make_study_id(subject, feature_name))

    conn = connect(db_path)
    try:
        initialize_schema(conn)
        existing = conn.execute("SELECT 1 FROM studies WHERE study_id = ?", (study_id,)).fetchone()
        if existing:
            raise ValueError(f"study_id already exists: {study_id}")
        created_at = now_iso()
        conn.execute(
            """INSERT INTO studies (study_id, subject, feature_name, start_date, end_date, request_json, author_salt, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (study_id, subject, feature_name, start_date.isoformat(), end_date.isoformat(), json_text(request), stable_hash(study_id, created_at), created_at),
        )
        task_rows = []
        for competitor in competitors:
            competitor_name = require_text(competitor.get("name"), "competitors[].name")
            for query_text in build_query_texts(competitor, feature):
                for month_start, month_end in months_between(start_date, end_date):
                    for platform in sorted(PLATFORMS):
                        task_id = stable_hash(study_id, platform, competitor_name, query_text, month_start.isoformat())
                        row = {
                            "task_id": task_id,
                            "study_id": study_id,
                            "platform": platform,
                            "competitor": competitor_name,
                            "query_text": query_text,
                            "month_start": month_start.isoformat(),
                            "month_end": month_end.isoformat(),
                            "status": "planned",
                            "checkpoint_json": None,
                            "last_error": None,
                            "updated_at": created_at,
                        }
                        task_rows.append(row)
        conn.executemany(
            """INSERT INTO query_tasks (task_id, study_id, platform, competitor, query_text, month_start, month_end, status, checkpoint_json, last_error, updated_at)
            VALUES (:task_id, :study_id, :platform, :competitor, :query_text, :month_start, :month_end, :status, :checkpoint_json, :last_error, :updated_at)""",
            task_rows,
        )
        conn.commit()
    finally:
        conn.close()
    return {"study_id": study_id, "db_path": str(db_path.resolve()), "task_count": len(task_rows), "tasks": task_rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="创建三平台、近两年的竞品功能 VOC 研究库与查询计划")
    parser.add_argument("--request", type=Path, required=True, help="StudyRequest JSON")
    parser.add_argument("--db", type=Path, default=Path("workspace/竞品用户洞察/social-voice.db"))
    parser.add_argument("--plan-output", type=Path, default=None, help="可选：写出 JSONL 查询计划")
    args = parser.parse_args()
    try:
        result = create_study(load_request(args.request), args.db)
        if args.plan_output:
            args.plan_output.parent.mkdir(parents=True, exist_ok=True)
            with args.plan_output.open("w", encoding="utf-8", newline="\n") as handle:
                for task in result.pop("tasks"):
                    handle.write(json.dumps(task, ensure_ascii=False) + "\n")
        else:
            result.pop("tasks")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

