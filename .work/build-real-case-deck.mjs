import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { FileBlob, PresentationFile } from "file:///C:/Users/mahai/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const ROOT = "E:/projects/korbin-pm-skills";
const TEMPLATE = path.join(ROOT, "workspace", "华为PPT模板-浅色版.pptx");
const SKILL_DIR = "C:/Users/mahai/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations";
const HUAWEI_THEME = "C:/Users/mahai/.codex/skills/huawei-presentation/scripts/huawei-presentation-theme.mjs";
const RUNTIME_PYTHON = "C:/Users/mahai/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";
const STAGING = path.join(ROOT, ".codex-finalizer", "ai-pm-real-case-v3");
const OUT_DIR = path.join(ROOT, "outputs", "ai-pm-workflow-share", "huawei-real-case-final");
const FINAL_PPTX = path.join(OUT_DIR, "AI产品经理工作流演变_真实案例深化版.pptx");
const CASE_IMG = (n) => path.join(ROOT, ".work", "case", `slide-${String(n).padStart(2, "0")}.png`);

const {
  auditHuaweiOfficialTemplateContract,
  auditHuaweiTitle,
  auditHuaweiDeckComposition,
  auditHuaweiPageDensity,
  getHuaweiDensityProfile,
  HUAWEI_OFFICIAL_LIGHT_TEMPLATE,
} = await import(pathToFileURL(HUAWEI_THEME).href);

await fs.mkdir(STAGING, { recursive: true });
await fs.mkdir(OUT_DIR, { recursive: true });

const deck = await PresentationFile.importPptx(await FileBlob.load(TEMPLATE));
const cover = deck.slides.getItem(0);
const section1 = deck.slides.getItem(1);
const contentBase = deck.slides.getItem(2);
const paletteReference = deck.slides.getItem(3);
const end = deck.slides.getItem(4);
paletteReference.delete();

const content = [contentBase];
for (let i = 1; i < 16; i++) content.push(contentBase.duplicate());
const section2 = section1.duplicate();
const desired = [
  cover,
  content[0], content[1], content[2],
  section1,
  content[3], content[4], content[5], content[6], content[7], content[8],
  section2,
  content[9], content[10], content[11], content[12], content[13], content[14], content[15],
  end,
];
desired.forEach((slide, i) => slide.moveTo(i));

const C = {
  red: "#C7000A", brightRed: "#E9002F", redSoft: "#FCEBED",
  ink: "#1D1D1A", body: "#575756", muted: "#919191", line: "#D4D4D4",
  surface: "#F5F5F5", white: "#FFFFFF", black: "#0D0D0D",
  green: "#267A53", greenSoft: "#E8F3ED", amber: "#C47B00", amberSoft: "#FFF3DC",
  blue: "#315C88", blueSoft: "#EAF1F8",
};
const FONT = "Microsoft YaHei";
const BODY = { left: 82, top: 160, width: 1116, height: 482 };
const profile = getHuaweiDensityProfile("dense");
const pages = [];
const compPages = [];

function rect(slide, x, y, w, h, fill = "none", stroke = "none", sw = 0, radius = 0, name = "") {
  return slide.shapes.add({
    geometry: radius ? "roundRect" : "rect",
    name,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: stroke === "none" ? { fill: "none", width: 0 } : { style: "solid", fill: stroke, width: sw },
    ...(radius ? { borderRadius: radius } : {}),
  });
}

function line(slide, x, y, w, h, color = C.line, sw = 1, name = "") {
  return slide.shapes.add({
    geometry: "line", name,
    position: { left: x, top: y, width: w, height: h },
    fill: "none", line: { style: "solid", fill: color, width: sw },
  });
}

function text(slide, value, x, y, w, h, opts = {}) {
  const sh = slide.shapes.add({
    geometry: "textbox", name: opts.name ?? "",
    position: { left: x, top: y, width: w, height: h },
    fill: "none", line: { fill: "none", width: 0 },
  });
  sh.text = value;
  sh.text.style = {
    typeface: opts.typeface ?? FONT,
    fontSize: opts.size ?? profile.detail,
    bold: opts.bold ?? false,
    color: opts.color ?? C.body,
    alignment: opts.align ?? "left",
    verticalAlignment: opts.valign ?? "middle",
    autoFit: "none", wrap: "square",
    insets: opts.insets ?? { left: 0, right: 0, top: 0, bottom: 0 },
    ...(opts.lineSpacing ? { lineSpacing: opts.lineSpacing } : {}),
  };
  return sh;
}

function title(slide, value, lead = "") {
  rect(slide, 82, 50, 54, 5, C.red, "none", 0, 0, "title-accent");
  text(slide, value, 82, 62, 1116, 52, { size: 38, bold: true, color: C.ink, name: "slide-title" });
  if (lead) text(slide, lead, 82, 116, 1116, 32, { size: 18, bold: true, color: C.body, name: "slide-lead" });
  const a = auditHuaweiTitle(value);
  if (!a.ok) console.warn("TITLE_AUDIT", value, a.warnings);
}

function note(slide, timing, body, sources = []) {
  slide.speakerNotes.textFrame.setText([
    `建议用时：${timing}`,
    body,
    "",
    "[Sources]",
    ...sources.map((s) => `- ${s}`),
  ].join("\n"));
}

function bodyBox(slide, ledger, x, y, w, h, fill = "none", stroke = "none", sw = 0, radius = 0, name = "") {
  ledger.push({ left: x, top: y, width: w, height: h });
  return rect(slide, x, y, w, h, fill, stroke, sw, radius, name);
}

function bodyText(slide, ledger, value, x, y, w, h, opts = {}) {
  ledger.push({ left: x, top: y, width: w, height: h });
  return text(slide, value, x, y, w, h, opts);
}

function bodyLine(slide, ledger, x, y, w, h, color = C.line, sw = 1, name = "") {
  ledger.push({ left: x, top: y, width: w, height: Math.max(h, 1) });
  return line(slide, x, y, w, h, color, sw, name);
}

async function bodyImage(slide, ledger, filePath, x, y, w, h, name = "") {
  ledger.push({ left: x, top: y, width: w, height: h });
  const bytes = new Uint8Array(await fs.readFile(filePath));
  return slide.images.add({ blob: bytes, contentType: "image/png", alt: name || "真实产品方案交付物截图", fit: "contain", position: { left: x, top: y, width: w, height: h } });
}

function pill(slide, ledger, value, x, y, w, fill = C.surface, color = C.ink, stroke = "none") {
  bodyBox(slide, ledger, x, y, w, 30, fill, stroke, stroke === "none" ? 0 : 1, 15);
  bodyText(slide, ledger, value, x + 8, y + 3, w - 16, 24, { size: 14, bold: true, color, align: "center" });
}

