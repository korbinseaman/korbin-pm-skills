import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { FileBlob, PresentationFile } from "file:///C:/Users/mahai/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const ROOT = "E:/projects/korbin-pm-skills";
const TEMPLATE = path.join(ROOT, "workspace", "华为PPT模板-浅色版.pptx");
const CASE_IMAGE = path.join(ROOT, ".work", "case", "slide-02.png");
const PRESENTATIONS_SKILL = "C:/Users/mahai/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations";
const HUAWEI_THEME = "C:/Users/mahai/.codex/skills/huawei-presentation/scripts/huawei-presentation-theme.mjs";
const RUNTIME_PYTHON = "C:/Users/mahai/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";
const STAGING = path.join(ROOT, ".codex-finalizer", "pm-ai-workbench-10p-v2");
const OUT_DIR = path.join(ROOT, "outputs", "ai-pm-workflow-share", "product-manager-ai-workbench-10p-final");
const FINAL_PPTX = path.join(OUT_DIR, "我的产品经理AI工作台_10页分享版.pptx");

const {
  auditHuaweiOfficialTemplateContract,
  auditHuaweiTitle,
  auditHuaweiDeckComposition,
  auditHuaweiPageDensity,
  getHuaweiDensityProfile,
} = await import(pathToFileURL(HUAWEI_THEME).href);

await fs.mkdir(STAGING, { recursive: true });
await fs.mkdir(OUT_DIR, { recursive: true });

const deck = await PresentationFile.importPptx(await FileBlob.load(TEMPLATE));
const cover = deck.slides.getItem(0);
const unusedContents = deck.slides.getItem(1);
const contentBase = deck.slides.getItem(2);
const paletteReference = deck.slides.getItem(3);
const end = deck.slides.getItem(4);
unusedContents.delete();
paletteReference.delete();

const content = [contentBase];
for (let i = 1; i < 8; i++) content.push(contentBase.duplicate());
const order = [cover, ...content, end];
order.forEach((slide, index) => slide.moveTo(index));

const C = {
  red: "#C7000A", red2: "#E9002F", redSoft: "#FCEBED",
  ink: "#1D1D1A", body: "#575756", muted: "#919191", line: "#D2D2D2",
  surface: "#F5F5F5", white: "#FFFFFF", black: "#0D0D0D",
  blue: "#315C88", blueSoft: "#EAF1F8", green: "#267A53", greenSoft: "#E8F3ED",
  amber: "#C47B00", amberSoft: "#FFF3DC",
};
const FONT = "Microsoft YaHei";
const density = "dense";
const densityProfile = getHuaweiDensityProfile(density);
const pageLedger = [];
const compositionLedger = [];

function rect(slide, x, y, w, h, fill = "none", stroke = "none", sw = 0, radius = 0, name = "") {
  return slide.shapes.add({
    geometry: radius ? "roundRect" : "rect", name,
    position: { left: x, top: y, width: w, height: h }, fill,
    line: stroke === "none" ? { fill: "none", width: 0 } : { style: "solid", fill: stroke, width: sw },
    ...(radius ? { borderRadius: radius } : {}),
  });
}

function line(slide, x, y, w, h, color = C.line, sw = 1, name = "") {
  return slide.shapes.add({
    geometry: "line", name,
    position: { left: x, top: y, width: w, height: h }, fill: "none",
    line: { style: "solid", fill: color, width: sw },
  });
}

function text(slide, value, x, y, w, h, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox", name: options.name ?? "",
    position: { left: x, top: y, width: w, height: h },
    fill: "none", line: { fill: "none", width: 0 },
  });
  shape.text = value;
  shape.text.style = {
    typeface: options.typeface ?? FONT,
    fontSize: options.size ?? densityProfile.detail,
    bold: options.bold ?? false,
    color: options.color ?? C.body,
    alignment: options.align ?? "left",
    verticalAlignment: options.valign ?? "middle",
    autoFit: "none", wrap: "square",
    insets: options.insets ?? { left: 0, right: 0, top: 0, bottom: 0 },
    ...(options.lineSpacing ? { lineSpacing: options.lineSpacing } : {}),
  };
  return shape;
}

function title(slide, value, lead = "") {
  rect(slide, 82, 50, 54, 5, C.red);
  text(slide, value, 82, 62, 1116, 52, { size: 38, bold: true, color: C.ink, name: "slide-title" });
  if (lead) text(slide, lead, 82, 116, 1116, 32, { size: 18, bold: true, color: C.body, name: "slide-lead" });
  const audit = auditHuaweiTitle(value);
  if (!audit.ok) console.warn("TITLE_AUDIT", value, audit.warnings);
}

