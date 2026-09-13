# 作答输出

所有用户回答汇总为一个 `survey_responses_<run_id>.xlsx`，个人答卷保存在 `answers_<run_id>/`，列结构和校验规则见 [../references/io-contract.md](../references/io-contract.md)。质量报告 Markdown 使用：

```markdown
# 合成调研数据质量报告

> 此批次为合成数据；真实性检查只能识别风险信号。

## 执行概览
- run_id / 模式 / 样本数 / 完成率
- 提供商与模型分配
- 测试模式与重试情况

## 问题统计
| 类型 | 严重度 | 数量 | 涉及用户ID |

## 需要人工复核
## 问卷工具问题
## 模型与画像问题
## 结论与是否可进入分析
```