async function contentPage(slide, pageKind, titleText, leadText, build, densityItems, talk, sources) {
  const addedBoxes = [];
  title(slide, titleText, leadText);
  await build(slide, addedBoxes);
  const pageNo = pages.length + 1;
  pages.push({ kind: "content", sourceSlide: 3, inheritedFooter: true, duplicateFooter: false, addedBoxes });
  compPages.push({ kind: pageKind, measured: false, primaryVisualAreaPct: 45, tableAreaPct: pageKind === "table" ? 50 : 0 });
  const d = auditHuaweiPageDensity(densityItems, { density: "dense" });
  if (!d.ok) console.warn("DENSITY_AUDIT", pageNo, d.warnings);
  note(slide, talk.timing, talk.body, sources);
}

function sectionPage(slide, no, heading, subtitle, chapter) {
  try { slide.placeholders.getItem("body").text = ""; } catch {}
  // Keep the official placeholder geometry for template fidelity while covering
  // the inherited automatic-list marker before drawing the large chapter number.
  rect(slide, 108, 190, 180, 108, "#F2F2F2", "none", 0, 0, "section-number-backdrop");
  text(slide, no, 108, 190, 180, 108, { size: 82, bold: true, color: C.red });
  rect(slide, 108, 320, 62, 5, C.red);
  text(slide, heading, 108, 342, 980, 72, { size: 44, bold: true, color: C.ink });
  text(slide, subtitle, 108, 430, 940, 66, { size: 22, color: C.body, lineSpacing: 1.1 });
  text(slide, chapter, 1050, 578, 120, 24, { size: 14, bold: true, color: C.muted, align: "right" });
  pages.push({ kind: "section", sourceSlide: 2 });
  compPages.push({ kind: "section" });
}

// 1 Cover
try { cover.placeholders.getItem("body").text = ""; } catch {}
try { cover.placeholders.getItem("title").text = ""; } catch {}
const securityLevel = cover.shapes.items.find((shape) => shape.name === "Text Placeholder 3");
if (securityLevel) securityLevel.text = "Security Level: Internal";
rect(cover, 78, 68, 730, 244, "#FFFFFF/82", "none", 0, 0, "cover-text-backdrop");
text(cover, "从“会聊天”到“能承担决策”", 96, 88, 680, 72, { size: 48, bold: true, color: C.ink });
text(cover, "我的 AI 产品经理工作系统：Prompt → Context → Agent → Harness", 98, 174, 668, 54, { size: 21, bold: true, color: C.red });
text(cover, "用研 × 竞品 × PRD × 原型｜两个真实工作案例", 98, 236, 668, 38, { size: 18, color: C.body });
text(cover, "产品经理团队分享  /  45 min", 98, 292, 480, 28, { size: 14, color: C.muted });
pages.push({ kind: "cover", sourceSlide: 1 });
compPages.push({ kind: "cover" });
note(cover, "1 分钟", "开场不要从模型或工具名讲起。直接给结论：过去的 AI 工作流帮我写得更快；现在的工作流开始帮我更早暴露错误、更清楚地做取舍，并把结论交给下游继续执行。今天用两个真实交付物证明这一点。", ["本地文件：workspace/华为PPT模板-浅色版.pptx", "本地案例：手机图库 AI 功能需求问卷；鸿蒙图库一句话清理图片产品方案决策汇报"]);

// 2 Executive summary
await contentPage(content[0], "comparison", "AI 工作流的收益来自四类风险被前置控制", "不是更快生成四份文档，而是更早阻止四次错误决策", (s, b) => {
  const cols = [
    ["事实风险", "证据与版本", "不再把“没搜到”写成“不支持”", C.blue],
    ["决策风险", "规则与取舍", "每个结论必须回答做不做、先做什么", C.red],
    ["交接风险", "文件与状态", "下游读取确定产物，不依赖上轮聊天记忆", C.green],
    ["上线风险", "门禁与退出", "先验证误选、理解、性能、隐私，再立项", C.amber],
  ];
  cols.forEach((it, i) => {
    const x = 82 + i * 279;
    bodyText(s, b, `0${i + 1}`, x, 174, 48, 28, { size: 15, bold: true, color: it[3] });
    bodyLine(s, b, x, 212, 238, 1, C.line);
    bodyText(s, b, it[0], x, 228, 238, 44, { size: 25, bold: true, color: C.ink });
    bodyText(s, b, it[1], x, 278, 238, 30, { size: 17, bold: true, color: it[3] });
    bodyText(s, b, it[2], x, 320, 238, 100, { size: 17, color: C.body, lineSpacing: 1.15 });
  });
  bodyBox(s, b, 82, 482, 1116, 116, C.black, "none", 0, 0);
  bodyText(s, b, "产品经理的核心产出，从“文档”升级为“可验证的决策系统”", 108, 500, 760, 38, { size: 25, bold: true, color: C.white });
  bodyText(s, b, "证据可追溯  ·  范围可解释  ·  异常可恢复  ·  失败可停损", 108, 548, 980, 30, { size: 17, color: "#FFFFFF/78" });
}, [{type:"comparison",count:4},{type:"constraint",count:2},{type:"action",count:2}], {timing:"2 分钟", body:"这四类风险是全场的导航。后面每个案例不比较‘AI 写得快不快’，而是看它是否改变了产品决策：是否避免了错误事实、是否把优先级规则写清、是否让研究和方案能继续被下游使用、是否设置了退出条件。"}, ["本地工作区案例归纳；不包含外部市场数据"]);

// 3 Evolution
await contentPage(content[1], "timeline", "四次演变，本质是把控制权逐层移出聊天框", "每一层保留上一层能力，同时补上新的交付契约", (s, b) => {
  const stages = [
    ["Prompt", "回答契约", "意图、角色、格式", "仍依赖模型临场记忆", "会提问"],
    ["Context", "证据契约", "资料、版本、状态", "知道事实但不能行动", "会组织证据"],
    ["Agent", "行动契约", "工具选择与循环", "能行动但可能失控", "会委派与验收"],
    ["Harness", "交付契约", "权限、门禁、恢复、审计", "需要持续治理", "会设计工作系统"],
  ];
  stages.forEach((it, i) => {
    const x = 82 + i * 279;
    const active = i === 3;
    bodyBox(s, b, x, 188, 246, 300, active ? C.redSoft : C.surface, active ? C.red : C.line, active ? 2 : 1, 8);
    bodyText(s, b, it[0], x + 18, 204, 210, 38, { size: 26, bold: true, color: active ? C.red : C.ink });
    bodyText(s, b, it[1], x + 18, 250, 210, 26, { size: 16, bold: true, color: active ? C.red : C.blue });
    bodyLine(s, b, x + 18, 288, 210, 1, C.line);
    bodyText(s, b, it[2], x + 18, 300, 210, 56, { size: 17, bold: true, color: C.ink });
    bodyText(s, b, it[3], x + 18, 370, 210, 54, { size: 15, color: C.body });
    bodyText(s, b, `PM：${it[4]}`, x + 18, 442, 210, 28, { size: 15, bold: true, color: active ? C.red : C.body });
    if (i < 3) bodyText(s, b, "→", x + 248, 310, 28, 46, { size: 28, bold: true, color: C.red, align: "center" });
  });
  bodyText(s, b, "关键变化：上下文不再只是“喂资料”，而是把证据、任务状态和质量标准变成可被工具读取的外部对象。", 82, 526, 1116, 66, { size: 19, bold: true, color: C.ink, align: "center" });
}, [{type:"diagramNode",count:8},{type:"comparison",count:2},{type:"constraint",count:2}], {timing:"3 分钟", body:"不要把这张图讲成四代产品史。讲控制权：Prompt 只控制一次回答；Context 控制模型能看到什么；Agent 控制能做什么；Harness 控制在什么权限、状态和验证条件下完成。PM 的能力也从写提示词，升级到设计任务、证据和验收系统。"}, ["基于本次工作流实践的阶段归纳"]);

