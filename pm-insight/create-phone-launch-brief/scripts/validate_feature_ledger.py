#!/usr/bin/env python3
"""Validate the temporary evidence ledger used by create-phone-launch-brief."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CATEGORIES = {
    "新品硬件与价格",
    "操作系统与系统软件",
    "系统应用AI",
    "相机",
    "图库",
    "桌面与锁屏",
    "通信",
    "隐私与安全",
    "办公效率",
    "云服务",
    "跨设备协同",
    "其他软件能力",
}
EVIDENCE_LEVELS = {"official-announcement", "official-demo", "media-report", "media-test"}
AVAILABILITY = {"available", "preview", "phased-rollout", "unknown"}
PRIORITIES = {"key", "supporting"}


def nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return value is not None


def validate(data: Any, mode: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        return ["Root value must be a JSON object."], warnings

    event = data.get("event")
    sources = data.get("sources")
    features = data.get("features")

    if not isinstance(event, dict):
        errors.append("event must be an object.")
        event = {}
    for field in ("brand", "name", "date", "region", "edition"):
        if not nonempty(event.get(field)):
            errors.append(f"event.{field} is required.")
    if event.get("edition") not in {"速递版", "完整版", None}:
        errors.append("event.edition must be 速递版 or 完整版.")

    if not isinstance(sources, list) or not sources:
        errors.append("sources must be a non-empty array.")
        sources = []
    policy = event.get("source_policy", "official-and-mainstream-media")
    if policy not in {"official-only", "official-and-mainstream-media"}:
        errors.append("event.source_policy is invalid.")
    source_ids: set[str] = set()
    source_map: dict[str, dict] = {}
    for index, source in enumerate(sources):
        label = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{label} must be an object.")
            continue
        for field in ("source_id", "type", "title", "publisher", "url", "accessed_at"):
            if not nonempty(source.get(field)):
                errors.append(f"{label}.{field} is required.")
        source_id = source.get("source_id")
        if nonempty(source_id):
            if source_id in source_ids:
                errors.append(f"Duplicate source_id: {source_id}.")
            source_ids.add(source_id)
            source_map[source_id] = source
        source_class = source.get("source_class")
        if source_class == "official":
            if source.get("official") is not True:
                errors.append(f"{label}: official source_class requires official=true.")
        elif source_class == "mainstream-media":
            if source.get("official") is not False:
                errors.append(f"{label}: mainstream-media requires official=false.")
            if policy == "official-only":
                errors.append(f"{label}: media sources are disallowed by official-only policy.")
            for field in ("credibility_basis", "published_at"):
                if not nonempty(source.get(field)):
                    errors.append(f"{label}.{field} is required for mainstream media.")
        else:
            errors.append(f"{label}.source_class must be official or mainstream-media.")
        url = source.get("url")
        if isinstance(url, str) and not url.startswith(("https://", "http://")):
            warnings.append(f"{label}.url is not an HTTP(S) URL: {url}")
        if not nonempty(source.get("locator")):
            warnings.append(f"{label}.locator is missing; add a section, paragraph, or video range.")

    if not isinstance(features, list) or not features:
        errors.append("features must be a non-empty array.")
        features = []
    feature_ids: set[str] = set()
    key_count = 0
    for index, feature in enumerate(features):
        label = f"features[{index}]"
        if not isinstance(feature, dict):
            errors.append(f"{label} must be an object.")
            continue
        for field in (
            "feature_id",
            "name",
            "category",
            "priority",
            "part",
            "claim",
            "availability_status",
            "evidence_level",
            "source_refs",
        ):
            if not nonempty(feature.get(field)):
                errors.append(f"{label}.{field} is required.")

        feature_id = feature.get("feature_id")
        if nonempty(feature_id):
            if feature_id in feature_ids:
                errors.append(f"Duplicate feature_id: {feature_id}.")
            feature_ids.add(feature_id)

        if feature.get("category") not in CATEGORIES and feature.get("category") is not None:
            errors.append(f"{label}.category is not an allowed category.")
        if feature.get("priority") not in PRIORITIES and feature.get("priority") is not None:
            errors.append(f"{label}.priority must be key or supporting.")
        if feature.get("evidence_level") not in EVIDENCE_LEVELS and feature.get("evidence_level") is not None:
            errors.append(f"{label}.evidence_level is invalid.")
        if feature.get("availability_status") not in AVAILABILITY and feature.get("availability_status") is not None:
            errors.append(f"{label}.availability_status is invalid.")

        part = feature.get("part")
        expected_part = {"新品硬件与价格": 1, "操作系统与系统软件": 2}.get(feature.get("category"), 3)
        if type(part) is not int or part not in {1, 2, 3}:
            errors.append(f"{label}.part must be 1, 2 or 3.")
        elif part != expected_part:
            errors.append(f"{label}.part does not match its category.")
        for field in ("analysis", "harmony_implication"):
            if nonempty(feature.get(field)):
                errors.append(f"{label}.{field} is outside this factual briefing's scope.")
        if not (nonempty(feature.get("text_locator")) or nonempty(feature.get("video_timestamp"))):
            errors.append(f"{label} needs a direct text locator or video timestamp.")

        refs = feature.get("source_refs")
        if isinstance(refs, list):
            for ref in refs:
                if ref not in source_ids:
                    errors.append(f"{label}.source_refs contains unknown source: {ref}.")
        elif refs is not None:
            errors.append(f"{label}.source_refs must be an array.")

        cited_sources = [source_map[ref] for ref in refs if ref in source_map] if isinstance(refs, list) else []
        evidence = feature.get("evidence_level", "")
        required_class = "official" if evidence.startswith("official-") else "mainstream-media"
        if evidence in EVIDENCE_LEVELS and not any(s.get("source_class") == required_class for s in cited_sources):
            errors.append(f"{label}: evidence_level requires a {required_class} source.")
        if evidence == "media-test" and not nonempty(feature.get("test_conditions")):
            errors.append(f"{label}.test_conditions is required for media-test.")
        if evidence == "official-demo" and not nonempty(feature.get("video_timestamp")):
            warnings.append(f"{label}: verify the actual official demo visual and record its locator.")

        if feature.get("priority") == "key":
            key_count += 1
            key_fields = ("user_scenario", "result", "applicable_devices") if part == 3 else ("applicable_devices",)
            for field in key_fields:
                if not nonempty(feature.get(field)):
                    warnings.append(f"{label}.{field} is missing for a key feature.")
            if not nonempty(feature.get("visual_source")):
                warnings.append(f"{label}.visual_source is missing for a key feature.")
            if not (nonempty(feature.get("text_locator")) or nonempty(feature.get("video_timestamp"))):
                warnings.append(f"{label} needs a text locator or video timestamp.")

        if feature.get("availability_status") == "unknown":
            warnings.append(f"{label} has unknown availability; retain it in the pending-verification list.")

    covered_parts = {f.get("part") for f in features if isinstance(f, dict) and isinstance(f.get("part"), int)}
    for part in {1, 2, 3} - covered_parts:
        warnings.append(f"Part {part} has no supported claims; collect evidence or disclose the coverage gap.")
    if key_count == 0:
        warnings.append("No key features are marked; the deck may lack focused feature pages.")

    if mode == "verified":
        if event.get("edition") not in {"完整版", None}:
            errors.append("Verified mode requires event.edition to be 完整版.")
        for index, feature in enumerate(features):
            if not isinstance(feature, dict) or feature.get("priority") != "key":
                continue
            if feature.get("availability_status") == "unknown":
                warnings.append(
                    f"features[{index}] remains unknown in verified mode; explain why official materials do not resolve it."
                )
            if not nonempty(feature.get("video_timestamp")) and not nonempty(feature.get("text_locator")):
                errors.append(f"features[{index}] lacks a direct locator in verified mode.")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path, help="Path to the feature ledger JSON file")
    parser.add_argument("--mode", choices=("rapid", "verified"), default="rapid")
    args = parser.parse_args()

    try:
        data = json.loads(args.ledger.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: file not found: {args.ledger}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}", file=sys.stderr)
        return 2

    errors, warnings = validate(data, args.mode)
    for message in warnings:
        print(f"WARNING: {message}")
    for message in errors:
        print(f"ERROR: {message}", file=sys.stderr)

    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s).", file=sys.stderr)
        return 1
    print(f"OK: ledger valid with {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