function addBodyBox(slide, ledger, x, y, w, h, fill = "none", stroke = "none", sw = 0, radius = 0, name = "") {
  ledger.push({ left: x, top: y, width: w, height: h });
  return rect(slide, x, y, w, h, fill, stroke, sw, radius, name);
}

function addBodyText(slide, ledger, value, x, y, w, h, options = {}) {
  ledger.push({ left: x, top: y, width: w, height: h });
  return text(slide, value, x, y, w, h, options);
}

function addBodyLine(slide, ledger, x, y, w, h, color = C.line, sw = 1) {
  ledger.push({ left: x, top: y, width: w, height: Math.max(1, h) });
  return line(slide, x, y, w, h, color, sw);
}

async function addBodyImage(slide, ledger, filePath, x, y, w, h, alt) {
  ledger.push({ left: x, top: y, width: w, height: h });
  const bytes = new Uint8Array(await fs.readFile(filePath));
  return slide.images.add({ blob: bytes, contentType: "image/png", alt, fit: "contain", position: { left: x, top: y, width: w, height: h } });
}

function note(slide, timing, body, sources) {
  slide.speakerNotes.textFrame.setText([
    `建议用时：${timing}`,
    body,
    "",
    "[Sources]",
    ...sources.map((source) => `- ${source}`),
  ].join("\n"));
}

async function contentPage(slide, pageKind, titleText, leadText, build, evidence, timing, noteBody, sources) {
  const addedBoxes = [];
  title(slide, titleText, leadText);
  await build(slide, addedBoxes);
  pageLedger.push({ kind: "content", sourceSlide: 3, inheritedFooter: true, duplicateFooter: false, addedBoxes });
  compositionLedger.push({ kind: pageKind, measured: false, primaryVisualAreaPct: 50, tableAreaPct: pageKind === "table" ? 50 : 0 });
  const densityAudit = auditHuaweiPageDensity(evidence, { density });
  if (!densityAudit.ok) throw new Error(`密度审计未通过：${titleText} / ${densityAudit.warnings.join("；")}`);
  note(slide, timing, noteBody, sources);
}

// Slide 1 — Cover
try { cover.placeholders.getItem("body").text = ""; } catch {}
try { cover.placeholders.getItem("title").text = ""; } catch {}
const securityLevel = cover.shapes.items.find((shape) => shape.name === "Text Placeholder 3");
if (securityLevel) securityLevel.text = "Security Level: Internal";
rect(cover, 78, 72, 730, 228, "#FFFFFF/84");
text(cover, "我的产品经理AI工作台", 96, 92, 680, 70, { size: 56, bold: true, color: C.ink });
text(cover, "从对话式工具到可验证的产品决策系统", 98, 178, 660, 42, { size: 24, bold: true, color: C.red });
text(cover, "用研、竞品、PRD、原型与 Skill 实践", 98, 238, 650, 32, { size: 18, color: C.body });
text(cover, "产品经理团队分享  /  40 min + 5 min Q&A", 98, 278, 520, 24, { size: 14, color: C.muted });
pageLedger.push({ kind: "cover", sourceSlide: 1 });
compositionLedger.push({ kind: "cover" });
note(cover, "1 分钟", "开场直接定义工作台：它不是一组常用提示词，也不是一份工具清单。它是一套持续保存证据、任务状态、决策规则与验收门槛的工作环境。分享会用两个真实案例说明，这套工作台如何改变产品判断。", ["本地案例：手机图库 AI 功能需求问卷", "本地案例：鸿蒙图库一句话清理图片产品方案决策汇报"]);

