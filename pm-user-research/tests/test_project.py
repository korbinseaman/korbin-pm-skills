from __future__ import annotations

import json
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import unittest
import uuid
import zipfile
from collections import Counter
from contextlib import contextmanager
from unittest import mock
from pathlib import Path
from xml.sax.saxutils import escape


PROJECT = Path(__file__).resolve().parents[1]
SKILLS = {
    "ur-design-survey",
    "ur-generate-personas",
    "ur-user-simulator",
    "ur-synthesize-report",
}
EXAMPLE = PROJECT / "output" / "20260816手机相册云相册分相册控制需求调研"
QUESTIONNAIRE_DIR = EXAMPLE / "手机相册云相册分相册控制需求调研_Questionnaire"
QUESTIONNAIRE = QUESTIONNAIRE_DIR / "questionnaire.md"
PERSONAS = PROJECT / "output" / "personas_data" / "personas.json"
PERSONS_SUMMARY = PROJECT / "output" / "personas_data" / "persons_summary.html"
PERSONS_DIR = PROJECT / "output" / "personas_data" / "persons"
PERSONA_AUDIT = PROJECT / "output" / "personas_data" / "persona_audit.json"
MOCK_CONFIG = PROJECT / "tests" / "llm.mock.json"
RUNTIME = PROJECT / "tests" / ".runtime"


@contextmanager
def workspace_temp():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    path = RUNTIME / uuid.uuid4().hex
    path.mkdir()
    try:
        yield str(path)
    finally:
        shutil.rmtree(path, ignore_errors=True)