// 4 Agent tools
await contentPage(content[2], "diagram", "Agent 工具从回答器演变为有门禁的执行环境", "真正的分水岭不是能否调用工具，而是任务是否可恢复、可验证、可审计", (s, b) => {
  bodyLine(s, b, 128, 430, 998, 0, C.line, 3);
  const pts = [
    ["对话助手", "生成回答", 148, 340, C.muted],
    ["知识助手", "检索资料", 358, 302, C.blue],
    ["工具 Agent", "搜索/计算/写文件", 570, 258, C.amber],
    ["工作区 Agent", "跨文件执行与交接", 782, 214, C.green],
    ["Harness", "权限/状态/门禁/恢复", 994, 170, C.red],
  ];
  pts.forEach((p, i) => {
    bodyBox(s, b, p[2], 414, 22, 22, p[4], "none", 0, 11);
    bodyText(s, b, p[0], p[2] - 58, p[3], 140, 28, { size: 18, bold: true, color: C.ink, align: "center" });
    bodyText(s, b, p[1], p[2] - 70, p[3] + 32, 164, 36, { size: 14, color: C.body, align: "center" });
  });
  bodyText(s, b, "自动化程度 →", 966, 472, 160, 26, { size: 14, bold: true, color: C.muted, align: "right" });
  bodyText(s, b, "PM 的价值变化", 82, 524, 180, 26, { size: 16, bold: true, color: C.red });
  bodyText(s, b, "写提示词", 260, 522, 140, 30, { size: 17, bold: true, color: C.body, align: "center" });
  bodyText(s, b, "组织证据", 454, 522, 140, 30, { size: 17, bold: true, color: C.body, align: "center" });
  bodyText(s, b, "定义动作", 648, 522, 140, 30, { size: 17, bold: true, color: C.body, align: "center" });
  bodyText(s, b, "设计门禁", 842, 522, 140, 30, { size: 17, bold: true, color: C.red, align: "center" });
  bodyText(s, b, "← 单次内容质量                                      端到端任务可靠性 →", 260, 570, 722, 26, { size: 14, color: C.muted, align: "center" });
}, [{type:"diagramNode",count:8},{type:"comparison",count:2},{type:"annotation",count:2}], {timing:"2 分钟", body:"工具演变只讲一条线：从回答、检索、工具调用到工作区执行。到 Harness 阶段，Agent 不只是会用浏览器或写文件，而是知道输入输出契约、权限边界、失败停止、恢复方式和验收门槛。这才对应产品经理真正可托付的任务。"}, ["基于对话式、检索式、工具调用与工作区 Agent 的能力抽象"]);

// 5 section 1
sectionPage(section1, "01", "用户研究：把意见收集改造成决策证据", "真实案例：手机图库 AI 功能使用与需求调研｜12 题｜原始需求洞察", "CASE 01 / USER RESEARCH");
note(section1, "0.5 分钟", "第一部分只回答一个问题：为什么问卷不是让 AI 多写一些题，而是让产品经理把要做的决策、需要的证据和题目顺序事先写清。", ["pm-user-research/用户调研/20260913手机图库AI功能需求/questionnaire.md"]);

// 6 research brief
await contentPage(content[3], "comparison", "功能意愿不能直接支持图库 AI 的优先级决策", "“你想要什么”只能得到愿望清单；优先级需要行为、问题、后果与强制取舍", (s, b) => {
  bodyText(s, b, "表面提问", 82, 180, 220, 30, { size: 16, bold: true, color: C.muted });
  bodyText(s, b, "用户最想要哪些\n图库 AI 功能？", 82, 218, 300, 94, { size: 30, bold: true, color: C.ink, lineSpacing: 1.05 });
  bodyText(s, b, "→", 392, 248, 64, 50, { size: 34, bold: true, color: C.red, align: "center" });
  bodyText(s, b, "真正要支持的 4 个决策", 474, 180, 430, 30, { size: 18, bold: true, color: C.red });
  const qs = [
    ["01", "有没有真实发生", "过去 3 个月是否使用，最近一次完成什么任务"],
    ["02", "问题是否足够痛", "遇到什么问题，造成返工、换工具还是放弃"],
    ["03", "只能做一个时选谁", "功能广度之后强制 Top 1，并追问原因"],
    ["04", "方案要加什么边界", "误删、隐私、时延等问题怎样改变交互"],
  ];
  qs.forEach((q, i) => {
    const y = 220 + i * 72;
    bodyText(s, b, q[0], 474, y, 40, 26, { size: 14, bold: true, color: C.red });
    bodyText(s, b, q[1], 526, y, 214, 28, { size: 19, bold: true, color: C.ink });
    bodyText(s, b, q[2], 754, y, 420, 38, { size: 15, color: C.body });
    if (i < 3) bodyLine(s, b, 474, y + 54, 700, 1, C.line);
  });
  bodyBox(s, b, 82, 528, 1116, 72, C.redSoft, "none", 0, 0);
  bodyText(s, b, "普通提示词最容易漏掉：非用户分流、互斥选项、题间关联、分析用途和“若结果出现 X，产品做什么”。", 104, 542, 1072, 42, { size: 18, bold: true, color: C.red });
}, [{type:"comparison",count:4},{type:"constraint",count:3},{type:"action",count:2}], {timing:"2.5 分钟", body:"这页先把业务问题讲透。直接问偏好会得到每个功能都有人选，无法支持资源取舍。真正需要回答四件事：是否真实发生、问题是否够痛、只能做一个时选谁、体验风险会如何改变方案。Skill 的第一价值不是写题，而是阻止研究目标继续含糊。"}, ["pm-user-research/用户调研/20260913手机图库AI功能需求/questionnaire.md"]);