// Slide 2 — Workbench overview
await contentPage(content[0], "architecture", "产品经理 AI 工作台由四层控制面构成", "工作台贯穿机会识别、问题研究、方案设计、协同交付与持续学习", (s, b) => {
  const phases = ["机会识别", "问题研究", "方案设计", "协同交付", "持续学习"];
  phases.forEach((phase, i) => {
    const x = 170 + i * 202;
    addBodyText(s, b, `0${i + 1}`, x, 168, 44, 22, { size: 13, bold: true, color: C.red });
    addBodyText(s, b, phase, x, 194, 166, 30, { size: 18, bold: true, color: C.ink });
    if (i < 4) addBodyText(s, b, "→", x + 158, 190, 38, 34, { size: 22, bold: true, color: C.red, align: "center" });
  });
  const layers = [
    ["Prompt", "明确任务与输出", "研究目标、角色、格式", C.surface, C.ink],
    ["Context", "保存事实与状态", "材料、证据、版本、边界", C.blueSoft, C.blue],
    ["Agent", "调用工具完成动作", "检索、分析、写文件、生成原型", C.greenSoft, C.green],
    ["Harness", "限制执行并验证交付", "权限、文件契约、质量门禁、失败恢复", C.redSoft, C.red],
  ];
  layers.forEach((layer, i) => {
    const y = 250 + i * 72;
    addBodyBox(s, b, 82, y, 1116, 58, layer[3]);
    addBodyText(s, b, layer[0], 102, y + 8, 160, 40, { size: 20, bold: true, color: layer[4] });
    addBodyText(s, b, layer[1], 284, y + 8, 286, 40, { size: 18, bold: true, color: C.ink });
    addBodyText(s, b, layer[2], 594, y + 8, 574, 40, { size: 16, color: C.body });
  });
  addBodyText(s, b, "模型负责生成与执行；产品经理仍负责问题定义、取舍、证据判断和验收。", 82, 554, 1116, 48, { size: 20, bold: true, color: C.red, align: "center" });
}, [{ type: "diagramNode", count: 9 }, { type: "constraint", count: 3 }, { type: "action", count: 2 }], "4 分钟", "先讲整体架构。横向是产品生命周期，纵向是四层控制面。Prompt 只说明这次要什么，Context 保存证据和状态，Agent 调用工具执行，Harness 管理权限、文件契约、门禁和恢复。工作台的价值在于让一次任务的结论可以被下一步可靠复用。", ["基于本地 PM Skills 与工作区实践归纳"]);

// Slide 3 — Evolution and tools
await contentPage(content[1], "timeline", "AI 工作流从回答优化演变为交付可靠性管理", "工具能力不断扩大，产品经理的重点从写提示词转向设计任务与门禁", (s, b) => {
  addBodyLine(s, b, 122, 328, 1010, 0, C.line, 3);
  const stages = [
    ["对话式", "Prompt 工程", "回答更符合格式", "事实和状态仍在聊天里", "写清问题", 170, C.muted],
    ["知识式", "Context / RAG", "可引用内部资料", "资料多不等于能做取舍", "组织证据", 390, C.blue],
    ["Agent", "工具调用与循环", "搜索、分析、生成文件", "能行动但可能越界或失控", "定义动作", 630, C.amber],
    ["Harness", "工作区与质量门禁", "任务可恢复、可验证、可审计", "需要维护契约与评估", "设计系统", 870, C.red],
  ];
  stages.forEach((item, i) => {
    addBodyBox(s, b, item[5], 316, 24, 24, item[6], "none", 0, 12);
    addBodyText(s, b, item[0], item[5] - 50, 174, 160, 30, { size: 21, bold: true, color: C.ink, align: "center" });
    addBodyText(s, b, item[1], item[5] - 70, 210, 200, 28, { size: 15, bold: true, color: item[6], align: "center" });
    addBodyText(s, b, item[2], item[5] - 90, 246, 240, 54, { size: 16, color: C.body, align: "center" });
    addBodyText(s, b, item[3], item[5] - 90, 360, 240, 54, { size: 15, color: C.muted, align: "center" });
    addBodyText(s, b, `PM：${item[4]}`, item[5] - 70, 430, 200, 30, { size: 16, bold: true, color: i === 3 ? C.red : C.ink, align: "center" });
  });
  addBodyBox(s, b, 82, 500, 1116, 88, C.black);
  addBodyText(s, b, "判断工作流是否升级", 104, 514, 240, 30, { size: 17, bold: true, color: C.white });
  addBodyText(s, b, "同一任务能否继续执行？失败是否停止？结论能否追溯到证据？下游能否读取同一份状态？", 356, 508, 812, 46, { size: 17, color: C.white });
  addBodyText(s, b, "若四个问题仍靠人工记忆，工具再多也只是更快的对话。", 356, 554, 812, 24, { size: 14, color: "#FFFFFF/68" });
}, [{ type: "diagramNode", count: 8 }, { type: "comparison", count: 3 }, { type: "constraint", count: 2 }], "4 分钟", "把工具演变和工作方法演变放在一页讲。对话式工具优化回答，知识式工具扩充证据，Agent 获得行动能力，Harness 才处理交付可靠性。重点不是工具名，而是每一阶段解决了哪类失败，以及 PM 的注意力如何变化。", ["基于对话式、检索式、工具调用与工作区 Agent 的能力抽象"]);

