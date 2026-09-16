import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = "E:\\projects\\korbin-pm-skills";
const SKILL_DIR = "C:\\Users\\mahai\\.codex\\plugins\\cache\\openai-primary-runtime\\presentations\\26.904.11930\\skills\\presentations";
const RUNTIME_PYTHON = "C:\\Users\\mahai\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe";
const TMP_DIR = path.join(workspaceDir, ".codex-ppt-build", "ai-pm-workflow");
const OUT_DIR = path.join(workspaceDir, "outputs", "ai-pm-workflow-share");
const FINAL_PPTX = path.join(OUT_DIR, "从会聊天到能交付_AI产品经理工作流演变_v2.pptx");
const heroPath = path.join(OUT_DIR, "assets", "workflow-evolution-hero.png");

await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(OUT_DIR, { recursive: true });

const W = 1280;
const H = 720;
const FONT = "Microsoft YaHei";
const C = {
  ink: "#13181D",
  paper: "#F4F0E8",
  paper2: "#EAE5DC",
  white: "#FFFFFF",
  red: "#E5483F",
  red2: "#B8322A",
  blue: "#3E718D",
  blue2: "#264F65",
  steel: "#87949C",
  muted: "#676F72",
  pale: "#D7D2C8",
  green: "#4E7B68",
  amber: "#B78136",
  dark2: "#20272D",
};

const presentation = Presentation.create({ slideSize: { width: W, height: H } });

function rect(slide, x, y, w, h, fill, radius = 0, lineFill = "none", lineWidth = 0) {
  return slide.shapes.add({
    geometry: radius ? "roundRect" : "rect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: lineFill === "none" ? { fill: "none", width: 0 } : { style: "solid", fill: lineFill, width: lineWidth },
    ...(radius ? { borderRadius: radius } : {}),
  });
}

function ellipse(slide, x, y, w, h, fill, lineFill = "none", lineWidth = 0) {
  return slide.shapes.add({
    geometry: "ellipse",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: lineFill === "none" ? { fill: "none", width: 0 } : { style: "solid", fill: lineFill, width: lineWidth },
  });
}

function line(slide, x, y, w, h, color = C.pale, width = 2, dash = "solid") {
  if (w < 0) { x += w; w = -w; }
  if (h < 0) { y += h; h = -h; }
  return slide.shapes.add({
    geometry: "line",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { style: dash, fill: color, width },
  });
}

function text(slide, value, x, y, w, h, opts = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  shape.text = value;
  shape.text.style = {
    typeface: opts.typeface ?? FONT,
    fontSize: opts.size ?? 24,
    bold: opts.bold ?? false,
    color: opts.color ?? C.ink,
    alignment: opts.align ?? "left",
    verticalAlignment: opts.valign ?? "middle",
    autoFit: "none",
    wrap: "square",
    insets: opts.insets ?? { left: 0, right: 0, top: 0, bottom: 0 },
    ...(opts.lineSpacing ? { lineSpacing: opts.lineSpacing } : {}),
  };
  return shape;
}

function addTitle(slide, title, section = "") {
  rect(slide, 56, 48, 8, 54, C.red);
  text(slide, title, 84, 42, 1050, 62, { size: 34, bold: true });
  if (section) text(slide, section, 1040, 54, 174, 28, { size: 14, bold: true, color: C.muted, align: "right" });
}

function addFooter(slide, n, dark = false) {
  const color = dark ? "#FFFFFF/58" : C.muted;
  text(slide, String(n).padStart(2, "0"), 1160, 670, 52, 22, { size: 13, bold: true, color, align: "right" });
}

function addNote(slide, note) {
  slide.speakerNotes.textFrame.setText(note);
}

function stageLabel(slide, n, label, x, y, color) {
  ellipse(slide, x, y, 54, 54, color);
  text(slide, n, x, y + 1, 54, 52, { size: 20, bold: true, color: C.white, align: "center" });
  text(slide, label, x + 70, y - 2, 220, 60, { size: 23, bold: true });
}

function tag(slide, label, x, y, w, fill = C.ink, color = C.white) {
  rect(slide, x, y, w, 34, fill, 17);
  text(slide, label, x, y, w, 34, { size: 15, bold: true, color, align: "center" });
}

// 1. Cover
{
  const slide = presentation.slides.add();
  slide.background.fill = C.ink;
  const hero = new Uint8Array(await fs.readFile(heroPath));
  slide.images.add({ blob: hero, contentType: "image/png", alt: "对话节点扩展为可执行工作系统的抽象主视觉", fit: "cover", position: { left: 0, top: 0, width: W, height: H } });
  rect(slide, 0, 0, 650, H, "#0D1116/86");
  rect(slide, 72, 100, 12, 92, C.red);
  text(slide, "从会聊天\n到能交付", 112, 94, 500, 190, { size: 56, bold: true, color: C.white, lineSpacing: 0.9 });
  text(slide, "我的 AI 产品经理工作流演变", 114, 306, 440, 54, { size: 25, color: "#FFFFFF/88" });
  line(slide, 114, 404, 304, 0, "#FFFFFF/32", 1);
  text(slide, "Prompt    Context    Agent    Harness", 114, 424, 440, 28, { size: 15, bold: true, color: "#FFFFFF/68" });
  text(slide, "产品经理团队分享  |  45 min", 114, 614, 360, 28, { size: 16, color: "#FFFFFF/60" });
  addNote(slide, "建议用时：1 分钟\n开场：过去一年，我不断更换 AI 使用方式。变化最大的并不是模型名称，而是我逐渐把工作方法变成了一个可执行、可检查的系统。今天分享这条演进路线，以及我如何把产品经理经验沉淀成 Skill。\n主视觉由图像生成工具制作，用于表达从单点对话到多工具工作系统的扩展。");
}

