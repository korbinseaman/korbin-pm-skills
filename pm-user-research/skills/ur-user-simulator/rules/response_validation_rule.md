# 回答逻辑校验

## 确定性错误

- `missing_answer`：适用且必答的题缺失。
- `out_of_range`：NPS 不在 0–10，或题目声明的量表范围之外。
- `invalid_option`：单选不属于选项，多选含未知选项或超过最大选择数。
- `skip_logic_violation`：不满足展示条件却作答，或满足条件的必答题被跳过。
- `unknown_question`：返回未定义的题目 ID。

## 条件性不一致

- 只执行研究方案中显式声明的 `consistency_rules`，例如“Q1=从未使用时，Q5 使用频率必须为空”。
- 画像字段与回答冲突时，指出冲突证据并标为 `warning`；现实中信息可能变化，不自动判为错误。
- 不使用“高收入应付费”“年轻人应熟练”等刻板规则。

每个问题包含 `type`、`severity`、`question_ids`、`evidence`、`explanation` 和 `suggestion`。