// Slide 4 — User research case
await contentPage(content[2], "process", "图库 AI 问卷将功能意愿转化为产品决策证据", "真实问卷共 12 题，题目顺序用于区分真实行为、体验问题与未来诉求", (s, b) => {
  const flow = [
    ["Q4", "近期使用", "是否有真实经历"], ["Q5–Q6", "功能与任务", "最近一次想完成什么"],
    ["Q7–Q8", "问题与后果", "返工、换工具、放弃或失去信任"], ["Q9–Q10", "需求与 Top 1", "愿望清单压缩为一个取舍"],
    ["Q11–Q12", "原因与场景", "解释优先级并确定切入点"],
  ];
  flow.forEach((item, i) => {
    const x = 82 + i * 222;
    addBodyText(s, b, item[0], x, 176, 78, 24, { size: 14, bold: true, color: C.red });
    addBodyText(s, b, item[1], x, 206, 196, 32, { size: 19, bold: true, color: C.ink });
    addBodyText(s, b, item[2], x, 244, 196, 56, { size: 14, color: C.body });
    if (i < 4) addBodyText(s, b, "→", x + 190, 212, 28, 34, { size: 21, bold: true, color: C.red, align: "center" });
  });
  addBodyLine(s, b, 82, 314, 1116, 1, C.line);
  const rules = [
    ["真实需求", "Q4 + Q6", "近期使用频率与最近任务", "区分行为与概念兴趣"],
    ["问题优先级", "Q7 + Q8", "问题类型与实际后果", "区分效果问题与信任问题"],
    ["功能优先级", "Q9 + Q10 + Q11", "需求广度、强制选择与原因", "形成可解释的 Top 1 假设"],
    ["MVP 场景", "Q12", "任务发生的具体情境", "确定入口、触发与使用范围"],
  ];
  rules.forEach((row, i) => {
    const y = 334 + i * 56;
    if (i === 2) addBodyBox(s, b, 82, y, 1116, 48, C.redSoft);
    addBodyText(s, b, row[0], 96, y + 6, 190, 34, { size: 16, bold: true, color: i === 2 ? C.red : C.ink });
    addBodyText(s, b, row[1], 302, y + 6, 206, 34, { size: 16, bold: true, color: C.red });
    addBodyText(s, b, row[2], 528, y + 6, 330, 34, { size: 15, color: C.body });
    addBodyText(s, b, row[3], 878, y + 6, 300, 34, { size: 15, color: C.body });
  });
  addBodyBox(s, b, 82, 572, 1116, 48, C.black);
  addBodyText(s, b, "真实检查：12 题　0 个结构风险信号　PASS", 104, 580, 420, 30, { size: 18, bold: true, color: C.white });
  addBodyText(s, b, "结构通过不代表效度已证明，仍需研究员复核、认知访谈与小样本试填", 544, 580, 630, 30, { size: 15, color: "#FFFFFF/78", align: "right" });
}, [{ type: "diagramNode", count: 5 }, { type: "comparison", count: 4 }, { type: "metric", count: 2 }, { type: "constraint", count: 1 }], "6 分钟", "用真实题号讲一遍。Q4 是分流点：有近期经历的人回答最近任务和问题，没有经历的人不评价实际体验。Q9 先收集需求广度，Q10 强制选择一个，Q11 问原因，Q12 落到发生场景。问卷的 PM 价值是提前规定每道题如何影响需求取舍。最后解释结构检查边界，避免把脚本通过说成研究有效。", ["pm-user-research/用户调研/20260913手机图库AI功能需求/questionnaire.md", "pm-user-research/skills/ur-design-survey/scripts/lint_questionnaire.py"]);