// 2. Same task, four modes
{
  const slide = presentation.slides.add(); slide.background.fill = C.paper;
  addTitle(slide, "同一个产品任务，四种完成方式", "开场");
  text(slide, "图库 AI 清理：需求研究、竞品判断、PRD 与原型", 84, 112, 900, 40, { size: 21, color: C.muted });
  const items = [
    ["01", "对话", "生成一份\n看起来完整的答案", C.steel],
    ["02", "上下文", "基于资料回答\n结论更贴近事实", C.blue],
    ["03", "Agent", "查、写、运行\n完成多步任务", C.red],
    ["04", "Harness", "按规则执行\n验证后再交付", C.ink],
  ];
  items.forEach((it, i) => {
    const x = 84 + i * 286;
    text(slide, it[0], x, 176, 72, 42, { size: 17, bold: true, color: it[3] });
    line(slide, x, 228, 230, 0, it[3], 5);
    text(slide, it[1], x, 252, 230, 52, { size: 31, bold: true });
    text(slide, it[2], x, 326, 228, 94, { size: 20, color: C.muted, lineSpacing: 1.15 });
  });
  rect(slide, 84, 494, 1112, 118, C.ink, 18);
  text(slide, "输出质量不仅由模型决定", 118, 510, 380, 42, { size: 27, bold: true, color: C.white });
  text(slide, "材料、工具、权限、规则和验证方式共同决定交付结果", 118, 558, 900, 30, { size: 20, color: "#FFFFFF/75" });
  addFooter(slide, 2);
  addNote(slide, "建议用时：2 分钟\n用一个大家熟悉的任务做对照。聊天框适合快速启动，加入检索后事实基础更好，Agent 可以真正行动，Harness 则让这些行动在稳定的边界里发生。\n互动问题：大家最近一次因为 AI 输出看起来正确、但无法直接交付而返工，问题出在哪里？");
}

// 3. Expanding control surface
{
  const slide = presentation.slides.add(); slide.background.fill = C.paper;
  addTitle(slide, "AI 工作流的四层控制面", "工作流演变");
  const bars = [
    ["回答", "这一轮怎么说", 360, C.steel],
    ["知识", "看见什么材料", 520, C.blue],
    ["行动", "如何调用工具", 720, C.red],
    ["系统", "在什么边界内完成", 960, C.ink],
  ];
  bars.forEach((b, i) => {
    const y = 156 + i * 104;
    rect(slide, 84, y, b[2], 72, b[3], 12);
    text(slide, b[0], 112, y + 6, 124, 58, { size: 27, bold: true, color: C.white });
    text(slide, b[1], 246, y + 7, b[2] - 180, 56, { size: 19, color: "#FFFFFF/78" });
  });
  text(slide, "Prompt", 1038, 164, 150, 28, { size: 16, bold: true, color: C.steel, align: "right" });
  text(slide, "Context / RAG", 1038, 268, 150, 28, { size: 16, bold: true, color: C.blue, align: "right" });
  text(slide, "Agent", 1038, 372, 150, 28, { size: 16, bold: true, color: C.red, align: "right" });
  text(slide, "Harness", 1038, 476, 150, 28, { size: 16, bold: true, color: C.ink, align: "right" });
  text(slide, "每次升级都保留前一层，并增加新的可控对象", 84, 612, 800, 36, { size: 22, bold: true });
  addFooter(slide, 3);
  addNote(slide, "建议用时：2 分钟\n这四层并非相互替代。好的 Agent 仍然需要好提示词，也需要好上下文。演变发生在控制面扩展：从回答、知识、行动到整个运行系统。后面的案例都可以放回这四层看。");
}

// 4. Prompt engineering
{
  const slide = presentation.slides.add(); slide.background.fill = C.paper;
  addTitle(slide, "第一阶段：提示词工程", "工作流演变");
  stageLabel(slide, "01", "把需求写清楚", 84, 142, C.steel);
  rect(slide, 84, 230, 586, 316, C.ink, 18);
  text(slide, "你是一名资深产品经理。\n\n请分析图库 AI 清理需求，输出：\n1. 用户痛点\n2. 核心场景\n3. 功能优先级\n\n参考下面示例格式……", 118, 256, 516, 250, { size: 21, color: "#FFFFFF/86", lineSpacing: 1.1 });
  text(slide, "得到什么", 738, 162, 180, 34, { size: 17, bold: true, color: C.blue });
  text(slide, "快速启动\n表达结构更稳定\n适合单次创作与分析", 738, 206, 430, 124, { size: 25, bold: true, lineSpacing: 1.2 });
  line(slide, 738, 358, 430, 0, C.pale, 1);
  text(slide, "为什么继续升级", 738, 386, 210, 34, { size: 17, bold: true, color: C.red });
  text(slide, "背景反复输入\n长对话逐渐漂移\n来源与质量难复查", 738, 430, 430, 124, { size: 23, color: C.muted, lineSpacing: 1.2 });
  addFooter(slide, 4);
  addNote(slide, "建议用时：2 分钟\n提示词工程让我第一次能稳定获得结构化内容。我逐渐形成角色、任务、格式、示例、限制等写法。瓶颈也很明显：同类任务每次重新写，资料散落在对话里，结果很难复查。\n这一阶段的关键经验是：提示词适合定义一轮回答，无法单独承担长任务的状态管理。");
}

