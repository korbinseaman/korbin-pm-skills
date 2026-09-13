我要开发四个用于产品经理做用户研究时调研用户痛点和需求的skill：ur-design-survey 用研课题分析和设计、ur-generate-personas 用户画像生成、ur-user-simulator 真实用户模拟回答、ur-synthesize-report 分析调研数据，输出调研报告。
这四个是原子能力，但是在常用的几个工作流里，需要多个skill协同完成任务。
请开发这四个skill和四个工作流，并完成测试验证。

# 1.项目目录结构
E:\projects\PM_Studio\pm-user-research-skills\
    ├── skills
        ├── ur-design-survey 用研设计：课题分析和调研设计
            ├── SKILL.md
            ├── rules
            ├── references
            ├── templates
            ├── scripts
        ├── ur-generate-personas 用户画像生成：生成真实用户画像，有基础用户画像维度和针对本次调研的自定义维度
            ├── SKILL.md
            ├── rules
            ├── references
            ├── templates
            ├── scripts
        ├── ur-user-simulator 合成用户问卷作答：模拟画像回答问卷，核查逻辑冲突和无依据内容
            ├── SKILL.md
            ├── rules
            ├── references
            ├── templates
            ├── scripts
        ├── ur-synthesize-report 分析调研数据，输出调研报告
            ├── SKILL.md
            ├── rules
            ├── references
            ├── templates
            ├── scripts
    ├── workflows
        ├── user-research-plan.md 只完成课题分析和调研设计，仅调用 ur-design-survey
        ├── user-research-pilot.md 完成课题分析和调研设计，用户画像生成，并先运行少量样本，检查问卷和模型表现，调用ur-design-survey、ur-generate-personas、ur-user-simulator
        ├── synthetic-interview.md 完成完整的用户深度访谈流程
        ├── synthetic-survey.md 完成完整的定量问卷调研流程
    ├── output_example
        ├── personas_data                 # 所有课题共用的画像库
        ├── 20260815图库AI修图用户需求调研
            ├── <调研课题名称>_Questionnaire
            ├── survey_response_data
            ├── report
    ├── README.md

# 2.各skill的主要职责和输入输出, 参考以下内容
## 2.1 ur-design-survey
## 触发场景
- 需要分析调研课题并设计一份调研问卷或访谈提纲
- 需要完成完整的调研课题设计、实施和报告，在分析设计环节使用本skill

### 核心职责：把模糊课题转化为可执行研究方案，并根据用户选择设计定量调研问卷、深度用户访谈脚本。
- 引导用户明确调研主题和目标
- 分析补充用户调研问题的领域知识
- 问卷设计、对话访谈设计、深度用户访谈提纲设计
- 质量检查 + 引导性/隐私风险规避

### 支持三种调研方法：
1.定量调研问卷
2.深度用户访谈
### 主要输入：调研主题、背景、目标、调研方法、目标用户群体、题目数量范围/访谈时长、用户其他输入材料

### 工作流程
- step 1. 接受需求
接受用户所有输入，分析调研主题、背景、目标、业务知识等
- 用户需求格式参考/ur-design-survey/references/requirement.md
- Step 2 · 构建上下文
收集：背景、调研目标、目标用户、研发阶段、题目数/访谈时长。
调用LLM 补充更多业务领域信息
- Step 3 · 与用户确认用户研究思路