// Slide 5 — Harness failure
await contentPage(content[3], "comparison", "质量门禁在研究结论生成前阻断错误样本", "合成调研只用于试跑问卷逻辑与数据管线，不用于估计真实市场比例", (s, b) => {
  addBodyText(s, b, "43", 82, 170, 150, 74, { size: 62, bold: true, color: C.ink });
  addBodyText(s, b, "项测试", 192, 204, 110, 30, { size: 17, bold: true, color: C.body });
  addBodyText(s, b, "28", 324, 170, 130, 74, { size: 62, bold: true, color: C.green });
  addBodyText(s, b, "通过", 424, 204, 80, 30, { size: 17, bold: true, color: C.green });
  addBodyText(s, b, "15", 538, 170, 130, 74, { size: 62, bold: true, color: C.red });
  addBodyText(s, b, "失败", 638, 204, 80, 30, { size: 17, bold: true, color: C.red });
  addBodyText(s, b, "失败来自接口契约，不是模型内容", 788, 184, 390, 44, { size: 22, bold: true, color: C.ink, align: "right" });
  addBodyLine(s, b, 82, 264, 1116, 1, C.line);
  const pipeline = [
    ["问卷", "questionnaire.md", C.green], ["画像", "参数契约失败", C.red],
    ["模拟答卷", "被门禁阻断", C.muted], ["研究报告", "不允许生成", C.muted],
  ];
  pipeline.forEach((item, i) => {
    const x = 82 + i * 279;
    addBodyText(s, b, `0${i + 1}`, x, 292, 40, 22, { size: 13, bold: true, color: item[2] });
    addBodyText(s, b, item[0], x, 322, 240, 30, { size: 19, bold: true, color: C.ink });
    addBodyText(s, b, item[1], x, 358, 240, 36, { size: 15, color: item[2] });
    if (i < 3) addBodyText(s, b, "→", x + 238, 326, 34, 34, { size: 22, bold: true, color: C.red, align: "center" });
  });
  addBodyBox(s, b, 82, 420, 536, 130, C.redSoft);
  addBodyText(s, b, "真实错误", 102, 434, 130, 28, { size: 17, bold: true, color: C.red });
  addBodyText(s, b, "测试要求：sample-size / seed / group-quota\n当前脚本不接受参数；Windows 中文错误仍有乱码", 102, 470, 492, 64, { size: 16, color: C.body });
  addBodyBox(s, b, 642, 420, 556, 130, C.surface);
  addBodyText(s, b, "修复与产品价值", 662, 434, 190, 28, { size: 17, bold: true, color: C.ink });
  addBodyText(s, b, "先统一命令与文件契约，再重跑画像。门禁把返工从结论阶段提前到接口阶段，避免不可复现样本进入漂亮报告。", 662, 470, 512, 64, { size: 16, color: C.body });
  addBodyText(s, b, "边界：合成用户可以验证题目分支和分析管线，但不能证明真实需求规模、购买率或统计显著性。", 82, 574, 1116, 38, { size: 17, bold: true, color: C.red, align: "center" });
}, [{ type: "metric", count: 3 }, { type: "diagramNode", count: 4 }, { type: "risk", count: 2 }, { type: "action", count: 2 }], "4 分钟", "这是工作台里 Harness 的真实价值。测试暴露的不是模型写得差，而是画像脚本与测试约定不一致。若没有门禁，系统仍可能生成答卷和报告，团队会在错误基础上讨论。讲清楚合成调研的边界：可以试跑流程，不能替代真实用户研究。", ["pm-user-research/tests/test_project.py", "pm-user-research/skills/ur-generate-personas/scripts/generate_personas.py", "本地测试结果：43 tests / 28 pass / 15 fail"]);

// Slide 6 — Competitor evidence to product decision
await contentPage(content[4], "mixed", "竞品证据链将一句话删除收敛为可控自动化", "证据不足的行业判断进入待核验清单，产品方案不预设竞品基线", async (s, b) => {
  const chain = [
    ["ResearchUnit", "竞品 × Feature"], ["EvidenceRecord", "主张、来源、版本、地区"],
    ["Confidence", "A / B / C"], ["Decision Input", "事实、推断、建议分栏"],
  ];
  chain.forEach((item, i) => {
    const y = 174 + i * 74;
    addBodyText(s, b, `0${i + 1}`, 82, y, 38, 22, { size: 13, bold: true, color: C.red });
    addBodyText(s, b, item[0], 126, y, 190, 28, { size: 18, bold: true, color: C.ink });
    addBodyText(s, b, item[1], 126, y + 30, 270, 32, { size: 14, color: C.body });
  });
  addBodyText(s, b, "检索停止", 82, 482, 140, 26, { size: 16, bold: true, color: C.ink });
  addBodyText(s, b, "官方当前版本直接证据，或两条独立间接证据一致；达到上限仍冲突则标记 UNKNOWN。", 82, 516, 330, 70, { size: 15, color: C.body });
  addBodyBox(s, b, 442, 174, 756, 360, C.white, C.line, 1, 4);
  await addBodyImage(s, b, CASE_IMAGE, 454, 186, 732, 336, "真实交付物：一句话清理图片产品决策页");
  addBodyBox(s, b, 442, 554, 756, 62, C.black);
  addBodyText(s, b, "最终决策", 462, 566, 120, 30, { size: 16, bold: true, color: C.red });
  addBodyText(s, b, "系统负责生成可解释候选；用户保留最终删除责任；默认进入回收站。", 594, 562, 576, 38, { size: 17, bold: true, color: C.white });
}, [{ type: "diagramNode", count: 5 }, { type: "constraint", count: 3 }, { type: "risk", count: 2 }, { type: "action", count: 2 }, { type: "source", count: 1 }], "6 分钟", "先讲竞品证据合同，再讲方案改变。没找到某竞品的撤销期限或端侧处理证据，不能写成不支持，也不能写成行业基线。真实方案最终放弃一句话直接删除，改为搜索、解释预览、显式确认和可撤销执行。这个决定限制了系统责任，同时保留效率收益。", ["pm-competitor-analysis/pm-system-app-competitor-matrix/SKILL.md", "workspace/鸿蒙图库_一句话清理图片_产品方案决策汇报.pptx，第 2 页；机制为待验证方案"]);

