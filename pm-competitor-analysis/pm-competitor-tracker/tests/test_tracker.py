from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import changelog_store  # noqa: E402
import research_plan  # noqa: E402


def sample_finding() -> dict:
    return {
        "competitor": {"name": "Apple", "platform": "iOS", "app_name": "Photos"},
        "app_name": "照片",
        "feature": {"path": ["编辑", "AI 编辑", "消除"], "name": "Clean Up", "tags": ["AI"]},
        "change": {
            "type": "feature_added",
            "title": "Clean Up 新增对象移除能力",
            "summary": "用户可在照片中移除干扰对象。",
        },
        "release": {
            "version": "iOS 27.0",
            "published_at": "2026-09-21",
            "regions": ["全球"],
            "models": [],
        },
        "source": {
            "type": "official",
            "name": "Apple Support",
            "url": "https://support.apple.com/example?utm_source=test",
            "language": "en",
        },
    }


class TimeWindowTests(unittest.TestCase):
    def setUp(self):
        self.tz = ZoneInfo("Asia/Shanghai")
        self.run_at = datetime(2026, 9, 22, 9, 0, tzinfo=self.tz)

    def test_daily_targets_previous_calendar_day_with_overlap(self):
        window = research_plan.calculate_time_window("daily", self.run_at)
        self.assertTrue(window["period_start"].startswith("2026-09-21T00:00:00"))
        self.assertTrue(window["period_end"].startswith("2026-09-21T23:59:59"))
        self.assertTrue(window["query_start"].startswith("2026-09-20T00:00:00"))
        self.assertEqual(24, window["overlap_hours"])

        plan = research_plan.generate_plan("照片", "daily", self.run_at)
        self.assertEqual(window["run_id"], plan["run_id"])
        self.assertEqual(8, len(plan["vendors"]))
        self.assertIn("Apple", plan["vendors"])
        self.assertEqual("苹果", plan["vendors"]["Apple"]["display_name"])
        for vendor in plan["vendors"].values():
            self.assertTrue(vendor["display_name"])
            self.assertTrue(Path(vendor["icon_path"]).is_file())
        self.assertEqual(1, plan["vendors"]["Apple"]["base_sources"][0]["priority"])
        self.assertIn("2026", plan["vendors"]["Apple"]["search_keywords"][0])

    def test_weekly_targets_previous_monday_to_sunday(self):
        window = research_plan.calculate_time_window("weekly", self.run_at)
        self.assertTrue(window["period_start"].startswith("2026-09-14T00:00:00"))
        self.assertTrue(window["period_end"].startswith("2026-09-20T23:59:59"))
        self.assertTrue(window["query_start"].startswith("2026-09-12T00:00:00"))
        self.assertEqual(48, window["overlap_hours"])


class ChangelogStoreTests(unittest.TestCase):
    def test_upsert_creates_per_competitor_file_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            first = changelog_store.upsert_findings(
                [sample_finding()], output_dir, "run-1", "daily", "2026-09-22T09:00:00+08:00"
            )
            second = changelog_store.upsert_findings(
                [sample_finding()], output_dir, "run-2", "daily", "2026-09-23T09:00:00+08:00"
            )
            path = output_dir / "Apple_照片_changelog.jsonl"
            self.assertTrue(path.exists())
            self.assertEqual(1, first["added"])
            self.assertEqual(0, second["added"])
            self.assertEqual(1, second["updated"])
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(1, len(lines))
            record = json.loads(lines[0])
            self.assertEqual(["编辑", "AI 编辑", "消除"], record["feature"]["path"])
            self.assertEqual(2, record["tracking"]["seen_count"])
            self.assertNotIn("utm_source", record["source"]["url"])

    def test_invalid_feature_path_is_rejected(self):
        finding = sample_finding()
        finding["feature"]["path"] = []
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "feature.path"):
                changelog_store.upsert_findings(
                    [finding], Path(temp_dir), "run-1", "daily", "2026-09-22T09:00:00+08:00"
                )


if __name__ == "__main__":
    unittest.main()