- Step 4 · 生成问卷或者方案脚本
1.如果step 2中用户希望做定量问卷调查，则调用 LLM 引擎生成问卷，问卷规则如下：
（1）题目数根据用户输入决定，如果用户无输入，默认10道题；
题目类型有单选、多选、排序、最后的建议题为文本题；
题目与题目之间，需要考虑逻辑跳转关系和互相论证；
问卷设计成一个固定7段式： 「用户画像 → 行为 → 痛点 → 现有方案 → 新功能 Concept Test → 使用意愿 → 优先级」
（2）题目由三部分组成：
（2.1）被调研用户筛选和画像题，这部分从/ur-design-survey/templates/survey_basic_question.md中获取
画像：年龄、职业、设备、用户类型、使用经验等
筛选用户：是否使用过产品/功能、最近使用时间、使用频率
这部分题目数占问卷全量问题数的1/4左右 
（2.2）被调研用户行为现状、痛点和需求题：这部分需要结合前几步的上下文调用LLM生成，规格参考/ur-design-survey/rules/survey_user_challenges_rule.md，模板可参考/ur-design-survey/templates/survey_user_challenges_question.md
使用频率、使用场景、完成任务的方式；遇到过哪些问题、发生频率、严重程度
这部分题目数占问卷全量问题数的1/4左右 
（2.3）功能价值题：这部分需要结合前几步的上下文调用LLM生成，规格参考/ur-design-survey/rules/survey_feature_value_rule.md，模板可参考/ur-design-survey/templates/survey_feature_value_question.md
用户是否需要这个功能，兴趣度、价值感知、使用意愿、使用场景
这部分题目数占问卷全量问题数的1/4左右 
（2.4）方案验证题:这部分需要结合前几步的上下文调用LLM生成，规格参考/ur-design-survey/rules/survey_feature_plan_rule.md，模板可参考/ur-design-survey/templates/survey_feature_plan_question.md
哪个方案更好？功能优先级、方案偏好、概念选择
这部分题目可选，根据用户输入决定。
这部分题目数占问卷全量问题数的1/4左右 
（2.5）其他题：用户对功能的建议、满意度等，可选，根据输入决定

2.如果step 2中用户希望做深度用户访谈，则调用 LLM 引擎生成访谈脚本，问卷规则如下：
脚本结构建议固定为 6 段 ，一场 45～60 分钟的产品用户访谈，可以用下面的标准骨架。
以下部分需要结合前几步的上下文调用LLM生成，具体规格定义在/ur-design-survey/rules/interview_rule.md，模板可参考/ur-design-survey/templates/interview_script.md
1. 开场与热身｜3–5 分钟
目的不是收集核心洞察，而是让用户进入状态。
例如了解：
平时用什么手机
拍照多不多
平时会不会整理图库
希望分享真实经历
2. 用户背景与习惯｜5–10 分钟
建立用户上下文。
例如研究图库清理：
你手机大概有多少照片和视频？
这里重点建立：
用户类型 + 使用场景 + 行为习惯。
3、核心行为访谈｜15–20 分钟
这一段通常是整场访谈价值最高的部分。
建议大量使用：
“最近一次……”
例如：
最近一次你主动清理手机照片是什么时候？
然后连续追：
当时为什么突然想清理？
你第一步做了什么？
接下来呢？
你是怎么决定删哪张、留哪张的？
中间有没有哪一步让你犹豫？
最后清理了多少？
4.概念测试

- Step 5 · 质量检查
按下方「质量自检清单」逐项校验，不达标则修正或降级标记，具体规格定义在/ur-design-survey/rules/audit_interview_rule.md和/ur-design-survey/rules/audit_survey_rule.md 
检查题目数量、否定句、选项互斥
给出质量得分（0-100 分）和改进建议
- Step 6 · 保存输出，用户确认
本地 JSON 保存 + 展示题目/质量得分，等待用户**确认 / 修改 / 重新设计**。
问卷或脚本保存目录为/output/20260815图库AI修图用户需求调研/<调研课题名称>_Questionnaire
用户确认 :清晰展示设计结果 ,等待用户确认后再进行下一步, 展示给用户时使用md格式

### 主要输出：调研问卷/调研提纲
#### 调研问卷
模板参考 /ur-design-survey/templates/user_survey_plan.md
user_survey_plan.md 可参考这个 https://github.com/korbinseaman/synthetic-user-interview-v2/blob/master/agents/data/survey_design_20260414_124247.json
#### 调研提纲
模板参考 /ur-design-survey/templates/User_interview_plan.md
User_interview_plan.md参考这个skill中的 Output: Generate Interview Plan 部分：https://github.com/deanpeters/Product-Manager-Skills/blob/main/skills/discovery-interview-prep/SKILL.md