// 5. Context / RAG
{
  const slide = presentation.slides.add(); slide.background.fill = C.paper;
  addTitle(slide, "第二阶段：上下文工程与 RAG", "工作流演变");
  stageLabel(slide, "02", "让模型看到正确材料", 84, 132, C.blue);
  const docs = ["历史 PRD", "用户反馈", "设计规范", "竞品证据"];
  docs.forEach((d, i) => {
    rect(slide, 92, 236 + i * 68, 180, 46, C.paper2, 8);
    text(slide, d, 108, 236 + i * 68, 150, 46, { size: 18, bold: true });
    line(slide, 272, 259 + i * 68, 114, (351 - (259 + i * 68)), C.pale, 2);
  });
  ellipse(slide, 390, 304, 126, 126, C.blue);
  text(slide, "检索", 390, 320, 126, 48, { size: 26, bold: true, color: C.white, align: "center" });
  text(slide, "分块 / 元数据", 390, 370, 126, 28, { size: 13, color: "#FFFFFF/72", align: "center" });
  line(slide, 516, 367, 116, 0, C.blue, 4);
  rect(slide, 636, 290, 176, 152, C.ink, 18);
  text(slide, "LLM", 636, 314, 176, 56, { size: 32, bold: true, color: C.white, align: "center" });
  text(slide, "基于材料生成", 636, 372, 176, 36, { size: 16, color: "#FFFFFF/68", align: "center" });
  line(slide, 812, 367, 96, 0, C.red, 4);
  rect(slide, 912, 274, 260, 184, C.white, 18, C.pale, 1);
  text(slide, "带来源的回答", 940, 302, 204, 38, { size: 25, bold: true });
  text(slide, "事实更贴近业务\n版本边界更清楚\n可以追溯依据", 940, 354, 204, 84, { size: 19, color: C.muted, lineSpacing: 1.15 });
  rect(slide, 84, 574, 1088, 64, "#3E718D/12", 10);
  text(slide, "新的治理问题：检索结果是否相关、是否过期、是否冲突、是否有权限使用", 108, 574, 1038, 64, { size: 20, bold: true, color: C.blue2 });
  addFooter(slide, 5);
  addNote(slide, "建议用时：3 分钟\nRAG 把外部知识引入生成过程。对产品经理来说，历史 PRD、用户反馈、规范和竞品证据都能成为可检索上下文。\n需要强调：检索命中不代表结论可靠。仍然要治理版本、冲突、来源等级和权限。\n来源：Lewis 等，Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks，2020，https://arxiv.org/abs/2005.11401\n来源：Anthropic，Contextual Retrieval，https://www.anthropic.com/engineering/contextual-retrieval");
}

// 6. Agent
{
  const slide = presentation.slides.add(); slide.background.fill = C.paper;
  addTitle(slide, "第三阶段：Agent 模式", "工作流演变");
  stageLabel(slide, "03", "把语言模型接入行动", 84, 132, C.red);
  const loop = [
    ["理解目标", 150, 292, C.ink], ["规划步骤", 350, 214, C.blue], ["调用工具", 570, 292, C.red],
    ["观察结果", 780, 214, C.green], ["修正交付", 998, 292, C.ink],
  ];
  loop.forEach((d, i) => {
    ellipse(slide, d[1], d[2], 126, 126, d[3]);
    text(slide, d[0], d[1], d[2], 126, 126, { size: 20, bold: true, color: C.white, align: "center" });
    if (i < loop.length - 1) line(slide, d[1] + 126, d[2] + 63, loop[i + 1][1] - (d[1] + 126), loop[i + 1][2] + 63 - (d[2] + 63), C.pale, 3);
  });
  line(slide, 1060, 418, -840, 122, C.pale, 2, "dash");
  const tools = [["搜索", 184], ["浏览器", 364], ["代码", 544], ["文件", 724], ["办公应用", 904]];
  tools.forEach((t, i) => {
    rect(slide, t[1], 540, 148, 54, i === 2 ? C.red : C.paper2, 12);
    text(slide, t[0], t[1], 540, 148, 54, { size: 18, bold: true, color: i === 2 ? C.white : C.ink, align: "center" });
  });
  text(slide, "产品经理开始审查目标、边界和关键决策", 84, 632, 760, 34, { size: 22, bold: true });
  addFooter(slide, 6);
  addNote(slide, "建议用时：3 分钟\nAgent 的最小特征是模型能动态决定下一步并使用工具。工作方式从复制粘贴每一步，变为定义目标和边界，再审查关键决策与最终产物。\n要区分 workflow 和 agent。预定义路径更可控，动态路径更灵活。实际工作常常混合使用。\n来源：Anthropic，Building Effective Agents，https://www.anthropic.com/engineering/building-effective-agents\n来源：OpenAI API Quickstart，工具与 Agents SDK，https://platform.openai.com/docs/quickstart");
}

