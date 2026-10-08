#!/usr/bin/env python3
"""Persist task checkpoints and collection gaps emitted by browser or API collectors."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from voc_store import PLATFORMS, TASK_STATES, connect, create_gap, get_study, initialize_schema, json_text, now_iso, require_text


def apply_progress(db_path: Path, study_id: str, input_path: Path) -> dict[str, int]:
    conn = connect(db_path)
    updated = 0
    gaps = 0
    try:
        initialize_schema(conn)
        get_study(conn, study_id)
        with input_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError(f"line {line_number} must be a JSON object")
                task_id = require_text(raw.get("task_id"), "task_id")
                status = require_text(raw.get("status"), "status")
                if status not in TASK_STATES:
                    raise ValueError(f"line {line_number}: unsupported status {status}")
                task = conn.execute("SELECT * FROM query_tasks WHERE task_id = ? AND study_id = ?", (task_id, study_id)).fetchone()
                if task is None:
                    raise ValueError(f"line {line_number}: task_id does not belong to study")
                checkpoint = raw.get("checkpoint")
                if checkpoint is not None and not isinstance(checkpoint, dict):
                    raise ValueError(f"line {line_number}: checkpoint must be an object")
                error = str(raw.get("last_error") or "").strip() or None
                conn.execute(
                    "UPDATE query_tasks SET status = ?, checkpoint_json = ?, last_error = ?, updated_at = ? WHERE task_id = ?",
                    (status, json_text(checkpoint) if checkpoint is not None else task["checkpoint_json"], error, now_iso(), task_id),
                )
                updated += 1
                if status in {"partial", "blocked"} or error:
                    create_gap(
                        conn, study_id, task["platform"], "collection", "task_incomplete" if status == "partial" else "task_blocked",
                        task_id=task_id, competitor=task["competitor"], month_start=task["month_start"], detail=error,
                    )
                    gaps += 1
        conn.commit()
    finally:
        conn.close()
    return {"updated_tasks": updated, "new_gaps": gaps}


def main() -> int:
    parser = argparse.ArgumentParser(description="更新 VOC 采集任务状态和可恢复断点")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--study-id", required=True)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(apply_progress(args.db, args.study_id, args.input), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

