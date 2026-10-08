from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from create_study import create_study  # noqa: E402
from export_deliverables import export_deliverables  # noqa: E402
from import_voice_records import import_records  # noqa: E402
from voc_store import connect  # noqa: E402


def request() -> dict:
    return {
        "study_id": "gallery-ai-cleanup",
        "subject": "图库 AI 消除竞品反馈",
        "feature": {"name": "AI 消除", "aliases": ["路人消除", "对象移除"]},
        "competitors": [{"name": "Apple", "product": "Photos", "aliases": ["苹果相册"]}],
        "end_date": "2026-10-07",
        "start_date": "2024-10-07",
    }


def voice_records() -> list[dict]:
    return [
        {
            "platform": "weibo",
            "competitor": "Apple",
            "product": "Photos",
            "feature_path": ["编辑", "AI 消除"],
            "original_text": "AI 消除很方便，但复杂背景容易留下痕迹。",
            "source_url_raw": "https://weibo.com/1234567890/abc",
            "thread_url": "https://weibo.com/1234567890/abc",
            "address_type": "parent_thread",
            "source_comment_id": "wb-comment-1",
            "published_at": "2026-08-12T10:00:00+08:00",
            "author_handle": "测试用户A",
            "stance": "mixed",
            "theme": "复杂背景残留",
            "pain_point_tags": ["编辑瑕疵"],
        },
        {
            "platform": "xiaohongshu",
            "competitor": "Apple",
            "product": "Photos",
            "feature_path": ["编辑", "AI 消除"],
            "original_text": "旅行照片里路人终于能一键去掉了。",
            "source_url_raw": "https://www.xiaohongshu.com/explore/demo-note",
            "thread_url": "https://www.xiaohongshu.com/explore/demo-note",
            "address_type": "parent_thread",
            "source_comment_id": "xhs-comment-1",
            "published_at": "2026-07-01T09:00:00+08:00",
            "author_handle": "测试用户B",
            "stance": "positive",
            "theme": "旅行场景去路人",
            "scenario_tags": ["旅行拍照"],
        },
        {
            "platform": "coolapk",
            "competitor": "Apple",
            "product": "Photos",
            "feature_path": ["编辑", "AI 消除"],
            "original_text": "希望后续支持更复杂的边缘修复。",
            "source_url_raw": "https://www.coolapk.com/feed/123456",
            "thread_url": "https://www.coolapk.com/feed/123456",
            "address_type": "parent_thread",
            "source_comment_id": "coolapk-comment-1",
            "published_at": "2026-06-10T08:00:00+08:00",
            "author_handle": "测试用户C",
            "stance": "request",
            "theme": "边缘修复能力",
            "request_tags": ["边缘修复"],
        },
    ]


class VocSkillTests(unittest.TestCase):
    def test_request_platform_subset_limits_query_tasks(self):
        with tempfile.TemporaryDirectory() as directory:
            request_with_subset = request()
            request_with_subset["platforms"] = ["weibo", "xiaohongshu"]
            study = create_study(request_with_subset, Path(directory) / "social-voice.db")
            self.assertGreater(study["task_count"], 0)
            self.assertEqual({"weibo", "xiaohongshu"}, {task["platform"] for task in study["tasks"]})

    def test_end_to_end_exports_preserve_real_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path = root / "social-voice.db"
            study = create_study(request(), db_path)
            self.assertGreater(study["task_count"], 0)
            raw_path = root / "records.jsonl"
            raw_path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in voice_records()) + "\n", encoding="utf-8")
            result = import_records(db_path, study["study_id"], raw_path)
            self.assertEqual(3, result["imported"])

            outputs = export_deliverables(db_path, study["study_id"], root / "outputs")
            html_path = Path(outputs["html"])
            xlsx_path = Path(outputs["xlsx"])
            evidence_path = Path(outputs["evidence_pack"])
            self.assertTrue(html_path.is_file())
            self.assertTrue(xlsx_path.is_file())
            self.assertTrue(evidence_path.is_file())
            report = html_path.read_text(encoding="utf-8")
            self.assertIn("https://weibo.com/1234567890/abc", report)
            self.assertIn("旅行场景去路人", report)
            self.assertEqual(3, len(evidence_path.read_text(encoding="utf-8").splitlines()))
            with zipfile.ZipFile(xlsx_path) as workbook:
                names = workbook.namelist()
                self.assertIn("xl/workbook.xml", names)
                workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")
                self.assertIn("VOC汇总", workbook_xml)
                self.assertIn("用户原声_微博", workbook_xml)
                xml_payload = "".join(
                    workbook.read(name).decode("utf-8", errors="ignore")
                    for name in names
                    if name.endswith(".xml")
                )
                self.assertIn("https://weibo.com/1234567890/abc", xml_payload)

    def test_rejects_foreign_or_sensitive_source_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path = root / "social-voice.db"
            study = create_study(request(), db_path)
            invalid = voice_records()[0]
            invalid["source_url_raw"] = "https://example.com/comment"
            invalid_path = root / "invalid.jsonl"
            invalid_path.write_text(json.dumps(invalid, ensure_ascii=False) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match platform"):
                import_records(db_path, study["study_id"], invalid_path)

            sensitive = voice_records()[0]
            sensitive["source_url_raw"] = "https://weibo.com/1234567890/abc?access_token=secret"
            sensitive_path = root / "sensitive.jsonl"
            sensitive_path.write_text(json.dumps(sensitive, ensure_ascii=False) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "sensitive query parameter"):
                import_records(db_path, study["study_id"], sensitive_path)

    def test_import_does_not_persist_plain_author_handle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path = root / "social-voice.db"
            study = create_study(request(), db_path)
            raw_path = root / "records.jsonl"
            raw_path.write_text(json.dumps(voice_records()[0], ensure_ascii=False) + "\n", encoding="utf-8")
            import_records(db_path, study["study_id"], raw_path)
            conn = connect(db_path)
            try:
                row = conn.execute("SELECT author_hash FROM voice_records").fetchone()
                self.assertTrue(row["author_hash"])
                self.assertNotIn("测试用户A", row["author_hash"])
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()

