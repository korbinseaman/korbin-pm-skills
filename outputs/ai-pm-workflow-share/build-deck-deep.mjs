import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = "E:\\projects\\korbin-pm-skills";
const SKILL_DIR = "C:\\Users\\mahai\\.codex\\plugins\\cache\\openai-primary-runtime\\presentations\\26.904.11930\\skills\\presentations";
const RUNTIME_PYTHON = "C:\\Users\\mahai\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe";
const TMP_DIR = path.join(workspaceDir, ".codex-ppt-build", "ai-pm-workflow-deep");
const OUT_DIR = path.join(workspaceDir, "outputs", "ai-pm-workflow-share");
const FINAL_PPTX = path.join(OUT_DIR, "从提示词到可验证交付_AI产品经理工作系统_深化版_v4.pptx");
const heroPath = path.join(OUT_DIR, "assets", "workflow-evolution-hero.png");

await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(OUT_DIR, { recursive: true });

const W = 1280;
const H = 720;
const FONT = "Microsoft YaHei";
const C = {
  ink: "#13181D", paper: "#F4F0E8", paper2: "#E7E1D7", white: "#FFFFFF",
  red: "#E5483F", redDark: "#A9342E", blue: "#3E718D", blueDark: "#264F65",
  green: "#4E7B68", amber: "#B78136", muted: "#687175", pale: "#D2CCC1",
  steel: "#8B969C", black2: "#20272D", yellow: "#E0B257",
};

const p = Presentation.create({ slideSize: { width: W, height: H } });

function rect(s, x, y, w, h, fill = "none", radius = 0, stroke = "none", sw = 0) {
  return s.shapes.add({
    geometry: radius ? "roundRect" : "rect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: stroke === "none" ? { fill: "none", width: 0 } : { style: "solid", fill: stroke, width: sw },
    ...(radius ? { borderRadius: radius } : {}),
  });
}

function circle(s, x, y, d, fill, stroke = "none", sw = 0) {
  return s.shapes.add({
    geometry: "ellipse", position: { left: x, top: y, width: d, height: d }, fill,
    line: stroke === "none" ? { fill: "none", width: 0 } : { style: "solid", fill: stroke, width: sw },
  });
}

function line(s, x, y, w, h, color = C.pale, width = 2, dash = "solid") {
  if (w < 0) { x += w; w = -w; }
  if (h < 0) { y += h; h = -h; }
  return s.shapes.add({
    geometry: "line", position: { left: x, top: y, width: w, height: h }, fill: "none",
    line: { style: dash, fill: color, width },
  });
}

function text(s, value, x, y, w, h, o = {}) {
  const sh = s.shapes.add({
    geometry: "textbox", position: { left: x, top: y, width: w, height: h }, fill: "none",
    line: { fill: "none", width: 0 },
  });
  sh.text = value;
  sh.text.style = {
    typeface: o.typeface ?? FONT, fontSize: o.size ?? 22, bold: o.bold ?? false,
    color: o.color ?? C.ink, alignment: o.align ?? "left", verticalAlignment: o.valign ?? "middle",
    autoFit: "none", wrap: "square",
    insets: o.insets ?? { left: 0, right: 0, top: 0, bottom: 0 },
    ...(o.lineSpacing ? { lineSpacing: o.lineSpacing } : {}),
  };
  return sh;
}

function title(s, t, section = "") {
  rect(s, 56, 46, 8, 56, C.red);
  text(s, t, 84, 40, 1060, 66, { size: 34, bold: true });
  if (section) text(s, section, 1040, 54, 174, 26, { size: 13, bold: true, color: C.muted, align: "right" });
}

function footer(s, n, dark = false) {
  text(s, String(n).padStart(2, "0"), 1164, 672, 48, 20, { size: 12, bold: true, color: dark ? "#FFFFFF/55" : C.muted, align: "right" });
}

function note(s, body) { s.speakerNotes.textFrame.setText(body); }

function label(s, value, x, y, w, color = C.red) {
  rect(s, x, y, w, 30, color, 15);
  text(s, value, x, y, w, 30, { size: 13, bold: true, color: C.white, align: "center" });
}

function row(s, y, cols, fills = [], heights = 54, colors = []) {
  let x = 84;
  cols.forEach((c, i) => {
    if (fills[i]) rect(s, x, y, c.w, heights, fills[i]);
    text(s, c.t, x + 12, y, c.w - 24, heights, { size: c.size ?? 18, bold: c.bold ?? false, color: colors[i] ?? c.color ?? C.ink, align: c.align ?? "left", lineSpacing: 1.05 });
    x += c.w;
  });
  line(s, 84, y + heights, 1112, 0, C.pale, 1);
}

function darkSlide() { const s = p.slides.add(); s.background.fill = C.ink; return s; }
function lightSlide() { const s = p.slides.add(); s.background.fill = C.paper; return s; }

// 1 Cover
{
  const s = darkSlide();
  const hero = new Uint8Array(await fs.readFile(heroPath));
  s.images.add({ blob: hero, contentType: "image/png", alt: "从对话节点扩展为可执行工作系统的抽象视觉", fit: "cover", position: { left: 0, top: 0, width: W, height: H } });
  rect(s, 0, 0, 700, H, "#0B0F13/88");
  rect(s, 76, 104, 10, 90, C.red);
  text(s, "从提示词到\n可验证交付", 114, 96, 520, 192, { size: 54, bold: true, color: C.white, lineSpacing: 0.92 });
  text(s, "我的 AI 产品经理工作系统、Skill 与 Harness 实践", 116, 310, 510, 66, { size: 23, color: "#FFFFFF/82" });
  line(s, 116, 414, 390, 0, "#FFFFFF/30", 1);
  text(s, "Intent  ·  Evidence  ·  Action  ·  Governance", 116, 432, 510, 28, { size: 15, bold: true, color: "#FFFFFF/62" });
  text(s, "产品经理团队分享  /  45 min", 116, 620, 380, 26, { size: 15, color: "#FFFFFF/55" });
  note(s, "建议用时：1 分钟\n开场：过去一年我最大的变化，不是换了哪个模型，而是不断把自己的判断方式、任务状态和质量标准移出聊天框。今天不做名词科普，我想拆解为什么这些控制信息必须被外置，以及我怎样把它们做成 Skill、文件契约和验证器。\n主视觉由图像生成工具制作。背景节点从单点对话扩展为工作系统，对应本次分享的核心叙事。");
}

