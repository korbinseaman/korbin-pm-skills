"""Shared SQLite storage and validation helpers for competitor social VOC studies."""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


PLATFORMS = {"weibo", "xiaohongshu", "coolapk"}
ADDRESS_TYPES = {"direct_comment", "parent_thread", "thread"}
COLLECTION_STATES = {
    "complete_under_current_interface",
    "max_visible",
    "partial",
    "blocked",
    "accessible",
    "login_required",
    "deleted",
    "restricted",
}
TASK_STATES = {"planned", "in_progress", "complete_under_current_interface", "max_visible", "partial", "blocked"}
SENSITIVE_QUERY_KEYS = {"access_token", "token", "cookie", "session", "sessionid", "authorization", "auth", "passport"}
TRACKING_QUERY_KEYS = {"spm", "from", "source", "share_source", "share_platform", "share_session_id", "utm_source", "utm_medium", "utm_campaign"}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def parse_json_text(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def as_string_list(value: Any, field_name: str) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must be an array of strings")
    return [item.strip() for item in value if item.strip()]


def as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def platform_matches_url(platform: str, url: str) -> bool:
    host = urlsplit(url).hostname or ""
    host = host.lower()
    suffixes = {
        "weibo": ("weibo.com", "weibo.cn"),
        "xiaohongshu": ("xiaohongshu.com", "xhslink.com"),
        "coolapk": ("coolapk.com",),
    }
    return any(host == suffix or host.endswith(f".{suffix}") for suffix in suffixes[platform])


def validate_public_url(value: Any, platform: str, field_name: str) -> str:
    url = require_text(value, field_name)
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError(f"{field_name} must be an absolute HTTP(S) URL")
    if not platform_matches_url(platform, url):
        raise ValueError(f"{field_name} does not match platform {platform}")
    sensitive_keys = {key.lower() for key, _ in parse_qsl(parts.query, keep_blank_values=True)}
    leaked = sorted(sensitive_keys & SENSITIVE_QUERY_KEYS)
    if leaked:
        raise ValueError(f"{field_name} contains a sensitive query parameter: {', '.join(leaked)}")
    return url


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url)
    pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_KEYS and not key.lower().startswith("utm_")
    ]
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(sorted(pairs)), ""))