// 7. Harness
{
  const slide = presentation.slides.add(); slide.background.fill = C.ink;
  rect(slide, 56, 48, 8, 54, C.red);
  text(slide, "第四阶段：Harness", 84, 42, 900, 62, { size: 34, bold: true, color: C.white });
  text(slide, "工作流演变", 1040, 54, 174, 28, { size: 14, bold: true, color: "#FFFFFF/48", align: "right" });
  stageLabel(slide, "04", "让 Agent 在受控环境中持续交付", 84, 132, C.red);
  const layers = [
    ["目标与人工判断", "任务边界、确认点、审批", 168, C.red],
    ["Skill 与规则", "专业流程、输入输出、使用边界", 252, C.blue],
    ["工具与权限", "搜索、文件、代码、应用、沙箱", 336, C.green],
    ["状态与产物", "工作目录、版本、日志、共享上下文", 420, C.amber],
    ["验证与反馈", "测试、检查器、渲染、评审", 504, C.white],
  ];
  layers.forEach((l, i) => {
    rect(slide, 160 + i * 34, l[2], 900 - i * 68, 62, i === 4 ? "#FFFFFF/10" : `${l[3]}/18`, 10, i === 4 ? "#FFFFFF/38" : l[3], 1);
    text(slide, l[0], 192 + i * 34, l[2], 240, 62, { size: 21, bold: true, color: i === 4 ? C.white : l[3] });
    text(slide, l[1], 450 + i * 34, l[2], 540 - i * 68, 62, { size: 17, color: "#FFFFFF/68" });
  });
  text(slide, "Harness 管理长任务中的状态、边界与质量", 84, 632, 850, 34, { size: 23, bold: true, color: C.white });
  addFooter(slide, 7, true);
  addNote(slide, "建议用时：3 分钟\n我把 Harness 理解为 Agent 的工作环境与控制系统。它包括模型之外的规则、工具、目录、权限、状态、测试和人工确认点。\n长任务失败经常来自状态丢失、一次做太多、没有验证、错误覆盖产物。结构化文件、增量推进和 evaluator 能显著改善这些问题。\n来源：Anthropic，Effective Harnesses for Long-Running Agents，https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents\n来源：Anthropic，Harness Design for Long-Running Application Development，https://www.anthropic.com/engineering/harness-design-long-running-apps");
}

// 8. Tool evolution timeline
{
  const slide = presentation.slides.add(); slide.background.fill = C.paper;
  addTitle(slide, "Agent 工具的能力演变", "工具演变");
  line(slide, 92, 350, 1088, 0, C.pale, 4);
  const events = [
    ["2022", "聊天框", "生成与改写", 112, C.steel, -1],
    ["2023", "检索与函数", "外部知识\n结构化调用", 332, C.blue, 1],
    ["2024", "代码与 MCP", "执行任务\n标准化连接", 552, C.green, -1],
    ["2025", "Coding Agent", "真实工作区\n持续迭代", 772, C.red, 1],
    ["2026+", "Skills 与协作", "复用流程\n多 Agent 编排", 992, C.ink, -1],
  ];
  events.forEach((e) => {
    ellipse(slide, e[3], 328, 44, 44, e[4]);
    const top = e[5] < 0 ? 164 : 392;
    line(slide, e[3] + 22, e[5] < 0 ? 240 : 372, 0, e[5] < 0 ? 88 : 78, e[4], 2);
    text(slide, e[0], e[3] - 18, top, 100, 30, { size: 15, bold: true, color: e[4] });
    text(slide, e[1], e[3] - 18, top + 34, 184, 38, { size: 23, bold: true });
    text(slide, e[2], e[3] - 18, top + 78, 184, 60, { size: 17, color: C.muted, lineSpacing: 1.1 });
  });
  rect(slide, 84, 606, 1090, 48, "#13181D/08", 8);
  text(slide, "任务越长、动作越多、风险越高，越需要清晰的权限和验证机制", 106, 606, 1046, 48, { size: 19, bold: true });
  addFooter(slide, 8);
  addNote(slide, "建议用时：2 分钟\n这页讲能力形态，不追求列全厂商。工具演变大致经历聊天生成、外部检索、结构化工具调用、标准化连接、真实工作区执行，以及 Skill 和多 Agent 复用。\nMCP 把资源、提示和工具抽象为标准连接。Coding Agent 把文件、命令、浏览器和验证放进同一个工作台。\n时间点用于表达典型演进，不代表某个单一产品的精确发布时间。\n来源：MCP 规范，https://modelcontextprotocol.io/specification/2024-11-05\n来源：OpenAI Developers，Codex 能力与插件，https://developers.openai.com/\n来源：OpenAI Model Guidance，工具调用与多 Agent，https://developers.openai.com/api/docs/guides/latest-model");
}

// 9. PM workflow map
{
  const slide = presentation.slides.add(); slide.background.fill = C.paper;
  addTitle(slide, "我的产品经理 AI 工作流地图", "Skill 系统");
  const stages = [
    ["发现", "用研\n竞品\n行业洞察", C.blue],
    ["定义", "机会判断\n需求拆解\n优先级", C.red],
    ["设计", "PRD\n交互文案\n原型", C.amber],
    ["验证", "Pilot\n数据分析\n规则检查", C.green],
    ["沉淀", "Skill\nWorkflow\n测试", C.ink],
  ];
  stages.forEach((s, i) => {
    const x = 84 + i * 222;
    text(slide, String(i + 1).padStart(2, "0"), x, 142, 62, 30, { size: 15, bold: true, color: s[2] });
    line(slide, x, 184, 174, 0, s[2], 5);
    text(slide, s[0], x, 204, 174, 48, { size: 29, bold: true });
    text(slide, s[1], x, 274, 174, 112, { size: 20, color: C.muted, lineSpacing: 1.18 });
    if (i < stages.length - 1) line(slide, x + 174, 186, 48, 0, C.pale, 2);
  });
  rect(slide, 84, 444, 1098, 148, C.ink, 18);
  text(slide, "原子 Skill", 112, 466, 176, 38, { size: 22, bold: true, color: C.white });
  text(slide, "问卷设计、画像、模拟作答、数据综合、竞品矩阵、产品文案", 304, 466, 820, 38, { size: 18, color: "#FFFFFF/72" });
  line(slide, 112, 522, 1004, 0, "#FFFFFF/15", 1);
  text(slide, "Workflow", 112, 540, 176, 38, { size: 22, bold: true, color: C.red });
  text(slide, "围绕业务终点组合能力，并管理共享上下文、检查点和产物", 304, 540, 820, 38, { size: 18, color: "#FFFFFF/72" });
  addFooter(slide, 9);
  addNote(slide, "建议用时：2 分钟\n我用产品流程来组织 Skill，而不是按模型或软件分类。发现、定义、设计、验证和沉淀构成一条闭环。原子 Skill 保持单一职责，Workflow 围绕业务终点组合它们。");
}