// 7 evidence map
await contentPage(content[4], "process", "Skill 先建立决策—证据—题目映射，再允许写题", "每道题都必须说明分析用途和可能触发的产品动作", (s, b) => {
  const rows = [
    ["是否存在真实需求", "近期使用频率 + 最近一次任务", "Q4 / Q6", "区分真实行为与概念兴趣"],
    ["问题是否值得解决", "问题类型 + 后果", "Q7 / Q8", "识别效果问题还是信任问题"],
    ["优先做哪个功能", "需求广度 + 强制 Top 1 + 原因", "Q9 / Q10 / Q11", "形成可解释的优先级假设"],
    ["在哪个场景切入", "任务发生的具体情境", "Q12", "确定入口、触发和 MVP 场景"],
  ];
  bodyText(s, b, "产品决策", 96, 176, 220, 30, { size: 16, bold: true, color: C.muted });
  bodyText(s, b, "所需证据", 350, 176, 330, 30, { size: 16, bold: true, color: C.muted });
  bodyText(s, b, "题目", 718, 176, 180, 30, { size: 16, bold: true, color: C.muted });
  bodyText(s, b, "决策用途", 914, 176, 250, 30, { size: 16, bold: true, color: C.muted });
  rows.forEach((r, i) => {
    const y = 218 + i * 86;
    bodyBox(s, b, 82, y, 1116, 72, i === 2 ? C.redSoft : (i % 2 ? C.white : C.surface), i === 2 ? C.red : "none", i === 2 ? 1 : 0, 6);
    bodyText(s, b, r[0], 96, y + 10, 220, 48, { size: 18, bold: true, color: C.ink });
    bodyText(s, b, r[1], 350, y + 10, 330, 48, { size: 16, color: C.body });
    bodyText(s, b, r[2], 718, y + 10, 180, 48, { size: 17, bold: true, color: C.red });
    bodyText(s, b, r[3], 914, y + 10, 250, 48, { size: 15, color: C.body });
  });
  bodyText(s, b, "删除规则：无法说明决策用途的题目，不进入问卷。", 82, 580, 1116, 34, { size: 19, bold: true, color: C.red, align: "center" });
}, [{type:"comparison",count:4},{type:"action",count:4},{type:"constraint",count:2}], {timing:"3 分钟", body:"逐行讲，不要快速掠过。强调问卷的设计顺序：先写产品决策，再写需要看到的证据，最后才写题。比如 Q7/Q8 不是为了丰富报告，而是判断到底该提升识别效果，还是先解决误删、撤销与信任问题。"}, ["pm-user-research/skills/ur-design-survey/SKILL.md", "pm-user-research/用户调研/20260913手机图库AI功能需求/questionnaire.md"]);

// 8 survey flow
await contentPage(content[5], "process", "行为先于概念，使用者分流避免把想象当经历", "Q4 是关键路由：有经历的人谈最近任务，无经历的人直接进入未来诉求", (s, b) => {
  bodyBox(s, b, 82, 184, 170, 90, C.surface, C.line, 1, 8);
  bodyText(s, b, "Q1–Q3", 98, 198, 138, 24, { size: 15, bold: true, color: C.red });
  bodyText(s, b, "基本分层", 98, 228, 138, 30, { size: 20, bold: true, color: C.ink });
  bodyText(s, b, "→", 260, 208, 50, 50, { size: 30, bold: true, color: C.red, align: "center" });
  bodyBox(s, b, 318, 184, 190, 90, C.redSoft, C.red, 2, 8);
  bodyText(s, b, "Q4", 336, 198, 150, 24, { size: 15, bold: true, color: C.red });
  bodyText(s, b, "近 3 月使用频率", 336, 228, 150, 30, { size: 19, bold: true, color: C.ink });
  bodyText(s, b, "↙", 492, 270, 80, 60, { size: 30, bold: true, color: C.red, align: "center" });
  bodyText(s, b, "↘", 596, 270, 80, 60, { size: 30, bold: true, color: C.red, align: "center" });
  bodyBox(s, b, 282, 336, 366, 172, C.blueSoft, C.blue, 1, 8);
  bodyText(s, b, "有近期使用经历", 304, 350, 320, 30, { size: 20, bold: true, color: C.blue });
  bodyText(s, b, "Q5 用过哪些功能\nQ6 最近一次任务\nQ7 遇到什么问题\nQ8 问题造成什么后果", 304, 390, 320, 100, { size: 17, color: C.ink, lineSpacing: 1.12 });
  bodyBox(s, b, 684, 336, 366, 172, C.amberSoft, C.amber, 1, 8);
  bodyText(s, b, "无近期经历 / 从未使用", 706, 350, 320, 30, { size: 20, bold: true, color: C.amber });
  bodyText(s, b, "不要求评价实际体验\n直接进入 Q9–Q12\n只收集未来需求与发生场景", 706, 398, 320, 80, { size: 17, color: C.ink, lineSpacing: 1.15 });
  bodyText(s, b, "↓ 两条路径最终汇合到需求广度、强制优先级、原因与场景", 310, 540, 714, 34, { size: 18, bold: true, color: C.red, align: "center" });
  bodyText(s, b, "PM 价值：避免让从未用过的人评价准确性、速度或撤销体验。", 82, 594, 1116, 28, { size: 17, bold: true, color: C.ink, align: "center" });
}, [{type:"diagramNode",count:7},{type:"constraint",count:3},{type:"action",count:2}], {timing:"3 分钟", body:"这页讲问卷逻辑里最容易被生成式 AI 忽略的地方：没有使用过的人，没有资格回答最近一次体验。Q4 负责路由；有经历者进入 Q5–Q8 的行为链，无经历者只回答未来诉求。这样可以避免把想象当体验证据。"}, ["pm-user-research/用户调研/20260913手机图库AI功能需求/questionnaire.md", "pm-user-research/skills/ur-design-survey/references/questionnaire-logic-checklist.md"]);

// 9 interpretation rules
await contentPage(content[6], "comparison", "四连问把“想要”转成可执行的优先级假设", "这里展示的是预注册分析规则，不是尚未采集的用户结论", (s, b) => {
  const steps = [
    ["Q9", "需求广度", "最多选 3 项", C.blue],
    ["Q10", "强制取舍", "只能优先 1 项", C.red],
    ["Q11", "选择原因", "频率 / 耗时 / 复杂 / 无工具", C.amber],
    ["Q12", "发生场景", "空间不足 / 大量整理 / 快速选片", C.green],
  ];
  steps.forEach((it, i) => {
    const x = 82 + i * 279;
    bodyText(s, b, it[0], x, 182, 58, 28, { size: 15, bold: true, color: it[3] });
    bodyText(s, b, it[1], x, 216, 238, 36, { size: 23, bold: true, color: C.ink });
    bodyText(s, b, it[2], x, 258, 238, 46, { size: 15, color: C.body });
    if (i < 3) bodyText(s, b, "→", x + 232, 222, 38, 38, { size: 28, bold: true, color: C.red, align: "center" });
  });
  bodyLine(s, b, 82, 326, 1116, 1, C.line);
  bodyText(s, b, "若结果组合出现……", 82, 346, 250, 28, { size: 17, bold: true, color: C.muted });
  const rules = [
    ["清理无用照片 + 步骤复杂 + 存储不足", "优先验证低步骤清理入口，而不是扩充 AI 效果库"],
    ["误删/无法撤销 + 信任下降/放弃使用", "PRD 必须增加候选预览、显式确认、回收站与恢复"],
    ["识别不准 + 反复调整", "先定义候选误选率与可解释理由，再谈一键执行"],
  ];
  rules.forEach((r, i) => {
    const y = 386 + i * 66;
    bodyText(s, b, "IF", 82, y, 44, 30, { size: 14, bold: true, color: C.red });
    bodyText(s, b, r[0], 132, y, 420, 38, { size: 16, bold: true, color: C.ink });
    bodyText(s, b, "THEN", 578, y, 66, 30, { size: 14, bold: true, color: C.red });
    bodyText(s, b, r[1], 654, y, 520, 38, { size: 16, color: C.body });
  });
}, [{type:"diagramNode",count:4},{type:"action",count:3},{type:"constraint",count:3}], {timing:"3 分钟", body:"这里一定说明：这些不是问卷结果，而是发放前写好的解释规则。预注册的好处是减少看到数据后随意讲故事。示例一：如果优先项是清理，原因是步骤复杂，场景是空间不足，才支持验证更短的清理链路。示例二：如果误删担忧直接造成信任下降，方案边界就必须改变。"}, ["pm-user-research/用户调研/20260913手机图库AI功能需求/questionnaire.md；本页为基于题目结构设计的分析规则"]);

