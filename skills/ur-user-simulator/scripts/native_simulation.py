#!/usr/bin/env python3
"""Prepare current-model task descriptors and validate their answer files."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_responses import (  # noqa: E402
    parse_persons_summary,
    parse_questionnaire,
    quality_markdown,
    resolve_persona_files,
    validate_answer_directory,
)


def prepare(args: argparse.Namespace) -> int:
    questionnaire = args.questionnaire.resolve()
    persons_summary = args.persons_summary.resolve()
    persons_dir = args.persons_dir.resolve()
    parse_questionnaire(questionnaire)
    _, user_ids = parse_persons_summary(persons_summary)
    persona_files = resolve_persona_files(persons_dir, user_ids)
    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    answers_dir = args.output_dir.resolve() / f"answers_{run_id}"
    answers_dir.mkdir(parents=True, exist_ok=True)
    model = args.model_label.strip() or "current-model"
    tasks = [
        {
            "task_id": f"{run_id}-{user_id}",
            "user_id": user_id,
            "questionnaire_path": str(questionnaire),
            "persona_path": str(persona_files[user_id]),
            "output_path": str((answers_dir / f"{user_id}.md").resolve()),
            "model": model,
        }
        for user_id in user_ids
        if not (answers_dir / f"{user_id}.md").exists()
    ]
    print(json.dumps({
        "run_id": run_id,
        "model": model,
        "answers_dir": str(answers_dir),
        "total_users": len(user_ids),
        "pending_tasks": len(tasks),
        "tasks": tasks,
    }, ensure_ascii=False, indent=2))
    return 0


def finalize(args: argparse.Namespace) -> int:
    questionnaire = args.questionnaire.resolve()
    persons_summary = args.persons_summary.resolve()
    persons_dir = args.persons_dir.resolve()
    answers_dir = args.answers_dir.resolve()
    failures: dict[str, str] = {}
    for value in args.failure:
        if "=" not in value:
            raise ValueError("--failure 必须使用 USER_ID=ERROR 格式")
        user_id, message = value.split("=", 1)
        failures[user_id] = message
    quality = validate_answer_directory(questionnaire, persons_summary, persons_dir, answers_dir, failures)
    quality_report = args.quality_report.resolve()
    quality_report.parent.mkdir(parents=True, exist_ok=True)
    quality_report.write_text(quality_markdown(args.run_id, quality), encoding="utf-8")
    print(json.dumps({
        "run_id": args.run_id,
        "answers_dir": str(answers_dir),
        "quality_report": str(quality_report),
        "total": quality["total"],
        "completed": quality["completed"],
        "failed": quality["failed"],
        "data_integrity": quality["data_integrity"],
    }, ensure_ascii=False, indent=2))
    return 0 if quality["data_integrity"] in {"excellent", "good"} else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="准备或汇总当前模型的独立问卷任务")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--questionnaire", type=Path, required=True)
    prepare_parser.add_argument("--persons-summary", type=Path, required=True)
    prepare_parser.add_argument("--persons-dir", type=Path, required=True)
    prepare_parser.add_argument("--output-dir", type=Path, required=True)
    prepare_parser.add_argument("--run-id")
    prepare_parser.add_argument("--model-label", default="current-model")
    prepare_parser.set_defaults(handler=prepare)

    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument("--questionnaire", type=Path, required=True)
    finalize_parser.add_argument("--persons-summary", type=Path, required=True)
    finalize_parser.add_argument("--persons-dir", type=Path, required=True)
    finalize_parser.add_argument("--answers-dir", type=Path, required=True)
    finalize_parser.add_argument("--quality-report", type=Path, required=True)
    finalize_parser.add_argument("--run-id", required=True)
    finalize_parser.add_argument("--failure", action="append", default=[], metavar="USER_ID=ERROR")
    finalize_parser.set_defaults(handler=finalize)
    args = parser.parse_args()
    try:
        return args.handler(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    sys.exit(main())