def stable_hash(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def initialize_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS studies (
          study_id TEXT PRIMARY KEY,
          subject TEXT NOT NULL,
          feature_name TEXT NOT NULL,
          start_date TEXT NOT NULL,
          end_date TEXT NOT NULL,
          request_json TEXT NOT NULL,
          author_salt TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS query_tasks (
          task_id TEXT PRIMARY KEY,
          study_id TEXT NOT NULL REFERENCES studies(study_id),
          platform TEXT NOT NULL,
          competitor TEXT NOT NULL,
          query_text TEXT NOT NULL,
          month_start TEXT NOT NULL,
          month_end TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'planned',
          checkpoint_json TEXT,
          last_error TEXT,
          updated_at TEXT NOT NULL,
          UNIQUE(study_id, platform, competitor, query_text, month_start)
        );
        CREATE TABLE IF NOT EXISTS voice_records (
          record_id TEXT PRIMARY KEY,
          study_id TEXT NOT NULL REFERENCES studies(study_id),
          platform TEXT NOT NULL,
          competitor TEXT NOT NULL,
          product TEXT NOT NULL,
          feature_path_json TEXT NOT NULL,
          original_text TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          source_url_raw TEXT NOT NULL,
          source_url_canonical TEXT NOT NULL,
          thread_url TEXT NOT NULL,
          source_content_id TEXT,
          source_comment_id TEXT,
          parent_comment_id TEXT,
          address_type TEXT NOT NULL,
          published_at TEXT,
          captured_at TEXT NOT NULL,
          author_hash TEXT,
          engagement_json TEXT NOT NULL DEFAULT '{}',
          content_type TEXT,
          observed_version TEXT,
          observed_device TEXT,
          screenshot_ref TEXT,
          collection_status TEXT NOT NULL DEFAULT 'accessible',
          analysis_eligible INTEGER NOT NULL DEFAULT 1,
          exclusion_reason TEXT,
          stance TEXT,
          theme TEXT,
          reason_tags_json TEXT NOT NULL DEFAULT '[]',
          scenario_tags_json TEXT NOT NULL DEFAULT '[]',
          pain_point_tags_json TEXT NOT NULL DEFAULT '[]',
          request_tags_json TEXT NOT NULL DEFAULT '[]',
          manual_confirmation INTEGER NOT NULL DEFAULT 0,
          notes TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_voice_study ON voice_records(study_id);
        CREATE INDEX IF NOT EXISTS idx_voice_theme ON voice_records(study_id, competitor, theme);
        CREATE TABLE IF NOT EXISTS collection_gaps (
          gap_id TEXT PRIMARY KEY,
          study_id TEXT NOT NULL REFERENCES studies(study_id),
          task_id TEXT,
          platform TEXT NOT NULL,
          competitor TEXT,
          month_start TEXT,
          stage TEXT NOT NULL,
          error_type TEXT NOT NULL,
          raw_url TEXT,
          detail TEXT,
          occurred_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def get_study(conn: sqlite3.Connection, study_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM studies WHERE study_id = ?", (study_id,)).fetchone()
    if row is None:
        raise ValueError(f"study_id not found: {study_id}")
    return row


def record_id_for(study_id: str, raw: dict[str, Any], source_url_canonical: str) -> str:
    platform = str(raw["platform"])
    comment_id = str(raw.get("source_comment_id") or "").strip()
    content_id = str(raw.get("source_content_id") or "").strip()
    if comment_id:
        identity = [study_id, platform, "comment", comment_id]
    elif content_id:
        identity = [study_id, platform, "content", content_id]
    else:
        identity = [
            study_id,
            platform,
            source_url_canonical,
            str(raw.get("published_at") or ""),
            str(raw.get("original_text") or ""),
        ]
    return stable_hash(*identity)


def normalise_voice_record(study: sqlite3.Row, raw: dict[str, Any]) -> dict[str, Any]:
    platform = require_text(raw.get("platform"), "platform").lower()
    if platform not in PLATFORMS:
        raise ValueError(f"unsupported platform: {platform}")
    source_url_raw = validate_public_url(raw.get("source_url_raw"), platform, "source_url_raw")
    thread_url = validate_public_url(raw.get("thread_url") or source_url_raw, platform, "thread_url")
    address_type = str(raw.get("address_type") or "").strip() or (
        "direct_comment" if raw.get("source_comment_id") else "parent_thread"
    )
    if address_type not in ADDRESS_TYPES:
        raise ValueError("address_type must be direct_comment, parent_thread, or thread")
    if address_type == "parent_thread" and not raw.get("source_comment_id") and source_url_raw != thread_url:
        raise ValueError("parent_thread records without a comment ID must use the verified thread URL")
    collection_status = str(raw.get("collection_status") or "accessible").strip()
    if collection_status not in COLLECTION_STATES:
        raise ValueError(f"unsupported collection_status: {collection_status}")
    original_text = require_text(raw.get("original_text"), "original_text")
    captured_at = str(raw.get("captured_at") or now_iso())
    source_url_canonical = canonicalize_url(source_url_raw)
    author_handle = str(raw.get("author_handle") or "").strip()
    author_hash = stable_hash(study["author_salt"], platform, author_handle) if author_handle else None
    eligible = as_bool(raw.get("analysis_eligible"), default=not bool(raw.get("exclusion_reason")))
    normalized = {
        "record_id": str(raw.get("record_id") or record_id_for(study["study_id"], raw, source_url_canonical)),
        "study_id": study["study_id"],
        "platform": platform,
        "competitor": require_text(raw.get("competitor"), "competitor"),
        "product": require_text(raw.get("product"), "product"),
        "feature_path_json": json_text(as_string_list(raw.get("feature_path"), "feature_path")),
        "original_text": original_text,
        "content_hash": stable_hash(original_text),
        "source_url_raw": source_url_raw,
        "source_url_canonical": source_url_canonical,
        "thread_url": thread_url,
        "source_content_id": str(raw.get("source_content_id") or "").strip() or None,
        "source_comment_id": str(raw.get("source_comment_id") or "").strip() or None,
        "parent_comment_id": str(raw.get("parent_comment_id") or "").strip() or None,
        "address_type": address_type,
        "published_at": str(raw.get("published_at") or "").strip() or None,
        "captured_at": captured_at,
        "author_hash": author_hash,
        "engagement_json": json_text(raw.get("engagement") if isinstance(raw.get("engagement"), dict) else {}),
        "content_type": str(raw.get("content_type") or "").strip() or None,
        "observed_version": str(raw.get("observed_version") or "").strip() or None,
        "observed_device": str(raw.get("observed_device") or "").strip() or None,
        "screenshot_ref": str(raw.get("screenshot_ref") or "").strip() or None,
        "collection_status": collection_status,
        "analysis_eligible": int(eligible),
        "exclusion_reason": str(raw.get("exclusion_reason") or "").strip() or None,
        "stance": str(raw.get("stance") or "").strip() or None,
        "theme": str(raw.get("theme") or "").strip() or None,
        "reason_tags_json": json_text(as_string_list(raw.get("reason_tags"), "reason_tags")),
        "scenario_tags_json": json_text(as_string_list(raw.get("scenario_tags"), "scenario_tags")),
        "pain_point_tags_json": json_text(as_string_list(raw.get("pain_point_tags"), "pain_point_tags")),
        "request_tags_json": json_text(as_string_list(raw.get("request_tags"), "request_tags")),
        "manual_confirmation": int(as_bool(raw.get("manual_confirmation"), default=False)),
        "notes": str(raw.get("notes") or "").strip() or None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    return normalized


def upsert_voice_record(conn: sqlite3.Connection, record: dict[str, Any]) -> None:
    columns = list(record)
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(f"{name}=excluded.{name}" for name in columns if name not in {"record_id", "study_id", "created_at"})
    conn.execute(
        f"INSERT INTO voice_records ({', '.join(columns)}) VALUES ({placeholders}) "
        f"ON CONFLICT(record_id) DO UPDATE SET {updates}",
        [record[column] for column in columns],
    )


def create_gap(
    conn: sqlite3.Connection,
    study_id: str,
    platform: str,
    stage: str,
    error_type: str,
    *,
    task_id: str | None = None,
    competitor: str | None = None,
    month_start: str | None = None,
    raw_url: str | None = None,
    detail: str | None = None,
) -> None:
    gap_id = stable_hash(study_id, platform, stage, error_type, raw_url or "", detail or "", now_iso())
    conn.execute(
        """INSERT INTO collection_gaps
        (gap_id, study_id, task_id, platform, competitor, month_start, stage, error_type, raw_url, detail, occurred_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (gap_id, study_id, task_id, platform, competitor, month_start, stage, error_type, raw_url, detail, now_iso()),
    )


def fetch_records(conn: sqlite3.Connection, study_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM voice_records WHERE study_id = ? ORDER BY published_at, record_id", (study_id,)
    ).fetchall()
    records = []
    for row in rows:
        record = dict(row)
        for name in ("feature_path", "reason_tags", "scenario_tags", "pain_point_tags", "request_tags"):
            record[name] = parse_json_text(record.pop(f"{name}_json"), [])
        record["engagement"] = parse_json_text(record.pop("engagement_json"), {})
        record["analysis_eligible"] = bool(record["analysis_eligible"])
        record["manual_confirmation"] = bool(record["manual_confirmation"])
        records.append(record)
    return records


def safe_file_stem(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value.strip())
    value = re.sub(r"\s+", "_", value).strip("._")
    return value or "voc"


def make_study_id(subject: str, feature: str) -> str:
    prefix = safe_file_stem(f"{subject}-{feature}")[:36]
    return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3)}"