// 10 outputs and gate
await contentPage(content[7], "diagram", "三份交付物和结构门禁让问卷成为协作资产", "同一 Markdown 事实源派生评审、平台配置和校验结果，减少版本漂移", (s, b) => {
  const outs = [
    ["questionnaire.md", "事实源", "题目、选项、分支和配置注记"],
    ["questionnaire-design.html", "评审版", "研究目标、题目逻辑与可视化浏览"],
    ["questionnaire_for_userclub.txt", "配置版", "可直接交给问卷平台录入"],
  ];
  outs.forEach((o, i) => {
    const x = 82 + i * 326;
    bodyText(s, b, `0${i + 1}`, x, 184, 44, 24, { size: 14, bold: true, color: C.red });
    bodyText(s, b, o[0], x, 218, i === 2 ? 430 : 290, 34, { size: i === 2 ? 16 : 19, bold: true, color: C.ink });
    bodyText(s, b, o[1], x, 258, 290, 26, { size: 15, bold: true, color: C.red });
    bodyText(s, b, o[2], x, 294, 290, 70, { size: 16, color: C.body });
    if (i < 2) bodyText(s, b, "→", x + 292, 248, 30, 40, { size: 26, bold: true, color: C.red, align: "center" });
  });
  bodyBox(s, b, 82, 404, 1116, 166, C.black, "none", 0, 0);
  bodyText(s, b, "真实结构检查", 108, 422, 210, 30, { size: 17, bold: true, color: "#FFFFFF/70" });
  bodyText(s, b, "12", 108, 458, 150, 62, { size: 50, bold: true, color: C.white });
  bodyText(s, b, "题", 200, 476, 50, 30, { size: 18, bold: true, color: C.white });
  bodyText(s, b, "0", 354, 458, 120, 62, { size: 50, bold: true, color: C.white });
  bodyText(s, b, "结构风险信号", 410, 476, 180, 30, { size: 18, bold: true, color: C.white });
  bodyText(s, b, "PASS", 700, 464, 170, 52, { size: 34, bold: true, color: "#5FD18A" });
  bodyText(s, b, "通过结构门禁", 862, 476, 230, 30, { size: 18, bold: true, color: C.white });
  bodyText(s, b, "注意：通过结构检查 ≠ 问卷已证明效度；仍需研究员复核、认知访谈和小样本试填。", 108, 530, 984, 28, { size: 15, color: "#FFFFFF/72" });
}, [{type:"diagramNode",count:4},{type:"metric",count:3},{type:"constraint",count:2}], {timing:"2.5 分钟", body:"交付物不是三个各自维护的文档。questionnaire.md 是事实源，HTML 用于评审，UserClub 文本用于配置。脚本对真实问卷给出的结果是 12 题、0 个结构风险信号、通过。但我会明确说，Lint 只能检查可确定的结构问题，不能替代研究效度判断。"}, ["pm-user-research/用户调研/20260913手机图库AI功能需求/questionnaire.md", "pm-user-research/skills/ur-design-survey/scripts/lint_questionnaire.py"]);

// 11 real failure
await contentPage(content[8], "comparison", "Harness 在假洞察产生前暴露真实契约错误", "合成调研的正确用途是试跑逻辑与管线，而不是制造看似精确的市场比例", (s, b) => {
  bodyText(s, b, "43", 82, 182, 150, 80, { size: 64, bold: true, color: C.ink });
  bodyText(s, b, "项测试", 194, 218, 110, 30, { size: 18, bold: true, color: C.body });
  bodyText(s, b, "28", 332, 182, 130, 80, { size: 64, bold: true, color: C.green });
  bodyText(s, b, "通过", 432, 218, 80, 30, { size: 18, bold: true, color: C.green });
  bodyText(s, b, "15", 548, 182, 130, 80, { size: 64, bold: true, color: C.red });
  bodyText(s, b, "失败", 648, 218, 80, 30, { size: 18, bold: true, color: C.red });
  bodyText(s, b, "不是模型答错，而是接口契约错", 790, 196, 390, 58, { size: 23, bold: true, color: C.ink, align: "right" });
  bodyLine(s, b, 82, 286, 1116, 1, C.line);
  const rows = [
    ["测试要求", "画像生成命令支持 sample-size / seed / group-quota"],
    ["当前实现", "generate_personas.py 未接受这些参数；Windows 中文错误输出还出现乱码"],
    ["若无门禁", "样本配额不可复现，仍可能继续生成答卷和报告，形成“假稳定”"],
    ["修复顺序", "先统一 CLI 与文件契约 → 再重跑画像 → 再允许模拟与报告"],
  ];
  rows.forEach((r, i) => {
    const y = 314 + i * 66;
    bodyText(s, b, r[0], 82, y, 150, 34, { size: 16, bold: true, color: i === 2 ? C.red : C.ink });
    bodyText(s, b, r[1], 246, y, 930, 42, { size: 16, color: i === 2 ? C.red : C.body });
  });
  bodyBox(s, b, 82, 584, 1116, 42, C.redSoft, "none", 0, 0);
  bodyText(s, b, "PM 价值：阻断错误样本进入“漂亮报告”，把返工从结论阶段提前到接口阶段。", 100, 590, 1080, 28, { size: 18, bold: true, color: C.red, align: "center" });
}, [{type:"metric",count:3},{type:"comparison",count:3},{type:"risk",count:2},{type:"action",count:2}], {timing:"2.5 分钟", body:"这是最重要的失败案例。43 项测试里 15 项失败，原因不是内容质量，而是画像生成脚本没有实现测试规定的三个参数。若没有 Harness，系统可能继续往下生成答卷和报告，最终让团队讨论一份不可复现的结果。门禁在这里替 PM 做的是阻断，而不是润色。"}, ["pm-user-research/tests/test_project.py", "pm-user-research/skills/ur-generate-personas/scripts/generate_personas.py", "本地测试结果：43 tests / 28 pass / 15 fail"]);

// 12 section 2
sectionPage(section2, "02", "产品方案：把自然语言能力收敛成可控决策", "真实案例：鸿蒙图库“一句话清理图片”｜竞品证据 × PRD × 原型 × 阶段门", "CASE 02 / PRODUCT DECISION");
note(section2, "0.5 分钟", "第二部分换一个视角：Agent 不只是加速研究，它也能帮助产品经理把一句卖点拆成责任边界、风险等级、异常状态和退出条件。", ["workspace/鸿蒙图库_一句话清理图片_产品方案决策汇报.pptx"]);