// 10. Repo snapshot
{
  const slide = presentation.slides.add(); slide.background.fill = C.paper;
  addTitle(slide, "当前仓库：9 个 Skill 的产品经理能力栈", "Skill 系统");
  const metrics = [["9", "Skills"], ["29", "References"], ["21", "Templates"], ["19", "Scripts"], ["2", "Workflows"]];
  metrics.forEach((m, i) => {
    const x = 84 + i * 218;
    text(slide, m[0], x, 142, 180, 72, { size: 48, bold: true, color: i === 0 ? C.red : C.ink });
    text(slide, m[1], x, 214, 180, 28, { size: 15, bold: true, color: C.muted });
  });
  line(slide, 84, 270, 1094, 0, C.pale, 1);
  const lanes = [
    ["用户研究", "问卷设计 / 画像 / 模拟作答 / 研究报告", C.blue],
    ["竞品分析", "单功能对比 / 动态追踪 / 系统应用矩阵", C.red],
    ["洞察表达", "手机发布会速递 / 证据账本 / PPTX", C.green],
    ["产品设计", "系统应用文案已完成，PRD 与原型待补齐", C.amber],
  ];
  lanes.forEach((l, i) => {
    const y = 316 + i * 72;
    rect(slide, 84, y, 10, 46, l[2]);
    text(slide, l[0], 116, y, 170, 46, { size: 21, bold: true });
    text(slide, l[1], 306, y, 852, 46, { size: 19, color: C.muted });
  });
  addFooter(slide, 10);
  addNote(slide, "建议用时：2 分钟\n数据来自当前仓库文件清单。9 个 Skill、29 个 reference 文件、21 个模板、19 个脚本和 2 个 Workflow。\n这里要主动说明现状：用研和竞品已经形成较完整系统，PRD 与原型仍是下一组要建设的能力，当前只有系统应用文案 Skill。");
}

// 11. Skill vs Workflow
{
  const slide = presentation.slides.add(); slide.background.fill = C.paper;
  addTitle(slide, "Skill 与 Workflow 的分工", "Skill 系统");
  rect(slide, 84, 150, 488, 366, "#3E718D/10", 18, C.blue, 1);
  tag(slide, "Skill", 116, 180, 94, C.blue);
  text(slide, "一个可独立验收的专业能力", 116, 236, 402, 48, { size: 27, bold: true });
  text(slide, "触发条件\n输入与输出契约\n判断规则与使用边界\n模板、脚本和质量检查", 116, 310, 390, 144, { size: 21, color: C.muted, lineSpacing: 1.22 });
  rect(slide, 648, 150, 548, 366, "#E5483F/09", 18, C.red, 1);
  tag(slide, "Workflow / Command", 680, 180, 204, C.red);
  text(slide, "围绕业务终点组合多项能力", 680, 236, 454, 48, { size: 27, bold: true });
  text(slide, "调用顺序与依赖\n共享上下文与文件状态\n人工确认点\n失败恢复与最终交付", 680, 310, 420, 144, { size: 21, color: C.muted, lineSpacing: 1.22 });
  text(slide, "能单独验收的能力做 Skill\n需要管理依赖和状态的端到端任务做 Workflow", 84, 566, 1112, 68, { size: 21, bold: true, align: "center", lineSpacing: 1.05 });
  addFooter(slide, 11);
  addNote(slide, "建议用时：2 分钟\nSkill 类似岗位能力说明书，Workflow 类似跨岗位项目 SOP。拆分标准不是文件大小，而是能否独立验收。\n一个 Skill 应该能在不同任务中单独使用。一个 Workflow 需要管理多个 Skill 之间的依赖、状态和人工确认点。");
}

// 12. User research pipeline
{
  const slide = presentation.slides.add(); slide.background.fill = C.ink;
  rect(slide, 56, 48, 8, 54, C.red);
  text(slide, "案例一：用户研究拆成四个原子 Skill", 84, 42, 1010, 62, { size: 34, bold: true, color: C.white });
  text(slide, "用研案例", 1040, 54, 174, 28, { size: 14, bold: true, color: "#FFFFFF/48", align: "right" });
  const skills = [
    ["01", "ur-design-survey", "把模糊课题变成\n可分析问卷", C.blue],
    ["02", "ur-generate-personas", "生成分层、可审计的\n合成画像", C.green],
    ["03", "ur-user-simulator", "隔离模拟作答\n记录质量与模型", C.red],
    ["04", "ur-synthesize-report", "清理数据并完成\n统计与证据综合", C.amber],
  ];
  skills.forEach((s, i) => {
    const x = 84 + i * 282;
    text(slide, s[0], x, 144, 60, 32, { size: 15, bold: true, color: s[3] });
    line(slide, x, 188, 228, 0, s[3], 5);
    text(slide, s[1], x, 212, 248, 56, { size: 21, bold: true, color: C.white });
    text(slide, s[2], x, 286, 238, 92, { size: 19, color: "#FFFFFF/66", lineSpacing: 1.15 });
  });
  rect(slide, 84, 434, 1112, 112, "#FFFFFF/07", 16, "#FFFFFF/14", 1);
  text(slide, "为什么拆分", 112, 456, 164, 32, { size: 20, bold: true, color: C.red });
  text(slide, "每一步的输入、风险和验收方式不同，可以单用，也可以组合", 296, 456, 830, 32, { size: 20, color: C.white });
  text(slide, "使用边界", 112, 500, 164, 32, { size: 20, bold: true, color: C.blue });
  text(slide, "合成用户用于 Pilot、管线验证和提出假设，不替代真实用户研究", 296, 500, 830, 32, { size: 20, color: C.white });
  addFooter(slide, 12, true);
  addNote(slide, "建议用时：2 分钟\n用户研究最初是一条很长的提示词，后来我发现问卷、画像、作答和报告拥有完全不同的输入契约与风险，因此拆成四个原子 Skill。\n合成研究必须明确使用边界：它适合检查问卷和数据管线、暴露假设，不能用于估计真实市场比例或替代真实用户。");
}

