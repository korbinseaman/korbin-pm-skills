# 输出契约

## 使用方式

本文件定义批量文件组织与校验约束；[../templates/persona_template.json](../templates/persona_template.json) 是单人画像允许字段、字段顺序和写法的唯一来源。生成器与校验器在运行时读取该文件。

画像内容由调用本 Skill 的大模型根据直接输入生成。大模型先在临时位置输出完整的 `personas.json`，再调用 `scripts/generate_personas.py` 完成字段规范化、单人 TXT、HTML 汇总、Excel 汇总和目录落盘；脚本不创作人物，也不调用任何外部画像数据库。

```bash
python "<SKILL_DIR>/scripts/generate_personas.py" \
  "<LLM_PERSONAS_JSON>" \
  --output-dir "<WORK_DIR>/用户调研/personas_data"
```

`--replace-existing` 仅在用户明确要求重建全局画像库时使用。普通课题直接复用已经通过审计的 `personas_data/`，不再次生成。

模板是允许字段集合和内容示例，不是必须填满的表单。某项对当前人物没有实际内容时，整项省略；禁止输出 null、空字符串、“不适用”或为了补齐结构而生成的模糊文字。

## 文件组织

`personas_data/` 是工作目录下所有用户研究任务共用的用户画像库，不属于某一个课题。课题和受众范围只来自本次对 `ur-generate-personas` 的直接输入；问卷、研究目标和其他任务文件不得写入画像库。

```text
<WORK_DIR>/用户调研/personas_data/
```

~~~text
personas_data/
├── personas.json
├── persons_summary.html
├── persons.xlsx
├── persons/
│   └── P001_<姓名>.txt
└── persona_audit.json
~~~

不生成合并版 personas.txt。persons 目录内的文件数量必须与 personas.json 的 sample_size 一致。

## personas.json

顶层 schema_version 为 5.3，并包含 topic、audience_groups、target_audience、synthetic、sample_size、generation_spec、personas、quality_check 和 limitations。

当批次以中文姓名为主且不少于 50 人时，`generation_spec` 还必须包含 `name_structure_allocation`，记录“2字全名”“3字全名”“4字全名”的精确人数；三项合计必须等于中文姓名人数。该字段记录合成构建配额，不得解释为真实人口分布。

personas 中的每个对象只描述具体人物事实，使用扁平中文键值。不得写入所属群体、是否为目标用户、画像模型层级或给 LLM 的角色指令等内部管理信息。

### 必须字段

- 画像编号
- 姓名
- 年龄
- 性别
- 职业
- 通用行为
- 使用设备
- 相关使用经验
- 使用阶段
- 系统App使用习惯

除“必须字段”外，模板中的其他字段均按人物实际内容选用。模板增加、删除或重排字段后，生成器输出应同步变化，不在本契约中重复维护另一份字段清单。

字段省略规则：

- 使用阶段只能是“当前使用者”“曾经使用者”或“潜在用户”。
- 潜在用户不输出“相关产品或功能使用习惯”和“判断”。
- 当前使用者和曾经使用者必须输出具体的使用习惯和判断。
- 某项只有“不适用”“未知”“暂无”等占位内容时，直接省略。
- 年龄使用整数，收入使用区间，避免伪精确。
- 姓名必须与年龄对应的出生年代、地域文化基本相符。批量画像不得跨年龄段重复套用同一代流行字；不得因为姓名风格推断人物的性格、能力、职业、收入或使用态度。
- 中文姓名批次必须以三字全名为主体，同时自然保留两字全名；50 人以上的通用库应有极少量四字全名。四字全名必须具有真实复姓或已由人物背景支持的姓名结构，不能机械拼接字符。
- 通用行为与使用设备使用一条简洁、完整的事实描述，不拆成内部技术字段。
- 系统App使用习惯描述日常使用系统相册、文件、浏览器、设置、电话、日历等系统 App 的方式；不得写入本次问卷题目、方案或用户对未见过功能的预设评价。

单人画像对象不得出现 base_profile、research_profile、fact_anchors、response_style、knowledge_boundary、persona_id、display_name、eligibility、所属用户群体、本次目标用户等实现或管理字段。

## persons_summary.html

必须包含画像总数、全量用户 ID 数组，以及用户群体、性别、年龄段、姓名结构、相关经验、使用阶段、系统 App 使用习惯、判断标准和采用顾虑的构建分布。用户群体分布从 generation_spec.group_allocation 汇总，不要求把群体管理字段写回每个 persona。所有占比必须注明仅代表本次合成画像构成。

页面正文展示全量用户 ID；页面必须额外嵌入一个 `script#persona-summary-data[type="application/json"]`，其 JSON 至少包含 `topic`、`total` 和 `persona_ids`。模拟器和审计器读取该 JSON，不依赖 HTML 可视文本或正则解析样式。

~~~text
{"topic":"手机软件调研","total":3,"persona_ids":["P001","P002","P003"]}
~~~

数组必须包含全部画像编号，不得重复或遗漏；顺序必须与 personas.json 的 personas 数组及 persons/ 中的画像编号顺序一致，供 ur-user-simulator 按 ID 查找画像并分发子任务。HTML 不承载逐人画像事实。

## persons.xlsx

由 `scripts/render_personas_xlsx.mjs` 使用 `@oai/artifact-tool` 生成，文件名固定为 `persons.xlsx`，与 `personas.json`、`persons_summary.html` 同级。

- `画像总表`：每行一个用户，列顺序遵循 `persona_template.json`，缺失的可选字段为空；启用筛选、冻结前四行和前两列、自动换行。
- `构成摘要`：显示课题、画像总数、全量用户 ID、合成数据说明和群体配额。
- Excel 是阅读与筛选副本，不替代 `personas.json` 的机器接口，也不作为模拟器的画像输入。
- 生成失败时不得输出一个空的或不完整的 `.xlsx`；应停止交付并报告 Node.js 或 `@oai/artifact-tool` 依赖问题。

## 单人画像文件

按 P001_<姓名>.txt 命名。每行使用“字段名：字段值”，字段与顺序必须和同一 persona 完全一致：

- 不添加标题、字段分组、1–6 编号、小结或 JSON 中不存在的人物事实。
- JSON 中存在的字段必须逐项输出，值不得改写。
- JSON 中省略的可选字段，TXT 同样省略，不显示空行或占位值。