// 2 Failure modes
{
  const s = lightSlide(); title(s, "模型更强，交付为什么仍然不稳定", "问题");
  text(s, "贯穿案例：为“手机图库 AI 清理”完成研究、竞品判断、PRD 与原型", 84, 112, 1040, 34, { size: 20, color: C.muted });
  const items = [
    ["事实失败", "资料过期\n把“没搜到”写成“不支持”", C.blue],
    ["决策失败", "内容完整\n却没有回答做不做、先做什么", C.red],
    ["执行失败", "中间状态留在聊天里\n下游读不到上游边界", C.green],
    ["交付失败", "格式正确\n需求、状态、证据与验收没有映射", C.amber],
  ];
  items.forEach((it, i) => {
    const y = 174 + i * 96;
    text(s, `0${i + 1}`, 84, y, 52, 56, { size: 16, bold: true, color: it[2] });
    line(s, 142, y + 28, 70, 0, it[2], 4);
    text(s, it[0], 230, y, 190, 56, { size: 25, bold: true });
    text(s, it[1], 446, y, 526, 56, { size: 19, color: C.muted, lineSpacing: 1.05 });
  });
  rect(s, 84, 578, 1112, 62, C.ink, 10);
  text(s, "模型决定局部推理上限；工作系统决定任务能否稳定完成", 108, 578, 1064, 62, { size: 22, bold: true, color: C.white, align: "center" });
  footer(s, 2);
  note(s, "建议用时：1.5 分钟\n先把问题从‘提示词写得好不好’扩大到交付系统。同一个图库 AI 清理任务，会在事实、决策、执行和最终交付四处失败。四种失败无法只靠换模型解决。后面每一层演进，都对应消除一类系统性失败。\n可以现场问：大家最近一次 AI 返工，属于这四类里的哪一类？");
}

// 3 Four contracts
{
  const s = lightSlide(); title(s, "四层控制面与四种契约", "分析框架");
  row(s, 132, [
    { t: "层次", w: 170, bold: true }, { t: "外置的控制信息", w: 310, bold: true },
    { t: "形成的契约", w: 250, bold: true }, { t: "仍会失败的地方", w: 382, bold: true },
  ], [C.ink, C.ink, C.ink, C.ink], 50, [C.white, C.white, C.white, C.white]);
  const rows = [
    ["Prompt", "表达意图与输出要求", "回答契约", "事实、状态和执行仍留在外部", C.steel],
    ["Context", "知识、证据与运行状态", "证据契约", "模型知道什么，但还不能行动", C.blue],
    ["Agent", "动作选择与工具循环", "行动契约", "能行动，但不一定安全和可恢复", C.red],
    ["Harness", "权限、状态、验证与审计", "交付契约", "需要持续治理版本与评估", C.ink],
  ];
  rows.forEach((r, i) => row(s, 182 + i * 82, [
    { t: r[0], w: 170, bold: true, color: r[4], size: 22 }, { t: r[1], w: 310, size: 19 },
    { t: r[2], w: 250, bold: true, size: 20 }, { t: r[3], w: 382, size: 18, color: C.muted },
  ], [i % 2 ? "#FFFFFF/45" : "none", i % 2 ? "#FFFFFF/45" : "none", i % 2 ? "#FFFFFF/45" : "none", i % 2 ? "#FFFFFF/45" : "none"], 82));
  text(s, "后面的层级不会替代前面的层级；它只是把更多隐性控制信息变成显式系统", 84, 550, 1112, 54, { size: 22, bold: true, color: C.blueDark, align: "center" });
  footer(s, 3);
  note(s, "建议用时：2 分钟\n我把演变理解成四种契约。Prompt 规定怎样回答，Context 规定哪些事实和状态可以进入判断，Agent 规定可以采取哪些行动，Harness 规定行动如何在可恢复、可验证和可审计的环境中发生。\n这是全场的分析框架。后面讲每个 Skill 时都问四个问题：回答要求是什么、证据从哪里来、允许采取什么动作、如何证明交付合格。");
}

// 4 Prompt
{
  const s = lightSlide(); title(s, "Prompt 工程的边界", "Prompt");
  rect(s, 84, 146, 560, 386, C.ink, 16);
  label(s, "回答契约", 112, 172, 100, C.steel);
  text(s, "目标\n受众\n约束\n输出形态\n少量示例", 116, 226, 170, 250, { size: 27, bold: true, color: C.white, lineSpacing: 1.22 });
  line(s, 314, 214, 0, 270, "#FFFFFF/18", 1);
  text(s, "把一次回答写清楚\n\n适合\n快速启动、改写、单次分析\n\n优化目标\n局部内容的相关性与表达稳定性", 336, 218, 286, 270, { size: 18, color: "#FFFFFF/74", lineSpacing: 1.12 });
  text(s, "Prompt 外部仍未被控制", 714, 152, 430, 40, { size: 25, bold: true, color: C.red });
  const outside = ["材料可信度与版本", "长任务完成状态", "工具权限与副作用", "交付物验证方式"];
  outside.forEach((v, i) => {
    circle(s, 716, 224 + i * 68, 20, i < 2 ? C.blue : C.red);
    text(s, v, 754, 210 + i * 68, 390, 48, { size: 20, bold: true });
  });
  rect(s, 704, 516, 454, 96, "#E5483F/10", 10, C.red, 1);
  text(s, "当提示词开始塞入知识库、流程、模板和历史状态时，问题已经不再只是提示词问题", 728, 526, 406, 76, { size: 19, bold: true, color: C.redDark, align: "center", lineSpacing: 1.05 });
  footer(s, 4);
  note(s, "建议用时：2 分钟\n提示词工程没有过时。它仍然负责把一次回答的目标、受众、约束和输出写清楚。问题在于，很多团队用一个巨型 Prompt 同时承担知识库、流程、状态、权限和检查清单。Prompt 越来越长，其实是在替其他层级打补丁。\n转折点：当我开始复制历史 PRD、竞品资料和检查清单时，我需要的不再是更长的提示词，而是一个有生命周期的上下文系统。");
}

// 5 Context
{
  const s = lightSlide(); title(s, "Context 工程的四层工作集", "Context / RAG");
  const layers = [
    ["稳定规则", "角色边界、隐私、事实标准", C.ink],
    ["任务契约", "目标、用户、成功标准、交付要求", C.red],
    ["动态证据", "围绕当前判断检索的材料与来源", C.blue],
    ["运行状态", "已完成动作、关键决定、文件位置、阻塞", C.green],
  ];
  layers.forEach((l, i) => {
    const y = 144 + i * 88;
    rect(s, 84 + i * 22, y, 650 - i * 44, 66, `${l[2]}/16`, 8, l[2], 1);
    text(s, l[0], 112 + i * 22, y, 156, 66, { size: 22, bold: true, color: l[2] });
    text(s, l[1], 278 + i * 22, y, 410 - i * 44, 66, { size: 18, color: C.ink });
  });
  line(s, 774, 154, 0, 376, C.pale, 1);
  text(s, "RAG 只处理其中一层", 818, 150, 330, 38, { size: 25, bold: true, color: C.blue });
  text(s, "检索只是把候选证据放进窗口。真正的上下文工程还要回答：", 818, 202, 342, 70, { size: 18, color: C.muted, lineSpacing: 1.06 });
  const qs = ["最小证据集是什么", "版本或来源冲突怎么处理", "检索到什么程度必须停止", "哪些信息不能传给下游"];
  qs.forEach((q, i) => {
    text(s, `0${i + 1}`, 818, 292 + i * 58, 38, 36, { size: 14, bold: true, color: C.blue });
    text(s, q, 864, 284 + i * 58, 300, 50, { size: 18, bold: true });
  });
  rect(s, 84, 566, 1090, 64, C.blueDark, 10);
  text(s, "产品问题：这个决策最少需要哪些证据；证据不足时系统怎样保留不确定性", 108, 566, 1042, 64, { size: 20, bold: true, color: C.white, align: "center" });
  footer(s, 5);
  note(s, "建议用时：2.5 分钟\n上下文不是越多越好，而是一组为当前决策服务的工作集。稳定规则和任务契约尽量保持短而稳定；动态证据按 Research Question 检索；运行状态用于跨轮次、跨工具恢复。\nRAG 是动态证据进入上下文的一种操作。它不能自动解决过期、冲突、权限、检索停止和下游污染。\n来源：Lewis 等，Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks，https://arxiv.org/abs/2005.11401\n来源：Anthropic，Contextual Retrieval，https://www.anthropic.com/engineering/contextual-retrieval");
}

