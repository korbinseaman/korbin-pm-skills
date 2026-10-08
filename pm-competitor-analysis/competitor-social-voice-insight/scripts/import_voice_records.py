#!/usr/bin/env python3
"""Validate and upsert collected social voice JSONL into a VOC study database."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from voc_store import connect, get_study, initialize_schema, normalise_voice_record, upsert_voice_record


def import_records(db_path: Path, study_id: str, input_path: Path) -> dict[str, int]:
    conn = connect(db_path)
    submitted = 0
    imported = 0
    try:
        initialize_schema(conn)
        study = get_study(conn, study_id)
        with input_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                submitted += 1
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"line {line_number} is not valid JSON: {exc}") from exc
                if not isinstance(raw, dict):
                    raise ValueError(f"line {line_number} must be a JSON object")
                try:
                    record = normalise_voice_record(study, raw)
                except ValueError as exc:
                    raise ValueError(f"line {line_number}: {exc}") from exc
                upsert_voice_record(conn, record)
                imported += 1
        conn.commit()
    finally:
        conn.close()
    return {"submitted": submitted, "imported": imported}


def main() -> int:
    parser = argparse.ArgumentParser(description="导入并校验三平台用户原声 JSONL")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--study-id", required=True)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(import_records(args.db, args.study_id, args.input), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