// 13. Deep dive survey skill
{
  const slide = presentation.slides.add(); slide.background.fill = C.paper;
  addTitle(slide, "深拆 Skill：ur-design-survey", "用研案例");
  const steps = ["确认研究方向", "目标与证据", "模块蓝图", "设计题目", "逻辑审查", "双格式交付"];
  steps.forEach((s, i) => {
    const x = 84 + i * 184;
    ellipse(slide, x, 154, 46, 46, i < 2 ? C.blue : i === 4 ? C.red : C.ink);
    text(slide, String(i + 1), x, 154, 46, 46, { size: 16, bold: true, color: C.white, align: "center" });
    text(slide, s, x - 20, 214, 130, 56, { size: 17, bold: true, align: "center" });
    if (i < 5) line(slide, x + 46, 177, 138, 0, C.pale, 2);
  });
  line(slide, 84, 304, 1096, 0, C.pale, 1);
  const cols = [
    ["主 Skill", "流程合同\n触发与排除\n输入输出", C.blue],
    ["References", "研究方法\n题目标准\n逻辑清单", C.green],
    ["Templates", "四类场景\n确认卡\n平台格式", C.amber],
    ["Scripts", "结构检查\n逻辑 lint\n文件校验", C.red],
  ];
  cols.forEach((c, i) => {
    const x = 84 + i * 274;
    rect(slide, x, 344, 238, 194, "#FFFFFF", 14, C.pale, 1);
    rect(slide, x, 344, 238, 8, c[2]);
    text(slide, c[0], x + 22, 372, 194, 38, { size: 22, bold: true, color: c[2] });
    text(slide, c[1], x + 22, 424, 194, 94, { size: 18, color: C.muted, lineSpacing: 1.16 });
  });
  text(slide, "生成前确认方向，交付前运行确定性校验", 84, 582, 1096, 44, { size: 23, bold: true, align: "center" });
  addFooter(slide, 13);
  addNote(slide, "建议用时：3 分钟\n现场可以打开 SKILL.md，只展示三块：触发与排除、输入契约、六步流程。\n这个 Skill 的关键设计有两点。第一，生成前用确认卡锁定研究方向，避免问卷做完才发现目标错了。第二，Agent 负责专业判断，脚本负责题目结构、跳转和格式等确定性检查。\n本页内容依据仓库：pm-user-research/skills/ur-design-survey/SKILL.md。");
}

// 14. Workflow command
{
  const slide = presentation.slides.add(); slide.background.fill = C.paper;
  addTitle(slide, "深拆 Command：synthetic-survey", "用研案例");
  text(slide, "文件契约把状态从聊天记忆中移出来", 84, 112, 820, 42, { size: 23, bold: true, color: C.blue2 });
  const nodes = [
    ["shared_context.md", 84, 204, 202, C.ink],
    ["questionnaire.md", 330, 204, 202, C.blue],
    ["personas.json", 576, 204, 202, C.green],
    ["responses.xlsx", 822, 204, 202, C.red],
    ["report.html", 1068, 204, 128, C.amber],
  ];
  nodes.forEach((n, i) => {
    rect(slide, n[1], n[2], n[3], 68, n[4], 12);
    text(slide, n[0], n[1], n[2], n[3], 68, { size: i === 4 ? 16 : 17, bold: true, color: C.white, align: "center" });
    if (i < nodes.length - 1) line(slide, n[1] + n[3], 238, nodes[i + 1][1] - (n[1] + n[3]), 0, C.pale, 3);
  });
  const labels = ["研究设计", "画像生成", "并行模拟", "数据综合"];
  labels.forEach((l, i) => text(slide, l, 270 + i * 246, 292, 120, 28, { size: 14, bold: true, color: [C.blue, C.green, C.red, C.amber][i], align: "center" }));
  rect(slide, 84, 364, 1112, 170, C.ink, 18);
  text(slide, "Command 管理的不是调用次数", 114, 388, 430, 42, { size: 25, bold: true, color: C.white });
  const checks = ["依赖顺序", "共享状态", "人工确认点", "失败恢复", "产物路径"];
  checks.forEach((c, i) => {
    ellipse(slide, 116 + i * 202, 458, 24, 24, i === 2 ? C.red : C.blue);
    text(slide, c, 150 + i * 202, 444, 142, 52, { size: 18, bold: true, color: "#FFFFFF/78" });
  });
  text(slide, "问卷、画像、个人答卷、Excel、质量报告和离线报告均可独立复查", 84, 578, 1112, 44, { size: 20, bold: true, align: "center" });
  addFooter(slide, 14);
  addNote(slide, "建议用时：3 分钟\nWorkflow 的价值不是连续调用四次，而是管理依赖和状态。每一步通过文件契约交付，下一步只读取约定文件。这样任务跨多轮甚至跨工具时仍能恢复。\n需要保留人工确认点，包括研究方向、问卷定稿、异常样本排除和结论审阅。\n本页内容依据仓库：pm-user-research/workflows/synthetic-survey.md 与 pm-user-research/README.md。");
}