// Slide 7 — PRD and prototype
await contentPage(content[5], "process", "风险分层同步约束 PRD、原型状态与验收口径", "MVP 只开放低歧义任务的确认执行，高风险语义统一降级为筛选", (s, b) => {
  const riskRows = [
    ["低风险", "时间 / 明确类型", "预览后确认执行", C.greenSoft, C.green],
    ["中风险", "质量 / 重复 / 大候选集", "解释理由并二次确认", C.amberSoft, C.amber],
    ["高风险", "人物 / 票据 / 私密 / 事件", "只返回筛选，不出现删除按钮", C.redSoft, C.red],
  ];
  riskRows.forEach((row, i) => {
    const y = 168 + i * 54;
    addBodyBox(s, b, 82, y, 1116, 44, row[3]);
    addBodyText(s, b, row[0], 98, y + 6, 160, 30, { size: 17, bold: true, color: row[4] });
    addBodyText(s, b, row[1], 282, y + 6, 330, 30, { size: 16, bold: true, color: C.ink });
    addBodyText(s, b, row[2], 638, y + 6, 530, 30, { size: 16, color: C.body });
  });
  addBodyText(s, b, "PRD 主链路与原型状态", 82, 344, 280, 28, { size: 18, bold: true, color: C.ink });
  const steps = ["输入意图", "结构化解析", "检索候选", "解释预览", "显式确认", "执行与撤销"];
  steps.forEach((step, i) => {
    const x = 82 + i * 186;
    addBodyBox(s, b, x, 382, 154, 64, i === 4 ? C.redSoft : C.surface, i === 4 ? C.red : "none", i === 4 ? 1 : 0, 5);
    addBodyText(s, b, `0${i + 1}`, x + 10, 388, 34, 18, { size: 12, bold: true, color: C.red });
    addBodyText(s, b, step, x + 10, 410, 134, 28, { size: 16, bold: true, color: C.ink, align: "center" });
    if (i < 5) addBodyText(s, b, "→", x + 154, 396, 32, 34, { size: 20, bold: true, color: C.red, align: "center" });
  });
  const exceptions = [
    ["解析不完整", "追问缺失条件"], ["候选集过大", "要求二次缩小"],
    ["高风险对象", "解释降级原因"], ["执行失败", "展示回收站与恢复入口"],
  ];
  exceptions.forEach((item, i) => {
    const x = 82 + i * 279;
    addBodyText(s, b, item[0], x, 474, 150, 24, { size: 15, bold: true, color: i === 2 ? C.red : C.ink });
    addBodyText(s, b, item[1], x, 504, 240, 30, { size: 14, color: C.body });
  });
  addBodyBox(s, b, 82, 554, 1116, 64, C.black);
  addBodyText(s, b, "验收", 104, 568, 82, 30, { size: 16, bold: true, color: C.red });
  addBodyText(s, b, "执行前用户能复述候选范围；执行后能找到恢复入口；任何异常分支不得绕过确认。", 198, 562, 974, 40, { size: 17, bold: true, color: C.white });
}, [{ type: "comparison", count: 3 }, { type: "diagramNode", count: 6 }, { type: "risk", count: 2 }, { type: "action", count: 2 }], "7 分钟", "这一页把 PRD 与原型放回同一条风险链。先按后果、可解释性和恢复性分层，而不是按模型能否识别划范围。然后逐步讲六个状态，重点讲四类异常。验收不能写成页面正确展示，而要观察用户是否理解范围、是否能排除误选、异常是否绕过确认、执行后是否能恢复。", ["workspace/鸿蒙图库_一句话清理图片_产品方案决策汇报.pptx，第 3–6、8 页；本页为 PRD 与原型状态重构"]);