// 6 Agent state
{
  const s = darkSlide();
  rect(s, 56, 46, 8, 56, C.red); text(s, "Agent：任务被建模为状态迁移", 84, 40, 1040, 66, { size: 34, bold: true, color: C.white });
  text(s, "Agent", 1040, 54, 174, 26, { size: 13, bold: true, color: "#FFFFFF/50", align: "right" });
  rect(s, 88, 144, 1104, 82, "#FFFFFF/06", 12, "#FFFFFF/16", 1);
  text(s, "S(t)  +  目标 / 约束", 116, 144, 300, 82, { size: 27, bold: true, color: C.blue });
  text(s, "选择动作", 458, 144, 178, 82, { size: 24, bold: true, color: C.white, align: "center" });
  text(s, "工具结果 O(t)", 678, 144, 208, 82, { size: 24, bold: true, color: C.red, align: "center" });
  text(s, "S(t+1)", 950, 144, 192, 82, { size: 27, bold: true, color: C.green, align: "right" });
  line(s, 416, 185, 42, 0, "#FFFFFF/30", 3); line(s, 636, 185, 42, 0, "#FFFFFF/30", 3); line(s, 886, 185, 64, 0, "#FFFFFF/30", 3);
  text(s, "产品经理需要定义的控制信息", 88, 278, 500, 40, { size: 24, bold: true, color: C.white });
  const controls = [
    ["成功条件", "什么结果算真正完成", C.blue],
    ["动作空间", "允许访问哪些工具、数据和应用", C.green],
    ["停止条件", "何时证据已经足够；何时必须终止", C.amber],
    ["升级条件", "哪些判断、权限或风险需要人工接管", C.red],
  ];
  controls.forEach((c, i) => {
    const y = 342 + i * 64;
    text(s, `0${i + 1}`, 88, y, 46, 38, { size: 14, bold: true, color: c[2] });
    text(s, c[0], 146, y - 4, 170, 46, { size: 21, bold: true, color: C.white });
    text(s, c[1], 328, y - 4, 510, 46, { size: 18, color: "#FFFFFF/65" });
  });
  rect(s, 870, 304, 322, 244, "#FFFFFF/05", 12, "#FFFFFF/16", 1);
  text(s, "动态 Agent", 898, 324, 250, 36, { size: 23, bold: true, color: C.red });
  text(s, "根据观察结果改变路径\n\n适合\n信息不完整、需要探索\n工具结果会改变下一步", 898, 372, 256, 154, { size: 18, color: "#FFFFFF/70", lineSpacing: 1.12 });
  text(s, "Workflow 可以固定关键门禁，Agent 在门禁之间动态工作", 88, 614, 1104, 40, { size: 21, bold: true, color: C.white, align: "center" });
  footer(s, 6, true);
  note(s, "建议用时：2.5 分钟\nAgent 的核心不是多调用几个工具，而是根据观察结果更新状态并改变下一步。产品经理要把成功、动作、停止和升级四类条件产品化。\n预定义 Workflow 与动态 Agent 不冲突。研究确认、发布审批等关键门禁可以固定；证据搜索、文件定位和修复可以让 Agent 动态选择。\n来源：Anthropic，Building Effective Agents，https://www.anthropic.com/engineering/building-effective-agents\n来源：OpenAI Model Guidance，工具调用、状态管理与 stopping conditions，https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.5");
}

// 7 Harness table
{
  const s = lightSlide(); title(s, "Harness：围绕失败模式设计控制", "Harness");
  row(s, 134, [{ t: "长任务失败模式", w: 330, bold: true }, { t: "Harness 控制机制", w: 782, bold: true }], [C.ink, C.ink], 50, [C.white, C.white]);
  const rs = [
    ["上下文漂移，任务无法恢复", "结构化文件状态、压缩摘要、恢复点", C.blue],
    ["工具有副作用，重复执行造成损失", "沙箱、最小权限、人工审批、幂等与重试规则", C.red],
    ["搜索不断扩张，成本和时间失控", "Research Unit、检索预算、停止条件", C.amber],
    ["输出看似正确，实际无法交付", "Schema、lint、测试、渲染检查和人工评审", C.green],
    ["多个 Skill 读取过多信息，互相污染", "最小输入原则、文件契约、隔离上下文", C.ink],
  ];
  rs.forEach((r, i) => {
    row(s, 184 + i * 72, [
      { t: r[0], w: 330, bold: true, size: 18, color: r[2] },
      { t: r[1], w: 782, size: 19 },
    ], [i % 2 ? "#FFFFFF/45" : "none", i % 2 ? "#FFFFFF/45" : "none"], 72);
  });
  rect(s, 84, 570, 1112, 62, C.ink, 10);
  text(s, "Harness 的设计对象：工作目录、权限、工具描述、错误信息、日志、验证器和人工门禁", 108, 570, 1064, 62, { size: 19, bold: true, color: C.white, align: "center" });
  footer(s, 7);
  note(s, "建议用时：3 分钟\nHarness 不是一个单独软件名称，而是包围 Agent 的运行时产品。它设计的不是正常路径，而是状态丢失、工具副作用、无限搜索、假完成和上下文污染这些失败路径。\nOpenAI 的 Agent environment template 已经把 files、network、packages、plugins、skills 和 setup commands 当作可复用环境配置。这说明 Agent 能力正在从模型调用扩展到环境配置。\n来源：OpenAI，Create an agent environment template，https://developers.openai.com/api/reference/typescript/resources/beta/subresources/agents/subresources/environments/subresources/templates/methods/create\n来源：Anthropic，Effective Harnesses for Long-Running Agents，https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents");
}