def run(*args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, *map(str, args)],
        cwd=PROJECT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        timeout=30,
    )
    if result.returncode != expect:
        raise AssertionError(
            f"command returned {result.returncode}, expected {expect}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


class SkillStructureTests(unittest.TestCase):
    def test_all_skill_packages_are_complete_and_utf8(self) -> None:
        for name in SKILLS:
            folder = PROJECT / "skills" / name
            self.assertTrue(folder.is_dir(), name)
            expected_dirs = {"agents", "references", "templates", "scripts"} if name == "ur-generate-personas" else {"agents", "rules", "references", "templates", "scripts"}
            self.assertTrue(expected_dirs.issubset({item.name for item in folder.iterdir() if item.is_dir()}))
            for path in folder.rglob("*"):
                if path.is_file() and path.suffix in {".md", ".yaml", ".py", ".json"}:
                    text = path.read_text(encoding="utf-8")
                    self.assertNotIn("�", text, f"replacement character in {path}")

    def test_frontmatter_has_only_name_and_description(self) -> None:
        for name in SKILLS:
            path = PROJECT / "skills" / name / "SKILL.md"
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"))
            frontmatter = text.split("---", 2)[1].strip().splitlines()
            keys = {line.split(":", 1)[0].strip() for line in frontmatter if ":" in line}
            self.assertEqual(keys, {"name", "description"}, path)
            self.assertIn(f"name: {name}", text)
            self.assertLess(len(text.splitlines()), 500)

    def test_skill_local_markdown_links_exist(self) -> None:
        link_pattern = re.compile(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)")
        for skill in SKILLS:
            for source in (PROJECT / "skills" / skill).rglob("*.md"):
                for target in link_pattern.findall(source.read_text(encoding="utf-8")):
                    if "://" in target:
                        continue
                    resolved = (source.parent / target).resolve()
                    self.assertTrue(resolved.exists(), f"broken link {target} in {source}")

    def test_openai_metadata_mentions_matching_skill(self) -> None:
        for name in SKILLS:
            text = (PROJECT / "skills" / name / "agents" / "openai.yaml").read_text(encoding="utf-8")
            self.assertIn(f"${name}", text)
            self.assertIn("display_name:", text)
            self.assertIn("short_description:", text)


class ScriptTests(unittest.TestCase):
    @staticmethod
    def _load_script(name: str, path: Path):
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise AssertionError(f"cannot load {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_openai_compatible_provider_payload(self) -> None:
        script = PROJECT / "skills" / "ur-user-simulator" / "scripts" / "run_simulation.py"
        spec = importlib.util.spec_from_file_location("ur_simulator_test_module", script)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        captured = {}

        def fake_post(url, headers, payload, timeout):
            captured.update({"url": url, "headers": headers, "payload": payload, "timeout": timeout})
            return {"choices": [{"message": {"content": '{"answers":{"Q1":"ok"}}'}}]}

        provider = {
            "name": "local-contract-test", "provider_type": "openai_compatible",
            "base_url": "https://example.invalid/v1", "model": "test-model",
            "api_key_env": "TEST_LLM_KEY", "json_mode": True,
            "max_tokens_field": "max_completion_tokens", "extra_headers": {},
        }
        with mock.patch.dict(os.environ, {"TEST_LLM_KEY": "secret-for-contract-test"}), mock.patch.object(module, "post_json", fake_post):
            result = module.call_provider(provider, "system", "user", {"temperature": 0.2, "max_output_tokens": 321, "timeout_seconds": 9})
        self.assertEqual(result, '{"answers":{"Q1":"ok"}}')
        self.assertEqual(captured["url"], "https://example.invalid/v1/chat/completions")
        self.assertEqual(captured["payload"]["model"], "test-model")
        self.assertEqual(captured["payload"]["max_completion_tokens"], 321)
        self.assertEqual(captured["payload"]["response_format"], {"type": "json_object"})
        self.assertEqual(captured["headers"]["Authorization"], "Bearer secret-for-contract-test")

    def test_mainstream_provider_presets_only_require_model_and_key(self) -> None:
        module = self._load_script(
            "ur_simulator_provider_presets",
            PROJECT / "skills" / "ur-user-simulator" / "scripts" / "run_simulation.py",
        )
        config = module.load_config(PROJECT / "config" / "llm.example.yaml")
        providers = {item["name"]: item for item in config["providers"] if item["provider_type"] != "mock"}
        self.assertEqual({name: item["base_url"] for name, item in providers.items()}, {
            "deepseek": "https://api.deepseek.com",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
            "kimi": "https://api.moonshot.cn/v1",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "minimax": "https://api.minimaxi.com/v1",
            "openai": "https://api.openai.com/v1",
        })
        self.assertTrue(all(item["enabled"] is True for item in providers.values()))
        self.assertEqual(len({item["api_key_env"] for item in providers.values()}), 6)
        self.assertTrue(all(item["model"] == "" for item in providers.values()))
        self.assertLessEqual(len((PROJECT / "config" / "llm.example.yaml").read_text(encoding="utf-8").splitlines()), 7)
        ready, reason = module.provider_ready(providers["deepseek"])
        self.assertFalse(ready)
        self.assertIn("model ID", reason)
        configured = dict(providers["deepseek"], model="account-model-id")
        with mock.patch.dict(os.environ, {configured["api_key_env"]: "test-key"}):
            self.assertEqual(module.provider_ready(configured), (True, None))

    def test_example_persona_audit(self) -> None:
        run(
            PROJECT / "skills" / "ur-generate-personas" / "scripts" / "validate_personas.py",
            PERSONAS,
        )

    def test_persona_name_matches_birth_cohort(self) -> None:
        script = PROJECT / "skills" / "ur-generate-personas" / "scripts" / "validate_personas.py"
        spec = importlib.util.spec_from_file_location("validate_personas", script)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self.assertIsNotNone(module.name_age_conflict("王梓轩", 60))
        self.assertIsNotNone(module.name_age_conflict("李建国", 20))
        self.assertIsNone(module.name_age_conflict("程国华", 62))
        self.assertIsNone(module.name_age_conflict("林晨", 20))
        self.assertIsNone(module.name_age_conflict("欧阳昊泽", 21))

    def test_persona_name_batch_has_natural_structure_mix(self) -> None:
        personas = json.loads(PERSONAS.read_text(encoding="utf-8"))
        people = personas["personas"]
        counts = Counter(len(persona["姓名"]) for persona in people)
        self.assertEqual(counts, Counter({3: 75, 2: 23, 4: 2}))
        self.assertEqual(
            personas["generation_spec"]["name_structure_allocation"],
            {"2字全名": 23, "3字全名": 75, "4字全名": 2},
        )
        self.assertEqual(len({persona["姓名"] for persona in people}), len(people))
        for low, high in ((18, 24), (25, 34), (35, 44), (45, 54), (55, 64), (65, 80)):
            lengths = {len(persona["姓名"]) for persona in people if low <= persona["年龄"] <= high}
            self.assertGreaterEqual(len(lengths), 2, f"{low}–{high}岁姓名长度过于整齐")

    def test_persona_generation_uses_direct_input_contract(self) -> None:
        folder = PROJECT / "skills" / "ur-generate-personas"
        skill = (folder / "SKILL.md").read_text(encoding="utf-8")
        input_contract = (folder / "references" / "persona-generation-input.md").read_text(encoding="utf-8")
        self.assertIn("直接读取用户或调用方提供的参数", skill)
        self.assertIn("课题或全量候选用户群体缺失时由本 Skill 直接询问", skill)
        self.assertIn("不得读取其他用户研究 Skill 的任务文件或对话", skill)
        self.assertIn("课题和受众范围只来自本次", (folder / "references" / "io-contract.md").read_text(encoding="utf-8"))
        self.assertIn("不保存为任务级共享文件", input_contract)
        self.assertNotIn("shared_context.md", skill + input_contract)
        self.assertFalse((PROJECT / "skills" / "ur-design-survey" / "references" / "shared-context-schema.md").exists())
        self.assertFalse((PROJECT / "skills" / "ur-design-survey" / "scripts" / "validate_shared_context.py").exists())
        self.assertFalse((folder / "references" / "user_personas_input.md").exists())

    def test_survey_simulation_keeps_answers_only_in_temporary_workdir(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            sim_dir = root / "survey_response_data"
            run_id = f"test-{root.name}"
            result = run(
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "run_simulation.py",
                "--questionnaire", QUESTIONNAIRE,
                "--persons-summary", PERSONS_SUMMARY,
                "--persons-dir", PERSONS_DIR,
                "--config", MOCK_CONFIG, "--output-dir", sim_dir,
                "--run-id", run_id, "--max-retries", "0",
            )
            payload = json.loads(result.stdout)
            working_answers_dir = Path(payload["working_answers_dir"])
            quality_report = sim_dir / f"quality_report_{run_id}.md"
            expected_ids = sorted(path.name.split("_", 1)[0] for path in PERSONS_DIR.glob("P*.txt"))
            self.assertEqual(payload["completed"], len(expected_ids))
            self.assertEqual(payload["failed"], 0)
            self.assertIn(payload["data_integrity"], {"excellent", "good"})
            self.assertEqual(
                sorted(path.name for path in working_answers_dir.glob("*.md")),
                [f"{user_id}.md" for user_id in expected_ids],
            )
            self.assertEqual(set(sim_dir.iterdir()), {quality_report})
            self.assertFalse(any(path.name.startswith("answers_") for path in sim_dir.iterdir()))
            answer_text = (working_answers_dir / "P001.md").read_text(encoding="utf-8")
            self.assertIn("用户ID：P001", answer_text)
            self.assertIn(f"问卷来源：{QUESTIONNAIRE.resolve()}", answer_text)
            self.assertRegex(answer_text, r"(?m)^### Q1$")
            self.assertNotIn("过去 3 个月", answer_text)
            run(
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "native_simulation.py",
                "cleanup", "--working-answers-dir", working_answers_dir,
            )
            self.assertFalse(working_answers_dir.exists())

class SimulatorContractTests(unittest.TestCase):
    def _inputs(self, root: Path, count: int = 2) -> tuple[Path, Path, Path]:
        questionnaire = root / "questionnaire.md"
        questionnaire.write_text(
            "# 契约测试问卷\n\n## Q1 ｜ 单选\n是否使用过？\n\n- 是\n- 否\n\n"
            "## Q2 ｜ 开放文本\n请简要说明。\n",
            encoding="utf-8",
        )
        user_ids = [f"P{index:03d}" for index in range(1, count + 1)]
        summary = root / "persons_summary.txt"
        summary.write_text(
            f"画像总数：{count}人\n全量用户ID：{json.dumps(user_ids, ensure_ascii=False)}\n",
            encoding="utf-8",
        )
        persons_dir = root / "persons"
        persons_dir.mkdir()
        for index, user_id in enumerate(user_ids, start=1):
            (persons_dir / f"{user_id}_测试用户{index}.txt").write_text(
                f"画像编号：{user_id}\n姓名：测试用户{index}\n年龄：{20 + index}\n职业：职员\n",
                encoding="utf-8",
            )
        return questionnaire, summary, persons_dir

    def test_runner_reads_questionnaire_summary_and_person_files(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            questionnaire, summary, persons_dir = self._inputs(root)
            run_id = f"contract-{root.name}"
            result = run(
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "run_simulation.py",
                "--questionnaire", questionnaire,
                "--persons-summary", summary,
                "--persons-dir", persons_dir,
                "--config", MOCK_CONFIG, "--output-dir", root / "results", "--run-id", run_id,
            )
            payload = json.loads(result.stdout)
            working_answers_dir = Path(payload["working_answers_dir"])
            self.assertEqual(payload["completed"], 2)
            self.assertTrue((working_answers_dir / "P001.md").exists())
            self.assertEqual(
                set((root / "results").iterdir()),
                {root / "results" / f"quality_report_{run_id}.md"},
            )
            self.assertFalse(list((root / "results").glob("*.json")))
            run(
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "native_simulation.py",
                "cleanup", "--working-answers-dir", working_answers_dir,
            )

    def test_runner_rejects_summary_count_mismatch(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            questionnaire, summary, persons_dir = self._inputs(root)
            summary.write_text('画像总数：3人\n全量用户ID：["P001", "P002"]\n', encoding="utf-8")
            result = run(
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "run_simulation.py",
                "--questionnaire", questionnaire,
                "--persons-summary", summary,
                "--persons-dir", persons_dir,
                "--config", MOCK_CONFIG, "--output-dir", root / "results", expect=2,
            )
            self.assertIn("画像总数为 3，但全量用户ID 有 2 个", result.stderr)
            self.assertFalse((root / "results").exists())

    def test_runner_rejects_missing_persona_file(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            questionnaire, summary, persons_dir = self._inputs(root)
            (persons_dir / "P002_测试用户2.txt").unlink()
            result = run(
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "run_simulation.py",
                "--questionnaire", questionnaire,
                "--persons-summary", summary,
                "--persons-dir", persons_dir,
                "--config", MOCK_CONFIG, "--output-dir", root / "results", expect=2,
            )
            self.assertIn("应恰好对应一个画像文件", result.stderr)
            self.assertFalse((root / "results").exists())

    def test_empty_custom_config_requests_current_model_fallback(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            questionnaire, summary, persons_dir = self._inputs(root)
            result = run(
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "run_simulation.py",
                "--questionnaire", questionnaire,
                "--persons-summary", summary,
                "--persons-dir", persons_dir,
                "--config", PROJECT / "config" / "llm.example.yaml",
                "--output-dir", root / "results", expect=3,
            )
            self.assertEqual(json.loads(result.stdout)["status"], "fallback_current_model")
            self.assertFalse((root / "results").exists())

    def test_current_model_tasks_prepare_and_finalize(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            questionnaire, summary, persons_dir = self._inputs(root)
            run_id = f"current-{root.name}"
            prepared = run(
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "native_simulation.py",
                "prepare", "--questionnaire", questionnaire,
                "--persons-summary", summary, "--persons-dir", persons_dir,
                "--run-id", run_id,
            )
            manifest = json.loads(prepared.stdout)
            working_answers_dir = Path(manifest["working_answers_dir"])
            self.assertEqual([task["model"] for task in manifest["tasks"]], ["current-model", "current-model"])
            self.assertFalse((root / "results").exists())
            validator = ScriptTests._load_script(
                "ur_native_contract_validator",
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "validate_responses.py",
            )
            questions = validator.parse_questionnaire(questionnaire)
            for task in manifest["tasks"]:
                user_id = task["user_id"]
                persona = validator.parse_persona(Path(task["persona_path"]), user_id)
                validator.write_answer_markdown(
                    Path(task["output_path"]), run_id=run_id, user_id=user_id,
                    persona=persona, questionnaire_path=questionnaire,
                    provider="native-agent", model="current-model", questions=questions,
                    result={"answers": {"Q1": "是", "Q2": "合成回答"}, "answer_notes": {}},
                )
            finalized = run(
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "native_simulation.py",
                "finalize", "--questionnaire", questionnaire,
                "--persons-summary", summary, "--persons-dir", persons_dir,
                "--working-answers-dir", working_answers_dir,
                "--quality-report", root / "results" / f"quality_report_{run_id}.md",
                "--run-id", run_id,
            )
            payload = json.loads(finalized.stdout)
            self.assertEqual(payload["completed"], 2)
            self.assertTrue((root / "results" / f"quality_report_{run_id}.md").exists())
            cleaned = run(
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "native_simulation.py",
                "cleanup", "--working-answers-dir", working_answers_dir,
            )
            self.assertTrue(json.loads(cleaned.stdout)["removed"])
            self.assertFalse(working_answers_dir.exists())

    def test_current_model_tasks_record_known_model_id(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            questionnaire, summary, persons_dir = self._inputs(root, count=1)
            run_id = f"known-{root.name}"
            result = run(
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "native_simulation.py",
                "prepare", "--questionnaire", questionnaire,
                "--persons-summary", summary, "--persons-dir", persons_dir,
                "--model-label", "known-current-model", "--run-id", run_id,
            )
            manifest = json.loads(result.stdout)
            self.assertEqual(manifest["tasks"][0]["model"], "known-current-model")
            run(
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "native_simulation.py",
                "cleanup", "--working-answers-dir", manifest["working_answers_dir"],
            )

    def test_cleanup_rejects_non_simulator_temp_directory(self) -> None:
        with workspace_temp() as temp:
            protected = Path(temp) / "answers"
            protected.mkdir()
            marker = protected / "keep.txt"
            marker.write_text("keep", encoding="utf-8")
            result = run(
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "native_simulation.py",
                "cleanup", "--working-answers-dir", protected, expect=2,
            )
            self.assertIn("拒绝清理临时根目录以外的路径", result.stderr)
            self.assertTrue(marker.exists())


class SynthesizeReportContractTests(unittest.TestCase):
    @staticmethod
    def _write_xlsx(path: Path, headers: list[str], rows: list[list[object]]) -> None:
        def cell(reference: str, value: object) -> str:
            if value is None:
                return ""
            if isinstance(value, (int, float)):
                return f'<c r="{reference}"><v>{value}</v></c>'
            return f'<c r="{reference}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'

        def column_name(index: int) -> str:
            result = ""
            while index:
                index, remainder = divmod(index - 1, 26)
                result = chr(65 + remainder) + result
            return result

        sheet_rows = []
        for row_number, values in enumerate([headers, *rows], start=1):
            cells = "".join(cell(f"{column_name(index)}{row_number}", value) for index, value in enumerate(values, start=1))
            sheet_rows.append(f'<row r="{row_number}">{cells}</row>')
        content_types = '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>'
        root_rels = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
        workbook = '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="问卷回答" sheetId="1" r:id="rId1"/></sheets></workbook>'
        workbook_rels = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
        worksheet = '<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + "".join(sheet_rows) + '</sheetData></worksheet>'
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("[Content_Types].xml", content_types)
            archive.writestr("_rels/.rels", root_rels)
            archive.writestr("xl/workbook.xml", workbook)
            archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
            archive.writestr("xl/worksheets/sheet1.xml", worksheet)

    def _inputs(self, root: Path) -> dict[str, Path]:
        questionnaire = root / "questionnaire.md"
        questionnaire_text = QUESTIONNAIRE.read_text(encoding="utf-8")
        questionnaire.write_text(questionnaire_text, encoding="utf-8")
        design_doc = root / "survey-design-desc.html"
        design_doc.write_text(
            '<!doctype html><html lang="zh-CN"><body>'
            '<span data-field="decision">决定是否继续验证测试方案</span>'
            '<span data-field="target-audience">近期使用过相关功能的用户</span>'
            '<section id="research-goals">'
            '<article data-goal-id="G1" data-question-ids="Q1–Q4"><p data-field="goal-statement">判断近期行为是否存在</p></article>'
            '<article data-goal-id="G2" data-question-ids="Q5,Q6"><p data-field="goal-statement">识别主要问题与后果</p></article>'
            '</section><section id="analysis-advice"><ul><li>联读行为题与问题题</li></ul></section>'
            f'<section id="questionnaire-appendix"><pre>{escape(questionnaire_text)}</pre></section>'
            '</body></html>',
            encoding="utf-8",
        )
        run_id = "contract-run"
        question_ids = re.findall(r"(?m)^##\s+(Q[A-Za-z0-9_.-]+)\s*[｜|]", questionnaire_text)
        headers = ["任务ID", "用户ID", "姓名", "实际模型", "状态", "Q1", "Q1_回答原因", *question_ids[1:], "错误摘要"]
        completed = [f"{run_id}-P001", "P001", "测试用户", "current-model", "completed", "使用过", "用于测试的回答原因", *([None] * (len(question_ids) - 1)), None]
        second = [f"{run_id}-P002", "P002", "测试用户2", "current-model", "completed", "没有使用过", None, *([None] * (len(question_ids) - 1)), None]
        responses = root / f"survey_responses_{run_id}.xlsx"
        self._write_xlsx(responses, headers, [completed, second])
        persons_summary = root / "persons_summary.txt"
        persons_summary.write_text("调研课题：测试问卷\n画像总数：2人\n- 样本按预设构建分布生成\n", encoding="utf-8")
        return {"questionnaire": questionnaire, "design": design_doc, "responses": responses, "persons_summary": persons_summary}

    def test_report_preparation_consumes_current_skill_outputs(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            paths = self._inputs(root)
            report_dir = root / "report_contract-run"
            run(
                PROJECT / "skills" / "ur-synthesize-report" / "scripts" / "generate_report.py",
                "--questionnaire", paths["questionnaire"],
                "--design-doc", paths["design"], "--responses", paths["responses"],
                "--persons-summary", paths["persons_summary"],
                "--output-dir", report_dir, "--prepare-only",
            )
            analysis = json.loads((report_dir / "analysis_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(analysis["schema_version"], "2.0")
            self.assertEqual(analysis["run_id"], "contract-run")
            self.assertEqual(analysis["data_source"], "synthetic")
            self.assertEqual(analysis["sample"]["total"], 2)
            self.assertEqual(analysis["sample"]["analyzable"], 2)
            self.assertEqual(analysis["descriptive_results"][0]["distribution"][0]["label"], "使用过")
            self.assertIn("P001:Q1:reason", {item["evidence_id"] for item in analysis["qualitative_observations"]})
            self.assertEqual(analysis["sample_construction"]["declared_sample_size"], 2)
            self.assertEqual(analysis["research_context"]["decision"], "决定是否继续验证测试方案")
            self.assertEqual(analysis["research_context"]["target_audience"], "近期使用过相关功能的用户")
            self.assertEqual([item["id"] for item in analysis["research_context"]["research_goals"]], ["G1", "G2"])
            self.assertEqual(analysis["research_context"]["research_goals"][0]["question_ids"], ["Q1", "Q2", "Q3", "Q4"])
            self.assertEqual(analysis["research_context"]["analysis_advice"], ["联读行为题与问题题"])

            run(
                PROJECT / "skills" / "ur-synthesize-report" / "scripts" / "generate_report.py",
                "--questionnaire", paths["questionnaire"],
                "--design-doc", paths["design"], "--responses", paths["responses"],
                "--analysis", report_dir / "analysis_summary.json", "--output-dir", report_dir,
            )
            report = (report_dir / "report.html").read_text(encoding="utf-8")
            self.assertIn("contract-run", report)
            self.assertIn("样本构成说明", report)
            self.assertIn('id="filter-question"', report)
            self.assertIn('id="save-report"', report)
            self.assertIn('id="download-png"', report)
            self.assertNotIn("<h2>证据索引</h2>", report)
            self.assertNotRegex(report, r'(?:src|href)=["\']https?://')
            self.assertTrue((report_dir / "report_quality.md").exists())

    def test_report_rejects_duplicate_question_id(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            paths = self._inputs(root)
            paths["questionnaire"].write_text(
                paths["questionnaire"].read_text(encoding="utf-8") + "\n## Q1 ｜ 单选\n\n重复题目？\n\n- 是\n- 否\n",
                encoding="utf-8",
            )
            result = run(
                PROJECT / "skills" / "ur-synthesize-report" / "scripts" / "generate_report.py",
                "--questionnaire", paths["questionnaire"],
                "--design-doc", paths["design"], "--responses", paths["responses"],
                "--output-dir", root / "report_contract-run", "--prepare-only", expect=2,
            )
            self.assertIn("重复题号", result.stderr)

    def test_report_excludes_structurally_invalid_completed_response(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            paths = self._inputs(root)
            question_ids = re.findall(r"(?m)^##\s+(Q[A-Za-z0-9_.-]+)\s*[｜|]", paths["questionnaire"].read_text(encoding="utf-8"))
            headers = ["任务ID", "用户ID", "姓名", "实际模型", "状态", "Q1", *question_ids[1:], "错误摘要"]
            row = ["contract-run-P001", "P001", "测试用户", "current-model", "completed", "问卷外选项", *([None] * (len(question_ids) - 1)), None]
            self._write_xlsx(paths["responses"], headers, [row])
            report_dir = root / "report_contract-run"
            run(
                PROJECT / "skills" / "ur-synthesize-report" / "scripts" / "generate_report.py",
                "--questionnaire", paths["questionnaire"],
                "--design-doc", paths["design"], "--responses", paths["responses"],
                "--output-dir", report_dir, "--prepare-only",
            )
            analysis = json.loads((report_dir / "analysis_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(analysis["sample"]["completed"], 1)
            self.assertEqual(analysis["sample"]["analyzable"], 0)
            self.assertEqual(analysis["data_cleaning"]["excluded_count"], 1)
            self.assertIn("单选答案不在问卷选项中", analysis["data_cleaning"]["excluded_records"][0]["reason"])

    def test_report_excludes_response_that_breaks_question_logic(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            paths = self._inputs(root)
            question_ids = re.findall(r"(?m)^##\s+(Q[A-Za-z0-9_.-]+)\s*[｜|]", paths["questionnaire"].read_text(encoding="utf-8"))
            headers = ["任务ID", "用户ID", "姓名", "实际模型", "状态", *question_ids, "错误摘要"]
            answers = {"Q1": "没有使用过", "Q2": "iPhone/iOS"}
            row = ["contract-run-P001", "P001", "测试用户", "current-model", "completed", *(answers.get(qid) for qid in question_ids), None]
            self._write_xlsx(paths["responses"], headers, [row])
            report_dir = root / "report_contract-run"
            run(
                PROJECT / "skills" / "ur-synthesize-report" / "scripts" / "generate_report.py",
                "--questionnaire", paths["questionnaire"],
                "--design-doc", paths["design"], "--responses", paths["responses"],
                "--output-dir", report_dir, "--prepare-only",
            )
            analysis = json.loads((report_dir / "analysis_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(analysis["sample"]["analyzable"], 0)
            self.assertIn("触发结束答题后仍回答 Q2", analysis["data_cleaning"]["excluded_records"][0]["reason"])

    def test_scale_summary_includes_standard_deviation(self) -> None:
        script = PROJECT / "skills" / "ur-synthesize-report" / "scripts" / "generate_report.py"
        spec = importlib.util.spec_from_file_location("ur_synthesize_report_test_module", script)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        summary = module.distribution_for({"type": "likert_scale", "options": []}, [("P001", 2), ("P002", 4)])
        self.assertEqual(summary["numeric_summary"]["mean"], 3.0)
        self.assertEqual(summary["numeric_summary"]["standard_deviation"], 1.41)


class WorkflowTests(unittest.TestCase):
    def test_workflow_skill_composition(self) -> None:
        expected = {
            "survey-design.md": {"ur-design-survey"},
            "synthetic-survey.md": SKILLS,
        }
        for filename, wanted in expected.items():
            text = (PROJECT / "commands" / filename).read_text(encoding="utf-8")
            found = set(re.findall(r"\$?(ur-(?:design-survey|generate-personas|user-simulator|synthesize-report))", text))
            self.assertEqual(found, wanted, filename)
            self.assertIn("<WORK_DIR>/用户调研/<YYYYMMDD><课题>", text)
            self.assertNotIn("<课题>_Questionnaire", text)

    def test_synthetic_survey_reuses_sufficient_personas(self) -> None:
        text = (PROJECT / "commands" / "synthetic-survey.md").read_text(encoding="utf-8")
        self.assertIn("M >= N", text)
        self.assertIn("跳过 `$ur-generate-personas`", text)
        self.assertIn("M < N", text)
        self.assertIn("按 `N` 生成足量画像", text)
        self.assertIn("未指定 `N`", text)
        self.assertIn("本次选定的 `N` 人清单", text)

    def test_plan_skill_contains_domain_core_and_substantive_resources(self) -> None:
        folder = PROJECT / "skills" / "ur-design-survey"
        skill = (folder / "SKILL.md").read_text(encoding="utf-8")
        for section in ("## 输入契约", "## 工作流程", "## 输出契约", "## 交付给用户"):
            self.assertIn(section, skill)
        self.assertNotIn("## 优化现有问卷", skill)
        self.assertLess(skill.index("## 工作流程"), skill.index("## 输出契约"))
        self.assertLessEqual(len(skill.splitlines()), 220)
        invocation = skill.index("## 何时调用")
        input_contract = skill.index("## 输入契约")
        self.assertLess(invocation, input_contract)
        self.assertIn("新建定量问卷", skill)
        self.assertIn("正向触发关键词", skill)
        self.assertIn("场景识别词", skill)
        self.assertIn("不是新增问卷场景", skill)
        for canonical, aliases in (
            ("原始需求洞察", ("原始需求洞察", "需求洞察")),
            ("关键假设验证", ("关键假设验证", "假设验证", "概念测试")),
            ("产品方案选择", ("产品方案选择", "方案选择", "方案对比")),
            ("满意度调查", ("满意度调查", "满意度问卷")),
        ):
            mapping_line = next(line for line in skill.splitlines() if line.startswith(f"  - {canonical}："))
            for alias in aliases:
                self.assertIn(f"`{alias}`", mapping_line)
        self.assertNotIn("questionnaire.json", skill)
        self.assertNotIn("plan.json", skill)
        self.assertNotIn("survey.status", skill)
        for required_input in ("课题描述", "调研目标", "问卷场景"):
            self.assertIn(required_input, skill)
        for scenario in ("原始需求洞察", "关键假设验证", "产品方案选择", "满意度调查"):
            self.assertIn(scenario, skill)
        step_headings = list(re.finditer(r"(?m)^### ([1-6])\. ", skill))
        self.assertEqual([match.group(1) for match in step_headings], [str(i) for i in range(1, 7)])
        for index, match in enumerate(step_headings):
            end = step_headings[index + 1].start() if index + 1 < len(step_headings) else skill.index("## 输出契约")
            step = skill[match.start():end]
            for marker in ("**输入**", "**处理**", "**输出**"):
                self.assertIn(marker, step, f"Step {match.group(1)} missing {marker}")
        step_1 = skill.index("### 1. 补齐输入并确认研究方向")
        first_card = skill.index("#### 用户研究设计确认卡")
        step_2 = skill.index("### 2. 建立研究设计与目标—证据清单")
        self.assertLess(step_1, first_card)
        self.assertLess(first_card, step_2)
        self.assertLess(first_card, skill.index("## 输出契约"))
        self.assertIn("用户选择“全部采用推荐”、逐字段选项或直接输入内容后，才进入 Step 2", skill)
        self.assertIn("确认卡是可选择的研究方案，不是让用户补写的空表", skill)
        self.assertIn("references/confirmation-card.md", skill)
        self.assertIn("不得输出空白字段、占位符或泛化示例", skill)
        self.assertIn("#### Step 1 信息字段", skill)
        self.assertIn("| 字段 | 完整性要求 | 描述 | 示例 | 确认卡候选内容 |", skill)
        self.assertNotIn("| 字段 | 完整性要求 | 描述 | 示例 | 参考 |", skill)
        for field in (
            "产品决策",
            "目标用户",
            "待验证方案/概念材料",
        ):
            self.assertIn(f"| {field} |", skill)
        for removed_field in ("产品阶段", "已有材料", "是否筛选目标用户", "筛选条件", "关键假设", "实施约束"):
            self.assertNotIn(f"| {removed_field} |", skill)
        self.assertIn("| 课题描述 | 必选 |", skill)
        self.assertIn("必选字段为课题描述、调研目标、问卷场景", skill)
        self.assertIn("可选字段为产品决策、目标用户、待验证方案/概念材料", skill)
        self.assertIn("不得添加其他字段", skill)
        self.assertIn("传给 Step 2 的已确认研究输入摘要", skill)
        self.assertIn("不得添加其他字段或生成任务级共享上下文文件", skill)
        self.assertNotIn("references/shared-context-schema.md", skill)
        self.assertIn("**输入**：Step 1 的已确认研究输入摘要：必选为课题描述、调研目标、问卷场景；可选为产品决策、目标用户、待验证方案/概念材料。", skill)
        self.assertIn("目标用户有内容时，直接作为用户筛选模块的输入", skill)
        self.assertIn("不再单独询问“是否筛选”或拆分筛选条件", skill)
        self.assertIn("每个展示字段提供 2–3 个互斥的具体内容选项", skill)
        self.assertIn("允许用户直接输入", skill)
        self.assertIn("不得编造方案或用户事实", skill)
        self.assertIn("#### 问卷场景的确认条件", skill)
        self.assertIn("#### 返回确认卡的时机", skill)
        self.assertIn("先返回补充问题，不同时返回确认卡", skill)
        self.assertIn("在当前回复立即返回确认卡", skill)
        self.assertIn("必须更新并重新返回确认卡", skill)
        self.assertIn("未获得用户明确确认，不得进入 Step 2", skill)
        self.assertIn("涉及新方案时", skill)
        self.assertIn("至少两个信息对称且可比较的方案", skill)
        self.assertIn("| 目标 | 需要判断 | 优先证据 | 决策用途 |", skill)
        self.assertIn("#### 题目数量", skill)
        self.assertIn("#### 题型数量分布", skill)
        self.assertIn("#### 用户研究设计确认卡", skill)
        self.assertIn("问卷标题", skill)
        self.assertIn("问卷描述", skill)
        self.assertIn("原样保留 Step 1 的课题描述、调研目标、问卷场景及已有可选字段", skill)
        self.assertIn("**输入**：Step 2 的完整研究设计包，包括课题描述、调研目标、问卷场景", skill)
        self.assertIn("人口特征为必选模块", skill)
        self.assertIn("默认 3 题：性别、年龄、当前使用的手机品牌", skill)
        self.assertIn("| 问卷场景 | 推荐模块顺序 |", skill)
        self.assertNotIn("| 问卷场景 | 结构示例 | 推荐模块顺序 |", skill)
        self.assertIn("人口特征 → 用户筛选（按需）→ 近期真实行为 → 问题、后果与当前应对", skill)
        self.assertIn("概念测试 → 使用意愿与采用条件", skill)
        self.assertIn("概念测试 → 优先级与方案取舍", skill)
        self.assertIn("用户筛选（按需）→ 满意度诊断", skill)
        self.assertIn("模块顺序、模块目标、对应证据、题目数量、选用理由及出现条件", skill)
        self.assertIn("研究对象是产品整体、既有功能/能力、新概念还是多个方案", skill)
        self.assertIn("不得用母产品的使用行为替代具体功能的使用证据", skill)
        self.assertIn("每道题先定义测量卡", skill)
        self.assertIn("可独立开发或取舍的功能不得合并为一个选项", skill)
        self.assertIn("普通用户能立即理解的简短动宾短语", skill)
        self.assertIn("题干必须独立说明研究对象和所问事件", skill)
        self.assertIn("原始需求洞察且用户未限制题量时，再补充触发情景或期待结果", skill)
        self.assertIn("未指定上限时不设硬性题数", skill)
        self.assertIn("默认保存到 `<WORK_DIR>/用户调研/<YYYYMMDD><课题>/`", skill)
        self.assertNotIn("<课题>_Questionnaire", skill)
        self.assertIn("未用用户不评价体验", skill)
        self.assertIn("题数合计必须等于全卷计划总题数", skill)
        self.assertIn("未选模块不写入", skill)
        self.assertIn("Step 3 传来的完整研究设计包和模块蓝图", skill)
        output_contract = skill[skill.index("## 输出契约"):]
        self.assertIn("### 问卷模板引用规格", output_contract)
        self.assertIn("| 问卷场景 | 必须引用的问卷模板 | 继承的结构 |", output_contract)
        for scenario, template_name in (
            ("原始需求洞察", "questionnaire-original-needs-discovery.md"),
            ("关键假设验证", "questionnaire-key-hypothesis-validation.md"),
            ("产品方案选择", "questionnaire-solution-selection.md"),
            ("满意度调查", "questionnaire-satisfaction-survey.md"),
        ):
            self.assertRegex(output_contract, rf"\| {scenario} \| .*{re.escape(template_name)}")
        self.assertIn("每次只引用与问卷场景对应的一份模板", output_contract)
        self.assertIn("偏离模板时在 `survey-design-desc.html` 记录理由", output_contract)
        self.assertIn("#### 核心设计规格", skill)
        for example in (
            "questionnaire-original-needs-discovery.md",
            "questionnaire-key-hypothesis-validation.md",
            "questionnaire-solution-selection.md",
            "questionnaire-satisfaction-survey.md",
        ):
            self.assertIn(f"templates/{example}", skill)
        self.assertIn("不拼接其他场景模板", skill)
        expected = {
            "references/question-design-standards.md",
            "references/survey-patterns.md",
            "references/questionnaire-logic-checklist.md",
            "references/confirmation-card.md",
            "references/simulator-questionnaire-format.md",
            "references/userclub-import-format.md",
            "references/wenjuanxing-import-format.md",
            "templates/questionnaire-key-hypothesis-validation.md",
            "templates/questionnaire-original-needs-discovery.md",
            "templates/questionnaire-solution-selection.md",
            "templates/questionnaire-satisfaction-survey.md",
            "templates/survey-design-desc.html",
        }
        self.assertTrue(all((folder / item).exists() for item in expected))
        self.assertFalse((folder / "references" / "output-schema.md").exists())
        self.assertFalse((folder / "templates" / "plan.json").exists())
        self.assertFalse((folder / "scripts" / "validate_plan.py").exists())
        self.assertFalse((folder / "scripts" / "validate_questionnaire_pair.py").exists())
        for item in expected:
            self.assertGreater(len((folder / item).read_text(encoding="utf-8").splitlines()), 12, item)
        actual_resources = {
            str(path.relative_to(folder)).replace("\\", "/")
            for group in ("rules", "references", "templates")
            for pattern in ("*.md", "*.html")
            for path in (folder / group).glob(pattern)
        }
        self.assertEqual(actual_resources, expected)
        card = (folder / "references" / "confirmation-card.md").read_text(encoding="utf-8")
        for marker in (
            "| 字段 | 推荐内容 | 选项 |", "### 请确认",
            "必选字段固定展示；可选字段已有内容", "缺失且不影响研究时不占行",
            "2–3 个互斥的预设内容选项", "（推荐）", "自定义",
            "全部采用推荐", "字段=选项字母", "字段=自定义：具体内容", "重新设计研究思路",
        ):
            self.assertIn(marker, card)
        self.assertNotIn("| 字段 | 已确认内容 | 来源 |", skill)
        patterns = (folder / "references" / "survey-patterns.md").read_text(encoding="utf-8")
        self.assertNotIn("### 用户分层变量", patterns)
        for module in (
            "## 人口特征（必选）", "## 用户筛选", "## 近期真实行为", "## 问题、后果与当前应对",
            "## 概念测试", "## 使用意愿与采用条件", "## 优先级与方案取舍", "## 满意度诊断", "## 开放补充",
        ):
            self.assertIn(module, patterns)
        module_sections = re.split(r"(?m)^## ", patterns)[2:]
        for section in module_sections:
            if section.startswith("问卷场景与模块组合"):
                continue
            self.assertGreaterEqual(len(re.findall(r"Q(?:\d+|x)【", section)), 3, section.splitlines()[0])
        for question in ("您的性别是？", "您的年龄是？", "您当前主要使用的手机品牌是？"):
            self.assertIn(question, patterns)
        gender_block = re.search(r"Q1【单选题】（必填）您的性别是？(?P<body>.*?)Q2【", patterns, re.S)
        self.assertIsNotNone(gender_block)
        self.assertEqual(re.findall(r"(?m)^- (.+)$", gender_block.group("body")), ["男", "女", "不愿透露"])
        brand_block = re.search(r"Q3【单选题】（必填）您当前主要使用的手机品牌是？(?P<body>.*?)```", patterns, re.S)
        self.assertIsNotNone(brand_block)
        self.assertEqual(
            re.findall(r"(?m)^- (.+)$", brand_block.group("body")),
            ["苹果", "华为", "小米", "OPPO", "vivo", "荣耀", "其他（请说明）"],
        )
        standards = (folder / "references" / "question-design-standards.md").read_text(encoding="utf-8")
        for heading in ("### 题目关联", "### 选项关联（引用逻辑）", "### 跳题逻辑", "### 组合校验"):
            self.assertIn(heading, standards)
        for marker in (
            "## 锁定研究对象", "## 先写测量卡，再写题目", "| 分析变量 |",
            "一个选项只承载一个编码含义", "只靠“最多选择 3 项”不能声称得到第一优先级",
            "用普通用户熟悉的简短动宾短语", "两层深挖",
        ):
            self.assertIn(marker, standards)
        self.assertIn("题目关联控制后题是否显示", standards)
        self.assertNotIn("题目关联控制后题是否显示", skill)
        checklist = (folder / "references" / "questionnaire-logic-checklist.md").read_text(encoding="utf-8")
        self.assertIn("母产品使用不能替代功能使用证据", checklist)
        self.assertIn("必须有 Top 1 或等效强制取舍", checklist)
        original_needs = (folder / "templates" / "questionnaire-original-needs-discovery.md").read_text(encoding="utf-8")
        self.assertIn("不能照抄本例的母产品行为", original_needs)
        design_doc = (folder / "templates" / "survey-design-desc.html").read_text(encoding="utf-8")
        self.assertIn("Questionnaire Design Document", design_doc)
        self.assertIn('data-field="decision"', design_doc)
        self.assertIn('data-field="target-audience"', design_doc)
        self.assertIn('data-goal-id="G1"', design_doc)
        self.assertIn('id="analysis-advice"', design_doc)
        self.assertIn('id="user-review-points"', design_doc)
        self.assertIn('id="questionnaire-appendix"', design_doc)
        self.assertIn('data-questionnaire-source="questionnaire.md"', design_doc)
        self.assertNotIn("quality-report.md", skill)
        self.assertIn("questionnaire_for_userclub.txt", skill)
        self.assertIn("questionnaire_for_simulator.md", skill)
        self.assertIn("questionnaire_for_wenjuanxing.txt", skill)
        self.assertIn("### 平台导出规格", skill)
        self.assertIn("五份最终文件", skill)
        self.assertIn("不得猜测格式、漏题或生成不完整文件", skill)
        userclub = (folder / "references" / "userclub-import-format.md").read_text(encoding="utf-8")
        for required in (
            "【单选题】您的性别是？", "-男", "-女", "-不想透露",
            "【多选题】您喜欢的功能有？", "o-功能A", "o-功能B", "其他功能-----------",
            "题目顺序、题干语义和选项顺序必须与 `questionnaire.md` 一致",
            "出现量表、矩阵、排序、Top-N 或填空题时，先返回 Step 5",
        ):
            self.assertIn(required, userclub)
        simulator_format = (folder / "references" / "simulator-questionnaire-format.md").read_text(encoding="utf-8")
        for required in (
            "规则不得放在选项之后", "不暴露“希望验证什么”", "【显示条件】",
            "题号、题型、必填状态、题序、题意和选项顺序必须与 `questionnaire.md` 一致",
        ):
            self.assertIn(required, simulator_format)
        wjx = (folder / "references" / "wenjuanxing-import-format.md").read_text(encoding="utf-8")
        for required in (
            "===", "[单选题]", "[多选题]", "[填空题]", "[矩阵量表题]",
            "题目关联、跳题逻辑、选项关联", "导入后复核",
        ):
            self.assertIn(required, wjx)

    def test_questionnaire_exporter_generates_simulator_and_wenjuanxing(self) -> None:
        exporter = PROJECT / "skills" / "ur-design-survey" / "scripts" / "export_questionnaire.py"
        simulator_module = ScriptTests._load_script(
            "ur_simulator_export_parser",
            PROJECT / "skills" / "ur-user-simulator" / "scripts" / "validate_responses.py",
        )
        source_text = """# 测试问卷

> 请根据实际经历作答。

## 研究说明

“测试功能”指示例中的目标功能。

> 以下配置注记不向受访者展示。

Q1【单选题】（必填）您是否使用过测试功能？

- 使用过
- 没有使用过

Q2【多选题】（必填）您用过哪些能力？（最多选择 2 项）

- 能力 A
- 能力 B
- 题目关联：关联 Q1 的“使用过”。

Q3【填空题】（选填）您还有什么建议？

## 结束语

感谢参与。
"""
        with workspace_temp() as temp:
            root = Path(temp)
            source = root / "questionnaire.md"
            source.write_text(source_text, encoding="utf-8")
            run(exporter, source, "--output-dir", root)
            simulator_path = root / "questionnaire_for_simulator.md"
            wjx_path = root / "questionnaire_for_wenjuanxing.txt"
            simulator = simulator_path.read_text(encoding="utf-8")
            wjx = wjx_path.read_text(encoding="utf-8")
            q2 = simulator.index("Q2【多选题】")
            rule = simulator.index("> 【显示条件】", q2)
            option = simulator.index("- 能力 A", q2)
            self.assertLess(q2, rule)
            self.assertLess(rule, option)
            self.assertNotIn("配置注记", simulator)
            self.assertNotIn("感谢参与", simulator)
            self.assertTrue(simulator.rstrip().endswith("## 问卷结束"))
            self.assertIn("1. 您是否使用过测试功能？ [单选题]", wjx)
            self.assertIn("2. 您用过哪些能力？（最多选择 2 项） [多选题]", wjx)
            self.assertIn("3. 您还有什么建议？ [填空题]", wjx)
            self.assertNotIn("题目关联", wjx)
            questions = simulator_module.parse_questionnaire(simulator_path)
            by_id = {item["id"]: item for item in questions}
            self.assertEqual(by_id["Q2"]["options"], ["能力 A", "能力 B"])
            self.assertTrue(simulator_module.question_is_applicable(by_id["Q2"], {"Q1": "使用过"}))
            self.assertFalse(simulator_module.question_is_applicable(by_id["Q2"], {"Q1": "没有使用过"}))

    def test_questionnaire_template_uses_inline_question_format(self) -> None:
        template = PROJECT / "skills" / "ur-design-survey" / "templates" / "questionnaire-key-hypothesis-validation.md"
        text = template.read_text(encoding="utf-8")
        self.assertRegex(
            text,
            r"(?m)^Q1【单选题】（必填）您的性别是？$",
        )
        self.assertRegex(text, r"(?m)^Q2【单选题】（必填）您的年龄是？$")
        self.assertRegex(text, r"(?m)^Q3【单选题】（必填）您目前主要使用的手机品牌(?:/系统)?是？$")
        self.assertRegex(
            text,
            r"(?m)^Q4【单选题】（必填）过去 3 个月，您使用手机云相册/云备份功能的频率是？$",
        )
        self.assertIn("每周多次（每周 2–6 次）", text)
        self.assertNotRegex(text, r"(?m)^## Q\d+")
        self.assertEqual(
            re.findall(r"(?m)^(Q\d+)【", text),
            [f"Q{number}" for number in range(1, 12)],
        )
        question_blocks = re.split(r"(?m)^Q\d+【[^】]+】", text)[1:]
        self.assertEqual(len(question_blocks), 11)
        self.assertEqual(len(re.findall(r"(?m)^Q\d+【[^】]+】（(?:必填|选填)）", text)), 11)
        self.assertNotRegex(text, r"(?m)^- 是否必答：")
        self.assertNotRegex(
            text,
            r"(?m)^- (题目关联|跳题逻辑|选项关联|填写提示)：(无|不适用)",
        )
        self.assertEqual(len(re.findall(r"(?m)^- 题目关联：", text)), 7)
        self.assertEqual(len(re.findall(r"(?m)^- 跳题逻辑：", text)), 1)
        self.assertEqual(len(re.findall(r"(?m)^- 选项关联：", text)), 0)
        self.assertEqual(len(re.findall(r"(?m)^- 填写提示：", text)), 0)
        self.assertRegex(text, r"选“过去 3 个月没有使用过”或“不确定(?:/想不起来)?”时跳至问卷末尾")
        self.assertIn("关联 Q7 的任一问题选项", text)
        self.assertRegex(text, r"(?m)^Q9【多选题】（必填）未来 30 天")
        self.assertIn("没有遇到明显问题（与其他选项互斥）", text)
        self.assertIn("即使满足以上条件也不打算尝试（与其他选项互斥）", text)
        self.assertRegex(text, r"(?m)^Q11【填空题】（选填）您对手机云相册有什么其他建议？$")
        self.assertNotIn("回想最近一次使用云相册/云备份，你主要想完成什么", text)
        self.assertNotIn("在你刚才选择的问题中，哪一项对你的影响最大", text)
        self.assertNotIn("能带来的额外帮助有多大", text)
        self.assertNotIn("【量表题】", text)
        run(PROJECT / "skills" / "ur-design-survey" / "scripts" / "lint_questionnaire.py", template)

    def test_questionnaire_linter_rejects_empty_configuration_placeholder(self) -> None:
        template = PROJECT / "skills" / "ur-design-survey" / "templates" / "questionnaire-key-hypothesis-validation.md"
        text = template.read_text(encoding="utf-8")
        invalid_text = text.replace(
            "- 跳题逻辑：按选项跳转",
            "- 题目关联：无。\n- 跳题逻辑：按选项跳转",
            1,
        )
        with workspace_temp() as temp:
            invalid = Path(temp) / "questionnaire.md"
            invalid.write_text(invalid_text, encoding="utf-8")
            result = run(
                PROJECT / "skills" / "ur-design-survey" / "scripts" / "lint_questionnaire.py",
                invalid,
                expect=1,
            )
        self.assertIn("empty_configuration", result.stdout)

    def test_all_questionnaire_examples_are_structurally_valid(self) -> None:
        templates = PROJECT / "skills" / "ur-design-survey" / "templates"
        examples = sorted(templates.glob("questionnaire-*.md"))
        self.assertEqual(
            [path.name for path in examples],
            [
                "questionnaire-key-hypothesis-validation.md",
                "questionnaire-original-needs-discovery.md",
                "questionnaire-satisfaction-survey.md",
                "questionnaire-solution-selection.md",
            ],
        )
        for example in examples:
            text = example.read_text(encoding="utf-8")
            self.assertNotRegex(
                text,
                r"(?m)^Q\d+【[^\n]+(?:这项|这些|上述|刚才|前面|所选方案|该方案|该功能)",
                example.name,
            )
            run(
                PROJECT / "skills" / "ur-design-survey" / "scripts" / "lint_questionnaire.py",
                example,
            )

    def test_questionnaire_examples_follow_default_type_distribution(self) -> None:
        templates = PROJECT / "skills" / "ur-design-survey" / "templates"
        for example in templates.glob("questionnaire-*.md"):
            types = re.findall(r"(?m)^Q\d+【([^】]+)】", example.read_text(encoding="utf-8"))
            counts = {
                "single": sum(item == "单选题" for item in types),
                "multi": sum(item == "多选题" for item in types),
                "scale": sum("量表题" in item for item in types),
                "ranking": sum(item in {"排序题", "Top-N题"} for item in types),
                "open": sum(item == "填空题" for item in types),
            }
            self.assertLessEqual(len(types), 12, example.name)
            self.assertTrue(4 <= counts["single"] <= 7, example.name)
            self.assertTrue(2 <= counts["multi"] <= 3, example.name)
            self.assertTrue(0 <= counts["scale"] <= 2, example.name)
            self.assertTrue(0 <= counts["ranking"] <= 1, example.name)
            self.assertEqual(counts["open"], 1, example.name)

    def test_satisfaction_example_preserves_diagnostic_structure(self) -> None:
        template = PROJECT / "skills" / "ur-design-survey" / "templates" / "questionnaire-satisfaction-survey.md"
        text = template.read_text(encoding="utf-8")
        self.assertEqual(
            re.findall(r"(?m)^(Q\d+)【", text),
            [f"Q{number}" for number in range(1, 12)],
        )
        self.assertRegex(text, r"(?m)^Q5【单选题】（必填）总体而言，.*满意程度如何？$")
        self.assertRegex(text, r"(?m)^Q6【矩阵量表题】（必填）")
        self.assertIn("照片上传/备份稳定性", text)
        self.assertIn("隐私设置清晰度与可控性", text)
        self.assertIn("未使用/无法评价", text)
        self.assertRegex(text, r"(?m)^Q7【多选题】（必填）哪些方面没有达到您的预期？")
        self.assertIn("关联 Q5 的“不太满意”“非常不满意”", text)
        self.assertIn("或关联 Q6 任一评价对象", text)
        self.assertRegex(text, r"(?m)^Q8【单选题】（必填）.*问题最终是否解决？$")
        self.assertRegex(text, r"(?m)^Q9【量表题】（必填）.*0–10 分")
        self.assertRegex(text, r"(?m)^Q10【多选题】（必填）.*优先改进")
        self.assertRegex(text, r"(?m)^Q11【填空题】（选填）.*具体建议？$")
        self.assertLess(text.index("Q5【"), text.index("Q6【"))
        self.assertLess(text.index("Q6【"), text.index("Q7【"))
        self.assertLess(text.index("Q7【"), text.index("Q9【"))
        run(
            PROJECT / "skills" / "ur-design-survey" / "scripts" / "lint_questionnaire.py",
            template,
        )

    def test_schema3_logic_becomes_executable_branching(self) -> None:
        module = ScriptTests._load_script(
            "ur_plan_logic_contract",
            PROJECT / "skills" / "ur-user-simulator" / "scripts" / "validate_responses.py",
        )
        questions = module.parse_questionnaire(QUESTIONNAIRE)
        by_id = {question["id"]: question for question in questions}
        self.assertFalse(module.question_is_applicable(by_id["Q2"], {"Q1": "没有使用过"}))
        self.assertTrue(module.question_is_applicable(by_id["Q2"], {"Q1": "使用过"}))
        self.assertFalse(module.question_is_applicable(
            by_id["Q8"], {"Q1": "使用过", "Q7": ["没有遇到明显问题"]},
        ))
        self.assertTrue(module.question_is_applicable(
            by_id["Q8"], {"Q1": "使用过", "Q7": ["同步速度慢"]},
        ))

    def test_example_output_is_complete(self) -> None:
        questionnaire = QUESTIONNAIRE.parent
        self.assertTrue((questionnaire / "questionnaire.md").exists())
        self.assertTrue(PERSONAS.exists())
        self.assertTrue(PERSONS_SUMMARY.exists())
        self.assertTrue(PERSONA_AUDIT.exists())
        personas = json.loads(PERSONAS.read_text(encoding="utf-8"))
        self.assertEqual(personas["schema_version"], "5.3")
        self.assertTrue(personas["synthetic"])
        self.assertNotIn("design", personas)
        self.assertEqual(len(list(PERSONS_DIR.glob("P*.txt"))), personas["sample_size"])
        self.assertEqual(personas["quality_check"]["grade"], "excellent")


if __name__ == "__main__":
    unittest.main()
