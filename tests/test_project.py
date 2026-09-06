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
PLAN = EXAMPLE / "手机相册云相册分相册控制需求调研_Questionnaire" / "plan.json"
QUESTIONNAIRE = PLAN.parent / "questionnaire.md"
SHARED_CONTEXT = EXAMPLE / "shared_context.md"
PERSONAS = EXAMPLE / "personas_data" / "personas.json"
PERSONS_SUMMARY = EXAMPLE / "personas_data" / "persons_summary.txt"
PERSONS_DIR = EXAMPLE / "personas_data" / "persons"
PERSONA_AUDIT = EXAMPLE / "personas_data" / "persona_audit.json"
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


def shared_context_md(
    *,
    topic: str = "手机照片整理",
    groups: list[str] | None = None,
    selected: list[str] | None = None,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    exclusion_confirmed: bool = False,
    confirmed: bool = True,
) -> str:
    groups = ["当前用户", "潜在用户"] if groups is None else groups
    selected = list(groups) if selected is None else selected
    include = [] if include is None else include
    exclude = [] if exclude is None else exclude

    def bullets(values: list[str]) -> str:
        return "\n".join(f"- {value}" for value in values) if values else "- 无"

    return f"""# 用户研究共享上下文

## 任务信息

- 任务标识：test-mobile-photo
- 调研主题：{topic}

## 目标用户

### 全量候选群体

{bullets(groups)}

### 已选目标群体

{bullets(selected)}

### 纳入条件

{bullets(include)}

### 排除条件

{bullets(exclude)}

## 确认信息

- 排除条件由用户明确确认：{'是' if exclusion_confirmed else '否'}
- 状态：{'已确认' if confirmed else '待确认'}
- 确认人：用户
"""


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
            PROJECT / "skills" / "ur-design-survey" / "scripts" / "validate_shared_context.py",
            SHARED_CONTEXT,
        )
        run(
            PROJECT / "skills" / "ur-generate-personas" / "scripts" / "validate_personas.py",
            PERSONAS,
        )

    def test_persona_allocator_exact_total(self) -> None:
        with workspace_temp() as temp:
            output = Path(temp) / "personas.json"
            run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "generate_personas.py",
                SHARED_CONTEXT, "--sample-size", "7", "--seed", "42", "--output", output,
            )
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "5.3")
            self.assertEqual(data["sample_size"], 7)
            self.assertEqual(len(data["personas"]), 7)
            summary_path = output.parent / "persons_summary.txt"
            self.assertTrue(summary_path.exists())
            summary_text = summary_path.read_text(encoding="utf-8")
            summary_id_line = next(line for line in summary_text.splitlines() if line.startswith("全量用户ID："))
            self.assertEqual(
                json.loads(summary_id_line.removeprefix("全量用户ID：")),
                [persona["画像编号"] for persona in data["personas"]],
            )
            self.assertEqual(len(list((output.parent / "persons").glob("P*.txt"))), 7)
            self.assertFalse((output.parent / "personas.txt").exists())
            self.assertEqual(
                set(data["audience_groups"]),
                {item["audience_group"] for item in data["generation_spec"]["group_allocation"]},
            )
            self.assertEqual(data["generation_spec"]["allocation_basis"], "coverage_balanced")
            self.assertFalse(data["generation_spec"]["allocation_is_population_estimate"])
            self.assertEqual([item["count"] for item in data["generation_spec"]["group_allocation"]], [2, 2, 2, 1])
            first = data["personas"][0]
            template = json.loads(
                (PROJECT / "skills" / "ur-generate-personas" / "templates" / "persona_template.json").read_text(encoding="utf-8")
            )
            self.assertTrue(set(first).issubset(set(template)))
            self.assertFalse(first["姓名"].startswith("合成用户"))
            self.assertIsInstance(first["年龄"], int)
            self.assertTrue(first["居住地"])
            self.assertTrue(first["月收入"])
            self.assertTrue(first["使用设备"])
            self.assertTrue(first["通用行为"])
            for implementation_field in ("base_profile", "research_profile", "fact_anchors", "response_style", "knowledge_boundary", "persona_id", "display_name", "eligibility", "所属用户群体", "本次目标用户"):
                self.assertNotIn(implementation_field, first)
            if first["使用阶段"] != "潜在用户":
                self.assertTrue(first["相关产品或功能使用习惯"])
                self.assertTrue(first["判断"])
            txt = next((output.parent / "persons").glob("P001*.txt")).read_text(encoding="utf-8")
            pairs = [line.split("：", 1) for line in txt.splitlines() if line]
            self.assertEqual([key for key, _ in pairs], list(first))
            self.assertEqual({key: value for key, value in pairs}, {key: str(value) for key, value in first.items()})
            for removed_heading in ("基础画像：", "调研相关画像：", "人物概述：", "事实锚点：", "知识边界：", "回答风格："):
                self.assertNotIn(removed_heading, txt)
            run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "validate_personas.py",
                output,
            )

    def test_user_specified_group_quota_is_applied(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            input_path = root / "shared_context.md"
            input_path.write_text(shared_context_md(
                groups=["学生群体", "上班族", "宝爸宝妈", "内容创作者"],
            ), encoding="utf-8")
            output = root / "personas.json"
            run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "generate_personas.py",
                input_path, "--sample-size", "8",
                "--group-quota", "学生群体=1",
                "--group-quota", "上班族=3",
                "--group-quota", "宝爸宝妈=2",
                "--group-quota", "内容创作者=2",
                "--output-json", output,
            )
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["generation_spec"]["allocation_basis"], "user_specified")
            self.assertEqual(
                {item["audience_group"]: item["count"] for item in data["generation_spec"]["group_allocation"]},
                {"学生群体": 1, "上班族": 3, "宝爸宝妈": 2, "内容创作者": 2},
            )
            run(PROJECT / "skills" / "ur-generate-personas" / "scripts" / "validate_personas.py", output)

    def test_default_100_personas_have_no_duplicate_structure_warning(self) -> None:
        with workspace_temp() as temp:
            output = Path(temp) / "personas.json"
            run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "generate_personas.py",
                SHARED_CONTEXT, "--output-json", output,
            )
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["sample_size"], 100)
            result = run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "validate_personas.py",
                output,
            )
            audit = json.loads(result.stdout)
            self.assertEqual(audit["score"], 100)
            self.assertEqual(audit["warnings"], [])

    def test_persona_consistency_and_no_experience_condition(self) -> None:
        with workspace_temp() as temp:
            output = Path(temp) / "personas.json"
            run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "generate_personas.py",
                SHARED_CONTEXT, "--sample-size", "100", "--seed", "42", "--output-json", output,
            )
            data = json.loads(output.read_text(encoding="utf-8"))
            potential_count = 0
            for persona in data["personas"]:
                if "学生" in persona["职业"]:
                    self.assertLessEqual(persona["年龄"], 34)
                    self.assertIn(persona["月收入"], {"0–3000元", "3000元以下"})
                if "退休" in persona["职业"]:
                    self.assertGreaterEqual(persona["年龄"], 50)
                if persona["使用阶段"] == "潜在用户":
                    potential_count += 1
                    self.assertNotIn("相关产品或功能使用习惯", persona)
                    self.assertNotIn("判断", persona)
                    path = next((output.parent / "persons").glob(f"{persona['画像编号']}_*.txt"))
                    text = path.read_text(encoding="utf-8")
                    self.assertNotIn("（5）", text)
                    self.assertNotIn("（6）", text)
            self.assertGreater(potential_count, 0)

    def test_invalid_group_quota_total_is_rejected(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            input_path = root / "shared_context.md"
            input_path.write_text(shared_context_md(
                groups=["学生群体", "上班族", "宝爸宝妈", "内容创作者"],
            ), encoding="utf-8")
            result = run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "generate_personas.py",
                input_path, "--sample-size", "8",
                "--group-quota", "学生群体=1",
                "--group-quota", "上班族=1",
                "--group-quota", "宝爸宝妈=1",
                "--group-quota", "内容创作者=1",
                "--output-json", root / "personas.json", expect=2,
            )
            self.assertIn("人数之和必须等于 sample_size", result.stderr)

    def test_full_audience_groups_are_covered_and_target_groups_are_marked(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            input_path = root / "shared_context.md"
            output = root / "personas.json"
            input_path.write_text(shared_context_md(
                groups=["学生群体", "上班族", "宝爸宝妈", "内容创作者"],
                selected=["上班族", "宝爸宝妈"],
            ), encoding="utf-8")
            run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "generate_personas.py",
                input_path, "--sample-size", "8", "--seed", "1", "--output-json", output,
            )
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                set(data["audience_groups"]),
                {item["audience_group"] for item in data["generation_spec"]["group_allocation"]},
            )
            self.assertEqual(data["target_audience"]["selected_groups"], ["上班族", "宝爸宝妈"])
            potential = [p for p in data["personas"] if p["使用阶段"] == "潜在用户"]
            self.assertTrue(potential)
            self.assertTrue(all("没有相关经历" not in item for item in data["target_audience"]["exclude"]))
            run(PROJECT / "skills" / "ur-generate-personas" / "scripts" / "validate_personas.py", output)

    def test_empty_include_and_exclude_are_valid(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            input_path = root / "shared_context.md"
            output = root / "personas.json"
            input_path.write_text(shared_context_md(), encoding="utf-8")
            run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "generate_personas.py",
                input_path, "--sample-size", "4", "--output-json", output,
            )
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["target_audience"]["exclude"], [])
            self.assertIn("潜在用户", {p["使用阶段"] for p in data["personas"]})
            run(PROJECT / "skills" / "ur-generate-personas" / "scripts" / "validate_personas.py", output)

    def test_unconfirmed_exclusion_is_rejected(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            input_path = root / "shared_context.md"
            input_path.write_text(shared_context_md(exclude=["完全没有相关经历"]), encoding="utf-8")
            result = run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "generate_personas.py",
                input_path, "--sample-size", "4", "--output-json", root / "personas.json", expect=2,
            )
            self.assertIn("未经用户明确确认", result.stderr)

    def test_sample_size_cannot_be_smaller_than_audience_groups(self) -> None:
        with workspace_temp() as temp:
            output = Path(temp) / "personas.json"
            result = run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "generate_personas.py",
                SHARED_CONTEXT, "--sample-size", "3", "--output-json", output, expect=2,
            )
            self.assertIn("audience_groups 数量 4", result.stderr)

    def test_shared_context_rejects_research_design_fields(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            changed = SHARED_CONTEXT.read_text(encoding="utf-8") + "\n## 问卷\n\n- Q1：诱导性问题\n"
            input_path = root / "invalid-shared-context.md"
            input_path.write_text(changed, encoding="utf-8")
            result = run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "generate_personas.py",
                input_path, "--sample-size", "6", "--output-json", root / "personas.json", expect=2,
            )
            self.assertIn("不应暴露给画像生成", result.stderr)

    def test_plan_json_is_rejected_as_persona_input(self) -> None:
        with workspace_temp() as temp:
            result = run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "generate_personas.py",
                PLAN, "--output-json", Path(temp) / "personas.json", expect=2,
            )
            self.assertIn("不能使用 plan.json", result.stderr)

    def test_missing_selected_groups_is_rejected(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            context_path = root / "no-target.md"
            context_path.write_text(shared_context_md(selected=[]), encoding="utf-8")
            result = run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "generate_personas.py",
                context_path, "--output-json", root / "personas.json", expect=2,
            )
            self.assertIn("缺少已选目标群体", result.stderr)

    def test_persona_output_has_no_question_or_research_answer_fields(self) -> None:
        with workspace_temp() as temp:
            output = Path(temp) / "personas.json"
            run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "generate_personas.py",
                SHARED_CONTEXT, "--sample-size", "6", "--output-json", output,
            )
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(set(data), {"schema_version", "topic", "audience_groups", "target_audience", "synthetic", "sample_size", "generation_spec", "personas", "quality_check", "limitations"})
            self.assertNotIn("coverage_matrix", data)
            self.assertNotIn("design", data)
            for persona in data["personas"]:
                for field in ("question_answer_anchors", "concept_reaction", "extended", "fact_anchors", "base_profile", "research_profile", "response_style", "knowledge_boundary", "所属用户群体", "本次目标用户"):
                    self.assertNotIn(field, persona)
                self.assertFalse(re.search(r"\bQ\d+\b", json.dumps(persona, ensure_ascii=False)))
            run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "validate_personas.py",
                output,
            )

    def test_validator_blocks_incomplete_persona(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            output = root / "personas.json"
            run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "generate_personas.py",
                SHARED_CONTEXT, "--sample-size", "4", "--output-json", output,
            )
            data = json.loads(output.read_text(encoding="utf-8"))
            data["personas"][0].pop("判断")
            output.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "validate_personas.py",
                output, expect=1,
            )
            self.assertIn("experienced_content_missing", result.stdout)

    def test_validator_blocks_mismatched_summary_id_array(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            output = root / "personas.json"
            run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "generate_personas.py",
                SHARED_CONTEXT, "--sample-size", "4", "--output-json", output,
            )
            summary = root / "persons_summary.txt"
            summary_text = summary.read_text(encoding="utf-8")
            summary.write_text(
                re.sub(r"^全量用户ID：.*$", '全量用户ID：["P002", "P001", "P003", "P004"]', summary_text, flags=re.MULTILINE),
                encoding="utf-8",
            )
            result = run(
                PROJECT / "skills" / "ur-generate-personas" / "scripts" / "validate_personas.py",
                output, expect=1,
            )
            self.assertIn("summary_ids_mismatch", result.stdout)

    def test_survey_simulation_writes_only_answers_and_quality(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            sim_dir = root / "survey_response_data"
            result = run(
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "run_simulation.py",
                "--questionnaire", QUESTIONNAIRE,
                "--persons-summary", PERSONS_SUMMARY,
                "--persons-dir", PERSONS_DIR,
                "--config", MOCK_CONFIG, "--output-dir", sim_dir,
                "--run-id", "test-run", "--max-retries", "0",
            )
            payload = json.loads(result.stdout)
            answers_dir = sim_dir / "answers_test-run"
            quality_report = sim_dir / "quality_report_test-run.md"
            self.assertEqual(payload["completed"], 5)
            self.assertEqual(payload["failed"], 0)
            self.assertEqual(payload["data_integrity"], "excellent")
            self.assertEqual(
                sorted(path.name for path in answers_dir.glob("*.md")),
                ["P001.md", "P002.md", "P003.md", "P004.md", "P005.md"],
            )
            self.assertEqual(set(sim_dir.iterdir()), {answers_dir, quality_report})
            answer_text = (answers_dir / "P001.md").read_text(encoding="utf-8")
            self.assertIn("用户ID：P001", answer_text)
            self.assertIn(f"问卷来源：{QUESTIONNAIRE.resolve()}", answer_text)
            self.assertRegex(answer_text, r"(?m)^### Q1$")
            self.assertNotIn("过去 3 个月", answer_text)

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
            result = run(
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "run_simulation.py",
                "--questionnaire", questionnaire,
                "--persons-summary", summary,
                "--persons-dir", persons_dir,
                "--config", MOCK_CONFIG, "--output-dir", root / "results", "--run-id", "contract",
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["completed"], 2)
            self.assertTrue((root / "results" / "answers_contract" / "P001.md").exists())
            self.assertFalse(list((root / "results").glob("*.json")))

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
            prepared = run(
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "native_simulation.py",
                "prepare", "--questionnaire", questionnaire,
                "--persons-summary", summary, "--persons-dir", persons_dir,
                "--output-dir", root / "results", "--run-id", "current-test",
            )
            manifest = json.loads(prepared.stdout)
            self.assertEqual([task["model"] for task in manifest["tasks"]], ["current-model", "current-model"])
            self.assertFalse(list((root / "results").glob("*.json")))
            validator = ScriptTests._load_script(
                "ur_native_contract_validator",
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "validate_responses.py",
            )
            questions = validator.parse_questionnaire(questionnaire)
            for task in manifest["tasks"]:
                user_id = task["user_id"]
                persona = validator.parse_persona(Path(task["persona_path"]), user_id)
                validator.write_answer_markdown(
                    Path(task["output_path"]), run_id="current-test", user_id=user_id,
                    persona=persona, questionnaire_path=questionnaire,
                    provider="native-agent", model="current-model", questions=questions,
                    result={"answers": {"Q1": "是", "Q2": "合成回答"}, "answer_notes": {}},
                )
            finalized = run(
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "native_simulation.py",
                "finalize", "--questionnaire", questionnaire,
                "--persons-summary", summary, "--persons-dir", persons_dir,
                "--answers-dir", root / "results" / "answers_current-test",
                "--quality-report", root / "results" / "quality_report_current-test.md",
                "--run-id", "current-test",
            )
            payload = json.loads(finalized.stdout)
            self.assertEqual(payload["completed"], 2)
            self.assertTrue((root / "results" / "quality_report_current-test.md").exists())

    def test_current_model_tasks_record_known_model_id(self) -> None:
        with workspace_temp() as temp:
            root = Path(temp)
            questionnaire, summary, persons_dir = self._inputs(root, count=1)
            result = run(
                PROJECT / "skills" / "ur-user-simulator" / "scripts" / "native_simulation.py",
                "prepare", "--questionnaire", questionnaire,
                "--persons-summary", summary, "--persons-dir", persons_dir,
                "--model-label", "known-current-model", "--output-dir", root / "results",
            )
            manifest = json.loads(result.stdout)
            self.assertEqual(manifest["tasks"][0]["model"], "known-current-model")


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
        design_doc = root / "design-doc.md"
        design_doc.write_text((PLAN.parent / "design-doc.md").read_text(encoding="utf-8"), encoding="utf-8")
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

            run(
                PROJECT / "skills" / "ur-synthesize-report" / "scripts" / "generate_report.py",
                "--questionnaire", paths["questionnaire"],
                "--design-doc", paths["design"], "--responses", paths["responses"],
                "--analysis", report_dir / "analysis_summary.json", "--output-dir", report_dir,
            )
            report = (report_dir / "report.html").read_text(encoding="utf-8")
            self.assertIn("contract-run", report)
            self.assertIn("样本构成说明", report)
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
            text = (PROJECT / "workflows" / filename).read_text(encoding="utf-8")
            found = set(re.findall(r"\$?(ur-(?:design-survey|generate-personas|user-simulator|synthesize-report))", text))
            self.assertEqual(found, wanted, filename)
            self.assertIn("output", text)

    def test_plan_skill_contains_domain_core_and_substantive_resources(self) -> None:
        folder = PROJECT / "skills" / "ur-design-survey"
        skill = (folder / "SKILL.md").read_text(encoding="utf-8")
        for section in ("## 输入契约", "## 工作流程", "## 输出契约", "## 优化现有问卷", "## 交付给用户"):
            self.assertIn(section, skill)
        self.assertLess(skill.index("## 工作流程"), skill.index("## 输出契约"))
        self.assertLess(len(skill.splitlines()), 170)
        self.assertNotIn("questionnaire.json", skill)
        self.assertNotIn("plan.json", skill)
        self.assertNotIn("survey.status", skill)
        self.assertRegex(skill, r"人口特征.*用户筛选")
        self.assertIn("### 1. 定义调研问题并形成输入摘要", skill)
        self.assertIn("### 2. 建立目标—证据清单", skill)
        self.assertIn("| 目标 | 需要判断 | 优先证据 | 决策用途 |", skill)
        self.assertIn("#### 题目数量", skill)
        self.assertIn("#### 题型数量分布", skill)
        self.assertIn("### 用户研究设计确认卡", skill)
        self.assertIn("请确认：确认 / 修改 / 重新设计", skill)
        for example in (
            "questionnaire-original-needs-discovery.md",
            "questionnaire-key-hypothesis-validation.md",
            "questionnaire-solution-selection.md",
            "questionnaire-satisfaction-survey.md",
        ):
            self.assertIn(f"templates/{example}", skill)
        self.assertIn("不要直接拼接多份问卷", skill)
        expected = {
            "references/question-design-standards.md",
            "references/survey-patterns.md",
            "references/shared-context-schema.md",
            "references/questionnaire-logic-checklist.md",
            "templates/questionnaire-key-hypothesis-validation.md",
            "templates/questionnaire-original-needs-discovery.md",
            "templates/questionnaire-solution-selection.md",
            "templates/questionnaire-satisfaction-survey.md",
            "templates/design-doc.md",
            "templates/quality-report.md",
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
            for path in (folder / group).glob("*.md")
        }
        self.assertEqual(actual_resources, expected)
        patterns = (folder / "references" / "survey-patterns.md").read_text(encoding="utf-8")
        self.assertNotIn("## 模块选择逻辑", patterns)
        self.assertNotIn("### 用户分层变量", patterns)
        self.assertIn("## 用户筛选", patterns)
        standards = (folder / "references" / "question-design-standards.md").read_text(encoding="utf-8")
        for heading in ("### 题目关联", "### 选项关联（引用逻辑）", "### 跳题逻辑", "### 组合校验"):
            self.assertIn(heading, standards)
        self.assertIn("题目关联控制后题是否显示", standards)
        self.assertNotIn("题目关联控制后题是否显示", skill)
        design_doc = (folder / "templates" / "design-doc.md").read_text(encoding="utf-8")
        self.assertIn("调研问题：RQ1", design_doc)
        self.assertIn("题型分布：", design_doc)

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
        self.assertTrue(SHARED_CONTEXT.exists())
        shared_context = SHARED_CONTEXT.read_text(encoding="utf-8")
        self.assertTrue(shared_context.startswith("# 用户研究共享上下文\n"))
        self.assertIn("- 状态：已确认", shared_context)
        questionnaire = QUESTIONNAIRE.parent
        for filename in ("questionnaire.md", "design-doc.md", "quality-report.md"):
            self.assertTrue((questionnaire / filename).exists(), filename)
        self.assertTrue(PERSONAS.exists())
        self.assertTrue(PERSONS_SUMMARY.exists())
        self.assertEqual(len(list(PERSONS_DIR.glob("P*.txt"))), 5)
        self.assertTrue(PERSONA_AUDIT.exists())
        personas = json.loads(PERSONAS.read_text(encoding="utf-8"))
        self.assertEqual(personas["schema_version"], "5.3")
        self.assertTrue(personas["synthetic"])
        self.assertNotIn("design", personas)
        self.assertEqual(personas["sample_size"], 5)
        self.assertEqual(personas["quality_check"]["grade"], "excellent")


if __name__ == "__main__":
    unittest.main()