// 8 tools evolution
{
  const s = lightSlide(); title(s, "Agent 工具的能力栈演变", "工具");
  const stages = [
    ["Chat", "人决定每一步\n模型生成内容", C.steel],
    ["Retrieval / Functions", "取得外部事实\n调用结构化能力", C.blue],
    ["MCP / Connectors", "资源与工具连接\n逐步标准化", C.green],
    ["Workspace Agents", "观察并修改\n真实工作状态", C.red],
    ["Skills / Trace / Evals", "专业流程复用\n行为可追踪与回归", C.ink],
  ];
  stages.forEach((st, i) => {
    const x = 84 + i * 218;
    text(s, `0${i + 1}`, x, 142, 48, 28, { size: 14, bold: true, color: st[2] });
    line(s, x, 182, 176, 0, st[2], 5);
    text(s, st[0], x, 204, 190, 58, { size: 21, bold: true });
    text(s, st[1], x, 276, 188, 82, { size: 17, color: C.muted, lineSpacing: 1.08 });
  });
  line(s, 84, 406, 1112, 0, C.pale, 1);
  text(s, "一个可用的工具描述必须暴露", 84, 438, 440, 40, { size: 24, bold: true });
  const fields = ["用途与调用时机", "输入字段和约束", "影响范围与副作用", "重试安全与常见错误"];
  fields.forEach((f, i) => {
    const x = 84 + i * 278;
    rect(s, x, 504, 242, 72, i === 2 ? "#E5483F/10" : "#3E718D/09", 8, i === 2 ? C.red : C.blue, 1);
    text(s, f, x + 14, 504, 214, 72, { size: 18, bold: true, color: i === 2 ? C.redDark : C.blueDark, align: "center" });
  });
  text(s, "工具目录越大，路由、延迟加载和权限边界越重要", 84, 610, 1112, 34, { size: 20, bold: true, align: "center" });
  footer(s, 8);
  note(s, "建议用时：1.5 分钟\n这页不按厂商列时间线，而按能力栈解释。工具从回答界面变成真实运行环境；连接标准化以后，新的瓶颈变成路由、权限和可观察性。\n官方模型指南建议把工具用途、时机、输入、副作用、重试安全和错误模式放进工具描述。大型工具目录还需要延迟加载或 tool search。\n来源：OpenAI Model Guidance，https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.5\n来源：MCP Specification，https://modelcontextprotocol.io/specification/2024-11-05");
}

// 9 artifact chain
{
  const s = darkSlide();
  rect(s, 56, 46, 8, 56, C.red); text(s, "一个 PM 任务的端到端产物链", 84, 40, 1040, 66, { size: 34, bold: true, color: C.white });
  text(s, "系统地图", 1040, 54, 174, 26, { size: 13, bold: true, color: "#FFFFFF/50", align: "right" });
  text(s, "手机图库 AI 清理", 84, 126, 360, 36, { size: 22, bold: true, color: C.red });
  const nodes = [
    ["原始材料", "输入", C.steel], ["evidence_ledger", "证据", C.blue], ["research_design", "用研", C.green],
    ["questionnaire", "问卷", C.green], ["competitor_matrix", "竞品", C.blue],
    ["requirement_ledger", "需求", C.red], ["PRD", "定义", C.red], ["ux_contract", "设计", C.amber],
    ["prototype", "原型", C.amber], ["review_report", "验证", C.white],
  ];
  nodes.forEach((n, i) => {
    const r = i < 5 ? 0 : 1;
    const c = i % 5;
    const x = 84 + c * 220;
    const y = r === 0 ? 200 : 392;
    rect(s, x, y, 190, 82, "#FFFFFF/06", 10, n[2], 1);
    text(s, n[0], x + 8, y + 10, 174, 34, { size: n[0] === "requirement_ledger" ? 14 : 17, bold: true, color: C.white, align: "center" });
    text(s, n[1], x + 12, y + 45, 166, 24, { size: 13, bold: true, color: n[2], align: "center" });
    if (c < 4) line(s, x + 190, y + 41, 30, 0, "#FFFFFF/22", 2);
  });
  line(s, 1182, 282, 0, 70, "#FFFFFF/22", 2); line(s, 962, 352, 220, 0, "#FFFFFF/22", 2);
  const rules = ["Owner Skill", "稳定契约", "证据引用", "局部重跑"];
  rules.forEach((r, i) => {
    circle(s, 150 + i * 268, 556, 18, [C.blue, C.green, C.red, C.amber][i]);
    text(s, r, 184 + i * 268, 542, 190, 46, { size: 19, bold: true, color: C.white });
  });
  text(s, "聊天记录只是交互界面；文件与 ID 才是跨步骤的系统状态", 84, 622, 1112, 34, { size: 20, bold: true, color: "#FFFFFF/78", align: "center" });
  footer(s, 9, true);
  note(s, "建议用时：2 分钟\n这条链路是后半场的主线。每个节点由一个 Skill 负责，有稳定输入输出，并保留上游 evidence_ref。出错时从失败节点局部重跑。\n最重要的变化是：聊天记录不再承担唯一状态。文件、run_id 和 requirement_id 让任务可以跨轮次、跨工具恢复，也让另一位产品经理能够复查。");
}

// 10 skill package anatomy
{
  const s = lightSlide(); title(s, "Skill 包的工程结构", "Skill");
  text(s, "pm-user-research/skills/ur-design-survey/", 84, 122, 780, 34, { size: 18, bold: true, color: C.blueDark });
  const tree = [
    ["SKILL.md", "路由与契约", "触发、排除、输入输出、判断流程、停止条件", C.red],
    ["references/", "专业判断", "研究方法、题目标准、逻辑清单、共享上下文", C.blue],
    ["templates/", "交付结构", "四类问卷场景、确认卡、HTML 与平台格式", C.amber],
    ["scripts/", "确定性检查", "字段、格式、题号、逻辑、文件一致性", C.green],
    ["tests/evals", "回归资产", "契约变更、示例质量、跨 Skill 协作", C.ink],
  ];
  tree.forEach((it, i) => {
    const y = 170 + i * 74;
    line(s, 104, y + 30, 42, 0, C.pale, 2);
    text(s, it[0], 160, y, 190, 58, { size: 21, bold: true, color: it[3] });
    text(s, it[1], 366, y, 170, 58, { size: 18, bold: true });
    text(s, it[2], 552, y, 560, 58, { size: 18, color: C.muted });
  });
  line(s, 84, 554, 1112, 0, C.pale, 1);
  text(s, "模型判断", 84, 580, 150, 34, { size: 20, bold: true, color: C.blue });
  text(s, "研究目标、证据强弱、产品取舍", 236, 580, 350, 34, { size: 18 });
  text(s, "代码约束", 650, 580, 150, 34, { size: 20, bold: true, color: C.red });
  text(s, "格式、字段、统计、路径与完整性", 802, 580, 360, 34, { size: 18 });
  footer(s, 10);
  note(s, "建议用时：2.5 分钟\nSkill 不是把一个长 Prompt 保存为 Markdown。主文件负责路由和核心判断，references 按步骤加载专业方法，templates 固定交付结构，scripts 处理确定性工作，tests/evals 防止迭代漂移。\n设计原则是把不同类型的认知工作放到最适合的位置。模型处理无法穷举的判断；代码处理可确定验证的规则；任务状态留在工作目录。\nOpenAI Skills API 已把 Skill 作为可创建和版本化的资源，说明 Skill 正在从本地约定走向可管理能力。\n来源：OpenAI，Create Skill，https://developers.openai.com/api/reference/python/resources/skills/methods/create");
}