// 13 reframe
await contentPage(content[9], "mixed", "一句话删除被重构为责任可控的自动化决策", "系统负责生成可解释候选，用户保留最终删除责任，并获得恢复兜底", async (s, b) => {
  bodyText(s, b, "原始卖点", 82, 180, 180, 28, { size: 16, bold: true, color: C.muted });
  bodyText(s, b, "“说完即完成”", 82, 218, 340, 50, { size: 28, bold: true, color: C.ink });
  bodyText(s, b, "自然语言一旦缺少对象、条件或范围，效率优势就会放大成误删责任。", 82, 282, 350, 82, { size: 17, color: C.body });
  bodyText(s, b, "产品决策", 82, 390, 180, 28, { size: 16, bold: true, color: C.red });
  bodyText(s, b, "搜索 → 解释预览\n→ 显式确认 → 可撤销执行", 82, 428, 350, 92, { size: 24, bold: true, color: C.red, lineSpacing: 1.05 });
  bodyBox(s, b, 82, 548, 350, 58, C.black, "none", 0, 0);
  bodyText(s, b, "只批准方向与验证资源，不批准工程立项", 98, 556, 318, 42, { size: 15, bold: true, color: C.white, align: "center" });
  bodyBox(s, b, 468, 176, 730, 420, C.white, C.line, 1, 4);
  await bodyImage(s, b, CASE_IMG(2), 480, 188, 706, 396, "真实交付物：产品决策基础页");
}, [{type:"comparison",count:3},{type:"risk",count:2},{type:"action",count:3},{type:"source",count:1}], {timing:"3 分钟", body:"先展示真实交付物，而不是重讲整份方案。最关键的产品判断是：不做一句话直接删除。系统只承担可解释候选生成，最终删除仍需用户确认，并默认进入回收站。这样既保留效率价值，也限制了 AI 承担不了的责任。"}, ["workspace/鸿蒙图库_一句话清理图片_产品方案决策汇报.pptx，第 2 页；其中机制与阈值为待验证产品假设"]);

// 14 evidence contract
await contentPage(content[10], "process", "竞品结论必须先成为证据记录，才能进入 PRD", "“没找到”不等于“不支持”；未知与冲突也必须作为正式结果交付", (s, b) => {
  const flow = [
    ["ResearchUnit", "竞品 × Feature", "例：某图库 × 重复照片清理"],
    ["EvidenceRecord", "主张 + 来源 + 版本 + 地区", "记录支持/反对方向与原文事实"],
    ["Confidence", "A / B / C", "官方直接证据优先；间接证据降级"],
    ["Decision Input", "事实 / 推断 / 建议分栏", "只有可追溯事实进入 PRD 基线"],
  ];
  flow.forEach((f, i) => {
    const x = 82 + i * 279;
    bodyText(s, b, `0${i + 1}`, x, 180, 44, 24, { size: 14, bold: true, color: C.red });
    bodyText(s, b, f[0], x, 214, 240, 34, { size: 21, bold: true, color: C.ink });
    bodyText(s, b, f[1], x, 254, 240, 28, { size: 16, bold: true, color: C.red });
    bodyText(s, b, f[2], x, 292, 240, 72, { size: 15, color: C.body });
    if (i < 3) bodyText(s, b, "→", x + 238, 240, 34, 40, { size: 28, bold: true, color: C.red, align: "center" });
  });
  bodyLine(s, b, 82, 392, 1116, 1, C.line);
  bodyText(s, b, "检索停止规则", 82, 414, 200, 30, { size: 18, bold: true, color: C.ink });
  pill(s, b, "Tier 1 当前版本直接证据", 82, 462, 300, C.greenSoft, C.green, C.green);
  pill(s, b, "两条独立 Tier 2/3 证据一致", 408, 462, 334, C.blueSoft, C.blue, C.blue);
  pill(s, b, "达到上限仍冲突 → UNKNOWN", 768, 462, 360, C.redSoft, C.red, C.red);
  bodyText(s, b, "案例中的价值：若竞品撤销期限、端侧处理或人物语义没有直接证据，就不能被写成行业基线；它只能进入待核验清单。", 82, 532, 1116, 66, { size: 18, bold: true, color: C.ink, align: "center" });
}, [{type:"diagramNode",count:5},{type:"constraint",count:4},{type:"risk",count:2}], {timing:"3 分钟", body:"竞品分析最危险的不是漏一个功能，而是把搜索不到写成对方不支持，或把旧版本、其他地区的能力当成当前基线。Skill 把每个竞品和 Feature 变成 ResearchUnit，再要求 EvidenceRecord 记录来源、版本、地区、支持方向和置信度。未知就是未知，不强行填满矩阵。"}, ["pm-competitor-analysis/pm-system-app-competitor-matrix/SKILL.md", "pm-competitor-analysis/pm-system-app-competitor-matrix/references/research-evidence.md"]);

// 15 scope cuts
await contentPage(content[11], "comparison", "风险分层让六类请求收敛为低歧义 MVP", "功能范围不按“能不能识别”划分，而按误删后果、可解释性和可恢复性划分", (s, b) => {
  const bands = [
    ["低风险：进入确认执行", "时间 / 明确类型", "删除上个月截图｜清理明确重复组", C.greenSoft, C.green],
    ["中风险：解释后确认", "质量 / 组合条件", "模糊判定需说明理由｜候选集过大需二次缩小", C.amberSoft, C.amber],
    ["高风险：仅筛选不删除", "人物 / 票据 / 私密 / 事件", "不提供一句话直接执行；提示降级原因", C.redSoft, C.red],
  ];
  bands.forEach((it, i) => {
    const y = 184 + i * 118;
    bodyBox(s, b, 82, y, 1116, 94, it[3], "none", 0, 6);
    bodyText(s, b, it[0], 104, y + 14, 286, 30, { size: 20, bold: true, color: it[4] });
    bodyText(s, b, it[1], 420, y + 14, 250, 30, { size: 18, bold: true, color: C.ink });
    bodyText(s, b, it[2], 690, y + 12, 484, 52, { size: 16, color: C.body });
  });
  bodyText(s, b, "砍掉的不是能力，而是未经验证的执行权", 82, 560, 560, 38, { size: 24, bold: true, color: C.red });
  bodyText(s, b, "MVP 先验证用户能否理解候选范围，再决定是否扩大自动化。", 658, 562, 520, 34, { size: 17, bold: true, color: C.ink, align: "right" });
}, [{type:"comparison",count:3},{type:"risk",count:3},{type:"action",count:3}], {timing:"3 分钟", body:"这一页要讲具体砍法。六类自然语言请求并不是都放进 MVP：时间和明确类型可进入预览确认；模糊、重复等质量语义必须解释理由；人物、票据、私密和事件语义只返回筛选结果。产品经理真正增加的不是功能数，而是对执行权的分层。"}, ["workspace/鸿蒙图库_一句话清理图片_产品方案决策汇报.pptx，第 3、6、8 页；属于待验证范围设计"]);