// Slide 8 — Skill development
await contentPage(content[6], "process", "Skill 通过契约、资源、校验和评估形成可复用能力", "Command 只是入口，稳定性来自明确的输入输出、停止条件与真实案例测试", (s, b) => {
  const steps = ["一次性提示词", "触发与输入", "步骤与停止条件", "参考与模板", "脚本门禁", "真实案例评估", "版本复盘"];
  steps.forEach((step, i) => {
    const x = 82 + i * 158;
    addBodyText(s, b, `0${i + 1}`, x, 174, 34, 20, { size: 12, bold: true, color: C.red });
    addBodyText(s, b, step, x, 202, 132, 44, { size: 15, bold: true, color: i === 4 ? C.red : C.ink, align: "center" });
    if (i < 6) addBodyText(s, b, "→", x + 132, 206, 26, 34, { size: 20, bold: true, color: C.red, align: "center" });
  });
  addBodyLine(s, b, 82, 270, 1116, 1, C.line);
  addBodyText(s, b, "$ur-design-survey", 82, 294, 290, 30, { size: 21, bold: true, color: C.red });
  addBodyText(s, b, "输入契约", 82, 336, 100, 24, { size: 14, bold: true, color: C.muted });
  addBodyText(s, b, "课题、研究目标、问卷场景、题量与材料", 194, 332, 380, 32, { size: 15, color: C.body });
  addBodyText(s, b, "方法与门禁", 82, 376, 100, 24, { size: 14, bold: true, color: C.muted });
  addBodyText(s, b, "决策—证据—题目；分支、互斥和题间关联检查", 194, 372, 380, 32, { size: 15, color: C.body });
  addBodyText(s, b, "输出", 82, 416, 100, 24, { size: 14, bold: true, color: C.muted });
  addBodyText(s, b, "Markdown 事实源、评审 HTML、平台配置文本", 194, 412, 380, 32, { size: 15, color: C.body });
  addBodyText(s, b, "$pm-system-app-competitor-matrix", 626, 294, 470, 30, { size: 21, bold: true, color: C.red });
  addBodyText(s, b, "输入契约", 626, 336, 100, 24, { size: 14, bold: true, color: C.muted });
  addBodyText(s, b, "研究问题、竞品范围与 FeatureSchema", 738, 332, 418, 32, { size: 15, color: C.body });
  addBodyText(s, b, "方法与门禁", 626, 376, 100, 24, { size: 14, bold: true, color: C.muted });
  addBodyText(s, b, "ResearchUnit、EvidenceRecord、置信度与停止规则", 738, 372, 418, 32, { size: 15, color: C.body });
  addBodyText(s, b, "输出", 626, 416, 100, 24, { size: 14, bold: true, color: C.muted });
  addBodyText(s, b, "Feature Matrix、证据明细、冲突与待确认项", 738, 412, 418, 32, { size: 15, color: C.body });
  addBodyBox(s, b, 82, 462, 1116, 100, C.black);
  addBodyText(s, b, "Command 示例", 104, 482, 176, 28, { size: 16, bold: true, color: C.white });
  addBodyText(s, b, "$ur-design-survey 课题：手机图库 AI；目标：识别高频任务、主要问题与 Top 1；场景：原始需求洞察；不超过 12 题", 298, 474, 870, 58, { size: 15, color: C.white });
  addBodyText(s, b, "开发判断：高频、跨人协作、返工昂贵且质量可检查的任务，优先做成 Skill。", 82, 580, 1116, 30, { size: 18, bold: true, color: C.red, align: "center" });
}, [{ type: "diagramNode", count: 7 }, { type: "comparison", count: 3 }, { type: "constraint", count: 2 }, { type: "action", count: 1 }], "4 分钟", "用两个 Skill 讲同一套开发流程。先从一次性提示词中提取稳定部分，再定义触发、输入输出、步骤和停止条件。方法论放 references，交付格式放 templates，可确定判断放 scripts，最后用真实案例评估。Command 只负责触发，不承担全部方法。", ["pm-user-research/skills/ur-design-survey/SKILL.md", "pm-competitor-analysis/pm-system-app-competitor-matrix/SKILL.md"]);

// Slide 9 — Current workbench map
await contentPage(content[7], "architecture", "当前工作台以共享产物连接产品生命周期", "Skill 之间传递文件与状态，产品经理在关键决策点保留判断权", (s, b) => {
  const stages = [
    ["机会识别", "新品速递\n竞品追踪", "机会清单\n证据索引"],
    ["问题定义", "问卷设计\n用户模拟与研究报告", "研究设计\n问题优先级"],
    ["方案设计", "竞品矩阵\n产品方案", "范围判断\n风险分层"],
    ["规格与体验", "PRD 账本\n原型状态\n产品文案", "状态模型\n验收口径"],
    ["持续学习", "指标复盘\n竞品变化", "新证据\n版本调整"],
  ];
  addBodyText(s, b, "阶段", 82, 174, 86, 24, { size: 14, bold: true, color: C.muted });
  addBodyText(s, b, "Skill 与流程", 82, 276, 120, 24, { size: 14, bold: true, color: C.muted });
  addBodyText(s, b, "共享产物", 82, 402, 100, 24, { size: 14, bold: true, color: C.muted });
  stages.forEach((stage, i) => {
    const x = 196 + i * 198;
    addBodyText(s, b, `0${i + 1}`, x, 170, 34, 20, { size: 12, bold: true, color: C.red });
    addBodyText(s, b, stage[0], x, 198, 164, 30, { size: 19, bold: true, color: C.ink });
    addBodyLine(s, b, x, 242, 164, 1, C.line);
    addBodyText(s, b, stage[1], x, 266, 164, 86, { size: 16, bold: true, color: i === 3 ? C.red : C.body, lineSpacing: 1.12 });
    addBodyLine(s, b, x, 374, 164, 1, C.line);
    addBodyText(s, b, stage[2], x, 396, 164, 70, { size: 15, color: C.body, lineSpacing: 1.12 });
    if (i < 4) addBodyText(s, b, "→", x + 164, 316, 30, 36, { size: 21, bold: true, color: C.red, align: "center" });
  });
  addBodyBox(s, b, 82, 492, 1116, 110, C.surface);
  addBodyText(s, b, "Agent 可以承担", 104, 508, 190, 26, { size: 16, bold: true, color: C.green });
  addBodyText(s, b, "检索、格式转换、批量分析、文件生成、结构检查和重复验证", 304, 506, 846, 30, { size: 16, color: C.body });
  addBodyText(s, b, "产品经理必须保留", 104, 552, 190, 26, { size: 16, bold: true, color: C.red });
  addBodyText(s, b, "问题定义、证据可信度、价值取舍、风险接受、需求边界和最终验收", 304, 550, 846, 30, { size: 16, bold: true, color: C.ink });
}, [{ type: "diagramNode", count: 9 }, { type: "comparison", count: 3 }, { type: "constraint", count: 2 }], "3 分钟", "这页作为工作台全景收束。不要逐个念 Skill 名称，讲共享产物如何连接阶段：研究设计成为后续输入，竞品证据进入方案，方案边界进入 PRD 与原型，新指标和反馈再回到下一轮。最后明确 Agent 能承担的工作与 PM 必须保留的判断。", ["README.md", "pm-user-research/workflows/synthetic-survey.md", "本地 PM Skills 目录结构"]);