// 11 maturity matrix
{
  const s = lightSlide(); title(s, "当前仓库的能力成熟度", "现状");
  const widths = [220, 176, 176, 176, 176, 188];
  const heads = ["能力域", "输入输出契约", "专业规则", "确定性脚本", "Workflow", "回归验证"];
  let x = 84;
  heads.forEach((h, i) => { rect(s, x, 138, widths[i], 52, C.ink); text(s, h, x + 6, 138, widths[i] - 12, 52, { size: 15, bold: true, color: C.white, align: "center" }); x += widths[i]; });
  const data = [
    ["用户研究", "有", "有", "有", "有", "有，当前失败", C.blue],
    ["竞品矩阵", "有", "有", "有", "单 Skill 编排", "缺系统回归", C.red],
    ["新品洞察", "有", "有", "有", "无", "局部验证", C.green],
    ["产品文案", "有", "有", "有", "无", "局部验证", C.amber],
    ["PRD / 原型", "尚未形成", "尚未形成", "尚未形成", "尚未形成", "尚未形成", C.ink],
  ];
  data.forEach((r, ri) => {
    let xx = 84; const y = 190 + ri * 72;
    r.slice(0, 6).forEach((v, i) => {
      if (ri % 2) rect(s, xx, y, widths[i], 72, "#FFFFFF/50");
      text(s, v, xx + 8, y, widths[i] - 16, 72, { size: i === 0 ? 19 : 16, bold: i === 0 || (i === 5 && ri === 0), color: i === 0 ? r[6] : (i === 5 && ri === 0 ? C.red : C.ink), align: "center", lineSpacing: 1.05 });
      line(s, xx + widths[i], 138, 0, 412, C.pale, 1); xx += widths[i];
    });
    line(s, 84, y + 72, 1112, 0, C.pale, 1);
  });
  text(s, "有文件不等于团队可以依赖；成熟度取决于契约、验证和失败恢复是否一起成立", 84, 586, 1112, 46, { size: 21, bold: true, color: C.blueDark, align: "center" });
  footer(s, 11);
  note(s, "建议用时：1.5 分钟\n这次不再用 9 个 Skill、29 个 reference 这类文件统计证明成熟度。统一用契约、规则、脚本、工作流和回归验证五个维度。\n结论很明确：用研和竞品体系最完整，但仍有工程问题；PRD 和原型目前没有形成完整 Skill。后面分别拆一个成熟案例、一个暴露问题的案例和一组下一阶段设计。");
}

// 12 survey decision architecture
{
  const s = darkSlide();
  rect(s, 56, 46, 8, 56, C.red); text(s, "用研 Skill：先编码决策，再生成题目", 84, 40, 1040, 66, { size: 34, bold: true, color: C.white });
  text(s, "ur-design-survey", 1000, 54, 214, 26, { size: 13, bold: true, color: "#FFFFFF/50", align: "right" });
  const steps = [
    ["确认研究方向", "课题、目标、四选一场景", C.red],
    ["目标与证据", "需要判断什么；什么证据支持决策", C.blue],
    ["模块与分支", "谁回答什么；先测行为还是概念", C.green],
    ["题目与平台逻辑", "题干、选项、跳转、导入格式", C.amber],
  ];
  steps.forEach((st, i) => {
    const y = 150 + i * 96;
    circle(s, 86, y + 10, 42, st[2]); text(s, String(i + 1), 86, y + 10, 42, 42, { size: 15, bold: true, color: C.white, align: "center" });
    text(s, st[0], 152, y, 272, 60, { size: 24, bold: true, color: C.white });
    text(s, st[1], 446, y, 620, 60, { size: 19, color: "#FFFFFF/68" });
    if (i < 3) line(s, 107, y + 52, 0, 44, "#FFFFFF/20", 2);
  });
  rect(s, 84, 552, 1112, 72, "#FFFFFF/06", 10, "#FFFFFF/16", 1);
  text(s, "硬规则", 112, 552, 100, 72, { size: 19, bold: true, color: C.red });
  text(s, "概念后置；未用用户不评价体验；每道题必须能说明如何进入分析和影响产品决策", 234, 552, 922, 72, { size: 19, bold: true, color: C.white, align: "center" });
  footer(s, 12, true);
  note(s, "建议用时：3 分钟\n这个 Skill 的核心产物不是问卷文本，而是研究目标到证据再到决策的映射。它要求先在确认卡中锁定课题、调研目标和四选一问卷场景；再为每个目标定义判断变量和证据；之后才决定模块、分支和题目。\n三个重要规则：概念测试不能污染行为基线；没有使用经历的人不能评价体验；无法说明怎样进入分析和改变决策的问题不进入问卷。\n依据：pm-user-research/skills/ur-design-survey/SKILL.md 与 questionnaire-logic-checklist.md。");
}

// 13 actual questionnaire
{
  const s = lightSlide(); title(s, "真实问卷：12 道题背后的证据链", "用研案例");
  const blocks = [
    ["Q1–Q3", "分组变量", "性别、年龄、手机品牌\n用于切片，不直接证明需求", C.steel],
    ["Q4–Q6", "行为基础", "使用状态、近期频率、最近一次任务\n证明对象真实存在", C.blue],
    ["Q7–Q8", "问题价值", "亲历问题与实际后果\n避免只问‘想不想要’", C.red],
    ["Q9–Q12", "优先级决策", "需求范围、强制 Top 1、选择原因、触发场景", C.green],
  ];
  blocks.forEach((b, i) => {
    const y = 144 + i * 88;
    text(s, b[0], 84, y, 118, 64, { size: 22, bold: true, color: b[3] });
    line(s, 212, y + 32, 64, 0, b[3], 4);
    text(s, b[1], 300, y, 220, 64, { size: 23, bold: true });
    text(s, b[2], 536, y, 610, 64, { size: 18, color: C.muted, lineSpacing: 1.05 });
  });
  rect(s, 84, 510, 700, 106, C.ink, 12);
  text(s, "逻辑门", 108, 526, 100, 34, { size: 18, bold: true, color: C.red });
  text(s, "Q4 控制经历题；Q9 的‘目前不需要’阻断后续取舍；Q10 只显示 Q9 已选项", 220, 516, 536, 78, { size: 18, color: C.white, lineSpacing: 1.05 });
  rect(s, 816, 510, 380, 106, "#3E718D/12", 12, C.blue, 1);
  text(s, "Lint 实跑", 842, 522, 140, 32, { size: 17, bold: true, color: C.blue });
  text(s, "12 题  /  0 个结构风险信号", 842, 558, 322, 34, { size: 22, bold: true });
  text(s, "结构通过 ≠ 研究有效", 842, 590, 322, 20, { size: 14, color: C.red });
  footer(s, 13);
  note(s, "建议用时：2 分钟\n这是真实仓库产物，不是为了 PPT 编的例子。Q1 到 Q3 只是分组变量，Q4 到 Q6 建立使用与任务基础，Q7 到 Q8证明问题和后果，Q9 到 Q12形成需求范围、强制取舍和理由。\n脚本实际检查结果为 12 题、0 个结构风险、结构门禁通过。但必须强调：lint 只能证明格式和部分启发式规则没有阻断，不能证明研究目标正确、选项穷尽或结论有效。语义质量仍需要专家评审和真实 Pilot。\n依据：pm-user-research/用户调研/20260913手机图库AI功能需求/questionnaire.md 与 lint_questionnaire.py。");
}