// 16 PRD ledger
await contentPage(content[12], "table", "PRD 是证据、规则、状态与验收的决策账本", "每条需求都能追溯到风险假设，并明确异常状态与可观察验收", (s, b) => {
  const heads = [["证据 / 假设", 250], ["产品规则", 286], ["状态与异常", 250], ["验收口径", 330]];
  let x = 82;
  heads.forEach((h) => { bodyBox(s, b, x, 176, h[1], 44, C.black); bodyText(s, b, h[0], x + 12, 184, h[1] - 24, 28, { size: 16, bold: true, color: C.white }); x += h[1]; });
  const rows = [
    ["自然语言缺少对象/条件/范围", "缺失项必须追问，不自动补全删除范围", "解析不完整", "任何异常分支不绕过确认"],
    ["用户难以核对系统选择", "预览展示原词、条件、数量、分组与命中理由", "正常 / 候选过大", "执行前用户可复述选择范围"],
    ["删除后果高且可能误选", "显式确认；默认进入回收站；保留稳定恢复入口", "确认 / 执行 / 撤销", "执行后可在稳定入口恢复"],
    ["人物、票据等敏感对象", "高风险请求降级为筛选，不出现执行按钮", "高风险降级", "不得以高置信度跳过确认"],
  ];
  rows.forEach((r, ri) => {
    const y = 220 + ri * 84;
    let xx = 82;
    r.forEach((cell, ci) => {
      const w = heads[ci][1];
      bodyBox(s, b, xx, y, w, 84, ri % 2 ? C.white : C.surface, C.line, 1);
      bodyText(s, b, cell, xx + 12, y + 10, w - 24, 64, { size: ci === 1 ? 16 : 15, bold: ci === 1, color: ci === 3 ? C.red : C.body, lineSpacing: 1.08 });
      xx += w;
    });
  });
  bodyText(s, b, "这张账本让用研、体验、算法、工程和隐私评审讨论同一条可验证链路。", 82, 572, 1116, 34, { size: 18, bold: true, color: C.ink, align: "center" });
}, [{type:"comparison",count:4},{type:"constraint",count:4},{type:"action",count:2}], {timing:"3 分钟", body:"这就是我希望 AI 帮忙生成的 PRD 核心，不是更多页面描述，而是一张 Requirement Ledger。每行从证据或风险假设出发，落到产品规则、状态异常和可观察验收。例如解析不完整时必须追问；高风险对象没有删除按钮；任何异常都不能绕过确认。"}, ["workspace/鸿蒙图库_一句话清理图片_产品方案决策汇报.pptx，第 4、5、6 页；本页为可追踪 PRD 账本重构"]);

// 17 prototype states
await contentPage(content[13], "process", "原型必须覆盖系统理解、执行后果与恢复入口", "正常主链路只是 1 个状态；真正决定可信度的是异常如何降级", (s, b) => {
  const steps = ["输入意图", "结构化解析", "检索候选", "解释预览", "显式确认", "执行与撤销"];
  steps.forEach((st, i) => {
    const x = 82 + i * 186;
    bodyBox(s, b, x, 188, 154, 96, i === 4 ? C.redSoft : C.surface, i === 4 ? C.red : C.line, i === 4 ? 2 : 1, 6);
    bodyText(s, b, `0${i + 1}`, x + 12, 198, 36, 20, { size: 13, bold: true, color: C.red });
    bodyText(s, b, st, x + 12, 226, 130, 38, { size: 17, bold: true, color: C.ink, align: "center" });
    if (i < 5) bodyText(s, b, "→", x + 154, 214, 32, 42, { size: 25, bold: true, color: C.red, align: "center" });
  });
  bodyText(s, b, "原型必须单独画出的 4 类状态", 82, 326, 320, 30, { size: 18, bold: true, color: C.ink });
  const states = [
    ["解析不完整", "返回可选条件，不擅自补全范围"],
    ["候选集过大", "按时间/来源/类型分组，要求二次缩小"],
    ["高风险对象", "仅提供筛选，并解释为什么不能直接执行"],
    ["执行失败/需恢复", "展示结果、回收站期限和稳定恢复入口"],
  ];
  states.forEach((st, i) => {
    const x = 82 + (i % 2) * 558;
    const y = 372 + Math.floor(i / 2) * 88;
    bodyBox(s, b, x, y, 530, 68, i === 2 ? C.redSoft : C.white, i === 2 ? C.red : C.line, 1, 6);
    bodyText(s, b, st[0], x + 16, y + 10, 150, 26, { size: 16, bold: true, color: i === 2 ? C.red : C.ink });
    bodyText(s, b, st[1], x + 174, y + 8, 340, 48, { size: 15, color: C.body });
  });
  bodyText(s, b, "原型测试的不是“看起来顺不顺”，而是用户能否解释范围、排除误选、理解降级并找到恢复。", 82, 570, 1116, 38, { size: 18, bold: true, color: C.red, align: "center" });
}, [{type:"diagramNode",count:8},{type:"risk",count:4},{type:"action",count:2}], {timing:"3 分钟", body:"讲原型时不要只放高保真图。原型的任务是把不确定性显性化：系统理解了什么、候选为什么被选中、执行会发生什么、失败后如何恢复。至少要画四类异常状态，并用任务测试验证用户能否复述范围、排除误选、理解降级、找到恢复。"}, ["workspace/鸿蒙图库_一句话清理图片_产品方案决策汇报.pptx，第 4 页；本页为原型状态测试清单"]);

// 18 gates
await contentPage(content[14], "mixed", "阶段门只批准下一步，阻止过早工程承诺", "方向、可用性、技术与隐私分别过门；任一红线失败即停止立项", async (s, b) => {
  bodyBox(s, b, 82, 178, 690, 390, C.white, C.line, 1, 4);
  await bodyImage(s, b, CASE_IMG(11), 94, 190, 666, 366, "真实交付物：分阶段验证与退出条件");
  const phases = [
    ["P0 方案冻结", "交互原型 / 意图词表 / 风险分级"],
    ["P1 可用性验证", "任务脚本 / 理解偏差 / 口径达标"],
    ["P2 技术预研", "端侧样机 / 索引能力 / 隐私红线"],
    ["P3 工程立项", "MVP / 灰度 / 监控 / 回滚"],
  ];
  phases.forEach((p, i) => {
    const y = 184 + i * 82;
    bodyText(s, b, p[0], 806, y, 356, 28, { size: 18, bold: true, color: i === 0 ? C.red : C.ink });
    bodyText(s, b, p[1], 806, y + 32, 356, 38, { size: 15, color: C.body });
  });
  bodyBox(s, b, 806, 526, 356, 74, C.black, "none", 0, 0);
  bodyText(s, b, "退出条件", 824, 536, 92, 24, { size: 15, bold: true, color: C.red });
  bodyText(s, b, "误选不可控 / 不可理解 / 性能不达标 / 隐私不过线", 824, 562, 318, 28, { size: 14, bold: true, color: C.white });
}, [{type:"diagramNode",count:5},{type:"constraint",count:4},{type:"action",count:2},{type:"source",count:1}], {timing:"2.5 分钟", body:"这页体现方案汇报的产品价值：本次不是批准完整开发，而是批准下一阶段资源。P0 输出可评审，P1 验证用户是否理解，P2 验证端侧和隐私，只有都通过才进 P3。退出条件必须提前写：误选不可控、无法理解、性能不达标或隐私不过线时停止立项。"}, ["workspace/鸿蒙图库_一句话清理图片_产品方案决策汇报.pptx，第 11 页；阶段门为方案建议"]);