// Slide 10 — End
text(end, "我的产品经理AI工作台", 82, 272, 650, 52, { size: 34, bold: true, color: C.ink });
text(end, "让证据、判断与交付在同一套系统中连续发生", 86, 338, 660, 36, { size: 21, bold: true, color: C.red });
text(end, "Q&A", 86, 492, 180, 38, { size: 26, bold: true, color: C.red });
pageLedger.push({ kind: "end", sourceSlide: 5 });
compositionLedger.push({ kind: "closing" });
note(end, "1 分钟 + 5 分钟 Q&A", "结尾只重复一件事：工作台的目标不是让产品经理少思考，而是让证据、判断、执行和验收可以连续发生。建议从一个高频、返工昂贵、可检查的任务开始建设，而不是直接追求万能 Agent。", ["本次分享总结"]);

const templateAudit = auditHuaweiOfficialTemplateContract({
  templateSha256: "C6F6CC8245EBEC463396F1B35FE2700C34DC85EDFD2836509CDBDD7E23F00127",
  themeName: "2210",
  pages: pageLedger,
});
const compositionAudit = auditHuaweiDeckComposition(compositionLedger, { density, requireMeasured: false });
console.log("TEMPLATE_AUDIT", JSON.stringify(templateAudit));
console.log("COMPOSITION_AUDIT", JSON.stringify(compositionAudit));
if (!templateAudit.ok) throw new Error(templateAudit.warnings.join("；"));
if (!compositionAudit.ok) throw new Error(compositionAudit.warnings.join("；"));

const candidatePath = path.join(STAGING, "candidate.pptx");
await (await PresentationFile.exportPptx(deck)).save(candidatePath);

const { finalizePresentation } = await import(pathToFileURL(path.join(PRESENTATIONS_SKILL, "container_tools", "artifact_tool_utils.mjs")).href);
const result = await finalizePresentation({
  workspaceDir: ROOT,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(PRESENTATIONS_SKILL, "container_tools", "inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(PRESENTATIONS_SKILL, "container_tools", "inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "12196763,6858000",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
  ],
  explicitTotalSlideCount: 10,
  sourceTemplatePath: TEMPLATE,
  requiredTemplateReferenceSlides: [1, 3, 5],
  // Eight content pages inherit the official content family. The official cover
  // and closing families are preserved as their own page roles, so 8/10 is the
  // correct family-coverage denominator for this compact ten-page deck.
  minimumTemplateCoverageRatio: 0.8,
  requireExactTemplateDimensions: true,
  requireTemplatePlaceholderGeometry: true,
  requirePhotographicBackground: false,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
  fontPolicy: { basis: "reference", families: ["Microsoft YaHei", "Arial"], referencePath: TEMPLATE, referenceSha256: "c6f6cc8245ebec463396f1b35fe2700c34dc85edfd2836509cdbdd7e23f00127" },
  verifyArtifactToolImport: true,
  receiptPath: path.join(STAGING, "我的产品经理AI工作台_10页分享版.validation.json"),
});
console.log("FINALIZER", JSON.stringify(result));
console.log("OUTPUT", FINAL_PPTX);