// 14 workflow state machine
{
  const s = lightSlide(); title(s, "Synthetic Survey：文件状态机", "Workflow");
  text(s, "Skill 之间只传文件路径，不传上一步的对话内容", 84, 116, 820, 34, { size: 21, bold: true, color: C.blueDark });
  const files = [
    ["shared_context.md", "任务与受众", C.ink, 84, 184],
    ["questionnaire.md", "问卷权威来源", C.blue, 326, 184],
    ["personas.json", "审计后画像", C.green, 568, 184],
    ["responses_<run_id>.xlsx", "选定回答批次", C.red, 810, 184],
    ["report_<run_id>", "对应批次报告", C.amber, 1052, 184],
  ];
  files.forEach((f, i) => {
    const w = i === 4 ? 144 : 210;
    rect(s, f[3], f[4], w, 82, `${f[2]}/13`, 10, f[2], 1);
    text(s, f[0], f[3] + 8, f[4] + 10, w - 16, 34, { size: i === 3 ? 14 : 15, bold: true, color: f[2], align: "center" });
    text(s, f[1], f[3] + 8, f[4] + 46, w - 16, 24, { size: 13, color: C.muted, align: "center" });
    if (i < 4) line(s, f[3] + w, f[4] + 41, files[i + 1][3] - (f[3] + w), 0, C.pale, 3);
  });
  line(s, 84, 316, 1112, 0, C.pale, 1);
  text(s, "隔离边界", 84, 342, 150, 34, { size: 22, bold: true, color: C.red });
  const boundaries = [
    "画像不读取问卷和研究假设，避免把期待结论写进人设",
    "每个画像在独立上下文中作答，避免角色之间互相污染",
    "报告只读取问卷、设计文档和显式选择的回答批次",
  ];
  boundaries.forEach((b, i) => {
    circle(s, 86, 398 + i * 50, 16, [C.green, C.blue, C.amber][i]);
    text(s, b, 116, 384 + i * 50, 1000, 44, { size: 18, bold: true });
  });
  rect(s, 84, 558, 1112, 66, C.ink, 10);
  text(s, "返工传播：问卷变化重跑模拟和报告；画像变化重跑画像之后；报告失败无需重做问卷", 108, 558, 1064, 66, { size: 18, bold: true, color: C.white, align: "center" });
  footer(s, 14);
  note(s, "建议用时：2.5 分钟\n这个 Workflow 不是把四个 Skill 顺序调用一遍，而是定义一台文件状态机。下游只读取契约列出的文件。画像不读取问卷，是为了避免把调研期待写入人设；每个人独立作答，是为了避免交叉污染；报告使用显式 run_id，是为了避免自动拿到错误批次。\n文件契约还决定返工范围。问卷变化只影响模拟和报告，报告失败不需要重新生成问卷。\n依据：pm-user-research/workflows/synthetic-survey.md 与 shared-context-schema.md。");
}

// 15 test drift
{
  const s = darkSlide();
  rect(s, 56, 46, 8, 56, C.red); text(s, "测试暴露了真实的契约漂移", 84, 40, 1040, 66, { size: 34, bold: true, color: C.white });
  text(s, "Harness 实跑", 1000, 54, 214, 26, { size: 13, bold: true, color: "#FFFFFF/50", align: "right" });
  text(s, "43", 84, 126, 170, 92, { size: 62, bold: true, color: C.white });
  text(s, "项测试", 208, 172, 120, 32, { size: 18, color: "#FFFFFF/58" });
  rect(s, 84, 242, 760, 40, "#FFFFFF/10", 8);
  rect(s, 84, 242, 495, 40, C.green, 8);
  rect(s, 579, 242, 265, 40, C.red, 8);
  text(s, "28 通过", 96, 242, 470, 40, { size: 17, bold: true, color: C.white, align: "center" });
  text(s, "15 失败", 590, 242, 242, 40, { size: 17, bold: true, color: C.white, align: "center" });
  rect(s, 892, 126, 300, 156, "#FFFFFF/06", 12, "#FFFFFF/16", 1);
  text(s, "失败集中位置", 918, 144, 250, 32, { size: 18, bold: true, color: C.red });
  text(s, "画像生成器 CLI 契约\nWindows 中文输出编码", 918, 184, 250, 74, { size: 20, bold: true, color: C.white, lineSpacing: 1.1 });
  line(s, 84, 334, 1112, 0, "#FFFFFF/16", 1);
  text(s, "测试仍要求", 84, 360, 150, 34, { size: 18, bold: true, color: C.blue });
  text(s, "--sample-size     --seed     --group-quota", 244, 352, 730, 48, { size: 22, bold: true, color: C.white });
  text(s, "当前脚本不再接受这些参数，文档、脚本和测试已经独立演化", 84, 416, 1020, 40, { size: 20, color: "#FFFFFF/68" });
  rect(s, 84, 492, 1112, 104, "#E5483F/14", 10, C.red, 1);
  text(s, "工程结论", 112, 508, 130, 34, { size: 18, bold: true, color: C.red });
  text(s, "Skill 文档看起来完整，不代表 Workflow 仍可运行。Harness 应让契约漂移在下游启动前变成明确失败。", 260, 500, 900, 76, { size: 20, bold: true, color: C.white, align: "center", lineSpacing: 1.05 });
  text(s, "当前能力仍在工程化过程中；测试结果用于确定修复优先级", 84, 626, 1112, 28, { size: 16, color: "#FFFFFF/55", align: "center" });
  footer(s, 15, true);
  note(s, "建议用时：2 分钟\n这是我建议保留的坦诚页。当前用户研究模块实跑 43 项测试，28 项通过、15 项失败。失败主要集中在画像生成器 CLI：测试要求 sample-size、seed、group-quota，而当前脚本不再接受这些参数；Windows 中文输出也有编码问题。\n这不是为了展示测试数量，而是说明 Harness 怎样暴露假完成。没有回归测试时，SKILL.md 仍然很完整，真正的 Workflow 却可能已无法按原契约运行。\n实跑命令：python -m unittest discover -s tests -v。执行日期：2026-09-14。");
}