// 19 skill development
await contentPage(content[15], "process", "Skill 要通过契约、资源、校验与评估才可复用", "不是把长提示词保存起来，而是把判断方法拆成可维护的系统", (s, b) => {
  const life = ["一次性提示词", "触发与输入契约", "步骤与停止条件", "references / templates", "scripts 门禁", "真实案例 eval", "版本与复盘"];
  life.forEach((v, i) => {
    const x = 82 + i * 158;
    bodyBox(s, b, x, 180, 132, 62, i === 4 ? C.redSoft : C.surface, i === 4 ? C.red : "none", i === 4 ? 1 : 0, 6);
    bodyText(s, b, v, x + 8, 190, 116, 42, { size: 14, bold: true, color: i === 4 ? C.red : C.ink, align: "center" });
    if (i < 6) bodyText(s, b, "→", x + 132, 192, 26, 38, { size: 20, bold: true, color: C.red, align: "center" });
  });
  bodyLine(s, b, 82, 270, 1116, 1, C.line);
  bodyText(s, b, "$ur-design-survey", 82, 292, 250, 30, { size: 20, bold: true, color: C.red });
  bodyText(s, b, "输入：课题 / 目标 / 场景 / 约束", 82, 332, 330, 28, { size: 15, color: C.body });
  bodyText(s, b, "方法：目标—证据—题目、分支与互斥规则", 82, 366, 470, 28, { size: 15, color: C.body });
  bodyText(s, b, "门禁：12 题、0 风险信号；效度仍需人工验证", 82, 400, 470, 28, { size: 15, bold: true, color: C.ink });
  bodyText(s, b, "$pm-system-app-competitor-matrix", 620, 292, 430, 30, { size: 20, bold: true, color: C.red });
  bodyText(s, b, "输入：研究问题 / 竞品 / FeatureSchema", 620, 332, 520, 28, { size: 15, color: C.body });
  bodyText(s, b, "方法：ResearchUnit、EvidenceRecord、停止规则", 620, 366, 520, 28, { size: 15, color: C.body });
  bodyText(s, b, "门禁：事实、冲突、未知分栏；证据等级保留", 620, 400, 520, 28, { size: 15, bold: true, color: C.ink });
  bodyBox(s, b, 82, 462, 1116, 74, C.black, "none", 0, 0);
  bodyText(s, b, "Command 不是“魔法咒语”", 104, 474, 280, 30, { size: 17, bold: true, color: C.white });
  bodyText(s, b, "$ur-design-survey 课题：手机图库 AI；目标：识别高频任务、问题与 Top 1；场景：原始需求洞察；≤12 题", 394, 470, 776, 38, { size: 15, color: "#FFFFFF/86" });
  bodyText(s, b, "组合方式：机会洞察/竞品追踪 → 用户研究/竞品矩阵 → 产品方案/PRD/原型 → 功能命名/微文案 → 指标与反馈复盘", 82, 560, 1116, 44, { size: 16, bold: true, color: C.ink, align: "center" });
}, [{type:"diagramNode",count:7},{type:"comparison",count:3},{type:"constraint",count:2},{type:"action",count:1}], {timing:"3 分钟", body:"最后讲开发方法。Skill 不是把长提示词保存起来，而是先定义触发和输入契约，再拆步骤与停止条件，把知识放到 references，把格式放到 templates，把可确定判断交给 scripts，最后用真实案例做 eval。Command 只是入口，真正的可复用性来自后面的契约和门禁。其他 Skill 不逐个介绍，而是沿产品生命周期组合。"}, ["pm-user-research/skills/ur-design-survey/SKILL.md", "pm-competitor-analysis/pm-system-app-competitor-matrix/SKILL.md", "README.md"]);

// 20 end
text(end, "把 AI 当同事之前，\n先把自己的判断系统写出来。", 82, 246, 660, 100, { size: 34, bold: true, color: C.ink, lineSpacing: 1.03 });
text(end, "1  先选一个高频、返工昂贵、质量可检查的任务\n2  把输入、证据、状态、输出和停止条件写成契约\n3  让脚本检查可确定的错误，让产品经理保留价值判断", 86, 380, 720, 112, { size: 18, color: C.body, lineSpacing: 1.18 });
text(end, "Q&A", 86, 532, 160, 36, { size: 24, bold: true, color: C.red });
pages.push({ kind: "end", sourceSlide: 5 });
compPages.push({ kind: "closing" });
note(end, "0.5 分钟 + Q&A", "收束到三条可执行建议。不要从“做一个万能 Agent”开始；先选高频、跨人协作、返工昂贵、质量可检查的任务。把自己的判断写成契约，再决定哪些部分交给模型、工具和脚本。", ["本次分享两个案例的总结"]);

// Audits
const templateAudit = auditHuaweiOfficialTemplateContract({
  templateSha256: "C6F6CC8245EBEC463396F1B35FE2700C34DC85EDFD2836509CDBDD7E23F00127",
  themeName: "2210",
  pages,
});
const compositionAudit = auditHuaweiDeckComposition(compPages, { density: "dense", requireMeasured: false });
console.log("TEMPLATE_AUDIT", JSON.stringify(templateAudit));
console.log("COMPOSITION_AUDIT", JSON.stringify(compositionAudit));
if (!templateAudit.ok) throw new Error(`Huawei template contract failed: ${templateAudit.warnings.join(" | ")}`);
if (!compositionAudit.ok) console.warn("Huawei composition warnings:", compositionAudit.warnings);

const candidatePath = path.join(STAGING, "candidate.pptx");
await (await PresentationFile.exportPptx(deck)).save(candidatePath);

const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools", "artifact_tool_utils.mjs")).href);
const result = await finalizePresentation({
  workspaceDir: ROOT,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "12196763,6858000",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
  ],
  explicitTotalSlideCount: 20,
  sourceTemplatePath: TEMPLATE,
  requiredTemplateReferenceSlides: [1, 2, 3, 5],
  minimumTemplateCoverageRatio: 0.9,
  requireExactTemplateDimensions: true,
  requireTemplatePlaceholderGeometry: true,
  requirePhotographicBackground: false,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
  fontPolicy: { basis: "design", families: ["Microsoft YaHei", "Arial"] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(STAGING, "AI产品经理工作流演变_真实案例深化版.validation.json"),
});
console.log("FINALIZER", JSON.stringify(result));
console.log("OUTPUT", FINAL_PPTX);