## 2.2 ur-generate-personas
画像生成师负责生成多样化用户画像，包含基础维度、行为标签和用户分类。
原则：
1.生成多样化的用户画像
- 基础维度：基础信息（年龄、性别、城市、职业）、收入信息（月收入、收入等级、可支配比例）、行为标签（购物偏好、理财习惯、出游偏好、搜索行为、阅读行为、兴趣爱好），定义到/ur-generate-personas/reference/basic_user_personas_dim.md，可以参考定义的一些常用的值https://github.com/korbinseaman/synthetic-user-interview-v2/blob/master/agents/persona-generator/persona_generator.py
- 与本次调研主题有关的扩展维度：产品或功能的使用群体的特征（是否使用产品和功能、使用频率、用途、评价等），定义到/ur-generate-personas/reference/extended_user_personas_dim.md
- 用户分类分组，打标签（与调研主题关联） 、区分主要/次要人物模型
类型	占比	特征
主要人物模型 (Primary)	30%	核心目标用户，25-40 岁，一线城市
次要人物模型 (Secondary)	50%	重要用户群体，18-55 岁
边缘人物模型 (Tertiary)	20%	潜在用户，18-65 岁
2.输入
结合用户输入的调研主题、人数和ur-design-survey的step1的分析结果，构造本次调研的人数，是否为特定人群，人群特性等信息
输入可参考 /ur-generate-personas/reference/user_personas_input.md
3，输出
输出结果：JSON 或文件
输出可参考/ur-generate-personas/templates/user_personas_output.md，user_personas_output可以学习下，但是希望简化一下https://github.com/korbinseaman/synthetic-user-interview-v2/blob/master/agents/data/personas_20260414_155621.json
4.执行步骤

## 2.3 ur-user-simulator
合成用户问卷作答：模拟画像回答问卷，核查回答是否有逻辑冲突和无依据内容
## 职责
模拟合成用户回答问卷，调用 LLM 生成回答，校验逻辑，并内置数据记录（record()）。当前不处理访谈。
职责：
- 并行执行多个问卷任务
- 子 Agent 调用不同 LLM（Qwen3.8-max, deepseek-v4-pro, gpt-5.6 Sol 等）
- 平均分配给每个模型
- 详细记录执行过程
- 校验用户回答的逻辑性，标记不符合逻辑的地方
- 可解释的校验结果
## 输入输出
**输入：** `plan.json` 问卷方案、`personas.json`（画像列表）、可选 LLM 配置
**输出：**所有用户回答汇总到一个 Excel，同时保留个人答卷和质量报告，存储在：output/<时间><调研课题名称>/survey_response_data
## 执行步骤
1.读取输入
2.初始化LLM配置，分配任务
3.调用不同的LLM 并行执行
4.记录每一位模拟用户回答结果
5.核查回答是否合理，是否有伪造
按照本skill的职责规划，可以参考：https://github.com/korbinseaman/synthetic-user-interview-v2/blob/master/agents/interview-data/interview_data_agent.py

## 作答机制
- 每个画像 → 独立子 Agent（`SubInterviewerAgent`），按人设代入作答
- **真实调用 大模型** 生成回答
- 使用问卷提示模板

## 数据记录（record 方法）
- 输入任务结果 + `personas` → 输出 `answers_<run_id>/`、`survey_responses_*.xlsx` 和 `quality_report_*.md`
- 结构化记录含：response_id、persona_id、demographics、answers、status、llm_provider
- 质量分级：excellent / good / needs_review / poor

## 逻辑校验
| 类型 | 规则 |
|------|------|
| missing_answer | 回答缺失 |
| out_of_range | 量表越界（NPS 0-10，量表 1-5） |
| inconsistency | 交叉不一致 |

## 2.4 ur-synthesize-report
参考https://github.com/korbinseaman/synthetic-user-interview-v2/blob/master/agents/report-analyst/SKILL.md
**输出：**存储在：output/<时间><调研课题名称>/report
报告输出为html格式，显示图表分析

# 3.工作流开发


# 补充信息
1.生成的skill 支持在CodeX、claude CodeX、OpenCode等agent 平台使用；
2.skill.md正文主要使用中文；
3.需要的LLM API在配置文件中预留，我会在使用时设置；
4.skill内的分支逻辑、引用等要逻辑严谨
5.实际调用skill时，输出应该在工作目录在创建output