// 15. Competitor matrix
{
  const slide = presentation.slides.add(); slide.background.fill = C.paper;
  addTitle(slide, "案例二：竞品矩阵是一套证据系统", "竞品案例");
  const funnel = [
    ["Research Question", 1040, C.ink],
    ["竞品集合 + Feature Schema", 900, C.blue],
    ["UI / 机制 / 定量 / 来源", 760, C.green],
    ["Feature Matrix + 证据明细", 620, C.red],
    ["评分 / 定位图 / 产品方向", 480, C.amber],
  ];
  funnel.forEach((f, i) => {
    const x = 84 + (1040 - f[1]) / 2;
    const y = 144 + i * 78;
    rect(slide, x, y, f[1], 58, `${f[2]}/16`, 10, f[2], 1);
    text(slide, f[0], x, y, f[1], 58, { size: 20, bold: true, color: f[2], align: "center" });
  });
  rect(slide, 84, 574, 1090, 58, C.ink, 10);
  text(slide, "“没有找到”保持未知，不自动写成“不支持”", 108, 574, 1042, 58, { size: 21, bold: true, color: C.white, align: "center" });
  addFooter(slide, 15);
  addNote(slide, "建议用时：3 分钟\n竞品分析最容易退化成搜索结果拼贴。这个 Skill 先定义问题、竞品选择和 Feature Schema，再收集 UI、机制、定量与来源证据，最后才做状态判断和产品建议。\n一个关键硬规则是：没有找到证据只能标记未知，不能自动推断为竞品不支持。\n目录设计采用瘦主 Skill。References 放专业判断，Config 放常量，Scripts 放并行研究与图表重生成，Templates 固定交付结构。\n本页内容依据仓库：pm-competitor-analysis/pm-system-app-competitor-matrix/SKILL.md 与 README.md。");
}

// 16. PRD and prototype
{
  const slide = presentation.slides.add(); slide.background.fill = C.paper;
  addTitle(slide, "PRD 与原型：下一组需要补齐的 Skill", "设计闭环");
  const nodes = [
    ["研究证据", "用研结果\n竞品证据", 84, C.blue],
    ["pm-write-prd", "范围 / 场景\n状态 / 验收", 336, C.red],
    ["pm-prototype", "信息架构\n流程 / 可点击原型", 588, C.amber],
    ["review", "需求覆盖\n分支 / 一致性", 840, C.green],
  ];
  nodes.forEach((n, i) => {
    rect(slide, n[2], 190, 214, 176, "#FFFFFF", 16, n[3], 2);
    text(slide, n[0], n[2] + 18, 214, 178, 42, { size: 22, bold: true, color: n[3], align: "center" });
    text(slide, n[1], n[2] + 18, 270, 178, 72, { size: 18, color: C.muted, align: "center", lineSpacing: 1.18 });
    if (i < nodes.length - 1) line(slide, n[2] + 214, 278, 38, 0, C.pale, 3);
  });
  line(slide, 947, 366, -504, 112, C.pale, 2, "dash");
  rect(slide, 84, 444, 970, 108, C.ink, 16);
  text(slide, "需求 ID 保持映射", 112, 462, 250, 32, { size: 20, bold: true, color: C.red });
  text(slide, "证据进入 PRD，PRD 驱动原型，评审问题回写 PRD", 378, 462, 630, 32, { size: 20, color: C.white });
  text(slide, "当前已有：系统应用命名、Slogan、微文案和版本说明", 112, 506, 850, 28, { size: 18, color: "#FFFFFF/68" });
  tag(slide, "当前缺口", 1086, 194, 96, C.red);
  text(slide, "当前仓库还没有完整 PRD / 原型 Skill，本页表达下一阶段设计", 84, 590, 1098, 36, { size: 18, color: C.muted, align: "center" });
  addFooter(slide, 16);
  addNote(slide, "建议用时：2 分钟\n这一页必须明确区分现状和规划。当前仓库已有用户研究、竞品分析和产品文案，但没有完整 PRD 与原型 Skill。\n建议新增三项能力：写 PRD、从 PRD 生成原型、对 PRD 与原型做覆盖检查。关键机制是需求 ID 映射，让证据、需求、界面和验收标准可以追溯。");
}

