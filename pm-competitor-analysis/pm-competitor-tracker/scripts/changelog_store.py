#!/usr/bin/env python3
"""Validate and upsert competitor findings into per-competitor JSONL files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


SCHEMA_VERSION = 1
CHANGE_TYPES = {
    "feature_added",
    "feature_changed",
    "fix",
    "rollout",
    "service_or_pricing",
    "user_feedback",
    "news",
}
SOURCE_TYPES = {"official", "community_official", "community", "media"}
TRACKING_KEYS = {"fbclid", "gclid", "spm", "mc_cid", "mc_eid"}


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("source.url must be an absolute HTTP(S) URL")
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_KEYS
    ]
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(sorted(query)), ""))


def safe_filename_part(value: str) -> str:
    normalized = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value.strip())
    normalized = re.sub(r"\s+", "_", normalized).strip("._")
    return normalized or "unknown"


def changelog_path(output_dir: Path, competitor_name: str, app_name: str) -> Path:
    filename = f"{safe_filename_part(competitor_name)}_{safe_filename_part(app_name)}_changelog.jsonl"
    return output_dir / filename


def _require_mapping(item: dict[str, Any], key: str, prefix: str) -> dict[str, Any]:
    value = item.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{prefix}.{key} must be an object")
    return value


def normalize_finding(raw: dict[str, Any]) -> dict[str, Any]:
    competitor = _require_mapping(raw, "competitor", "finding")
    feature = _require_mapping(raw, "feature", "finding")
    change = _require_mapping(raw, "change", "finding")
    release = _require_mapping(raw, "release", "finding")
    source = _require_mapping(raw, "source", "finding")

    required_strings = {
        "competitor.name": competitor.get("name"),
        "competitor.app_name": competitor.get("app_name"),
        "app_name": raw.get("app_name"),
        "feature.name": feature.get("name"),
        "change.type": change.get("type"),
        "change.title": change.get("title"),
        "change.summary": change.get("summary"),
        "release.published_at": release.get("published_at"),
        "source.type": source.get("type"),
        "source.url": source.get("url"),
    }
    missing = [name for name, value in required_strings.items() if not isinstance(value, str) or not value.strip()]
    if missing:
        raise ValueError("missing required string fields: " + ", ".join(missing))

    path = feature.get("path")
    if not isinstance(path, list) or not path or not all(isinstance(value, str) and value.strip() for value in path):
        raise ValueError("feature.path must be a non-empty array of strings")
    tags = feature.get("tags", [])
    if not isinstance(tags, list) or not all(isinstance(value, str) for value in tags):
        raise ValueError("feature.tags must be an array of strings")
    if change["type"] not in CHANGE_TYPES:
        raise ValueError(f"unsupported change.type: {change['type']}")
    if source["type"] not in SOURCE_TYPES:
        raise ValueError(f"unsupported source.type: {source['type']}")
    try:
        datetime.strptime(release["published_at"], "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("release.published_at must be YYYY-MM-DD") from exc

    normalized = {
        "competitor": {
            "name": competitor["name"].strip(),
            "platform": str(competitor.get("platform") or "").strip() or None,
            "app_name": competitor["app_name"].strip(),
        },
        "app_name": raw["app_name"].strip(),
        "feature": {
            "path": [value.strip() for value in path],
            "name": feature["name"].strip(),
            "tags": sorted(set(value.strip() for value in tags if value.strip())),
        },
        "change": {
            "type": change["type"],
            "title": change["title"].strip(),
            "summary": change["summary"].strip(),
            "details": change.get("details"),
        },
        "release": {
            "version": release.get("version"),
            "published_at": release["published_at"],
            "regions": release.get("regions", []),
            "models": release.get("models", []),
        },
        "source": {
            "type": source["type"],
            "name": source.get("name"),
            "url": canonicalize_url(source["url"]),
            "language": source.get("language"),
        },
    }
    if not isinstance(normalized["release"]["regions"], list):
        raise ValueError("release.regions must be an array")
    if not isinstance(normalized["release"]["models"], list):
        raise ValueError("release.models must be an array")
    return normalized


def stable_id(finding: dict[str, Any]) -> str:
    identity = {
        "competitor": finding["competitor"]["name"],
        "app_name": finding["app_name"],
        "feature_path": finding["feature"]["path"],
        "feature_name": finding["feature"]["name"],
        "change_type": finding["change"]["type"],
        "version": finding["release"].get("version"),
        "published_at": finding["release"]["published_at"],
        "source_url": finding["source"]["url"],
    }
    payload = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON in {path} line {line_number}: {exc}") from exc
            record_id = record.get("id")
            if not isinstance(record_id, str) or not record_id:
                raise ValueError(f"missing id in {path} line {line_number}")
            records[record_id] = record
    return records


def atomic_write_jsonl(path: Path, records: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        ordered = sorted(
            records.values(),
            key=lambda item: (item["release"]["published_at"], item["id"]),
        )
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            for record in ordered:
                handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def upsert_findings(
    findings: list[dict[str, Any]],
    output_dir: Path,
    run_id: str,
    mode: str,
    seen_at: str,
) -> dict[str, Any]:
    if mode not in {"daily", "weekly"}:
        raise ValueError("mode must be daily or weekly")
    datetime.fromisoformat(seen_at)

    normalized_by_id: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(findings, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"finding[{index}] must be an object")
        try:
            normalized = normalize_finding(raw)
        except ValueError as exc:
            raise ValueError(f"finding[{index}]: {exc}") from exc
        normalized_by_id[stable_id(normalized)] = normalized

    groups: dict[Path, list[tuple[str, dict[str, Any]]]] = {}
    for record_id, finding in normalized_by_id.items():
        path = changelog_path(output_dir, finding["competitor"]["name"], finding["app_name"])
        groups.setdefault(path, []).append((record_id, finding))

    totals = {"submitted": len(findings), "unique_submitted": len(normalized_by_id), "added": 0, "updated": 0}
    files = []
    for path, group in groups.items():
        records = load_jsonl(path)
        file_added = 0
        file_updated = 0
        for record_id, finding in group:
            existing = records.get(record_id)
            if existing:
                tracking = existing.setdefault("tracking", {})
                run_ids = tracking.setdefault("run_ids", [])
                modes = tracking.setdefault("modes_seen", [])
                if run_id not in run_ids:
                    run_ids.append(run_id)
                    tracking["seen_count"] = int(tracking.get("seen_count", 1)) + 1
                if mode not in modes:
                    modes.append(mode)
                tracking["last_seen_at"] = seen_at
                existing.update(finding)
                existing["schema_version"] = SCHEMA_VERSION
                existing["id"] = record_id
                existing["tracking"] = tracking
                file_updated += 1
            else:
                records[record_id] = {
                    "schema_version": SCHEMA_VERSION,
                    "id": record_id,
                    **finding,
                    "tracking": {
                        "first_seen_at": seen_at,
                        "last_seen_at": seen_at,
                        "seen_count": 1,
                        "run_ids": [run_id],
                        "modes_seen": [mode],
                    },
                }
                file_added += 1
        atomic_write_jsonl(path, records)
        totals["added"] += file_added
        totals["updated"] += file_updated
        files.append({
            "path": str(path.resolve()),
            "added": file_added,
            "updated": file_updated,
            "total": len(records),
        })
    return {**totals, "files": files}


def load_findings(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        data = data.get("findings")
    if not isinstance(data, list):
        raise ValueError("input must be a JSON array or an object with a findings array")
    return data


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="将竞品发现写入按厂商拆分的 JSONL changelog")
    parser.add_argument("--input", type=Path, required=True, help="本次 findings JSON")
    parser.add_argument("--output-dir", type=Path, default=Path("workspace/竞品分析/changelog"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--mode", choices=["daily", "weekly"], required=True)
    parser.add_argument("--seen-at", default=None, help="ISO 8601；默认当前本地时间")
    args = parser.parse_args()
    try:
        result = upsert_findings(
            load_findings(args.input),
            args.output_dir,
            args.run_id,
            args.mode,
            args.seen_at or datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