// 16 evidence architecture
{
  const s = lightSlide(); title(s, "竞品矩阵：先建立证据对象", "竞品分析");
  const objs = [
    ["FeatureSchema", "User Task / Module / Feature\n类型与期望值", C.blue],
    ["ResearchUnit", "Competitor × Feature\n版本、地区、优先级", C.red],
    ["EvidenceRecord", "Claim、支持方向、来源等级\n事实、截图、置信度", C.green],
    ["Decision", "Feature 状态、产品定位\n方向与人工确认", C.amber],
  ];
  objs.forEach((o, i) => {
    const x = 84 + i * 278;
    text(s, `0${i + 1}`, x, 142, 44, 28, { size: 14, bold: true, color: o[2] });
    line(s, x, 182, 230, 0, o[2], 5);
    text(s, o[0], x, 206, 236, 48, { size: 23, bold: true });
    text(s, o[1], x, 270, 238, 82, { size: 17, color: C.muted, lineSpacing: 1.08 });
    if (i < 3) line(s, x + 230, 184, 48, 0, C.pale, 2);
  });
  rect(s, 84, 398, 1112, 164, C.ink, 14);
  text(s, "EvidenceRecord", 112, 416, 210, 38, { size: 21, bold: true, color: C.green });
  text(s, "claim", 112, 470, 92, 28, { size: 16, bold: true, color: C.white });
  text(s, "support_direction", 238, 470, 188, 28, { size: 16, bold: true, color: C.white });
  text(s, "source_tier", 464, 470, 130, 28, { size: 16, bold: true, color: C.white });
  text(s, "version / region", 632, 470, 178, 28, { size: 16, bold: true, color: C.white });
  text(s, "confidence", 846, 470, 130, 28, { size: 16, bold: true, color: C.white });
  text(s, "manual_confirmation", 1000, 470, 170, 28, { size: 15, bold: true, color: C.red });
  line(s, 112, 510, 1052, 0, "#FFFFFF/18", 1);
  text(s, "先记录 Claim 与证据，再判断 Feature 状态；最后才抽象定位和产品方向", 112, 522, 1052, 28, { size: 18, color: "#FFFFFF/70", align: "center" });
  text(s, "品牌印象不能直接跳到战略建议", 84, 598, 1112, 34, { size: 21, bold: true, color: C.redDark, align: "center" });
  footer(s, 16);
  note(s, "建议用时：3 分钟\n竞品分析 Skill 先把研究对象数据化。FeatureSchema 从用户任务拆出真正可比的 feature；ResearchUnit 把最小检索单元限定为 competitor × feature；EvidenceRecord 记录 claim、支持方向、来源、版本地区、事实、截图和置信度。\n只有 EvidenceRecords 完成后，系统才能判 Feature 状态和产品定位。这样产品方向可以反向追溯到具体证据，而不是从品牌印象直接得出。\n依据：pm-competitor-analysis/pm-system-app-competitor-matrix/config/schemas.md 与 SKILL.md。");
}

// 17 research unit
{
  const s = lightSlide(); title(s, "Research Unit 的查询与停止条件", "竞品分析");
  rect(s, 84, 132, 1112, 64, C.ink, 10);
  text(s, "示例单元", 108, 132, 130, 64, { size: 18, bold: true, color: C.red });
  text(s, "Apple Photos × 是否支持按未同步状态筛选", 252, 132, 900, 64, { size: 22, bold: true, color: C.white });
  text(s, "查询集合", 84, 230, 160, 36, { size: 22, bold: true, color: C.blue });
  const queries = ["官方术语", "用户任务", "同义机制", "界面证据", "反向验证", "版本 / 地区冲突"];
  queries.forEach((q, i) => {
    const x = 84 + i * 184;
    rect(s, x, 284, 154, 58, i === 4 ? "#E5483F/10" : "#3E718D/09", 8, i === 4 ? C.red : C.blue, 1);
    text(s, q, x + 8, 284, 138, 58, { size: 16, bold: true, color: i === 4 ? C.redDark : C.blueDark, align: "center" });
  });
  line(s, 84, 382, 1112, 0, C.pale, 1);
  text(s, "停止与状态规则", 84, 408, 220, 36, { size: 22, bold: true, color: C.red });
  const rules = [
    ["Tier 1 当前版本直接证明", "高置信判断", C.green],
    ["两个独立 Tier 2/3 一致且无反证", "停止检索", C.blue],
    ["只得到搜索失败", "未知；不能写不支持", C.red],
    ["达到最大 Pass 或冲突仍未解决", "未知 / 冲突 + 请人工确认", C.amber],
  ];
  rules.forEach((r, i) => {
    const y = 458 + i * 42;
    circle(s, 86, y + 9, 14, r[2]);
    text(s, r[0], 116, y, 520, 32, { size: 17, bold: true });
    text(s, r[1], 674, y, 470, 32, { size: 17, bold: true, color: r[2] });
  });
  text(s, "本页只演示研究过程，不预设 Apple 的真实支持状态", 84, 638, 1112, 24, { size: 14, color: C.muted, align: "center" });
  footer(s, 17);
  note(s, "建议用时：2 分钟\n每个重要 ResearchUnit 不是只搜一个关键词。它至少考虑官方术语、用户任务表达、同义机制、界面证据；当结论倾向不支持时必须做反向验证；有冲突时进一步查版本和地区。\n停止条件比查询数量更重要。当前版本官方证据可以直接停止；两个独立高质量来源一致也可停止；搜索失败只能得到 unknown；达到预算或仍冲突时进入人工确认。\n这页示例不代表 Apple Photos 的真实支持状态。\n依据：references/research-evidence.md。");
}

// 18 PRD architecture
{
  const s = darkSlide();
  rect(s, 56, 46, 8, 56, C.red); text(s, "PRD 与原型：用追溯关系连接证据和界面", 84, 40, 1060, 66, { size: 34, bold: true, color: C.white });
  label(s, "下一阶段设计", 1014, 118, 146, C.red);
  rect(s, 84, 138, 510, 360, "#FFFFFF/05", 12, "#FFFFFF/16", 1);
  text(s, "requirement_ledger.yaml", 112, 158, 430, 36, { size: 21, bold: true, color: C.blue });
  text(s,
`id: REQ-001
evidence_refs: [UR-Q7, COMP-EV-023]
problem: 用户担心 AI 清理误删原图
scenario: 存储空间不足时批量清理
requirement: 删除前显示可恢复范围与保留期限
acceptance: 支持预览、撤销和恢复状态说明`,
    112, 210, 450, 250, { size: 17, color: C.white, lineSpacing: 1.12 });
  const nodes = [
    ["pm-write-prd", "范围、场景、状态、验收", C.red],
    ["pm-prototype", "页面、跳转、状态、文案契约", C.amber],
    ["pm-design-review", "需求覆盖、异常状态、一致性", C.green],
  ];
  nodes.forEach((n, i) => {
    const y = 154 + i * 104;
    text(s, `0${i + 1}`, 650, y, 46, 34, { size: 14, bold: true, color: n[2] });
    text(s, n[0], 710, y - 8, 260, 48, { size: 22, bold: true, color: n[2] });
    text(s, n[1], 934, y - 8, 250, 48, { size: 17, color: "#FFFFFF/68" });
    if (i < 2) line(s, 672, y + 36, 0, 68, "#FFFFFF/20", 2);
  });
  rect(s, 650, 476, 542, 92, "#E0B257/10", 10, C.amber, 1);
  text(s, "状态覆盖", 676, 486, 126, 30, { size: 17, bold: true, color: C.amber });
  text(s, "空 / 加载 / 失败 / 权限拒绝 / 离线 / 处理中\n部分成功 / 撤销 / 恢复", 814, 480, 346, 66, { size: 17, bold: true, color: C.white, align: "center", lineSpacing: 1.05 });
  text(s, "每个需求必须同时找到证据来源、PRD 条目、界面落点和验收项", 84, 608, 1112, 40, { size: 21, bold: true, color: C.white, align: "center" });
  footer(s, 18, true);
  note(s, "建议用时：2.5 分钟\n当前仓库还没有完整 PRD 和原型 Skill，所以这页明确标记为下一阶段设计。关键不是让模型写一份更长的 PRD，而是建立 requirement_ledger。每条需求有稳定 ID、上游证据、问题、场景、要求和验收。\n写 PRD、生成原型和设计评审都围绕同一个 ID 工作。评审要检查每个需求是否有界面落点，是否覆盖空、加载、失败、权限、离线、处理中、部分成功、撤销和恢复等状态。\n这样用户反馈、竞品证据、PRD、原型和验收可以双向追溯。");
}