// 17. Skill development loop
{
  const slide = presentation.slides.add(); slide.background.fill = C.ink;
  rect(slide, 56, 48, 8, 54, C.red);
  text(slide, "一个 Skill 的开发流程", 84, 42, 900, 62, { size: 34, bold: true, color: C.white });
  text(slide, "开发方法", 1040, 54, 174, 28, { size: 14, bold: true, color: "#FFFFFF/48", align: "right" });
  const steps = [
    ["1", "找任务", "高频\n边界清楚\n可验收", C.blue],
    ["2", "找失败", "真实案例\n错误模式\n专业判断", C.green],
    ["3", "定契约", "触发\n输入输出\n确认点", C.red],
    ["4", "拆资源", "主 Skill\n参考与模板\n脚本", C.amber],
    ["5", "试跑", "最小任务\n记录偏差\n补规则", C.steel],
    ["6", "做评估", "结构测试\n样例评估\n产物验证", C.white],
  ];
  steps.forEach((s, i) => {
    const x = 84 + i * 184;
    ellipse(slide, x, 160, 46, 46, s[3]);
    text(slide, s[0], x, 160, 46, 46, { size: 16, bold: true, color: i === 5 ? C.ink : C.white, align: "center" });
    text(slide, s[1], x - 16, 226, 152, 38, { size: 22, bold: true, color: C.white });
    text(slide, s[2], x - 16, 278, 152, 92, { size: 17, color: "#FFFFFF/58", lineSpacing: 1.15 });
    if (i < steps.length - 1) line(slide, x + 46, 183, 138, 0, "#FFFFFF/18", 2);
  });
  rect(slide, 84, 432, 1112, 124, "#FFFFFF/06", 16, "#FFFFFF/14", 1);
  text(slide, "判断交给 Agent", 118, 456, 260, 34, { size: 23, bold: true, color: C.blue });
  text(slide, "研究目标、证据强弱、产品取舍", 118, 498, 430, 28, { size: 18, color: "#FFFFFF/68" });
  line(slide, 620, 454, 0, 76, "#FFFFFF/18", 1);
  text(slide, "确定性工作交给脚本", 674, 456, 312, 34, { size: 23, bold: true, color: C.red });
  text(slide, "格式、字段、逻辑、统计和文件完整性", 674, 498, 430, 28, { size: 18, color: "#FFFFFF/68" });
  text(slide, "优先固化判断与验收，再补充更多知识", 84, 608, 1112, 42, { size: 22, bold: true, color: C.white, align: "center" });
  addFooter(slide, 17, true);
  addNote(slide, "建议用时：2 分钟\n以用研 Skill 为例，开发从真实任务和失败模式开始。先定义边界与契约，再拆主 Skill、Reference、Template 和 Script。试跑之后，把重复失败变成规则，把确定性检查写成脚本。\n评估要覆盖结构、样例与最终产物。测试存在的意义不是追求数量，而是让能力变更可以被发现。\n参考：Anthropic，Writing Effective Tools for Agents，https://www.anthropic.com/engineering/writing-tools-for-agents\n参考：OpenAI Skills API 提供版本化的 Skill 资源，https://developers.openai.com/api/reference/python/resources/skills/methods/create");
}

// 18. Adoption and close
{
  const slide = presentation.slides.add(); slide.background.fill = C.paper;
  addTitle(slide, "把个人技巧变成团队工作系统", "团队落地");
  const weeks = [
    ["第 1 周", "选一个高频任务", "记录 3 个真实案例\n和主要失败模式", C.blue],
    ["第 2 周", "做最小 Skill", "明确输入输出\n增加 1 个质量门槛", C.green],
    ["第 3 周", "交叉使用", "由另一位产品经理试跑\n检查能否复现", C.red],
    ["第 4 周", "组合 Workflow", "连接相关 Skill\n建立共享仓库", C.ink],
  ];
  weeks.forEach((w, i) => {
    const x = 84 + i * 278;
    text(slide, w[0], x, 152, 212, 32, { size: 15, bold: true, color: w[3] });
    line(slide, x, 198, 212, 0, w[3], 5);
    text(slide, w[1], x, 224, 220, 46, { size: 25, bold: true });
    text(slide, w[2], x, 292, 220, 84, { size: 18, color: C.muted, lineSpacing: 1.2 });
  });
  rect(slide, 84, 444, 1112, 140, C.ink, 18);
  text(slide, "可复用", 118, 470, 220, 46, { size: 29, bold: true, color: C.blue });
  text(slide, "可组合", 410, 470, 220, 46, { size: 29, bold: true, color: C.red });
  text(slide, "可验证", 702, 470, 220, 46, { size: 29, bold: true, color: C.green });
  text(slide, "可追溯", 994, 470, 160, 46, { size: 29, bold: true, color: C.amber });
  text(slide, "从一个任务开始，建立团队的 AI 交付标准", 118, 530, 1036, 32, { size: 20, color: "#FFFFFF/72", align: "center" });
  text(slide, "Q&A", 84, 616, 220, 48, { size: 32, bold: true, color: C.red });
  text(slide, "你最想先做成 Skill 的产品经理任务是什么？", 306, 616, 830, 48, { size: 22, bold: true });
  addFooter(slide, 18);
  addNote(slide, "建议用时：1 分钟总结，随后留 5 分钟 Q&A\n给团队一个四周小实验，不要求一次建设完整平台。先挑高频任务，做最小 Skill，让同事交叉使用，再把成熟能力组合成 Workflow。\n结尾问题：你最想先做成 Skill 的产品经理任务是什么？\n总结句：当工作方法具备可复用、可组合、可验证和可追溯四个特征时，AI 才从个人技巧变成团队工作系统。");
}

const stagingDir = path.join(workspaceDir, ".codex-finalizer", "ai-pm-workflow");
await fs.mkdir(stagingDir, { recursive: true });
const candidatePath = path.join(stagingDir, "candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);

const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools", "artifact_tool_utils.mjs")).href);
const result = await finalizePresentation({
  explicitTotalSlideCount: 18,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
  workspaceDir,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-heading-fit"],
  fontPolicy: { basis: "design", families: [FONT] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "validation-v2.json"),
});

console.log(JSON.stringify({ final: FINAL_PPTX, result }, null, 2));
