from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/ur-design-survey/scripts/export_questionnaire.py'

def load_exporter():
    spec = importlib.util.spec_from_file_location('survey_export_regression', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

class SurveyExportTests(unittest.TestCase):
    def test_material_precedes_its_question_and_is_not_an_option(self):
        module = load_exporter()
        source = '''# 同步研究

## 研究说明
研究者希望证明按相册控制值得开发。

## 必要背景
本问卷的云相册指手机自带的照片同步服务。

Q1【单选题】（必填）过去 30 天是否同步照片？
- 是
- 否

## 概念卡
可以按相册选择后续同步；关闭后不删除已有云端照片。

Q2【单选题】（必填）与现有方式相比，按相册选择后续同步是否有帮助？
- 有
- 无
- 题目关联：关联 Q1 的“是”。

## 结束语
感谢参与。

## 模板使用说明
研究者的成功标准为测试用说明。
'''
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'questionnaire.md'
            p.write_text(source, encoding='utf-8')
            survey = module.parse_source(p)
            sim = module.simulator_markdown(survey)
        self.assertEqual(module.top_level_options(survey.questions[0].body), ['是', '否'])
        self.assertEqual(module.top_level_options(survey.questions[1].body), ['有', '无'])
        self.assertLess(sim.index('Q1【'), sim.index('## 概念卡'))
        self.assertLess(sim.index('## 概念卡'), sim.index('Q2【'))
        self.assertNotIn('研究者希望证明', sim)
        self.assertNotIn('成功标准', sim)
        self.assertIn('手机自带的照片同步服务', sim)
        _, warnings = module.wenjuanxing_text(survey)
        self.assertTrue(any('Q2' in warning and '材料' in warning for warning in warnings))

    def test_simulator_only_can_export_a_type_unknown_to_wenjuanxing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'questionnaire.md'
            source.write_text('# 数值问卷\n\nQ1【数值题】（必填）实际花了几分钟？\n', encoding='utf-8')
            result = subprocess.run([sys.executable, str(SCRIPT), str(source), '--formats', 'simulator'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['question_count'], 1)
            self.assertTrue((root / 'questionnaire_for_simulator.md').exists())
            self.assertFalse((root / 'questionnaire_for_wenjuanxing.txt').exists())

    def test_failed_requested_export_writes_no_partial_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'questionnaire.md'
            source.write_text('# 数值问卷\n\nQ1【数值题】（必填）实际花了几分钟？\n', encoding='utf-8')
            result = subprocess.run([sys.executable, str(SCRIPT), str(source)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / 'questionnaire_for_simulator.md').exists())
            self.assertFalse((root / 'questionnaire_for_wenjuanxing.txt').exists())

    def test_multi_select_rules_precede_options(self):
        module = load_exporter()
        q = module.Question('Q1', '多选题', '必填', '遇到哪些问题？（最多选择 2 项）', ['- 等待久', '- 操作难', '- 没有问题（与其他选项互斥）'])
        sim = module.simulator_markdown(module.Survey('问卷', [], [q], []))
        self.assertLess(sim.index('【作答约束】'), sim.index('- 等待久'))
        self.assertLess(sim.index('【排他规则】'), sim.index('- 等待久'))

if __name__ == '__main__':
    unittest.main()