// 19 development process
{
  const s = lightSlide(); title(s, "Skill 开发：从失败样本到回归资产", "开发方法");
  const steps = [
    ["选任务", "高频、边界清楚、可验收", C.blue],
    ["收失败", "至少 3 个真实案例与返工原因", C.red],
    ["定契约", "触发、排除、输入输出、确认与停止", C.green],
    ["拆资源", "判断写 Reference，确定性写 Script", C.amber],
    ["最小试跑", "先闭环，再扩模板和平台", C.blue],
    ["做回归", "把每次返工转成 test 或 eval", C.red],
    ["版本化", "记录上下游契约和迁移影响", C.ink],
  ];
  steps.forEach((st, i) => {
    const x = 84 + i * 158;
    circle(s, x, 150, 42, st[2]); text(s, String(i + 1), x, 150, 42, 42, { size: 14, bold: true, color: C.white, align: "center" });
    text(s, st[0], x - 12, 208, 142, 42, { size: 20, bold: true });
    text(s, st[1], x - 12, 260, 142, 100, { size: 15, color: C.muted, lineSpacing: 1.08 });
    if (i < 6) line(s, x + 42, 171, 116, 0, C.pale, 2);
  });
  line(s, 84, 404, 1112, 0, C.pale, 1);
  rect(s, 84, 442, 520, 126, "#3E718D/10", 10, C.blue, 1);
  text(s, "做 Skill", 112, 458, 130, 34, { size: 22, bold: true, color: C.blue });
  text(s, "跨任务复用，并且可以独立验收", 112, 506, 456, 38, { size: 19, bold: true });
  rect(s, 676, 442, 520, 126, "#E5483F/09", 10, C.red, 1);
  text(s, "做 Workflow", 704, 458, 180, 34, { size: 22, bold: true, color: C.red });
  text(s, "需要管理多个 Skill 的依赖、状态、人工门禁和局部重跑", 704, 496, 456, 58, { size: 18, bold: true, align: "center", lineSpacing: 1.05 });
  text(s, "团队真正复用的是失败处理和验收标准，不是某一句提示词", 84, 612, 1112, 34, { size: 21, bold: true, color: C.blueDark, align: "center" });
  footer(s, 19);
  note(s, "建议用时：2 分钟\n开发从失败样本开始，而不是从写 SKILL.md 开始。先选高频、边界清楚、可验收的任务，收集真实案例和返工原因；再定义契约，拆判断资源和确定性脚本；最小试跑之后，把返工原因变成测试。\n如果一项能力能跨任务复用并独立验收，适合做 Skill。如果任务需要管理多个能力的依赖、状态和人工门禁，适合做 Workflow。团队最值钱的资产是失败处理和验收标准。");
}

// 20 team adoption
{
  const s = lightSlide(); title(s, "团队落地：管理能力，而不是管理提示词", "落地");
  text(s, "Skill Registry", 84, 140, 300, 42, { size: 26, bold: true, color: C.red });
  const registry = ["Owner / 版本", "适用与排除边界", "输入输出与依赖", "最近 Eval 状态", "已知限制与升级影响"];
  registry.forEach((v, i) => {
    const y = 202 + i * 52;
    text(s, `0${i + 1}`, 84, y, 40, 36, { size: 13, bold: true, color: C.red });
    text(s, v, 138, y - 6, 360, 46, { size: 20, bold: true });
  });
  line(s, 544, 136, 0, 360, C.pale, 1);
  text(s, "试点看什么", 594, 140, 300, 42, { size: 26, bold: true, color: C.blue });
  const metrics = ["首轮交付可接受率", "证据覆盖与人工确认项", "关键校验通过率", "人工返工时间与原因", "版本升级后的回归情况"];
  metrics.forEach((v, i) => {
    const y = 202 + i * 52;
    text(s, `0${i + 1}`, 594, y, 40, 36, { size: 13, bold: true, color: C.blue });
    text(s, v, 648, y - 6, 450, 46, { size: 20, bold: true });
  });
  rect(s, 84, 528, 1112, 88, C.ink, 12);
  text(s, "Q&A", 112, 528, 140, 88, { size: 30, bold: true, color: C.red });
  text(s, "团队中哪一个高频任务，最值得先做成有契约、有证据、有验证的 Skill？", 272, 528, 872, 88, { size: 22, bold: true, color: C.white, align: "center" });
  footer(s, 20);
  note(s, "建议用时：1 分钟总结，随后 5 分钟 Q&A\n团队落地不应建立一个提示词收藏夹，而应建立 Skill Registry。每项能力有 owner、版本、边界、契约、依赖、eval 状态和已知限制。\n试点指标优先看首轮可接受率、证据覆盖、校验通过、人工返工和版本回归，不只看生成速度。\n结尾：当专业判断、证据、动作和验收都被外置，AI 才从个人效率工具变成团队可以依赖的交付系统。");
}

const stagingDir = path.join(workspaceDir, ".codex-finalizer", "ai-pm-workflow-deep");
await fs.mkdir(stagingDir, { recursive: true });
const candidatePath = path.join(stagingDir, "candidate-deep-v4.pptx");
await (await PresentationFile.exportPptx(p)).save(candidatePath);

const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools", "artifact_tool_utils.mjs")).href);
const result = await finalizePresentation({
  explicitTotalSlideCount: 20,
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
  receiptPath: path.join(stagingDir, "validation-deep-v4.json"),
});

console.log(JSON.stringify({ final: FINAL_PPTX, result }, null, 2));
