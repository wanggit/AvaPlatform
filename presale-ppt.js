const PptxGenJS = require("pptxgenjs");

const pres = new PptxGenJS();
pres.layout = "LAYOUT_16x9";

// Ocean Gradient配色
const C = {
  pri: "065A82",
  sec: "1C7293",
  acc: "21295C",
  bg: "F5F7FA",
  dark: "0B1628",
  text: "2D3748",
  white: "FFFFFF",
  light: "E8EDF2",
  cardBg: "FFFFFF",
  gold: "E8B84B",
  muted: "718096",
  red: "E53E3E",
  green: "2E7D6F",
  brown: "8B6914",
};

const FONT = "Microsoft YaHei";

// Helper functions
function tb(slide, title, subtitle) {
  slide.addShape(pres.shapes.RECTANGLE, {x: 0, y: 0, w: 10, h: 0.85, fill: {color: C.pri}});
  slide.addText(title, {x: 0.6, y: 0.12, w: 8.5, h: 0.5, fontSize: 24, fontFace: FONT, color: C.white, bold: true, margin: 0});
  if (subtitle) slide.addText(subtitle, {x: 0.6, y: 0.55, w: 8.5, h: 0.25, fontSize: 10.5, fontFace: FONT, color: "A8CCE0", margin: 0});
}

function cd(slide, x, y, w, h, opts = {}) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: x, y: y, w: w, h: h, fill: {color: opts.fill || C.cardBg},
    shadow: {type: "outer", blur: 4, offset: 2, angle: 135, color: "000000", opacity: 0.07},
    line: opts.border ? {color: opts.border, width: 1.5} : undefined
  });
  if (opts.accent) {
    slide.addShape(pres.shapes.RECTANGLE, {x: x, y: y, w: 0.05, h: h, fill: {color: opts.accent}});
  }
}

function lt(slide, x, y, text, width, bgColor) {
  slide.addShape(pres.shapes.RECTANGLE, {x: x, y: y, w: width, h: 0.25, fill: {color: bgColor || C.sec}});
  slide.addText(text, {x: x, y: y, w: width, h: 0.25, fontSize: 9, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
}

function pn(slide, n) {
  slide.addText(String(n), {x: 9.3, y: 5.2, w: 0.5, h: 0.3, fontSize: 9, fontFace: FONT, color: "999999", align: "right", margin: 0});
}

function cc(slide, x, y, w, h, text) {
  cd(slide, x, y, w, h, {accent: C.gold});
  slide.addShape(pres.shapes.RECTANGLE, {x: x + 0.15, y: y + 0.08, w: 0.6, h: 0.22, fill: {color: C.gold}});
  slide.addText("结论", {x: x + 0.15, y: y + 0.08, w: 0.6, h: 0.22, fontSize: 8.5, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
  slide.addText(text, {x: x + 0.15, y: y + 0.36, w: w - 0.3, h: h - 0.44, fontSize: 10.5, fontFace: FONT, color: C.acc, bold: true, margin: 0});
}

// ============ Slide 1: Cover ============
const s1 = pres.addSlide();
s1.background = {color: C.dark};
s1.addShape(pres.shapes.RECTANGLE, {x: 0, y: 0, w: 0.12, h: 5.625, fill: {color: C.sec}});
s1.addShape(pres.shapes.RECTANGLE, {x: 0.12, y: 0, w: 0.04, h: 5.625, fill: {color: C.pri}});
s1.addShape(pres.shapes.OVAL, {x: 6.5, y: -1, w: 5, h: 5, fill: {color: C.acc}, transparency: 70});
s1.addShape(pres.shapes.OVAL, {x: 7.5, y: 2, w: 4, h: 4, fill: {color: C.pri}, transparency: 75});
s1.addText("AI数字员工平台", {x: 0.8, y: 1.2, w: 8, h: 0.7, fontSize: 38, fontFace: FONT, color: C.white, bold: true, margin: 0});
s1.addText("让AI成为可管理的团队", {x: 0.8, y: 1.95, w: 8, h: 0.5, fontSize: 22, fontFace: FONT, color: "A8D8EA", bold: true, margin: 0});
s1.addShape(pres.shapes.RECTANGLE, {x: 0.8, y: 2.5, w: 2.5, h: 0.04, fill: {color: C.sec}});
s1.addText("基于Hermes Agent的企业级数字员工管理平台", {x: 0.8, y: 2.75, w: 8, h: 0.35, fontSize: 14, fontFace: FONT, color: "A0B8CC", margin: 0});

// ============ Slide 2: Table of Contents ============
const s2 = pres.addSlide();
s2.background = {color: C.bg};
tb(s2, "目录");
const tocItems = [
  ["01", "痛点与价值", "企业AI应用的困境与突破"],
  ["02", "平台架构", "三层架构与核心组件"],
  ["03", "核心能力", "从模板到协作的完整体系"],
  ["04", "落地场景", "三大试点岗位与自运营案例"],
  ["05", "技术优势", "Hermes Agent与企业级安全"],
  ["06", "实施路径", "三阶段落地计划"]
];
for (let i = 0; i < tocItems.length; i++) {
  const y = 1.1 + i * 0.65;
  s2.addShape(pres.shapes.OVAL, {x: 0.8, y: y + 0.05, w: 0.5, h: 0.5, fill: {color: i < 2 ? C.acc : i < 4 ? C.pri : C.sec}});
  s2.addText(tocItems[i][0], {x: 0.8, y: y + 0.05, w: 0.5, h: 0.5, fontSize: 18, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
  s2.addText(tocItems[i][1], {x: 1.5, y: y, w: 3, h: 0.6, fontSize: 18, fontFace: FONT, color: C.acc, bold: true, valign: "middle", margin: 0});
  s2.addText(tocItems[i][2], {x: 4.5, y: y, w: 5, h: 0.6, fontSize: 14, fontFace: FONT, color: C.muted, valign: "middle", margin: 0});
}
pn(s2, 2);

// ============ Slide 3: Core Question ============
const s3 = pres.addSlide();
s3.background = {color: C.dark};
s3.addShape(pres.shapes.RECTANGLE, {x: 0, y: 0, w: 0.12, h: 5.625, fill: {color: C.sec}});
s3.addShape(pres.shapes.RECTANGLE, {x: 0.12, y: 0, w: 0.04, h: 5.625, fill: {color: C.pri}});
s3.addShape(pres.shapes.OVAL, {x: 7, y: 3, w: 4, h: 4, fill: {color: C.acc}, transparency: 75});
s3.addText("核心问题", {x: 0.8, y: 0.3, w: 8, h: 0.5, fontSize: 14, fontFace: FONT, color: "8899AA", margin: 0});
s3.addText("为什么企业需要AI数字员工？", {x: 0.8, y: 0.9, w: 8, h: 0.7, fontSize: 32, fontFace: FONT, color: C.white, bold: true, margin: 0});
s3.addText("不是因为AI很酷，而是因为企业需要更高效、更可控、更可审计的工作方式", {x: 0.8, y: 1.8, w: 8, h: 0.4, fontSize: 16, fontFace: FONT, color: "A8CCE0", margin: 0});
pn(s3, 3);

// ============ Slide 4: Three Pain Points ============
const s4 = pres.addSlide();
s4.background = {color: C.bg};
tb(s4, "痛点与价值", "当前企业AI应用的三大困境");
const painPoints = [
  {title: "困境一：AI是黑箱", desc: "无法追踪AI的决策过程，出了问题不知道原因，无法审计和追责", icon: "🔍"},
  {title: "困境二：AI是孤岛", desc: "每个AI工具独立运行，无法协作，无法形成团队合力", icon: "🏝️"},
  {title: "困境三：AI是成本", desc: "Token消耗不可控，无法按目标预算，无法衡量ROI", icon: "💰"}
];
for (let i = 0; i < painPoints.length; i++) {
  const cx = 0.5 + i * 3.1;
  cd(s4, cx, 1.2, 2.9, 3.5, {accent: C.red});
  s4.addText(painPoints[i].icon, {x: cx + 0.2, y: 1.4, w: 0.8, h: 0.8, fontSize: 36, margin: 0});
  s4.addText(painPoints[i].title, {x: cx + 0.2, y: 2.3, w: 2.5, h: 0.4, fontSize: 16, fontFace: FONT, color: C.acc, bold: true, margin: 0});
  s4.addText(painPoints[i].desc, {x: cx + 0.2, y: 2.8, w: 2.5, h: 1.5, fontSize: 13, fontFace: FONT, color: C.text, margin: 0});
}
cc(s4, 0.5, 4.9, 9, 0.5, "传统AI工具无法满足企业级管理需求");
pn(s4, 4);

// ============ Slide 5: Mindset Shift ============
const s5 = pres.addSlide();
s5.background = {color: C.bg};
tb(s5, "痛点与价值", "从'AI工具'到'AI员工'的思维转变");
cd(s5, 0.5, 1.2, 4.3, 3.5, {border: C.red});
lt(s5, 0.65, 1.3, "传统AI工具", 1.2, C.red);
const oldWay = ["单点能力，独立运行", "无法管理，无法审计", "成本不可控", "无法协作", "出了问题无法追责"];
for (let i = 0; i < oldWay.length; i++) {
  s5.addText("✗  " + oldWay[i], {x: 0.8, y: 1.8 + i * 0.45, w: 3.8, h: 0.35, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
}
cd(s5, 5.2, 1.2, 4.3, 3.5, {accent: C.green});
lt(s5, 5.35, 1.3, "AI数字员工", 1.2, C.green);
const newWay = ["有岗位、有职责、有边界", "完整审计、可追溯", "预算管控、成本可控", "目标驱动、团队协作", "风险分级、审批机制"];
for (let i = 0; i < newWay.length; i++) {
  s5.addText("✓  " + newWay[i], {x: 5.5, y: 1.8 + i * 0.45, w: 3.8, h: 0.35, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
}
s5.addShape(pres.shapes.RECTANGLE, {x: 4.8, y: 2.5, w: 0.4, h: 0.04, fill: {color: C.sec}});
s5.addText("→", {x: 4.6, y: 2.2, w: 0.8, h: 0.6, fontSize: 24, fontFace: FONT, color: C.sec, bold: true, align: "center", valign: "middle", margin: 0});
pn(s5, 5);

// ============ Slide 6: Core Value ============
const s6 = pres.addSlide();
s6.background = {color: C.bg};
tb(s6, "痛点与价值", "平台核心价值：可管理、可审计、可协作");
const values = [
  {title: "可管理", desc: "岗位模板、组织架构、员工全生命周期管理", color: C.pri},
  {title: "可审计", desc: "完整操作记录、风险分级、审批机制", color: C.sec},
  {title: "可协作", desc: "目标驱动、动态委派、团队协作", color: C.acc}
];
for (let i = 0; i < values.length; i++) {
  const cx = 0.5 + i * 3.1;
  cd(s6, cx, 1.2, 2.9, 2.0, {accent: values[i].color});
  s6.addText(values[i].title, {x: cx + 0.2, y: 1.4, w: 2.5, h: 0.5, fontSize: 22, fontFace: FONT, color: values[i].color, bold: true, margin: 0});
  s6.addText(values[i].desc, {x: cx + 0.2, y: 2.0, w: 2.5, h: 0.8, fontSize: 13, fontFace: FONT, color: C.text, margin: 0});
}
cc(s6, 0.5, 3.5, 9, 1.5, "AI数字员工不是更聪明的工具，而是更可控的团队成员。\n\n它们有明确的岗位职责、可追踪的工作记录、可控的成本预算，\n以及清晰的风险边界。");
pn(s6, 6);

// ============ Slide 7: Customer Benefits ============
const s7 = pres.addSlide();
s7.background = {color: C.bg};
tb(s7, "痛点与价值", "客户收益：效率提升、成本可控、风险可管");
const benefits = [
  {metric: "70%", label: "方案准备时间缩短", desc: "数字员工自动完成客户研究、方案初稿"},
  {metric: "50%", label: "首次响应时间降低", desc: "客服工单自动分类、知识库检索"},
  {metric: "90%", label: "操作可追溯率", desc: "完整审计记录，问题可定位"},
  {metric: "30%", label: "Token成本节省", desc: "预算管控避免浪费"}
];
for (let i = 0; i < benefits.length; i++) {
  const cx = 0.5 + i * 2.35;
  cd(s7, cx, 1.2, 2.15, 3.5, {accent: i % 2 === 0 ? C.pri : C.sec});
  s7.addText(benefits[i].metric, {x: cx + 0.2, y: 1.4, w: 1.8, h: 0.8, fontSize: 36, fontFace: FONT, color: C.acc, bold: true, margin: 0});
  s7.addText(benefits[i].label, {x: cx + 0.2, y: 2.2, w: 1.8, h: 0.5, fontSize: 14, fontFace: FONT, color: C.acc, bold: true, margin: 0});
  s7.addText(benefits[i].desc, {x: cx + 0.2, y: 2.8, w: 1.8, h: 1.5, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
}
pn(s7, 7);

// ============ Slide 8: Overall Architecture ============
const s8 = pres.addSlide();
s8.background = {color: C.bg};
tb(s8, "平台架构", "总体架构：四层架构设计");
const layers = [
  {y: 1.15, h: 0.6, color: C.light, label: "管理后台 (React + Ant Design)", fs: 14},
  {y: 1.9, h: 0.8, color: C.acc, label: "Platform API (FastAPI)", fs: 16, bold: true},
  {y: 2.85, h: 0.6, color: C.pri, label: "Platform Store + Outbox + Worker Queue", fs: 14},
  {y: 3.6, h: 0.6, color: "003840", label: "Hermes Instance × N (数字员工运行时)", fs: 14, bold: true},
];
for (const l of layers) {
  s8.addShape(pres.shapes.RECTANGLE, {x: 0.5, y: l.y, w: 9, h: l.h, fill: {color: l.color}});
  s8.addText(l.label, {x: 0.5, y: l.y, w: 9, h: l.h, fontSize: l.fs, fontFace: FONT, color: l.bold ? C.white : C.text, bold: !!l.bold, align: "center", valign: "middle", margin: 0});
}
s8.addText("REST / SSE", {x: 4.2, y: 1.7, w: 1.6, h: 0.25, fontSize: 9, fontFace: FONT, color: C.acc, align: "center", margin: 0});
s8.addText("HTTP", {x: 4.2, y: 2.65, w: 1.6, h: 0.25, fontSize: 9, fontFace: FONT, color: C.acc, align: "center", margin: 0});
s8.addText("HTTP", {x: 4.2, y: 3.4, w: 1.6, h: 0.25, fontSize: 9, fontFace: FONT, color: C.acc, align: "center", margin: 0});
pn(s8, 8);

// ============ Slide 9: Core Components ============
const s9 = pres.addSlide();
s9.background = {color: C.bg};
tb(s9, "平台架构", "核心组件：管理后台 → Platform API → Hermes运行时");
const components = [
  {title: "管理后台", items: ["Dashboard", "员工管理", "目标管理", "模板管理", "知识库管理"], color: C.light},
  {title: "Platform API", items: ["Instance Manager", "Job Template Engine", "Goal Engine", "Skill Library", "Tool Registry"], color: C.acc},
  {title: "Hermes运行时", items: ["Profile", "SOUL.md", "Skills", "Tools", "API Server"], color: C.sec}
];
for (let i = 0; i < components.length; i++) {
  const cx = 0.5 + i * 3.1;
  cd(s9, cx, 1.2, 2.9, 3.8, {accent: i === 1 ? C.acc : i === 2 ? C.sec : undefined});
  s9.addShape(pres.shapes.RECTANGLE, {x: cx, y: 1.2, w: 2.9, h: 0.45, fill: {color: i === 1 ? C.acc : i === 2 ? C.sec : C.light}});
  s9.addText(components[i].title, {x: cx, y: 1.2, w: 2.9, h: 0.45, fontSize: 14, fontFace: FONT, color: i === 0 ? C.acc : C.white, bold: true, align: "center", valign: "middle", margin: 0});
  for (let j = 0; j < components[i].items.length; j++) {
    s9.addText("•  " + components[i].items[j], {x: cx + 0.2, y: 1.85 + j * 0.4, w: 2.5, h: 0.35, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
  }
}
pn(s9, 9);

// ============ Slide 10: Job Template System ============
const s10 = pres.addSlide();
s10.background = {color: C.bg};
tb(s10, "平台架构", "岗位模板系统：可复用的岗位蓝图");
cd(s10, 0.5, 1.2, 5.5, 4.0, {accent: C.pri});
s10.addText("什么是岗位模板？", {x: 0.7, y: 1.3, w: 5, h: 0.4, fontSize: 18, fontFace: FONT, color: C.acc, bold: true, margin: 0});
const templateFeatures = [
  "创建数字员工的岗位蓝图",
  "绑定部门、技能、知识源、工具",
  "定义红线和风险等级",
  "设置预算和审批规则",
  "版本管理和评测机制"
];
for (let i = 0; i < templateFeatures.length; i++) {
  s10.addText("✓  " + templateFeatures[i], {x: 0.8, y: 1.85 + i * 0.5, w: 5, h: 0.4, fontSize: 13, fontFace: FONT, color: C.text, margin: 0});
}
cd(s10, 6.2, 1.2, 3.3, 4.0, {accent: C.gold});
s10.addShape(pres.shapes.RECTANGLE, {x: 6.2, y: 1.2, w: 3.3, h: 0.45, fill: {color: C.gold}});
s10.addText("关键能力", {x: 6.2, y: 1.2, w: 3.3, h: 0.45, fontSize: 14, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
const templateCapabilities = [
  "System Prompt映射",
  "Skill自动分发",
  "知识权限继承",
  "工具白名单控制",
  "评测通过才能发布"
];
for (let i = 0; i < templateCapabilities.length; i++) {
  s10.addText("•  " + templateCapabilities[i], {x: 6.4, y: 1.85 + i * 0.5, w: 2.9, h: 0.4, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
}
pn(s10, 10);

// ============ Slide 11: Goal-Driven Collaboration ============
const s11 = pres.addSlide();
s11.background = {color: C.bg};
tb(s11, "平台架构", "目标驱动协作：动态执行图");
s11.addText("人类分配目标 → 数字员工拆解 → 平台控制委派 → 动态执行图", {x: 0.6, y: 1.1, w: 9, h: 0.4, fontSize: 14, fontFace: FONT, color: C.acc, bold: true, margin: 0});
const flowSteps = ["创建Goal", "拆解目标", "查询目录", "提出委派", "平台校验", "创建Work Item", "执行", "验收"];
const sw = 0.95, sgap = 0.15;
const startX = (10 - flowSteps.length * (sw + sgap) + sgap) / 2;
for (let i = 0; i < flowSteps.length; i++) {
  const cx = startX + i * (sw + sgap);
  s11.addShape(pres.shapes.RECTANGLE, {x: cx, y: 1.8, w: sw, h: 0.6, fill: {color: i < 3 ? C.acc : i < 6 ? C.pri : C.sec}});
  s11.addText(flowSteps[i], {x: cx, y: 1.8, w: sw, h: 0.6, fontSize: 10, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
  if (i < flowSteps.length - 1) s11.addText("→", {x: cx + sw, y: 1.8, w: sgap, h: 0.6, fontSize: 14, fontFace: FONT, color: C.muted, align: "center", valign: "middle", margin: 0});
}
cd(s11, 0.5, 2.8, 4.3, 2.2, {accent: C.pri});
s11.addText("核心特点", {x: 0.7, y: 2.9, w: 4, h: 0.35, fontSize: 14, fontFace: FONT, color: C.acc, bold: true, margin: 0});
const collabFeatures = ["动态执行图，非静态DAG", "Platform控制委派深度", "子员工不能继续委托", "Root Goal Owner始终不变"];
for (let i = 0; i < collabFeatures.length; i++) {
  s11.addText("•  " + collabFeatures[i], {x: 0.8, y: 3.4 + i * 0.4, w: 3.8, h: 0.35, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
}
cd(s11, 5.2, 2.8, 4.3, 2.2, {accent: C.gold});
s11.addShape(pres.shapes.RECTANGLE, {x: 5.2, y: 2.8, w: 4.3, h: 0.35, fill: {color: C.gold}});
s11.addText("Policy控制", {x: 5.2, y: 2.8, w: 4.3, h: 0.35, fontSize: 12, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
const policies = ["委托深度限制", "扇出数量控制", "预算管控", "并发限制"];
for (let i = 0; i < policies.length; i++) {
  s11.addText("•  " + policies[i], {x: 5.4, y: 3.3 + i * 0.4, w: 3.8, h: 0.35, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
}
pn(s11, 11);

// ============ Slide 12: Organization Structure ============
const s12 = pres.addSlide();
s12.background = {color: C.bg};
tb(s12, "平台架构", "组织架构：Lead-Staff层级管理");
s12.addText("数字员工不是独立的工具，而是有组织结构的团队", {x: 0.6, y: 1.1, w: 9, h: 0.4, fontSize: 15, fontFace: FONT, color: C.acc, bold: true, margin: 0});

// Lead node
s12.addShape(pres.shapes.ROUNDED_RECTANGLE, {x: 3.5, y: 1.7, w: 3, h: 0.7, fill: {color: C.acc}, rectRadius: 0.1});
s12.addText("运营经理（Lead）", {x: 3.5, y: 1.7, w: 3, h: 0.7, fontSize: 16, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});

// Connection lines from Lead to Staff (vertical line down, then split)
s12.addShape(pres.shapes.RECTANGLE, {x: 4.95, y: 2.4, w: 0.1, h: 0.5, fill: {color: C.acc}});
// Horizontal line connecting all three staff
s12.addShape(pres.shapes.RECTANGLE, {x: 2.45, y: 2.9, w: 5.1, h: 0.1, fill: {color: C.acc}});
// Vertical lines down to each staff
s12.addShape(pres.shapes.RECTANGLE, {x: 2.45, y: 2.9, w: 0.1, h: 0.4, fill: {color: C.acc}});
s12.addShape(pres.shapes.RECTANGLE, {x: 4.95, y: 2.9, w: 0.1, h: 0.4, fill: {color: C.acc}});
s12.addShape(pres.shapes.RECTANGLE, {x: 7.45, y: 2.9, w: 0.1, h: 0.4, fill: {color: C.acc}});

// Staff nodes
const staffPositions = [
  {name: "内容运营专员", desc: "撰写技术博客、产品介绍"},
  {name: "市场研究分析师", desc: "竞品分析、行业趋势"},
  {name: "客户咨询接待员", desc: "回答咨询、收集需求"}
];
for (let i = 0; i < staffPositions.length; i++) {
  const cx = 1.2 + i * 2.5;
  s12.addShape(pres.shapes.ROUNDED_RECTANGLE, {x: cx, y: 3.3, w: 2.5, h: 0.9, fill: {color: C.sec}, rectRadius: 0.1});
  s12.addText(staffPositions[i].name, {x: cx, y: 3.3, w: 2.5, h: 0.5, fontSize: 13, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
  s12.addText(staffPositions[i].desc, {x: cx, y: 3.75, w: 2.5, h: 0.4, fontSize: 10, fontFace: FONT, color: "A8CCE0", align: "center", valign: "middle", margin: 0});
}

// Arrow labels on connections
s12.addText("委派任务", {x: 5.1, y: 2.5, w: 1.5, h: 0.3, fontSize: 9, fontFace: FONT, color: C.acc, margin: 0});
s12.addText("验收产物", {x: 5.1, y: 3.0, w: 1.5, h: 0.3, fontSize: 9, fontFace: FONT, color: C.acc, margin: 0});

// Value cards at bottom
cd(s12, 0.5, 4.5, 4.3, 0.9, {accent: C.pri});
s12.addText("Lead的价值", {x: 0.7, y: 4.55, w: 4, h: 0.3, fontSize: 13, fontFace: FONT, color: C.acc, bold: true, margin: 0});
s12.addText("协调下属工作 → 审核产出 → 向人类汇报", {x: 0.8, y: 4.85, w: 3.8, h: 0.4, fontSize: 11, fontFace: FONT, color: C.text, margin: 0});

cd(s12, 5.2, 4.5, 4.3, 0.9, {accent: C.gold});
s12.addShape(pres.shapes.RECTANGLE, {x: 5.2, y: 4.5, w: 4.3, h: 0.3, fill: {color: C.gold}});
s12.addText("演示价值", {x: 5.2, y: 4.5, w: 4.3, h: 0.3, fontSize: 11, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
s12.addText("有Lead = 团队协作，没有Lead = 工具堆砌", {x: 5.4, y: 4.85, w: 3.8, h: 0.4, fontSize: 12, fontFace: FONT, color: C.acc, bold: true, margin: 0});
pn(s12, 12);

// ============ Slide 13: Employee Lifecycle ============
const s13 = pres.addSlide();
s13.background = {color: C.bg};
tb(s13, "核心能力", "数字员工全生命周期管理");
const lifecycle = ["创建", "配置", "测试", "上岗", "运行", "监控", "下线"];
const lcColors = [C.acc, C.pri, C.sec, C.green, C.pri, C.gold, C.muted];
const lcStartX = (10 - lifecycle.length * 1.2) / 2;
for (let i = 0; i < lifecycle.length; i++) {
  const cx = lcStartX + i * 1.2;
  s13.addShape(pres.shapes.OVAL, {x: cx, y: 1.3, w: 0.8, h: 0.8, fill: {color: lcColors[i]}});
  s13.addText(lifecycle[i], {x: cx, y: 1.3, w: 0.8, h: 0.8, fontSize: 11, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
  if (i < lifecycle.length - 1) s13.addText("→", {x: cx + 0.8, y: 1.3, w: 0.4, h: 0.8, fontSize: 16, fontFace: FONT, color: C.muted, align: "center", valign: "middle", margin: 0});
}
const lifecycleStates = [
  {title: "生命周期状态", items: ["provisioning", "pending_activation", "active", "disabled", "rollout_failed"], color: C.pri},
  {title: "运行时状态", items: ["not_started", "starting", "healthy", "unhealthy", "recovering", "stopped"], color: C.sec},
  {title: "可用性状态", items: ["idle", "busy", "unavailable"], color: C.acc}
];
for (let i = 0; i < lifecycleStates.length; i++) {
  const cx = 0.5 + i * 3.1;
  cd(s13, cx, 2.5, 2.9, 2.5, {accent: lifecycleStates[i].color});
  s13.addShape(pres.shapes.RECTANGLE, {x: cx, y: 2.5, w: 2.9, h: 0.4, fill: {color: lifecycleStates[i].color}});
  s13.addText(lifecycleStates[i].title, {x: cx, y: 2.5, w: 2.9, h: 0.4, fontSize: 12, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
  for (let j = 0; j < lifecycleStates[i].items.length; j++) {
    s13.addText("•  " + lifecycleStates[i].items[j], {x: cx + 0.15, y: 3.05 + j * 0.3, w: 2.6, h: 0.25, fontSize: 9, fontFace: FONT, color: C.text, margin: 0});
  }
}
pn(s13, 13);

// ============ Slide 14: Knowledge Integration ============
const s14 = pres.addSlide();
s14.background = {color: C.bg};
tb(s14, "核心能力", "知识库集成：RAGFlow适配");
s14.addText("Platform不自建知识库，适配企业现有知识系统", {x: 0.6, y: 1.1, w: 9, h: 0.4, fontSize: 15, fontFace: FONT, color: C.acc, bold: true, margin: 0});
cd(s14, 0.5, 1.7, 5.5, 3.5, {accent: C.pri});
s14.addText("知识检索流程", {x: 0.7, y: 1.8, w: 5, h: 0.35, fontSize: 14, fontFace: FONT, color: C.acc, bold: true, margin: 0});
const knowledgeFlow = [
  "1. 员工发起检索请求",
  "2. Platform校验Employee Service Token",
  "3. 获取授权Knowledge Source集合",
  "4. 调用RAGFlow检索",
  "5. 返回标准化结果和来源引用"
];
for (let i = 0; i < knowledgeFlow.length; i++) {
  s14.addText(knowledgeFlow[i], {x: 0.8, y: 2.3 + i * 0.45, w: 5, h: 0.35, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
}
cd(s14, 6.2, 1.7, 3.3, 3.5, {accent: C.gold});
s14.addShape(pres.shapes.RECTANGLE, {x: 6.2, y: 1.7, w: 3.3, h: 0.4, fill: {color: C.gold}});
s14.addText("关键特性", {x: 6.2, y: 1.7, w: 3.3, h: 0.4, fontSize: 12, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
const knowledgeFeatures = [
  "RAGFlow API Key不下发",
  "权限实时生效",
  "动态鉴权",
  "来源引用必填",
  "审计记录完整"
];
for (let i = 0; i < knowledgeFeatures.length; i++) {
  s14.addText("✓  " + knowledgeFeatures[i], {x: 6.4, y: 2.3 + i * 0.45, w: 2.9, h: 0.35, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
}
pn(s14, 14);

// ============ Slide 15: Tool Management ============
const s15 = pres.addSlide();
s15.background = {color: C.bg};
tb(s15, "核心能力", "工具管理：Tool Registry + 幂等性控制");
const toolTypes = [
  {title: "Hermes内置工具", desc: "文件、Shell、Web/Search等", color: C.pri},
  {title: "Platform API", desc: "知识检索、审批、目录查询", color: C.sec},
  {title: "HTTP API", desc: "CRM、工单、邮件等业务系统", color: C.acc},
  {title: "MCP Server", desc: "复杂工具集合", color: C.gold}
];
for (let i = 0; i < toolTypes.length; i++) {
  const cx = 0.5 + i * 2.35;
  cd(s15, cx, 1.2, 2.15, 1.8, {accent: toolTypes[i].color});
  s15.addShape(pres.shapes.RECTANGLE, {x: cx, y: 1.2, w: 2.15, h: 0.4, fill: {color: toolTypes[i].color}});
  s15.addText(toolTypes[i].title, {x: cx, y: 1.2, w: 2.15, h: 0.4, fontSize: 11, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
  s15.addText(toolTypes[i].desc, {x: cx + 0.15, y: 1.8, w: 1.9, h: 0.8, fontSize: 11, fontFace: FONT, color: C.text, margin: 0});
}
cd(s15, 0.5, 3.3, 4.3, 2.0, {accent: C.red});
s15.addText("风险控制", {x: 0.7, y: 3.4, w: 4, h: 0.35, fontSize: 14, fontFace: FONT, color: C.red, bold: true, margin: 0});
s15.addText("•  read Tool：只查询，需要审计\n•  write Tool：改变状态，需要审批\n•  high_risk Tool：敏感数据，高审计级别", {x: 0.8, y: 3.9, w: 3.8, h: 1.2, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
cd(s15, 5.2, 3.3, 4.3, 2.0, {accent: C.gold});
s15.addShape(pres.shapes.RECTANGLE, {x: 5.2, y: 3.3, w: 4.3, h: 0.35, fill: {color: C.gold}});
s15.addText("幂等性控制", {x: 5.2, y: 3.3, w: 4.3, h: 0.35, fontSize: 12, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
s15.addText("•  所有写Tool必须配置幂等策略\n•  Platform生成idempotency key\n•  重复调用返回已有结果或拒绝", {x: 5.4, y: 3.8, w: 3.8, h: 1.2, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
pn(s15, 15);

// ============ Slide 16: Budget Control ============
const s16 = pres.addSlide();
s16.background = {color: C.bg};
tb(s16, "核心能力", "预算管控：Organization Quota + Goal Budget");
cd(s16, 0.5, 1.2, 4.3, 3.5, {accent: C.pri});
s16.addText("Organization Quota", {x: 0.7, y: 1.3, w: 4, h: 0.4, fontSize: 18, fontFace: FONT, color: C.acc, bold: true, margin: 0});
s16.addText("平台整体每日Token硬上限", {x: 0.7, y: 1.8, w: 4, h: 0.35, fontSize: 13, fontFace: FONT, color: C.muted, margin: 0});
const quotaFeatures = [
  "超限后阻断数据面调用",
  "控制面保持可用",
  "按自然日重置",
  "预警阈值可配置"
];
for (let i = 0; i < quotaFeatures.length; i++) {
  s16.addText("•  " + quotaFeatures[i], {x: 0.8, y: 2.3 + i * 0.4, w: 3.8, h: 0.35, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
}
cd(s16, 5.2, 1.2, 4.3, 3.5, {accent: C.sec});
s16.addText("Goal Budget", {x: 5.4, y: 1.3, w: 4, h: 0.4, fontSize: 18, fontFace: FONT, color: C.sec, bold: true, margin: 0});
s16.addText("单个Goal Run的Token执行预算", {x: 5.4, y: 1.8, w: 4, h: 0.35, fontSize: 13, fontFace: FONT, color: C.muted, margin: 0});
const budgetFeatures = [
  "防止成本通过委派扩散",
  "超限后阻断该Goal Run",
  "保留诊断上下文",
  "管理员可调整预算"
];
for (let i = 0; i < budgetFeatures.length; i++) {
  s16.addText("•  " + budgetFeatures[i], {x: 5.5, y: 2.3 + i * 0.4, w: 3.8, h: 0.35, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
}
cc(s16, 0.5, 4.9, 9, 0.5, "预算判断基于已结算用量，不因请求前估算误差停用员工或杀掉Instance");
pn(s16, 16);

// ============ Slide 17: Risk Levels ============
const s17 = pres.addSlide();
s17.background = {color: C.bg};
tb(s17, "核心能力", "风险分级：L1-L4四级风险控制");
const riskLevels = [
  {level: "L1", name: "信息辅助", desc: "查询、总结、起草", example: "知识问答、报告初稿", color: C.green},
  {level: "L2", name: "工作协同", desc: "创建内部任务、草稿", example: "工单草稿、项目催办", color: C.pri},
  {level: "L3", name: "受控执行", desc: "审批后写业务系统", example: "发邮件、修改CRM", color: C.gold},
  {level: "L4", name: "高风险决策", desc: "AI只准备材料", example: "付款、签约、法律判断", color: C.red}
];
for (let i = 0; i < riskLevels.length; i++) {
  const cx = 0.5 + i * 2.35;
  cd(s17, cx, 1.2, 2.15, 3.8, {accent: riskLevels[i].color});
  s17.addShape(pres.shapes.RECTANGLE, {x: cx, y: 1.2, w: 2.15, h: 0.5, fill: {color: riskLevels[i].color}});
  s17.addText(riskLevels[i].level, {x: cx, y: 1.2, w: 2.15, h: 0.5, fontSize: 20, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
  s17.addText(riskLevels[i].name, {x: cx + 0.15, y: 1.85, w: 1.9, h: 0.4, fontSize: 14, fontFace: FONT, color: C.acc, bold: true, margin: 0});
  s17.addText("权限边界", {x: cx + 0.15, y: 2.3, w: 1.9, h: 0.3, fontSize: 10, fontFace: FONT, color: C.muted, margin: 0});
  s17.addText(riskLevels[i].desc, {x: cx + 0.15, y: 2.6, w: 1.9, h: 0.6, fontSize: 11, fontFace: FONT, color: C.text, margin: 0});
  s17.addText("示例", {x: cx + 0.15, y: 3.3, w: 1.9, h: 0.3, fontSize: 10, fontFace: FONT, color: C.muted, margin: 0});
  s17.addText(riskLevels[i].example, {x: cx + 0.15, y: 3.6, w: 1.9, h: 0.8, fontSize: 11, fontFace: FONT, color: C.text, margin: 0});
}
pn(s17, 17);

// ============ Slide 18: Audit Trail ============
const s18 = pres.addSlide();
s18.background = {color: C.bg};
tb(s18, "核心能力", "审计追踪：完整的操作记录");
s18.addText("每一次操作都有迹可循", {x: 0.6, y: 1.1, w: 9, h: 0.4, fontSize: 15, fontFace: FONT, color: C.acc, bold: true, margin: 0});
const auditEvents = [
  "red_line_triggered", "approval_requested", "approval_decided",
  "escalation_created", "abnormal_shutdown", "sensitive_operation",
  "budget_blocked", "knowledge_preview", "template_published", "skill_package_changed"
];
cd(s18, 0.5, 1.7, 5.5, 3.5, {accent: C.pri});
s18.addText("审计事件类型", {x: 0.7, y: 1.8, w: 5, h: 0.35, fontSize: 14, fontFace: FONT, color: C.acc, bold: true, margin: 0});
for (let i = 0; i < auditEvents.length; i++) {
  const col = i < 5 ? 0 : 1;
  const row = i < 5 ? i : i - 5;
  s18.addText("•  " + auditEvents[i], {x: 0.8 + col * 2.5, y: 2.3 + row * 0.4, w: 2.4, h: 0.35, fontSize: 10, fontFace: FONT, color: C.text, margin: 0});
}
cd(s18, 6.2, 1.7, 3.3, 3.5, {accent: C.gold});
s18.addShape(pres.shapes.RECTANGLE, {x: 6.2, y: 1.7, w: 3.3, h: 0.4, fill: {color: C.gold}});
s18.addText("审计规则能力", {x: 6.2, y: 1.7, w: 3.3, h: 0.4, fontSize: 12, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
const auditCapabilities = [
  "决定事件严重级别",
  "通知对象配置",
  "是否进入KPI",
  "是否需要人工复核",
  "规则测试功能"
];
for (let i = 0; i < auditCapabilities.length; i++) {
  s18.addText("•  " + auditCapabilities[i], {x: 6.4, y: 2.3 + i * 0.45, w: 2.9, h: 0.35, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
}
pn(s18, 18);

// ============ Slide 19: Approval Mechanism ============
const s19 = pres.addSlide();
s19.background = {color: C.bg};
tb(s19, "核心能力", "审批机制：人工审批 + 自动升级");
cd(s19, 0.5, 1.2, 4.3, 4.0, {accent: C.pri});
s19.addText("审批流程", {x: 0.7, y: 1.3, w: 4, h: 0.4, fontSize: 18, fontFace: FONT, color: C.acc, bold: true, margin: 0});
const approvalFlow = [
  "1. Tool调用触发审批需求",
  "2. Platform创建Approval Request",
  "3. 返回approval_required给Hermes",
  "4. 审批通过后携带approval_id重试",
  "5. Gateway校验后执行"
];
for (let i = 0; i < approvalFlow.length; i++) {
  s19.addText(approvalFlow[i], {x: 0.8, y: 1.85 + i * 0.45, w: 3.8, h: 0.35, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
}
cd(s19, 5.2, 1.2, 4.3, 4.0, {accent: C.sec});
s19.addText("审批人规则", {x: 5.4, y: 1.3, w: 4, h: 0.4, fontSize: 18, fontFace: FONT, color: C.sec, bold: true, margin: 0});
const approvalRules = [
  "默认：直属管理者或部门负责人",
  "高风险Tool：叠加Tool Owner",
  "高风险内置工具：平台管理员",
  "临时权限：部门负责人 + 管理员"
];
for (let i = 0; i < approvalRules.length; i++) {
  s19.addText("•  " + approvalRules[i], {x: 5.5, y: 1.85 + i * 0.5, w: 3.8, h: 0.4, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
}
s19.addShape(pres.shapes.RECTANGLE, {x: 5.5, y: 4.0, w: 3.8, h: 0.03, fill: {color: C.muted}});
s19.addText("支持Platform内部审批中心\n可扩展飞书、钉钉、邮件通知", {x: 5.5, y: 4.15, w: 3.8, h: 0.8, fontSize: 11, fontFace: FONT, color: C.muted, margin: 0});
pn(s19, 19);

// ============ Slide 20: Artifact Acceptance ============
const s20 = pres.addSlide();
s20.background = {color: C.bg};
tb(s20, "核心能力", "产物验收：Artifact Acceptance机制");
s20.addText("数字员工的产出必须经过验收才算完成", {x: 0.6, y: 1.1, w: 9, h: 0.4, fontSize: 15, fontFace: FONT, color: C.acc, bold: true, margin: 0});
const artifactFlow = ["执行", "产出Artifact", "提交验收", "验收通过", "完成"];
const afColors = [C.pri, C.sec, C.acc, C.green, C.gold];
const afStartX = (10 - artifactFlow.length * 1.5) / 2;
for (let i = 0; i < artifactFlow.length; i++) {
  const cx = afStartX + i * 1.5;
  s20.addShape(pres.shapes.RECTANGLE, {x: cx, y: 1.8, w: 1.2, h: 0.6, fill: {color: afColors[i]}});
  s20.addText(artifactFlow[i], {x: cx, y: 1.8, w: 1.2, h: 0.6, fontSize: 11, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
  if (i < artifactFlow.length - 1) s20.addText("→", {x: cx + 1.2, y: 1.8, w: 0.3, h: 0.6, fontSize: 14, fontFace: FONT, color: C.muted, align: "center", valign: "middle", margin: 0});
}
cd(s20, 0.5, 2.8, 4.3, 2.2, {accent: C.red});
s20.addText("验收失败处理", {x: 0.7, y: 2.9, w: 4, h: 0.35, fontSize: 14, fontFace: FONT, color: C.red, bold: true, margin: 0});
s20.addText("•  Work Item进入rework_required\n•  达到重试上限后failed\n•  记录失败原因和审计事件", {x: 0.8, y: 3.4, w: 3.8, h: 1.2, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
cd(s20, 5.2, 2.8, 4.3, 2.2, {accent: C.green});
s20.addShape(pres.shapes.RECTANGLE, {x: 5.2, y: 2.8, w: 4.3, h: 0.35, fill: {color: C.green}});
s20.addText("验收价值", {x: 5.2, y: 2.8, w: 4.3, h: 0.35, fontSize: 12, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
s20.addText("•  保证产出质量\n•  首次验收通过率作为KPI\n•  返工率可追踪", {x: 5.4, y: 3.4, w: 3.8, h: 1.2, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
pn(s20, 20);

// ============ Slide 21: Pilot Template 1 ============
const s21 = pres.addSlide();
s21.background = {color: C.bg};
tb(s21, "落地场景", "试点岗位：企业经营情报员工");
cd(s21, 0.5, 1.2, 5.5, 4.0, {accent: C.pri});
s21.addText("岗位职责", {x: 0.7, y: 1.3, w: 5, h: 0.4, fontSize: 18, fontFace: FONT, color: C.acc, bold: true, margin: 0});
const intelDuties = [
  "汇总内部经营数据",
  "监测行业和竞争对手",
  "生成管理周报",
  "标记异常",
  "提出需要管理者确认的问题"
];
for (let i = 0; i < intelDuties.length; i++) {
  s21.addText("•  " + intelDuties[i], {x: 0.8, y: 1.85 + i * 0.45, w: 5, h: 0.35, fontSize: 13, fontFace: FONT, color: C.text, margin: 0});
}
cd(s21, 6.2, 1.2, 3.3, 4.0, {accent: C.gold});
s21.addShape(pres.shapes.RECTANGLE, {x: 6.2, y: 1.2, w: 3.3, h: 0.4, fill: {color: C.gold}});
s21.addText("业务结果指标", {x: 6.2, y: 1.2, w: 3.3, h: 0.4, fontSize: 12, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
const intelMetrics = [
  "管理材料准备时间",
  "异常发现时效",
  "引用完整率",
  "管理者采纳率"
];
for (let i = 0; i < intelMetrics.length; i++) {
  s21.addText("•  " + intelMetrics[i], {x: 6.4, y: 1.85 + i * 0.5, w: 2.9, h: 0.4, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
}
s21.addShape(pres.shapes.RECTANGLE, {x: 6.4, y: 3.8, w: 2.9, h: 0.03, fill: {color: C.muted}});
s21.addText("边界：只读为主，不替管理层作最终决策", {x: 6.4, y: 3.95, w: 2.9, h: 0.6, fontSize: 11, fontFace: FONT, color: C.muted, margin: 0});
pn(s21, 21);

// ============ Slide 22: Pilot Template 2 ============
const s22 = pres.addSlide();
s22.background = {color: C.bg};
tb(s22, "落地场景", "试点岗位：客服工单协调员工");
cd(s22, 0.5, 1.2, 5.5, 4.0, {accent: C.sec});
s22.addText("岗位职责", {x: 0.7, y: 1.3, w: 5, h: 0.4, fontSize: 18, fontFace: FONT, color: C.sec, bold: true, margin: 0});
const csDuties = [
  "分类工单",
  "查询知识库",
  "汇总客户历史",
  "生成回复草稿",
  "推荐转派部门",
  "标记重大投诉"
];
for (let i = 0; i < csDuties.length; i++) {
  s22.addText("•  " + csDuties[i], {x: 0.8, y: 1.85 + i * 0.4, w: 5, h: 0.35, fontSize: 13, fontFace: FONT, color: C.text, margin: 0});
}
cd(s22, 6.2, 1.2, 3.3, 4.0, {accent: C.gold});
s22.addShape(pres.shapes.RECTANGLE, {x: 6.2, y: 1.2, w: 3.3, h: 0.4, fill: {color: C.gold}});
s22.addText("业务结果指标", {x: 6.2, y: 1.2, w: 3.3, h: 0.4, fontSize: 12, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
const csMetrics = [
  "首次响应时间",
  "平均处理时间",
  "转派准确率",
  "草稿采用率",
  "重复来询率"
];
for (let i = 0; i < csMetrics.length; i++) {
  s22.addText("•  " + csMetrics[i], {x: 6.4, y: 1.85 + i * 0.45, w: 2.9, h: 0.35, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
}
s22.addShape(pres.shapes.RECTANGLE, {x: 6.4, y: 3.8, w: 2.9, h: 0.03, fill: {color: C.muted}});
s22.addText("边界：初期不允许直接退款、承诺赔偿、关闭重大投诉", {x: 6.4, y: 3.95, w: 2.9, h: 0.6, fontSize: 11, fontFace: FONT, color: C.muted, margin: 0});
pn(s22, 22);

// ============ Slide 23: Pilot Template 3 ============
const s23 = pres.addSlide();
s23.background = {color: C.bg};
tb(s23, "落地场景", "试点岗位：销售方案协作员工");
cd(s23, 0.5, 1.2, 5.5, 4.0, {accent: C.acc});
s23.addText("岗位职责", {x: 0.7, y: 1.3, w: 5, h: 0.4, fontSize: 18, fontFace: FONT, color: C.acc, bold: true, margin: 0});
const salesDuties = [
  "客户研究",
  "历史交流汇总",
  "需求分析",
  "方案初稿",
  "产品资料查询",
  "合规检查",
  "拜访材料准备"
];
for (let i = 0; i < salesDuties.length; i++) {
  s23.addText("•  " + salesDuties[i], {x: 0.8, y: 1.85 + i * 0.38, w: 5, h: 0.3, fontSize: 13, fontFace: FONT, color: C.text, margin: 0});
}
cd(s23, 6.2, 1.2, 3.3, 4.0, {accent: C.gold});
s23.addShape(pres.shapes.RECTANGLE, {x: 6.2, y: 1.2, w: 3.3, h: 0.4, fill: {color: C.gold}});
s23.addText("业务结果指标", {x: 6.2, y: 1.2, w: 3.3, h: 0.4, fontSize: 12, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
const salesMetrics = [
  "方案准备周期",
  "销售准备时间",
  "方案采用率",
  "信息错误率",
  "商机转化辅助指标"
];
for (let i = 0; i < salesMetrics.length; i++) {
  s23.addText("•  " + salesMetrics[i], {x: 6.4, y: 1.85 + i * 0.45, w: 2.9, h: 0.35, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
}
s23.addShape(pres.shapes.RECTANGLE, {x: 6.4, y: 3.8, w: 2.9, h: 0.03, fill: {color: C.muted}});
s23.addText("边界：不自动承诺价格、合同条款或最终成交条件", {x: 6.4, y: 3.95, w: 2.9, h: 0.6, fontSize: 11, fontFace: FONT, color: C.muted, margin: 0});
pn(s23, 23);

// ============ Slide 24: Self-Operation Case ============
const s24 = pres.addSlide();
s24.background = {color: C.bg};
tb(s24, "落地场景", "自运营案例：用平台运营平台公司");
s24.addText("我们自己就是第一个客户", {x: 0.6, y: 1.1, w: 9, h: 0.4, fontSize: 18, fontFace: FONT, color: C.acc, bold: true, margin: 0});
const selfOpTeam = [
  {role: "运营经理（Lead）", desc: "协调团队、审核产出", color: C.acc},
  {role: "内容运营专员", desc: "撰写技术博客、产品介绍", color: C.pri},
  {role: "市场研究分析师", desc: "竞品分析、行业趋势", color: C.sec},
  {role: "客户咨询接待员", desc: "回答咨询、收集需求", color: C.green},
  {role: "技术文档工程师", desc: "维护API文档、接入指南", color: C.gold},
  {role: "售前方案设计师", desc: "生成定制化解决方案", color: C.brown}
];
for (let i = 0; i < selfOpTeam.length; i++) {
  const cx = 0.5 + (i % 3) * 3.1;
  const cy = 1.7 + Math.floor(i / 3) * 1.8;
  cd(s24, cx, cy, 2.9, 1.5, {accent: selfOpTeam[i].color});
  s24.addText(selfOpTeam[i].role, {x: cx + 0.15, y: cy + 0.1, w: 2.6, h: 0.4, fontSize: 13, fontFace: FONT, color: C.acc, bold: true, margin: 0});
  s24.addText(selfOpTeam[i].desc, {x: cx + 0.15, y: cy + 0.6, w: 2.6, h: 0.6, fontSize: 11, fontFace: FONT, color: C.text, margin: 0});
}
pn(s24, 24);

// ============ Slide 25: Hermes Agent ============
const s25 = pres.addSlide();
s25.background = {color: C.bg};
tb(s25, "技术优势", "Hermes Agent零改造 - 基于成熟开源Agent");
s25.addText("Platform不fork Hermes，不改Hermes核心", {x: 0.6, y: 1.1, w: 9, h: 0.4, fontSize: 16, fontFace: FONT, color: C.acc, bold: true, margin: 0});
cd(s25, 0.5, 1.7, 4.3, 3.5, {accent: C.pri});
s25.addText("集成方式", {x: 0.7, y: 1.8, w: 4, h: 0.35, fontSize: 14, fontFace: FONT, color: C.acc, bold: true, margin: 0});
const hermesIntegration = [
  "Profile文件配置",
  "Hermes API Server",
  "SOUL.md身份注入",
  "Skill自动分发",
  "Tool白名单控制"
];
for (let i = 0; i < hermesIntegration.length; i++) {
  s25.addText("•  " + hermesIntegration[i], {x: 0.8, y: 2.3 + i * 0.45, w: 3.8, h: 0.35, fontSize: 13, fontFace: FONT, color: C.text, margin: 0});
}
cd(s25, 5.2, 1.7, 4.3, 3.5, {accent: C.gold});
s25.addShape(pres.shapes.RECTANGLE, {x: 5.2, y: 1.7, w: 4.3, h: 0.4, fill: {color: C.gold}});
s25.addText("核心优势", {x: 5.2, y: 1.7, w: 4.3, h: 0.4, fontSize: 14, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
const hermesAdvantages = [
  "一个员工一个运行时实例",
  "独立Profile和配置",
  "进程隔离、互不影响",
  "可独立启停和监控",
  "快速获得上游更新"
];
for (let i = 0; i < hermesAdvantages.length; i++) {
  s25.addText("✓  " + hermesAdvantages[i], {x: 5.4, y: 2.3 + i * 0.45, w: 3.8, h: 0.35, fontSize: 13, fontFace: FONT, color: C.text, margin: 0});
}
pn(s25, 25);

// ============ Slide 26: Enterprise Security ============
const s26 = pres.addSlide();
s26.background = {color: C.bg};
tb(s26, "技术优势", "企业级安全：凭证管理、权限隔离");
const securityFeatures = [
  {title: "凭证管理", desc: "API Key、OAuth token等只保存在Platform，不下发到Profile", color: C.pri},
  {title: "权限隔离", desc: "每个员工只能访问授权的工具和知识源", color: C.sec},
  {title: "Token管理", desc: "Employee Service Token最小权限，可轮换和吊销", color: C.acc},
  {title: "审计记录", desc: "所有操作完整记录，敏感数据脱敏展示", color: C.gold}
];
for (let i = 0; i < securityFeatures.length; i++) {
  const cx = 0.5 + (i % 2) * 4.7;
  const cy = 1.2 + Math.floor(i / 2) * 2.0;
  cd(s26, cx, cy, 4.3, 1.7, {accent: securityFeatures[i].color});
  s26.addText(securityFeatures[i].title, {x: cx + 0.2, y: cy + 0.1, w: 3.9, h: 0.4, fontSize: 16, fontFace: FONT, color: C.acc, bold: true, margin: 0});
  s26.addText(securityFeatures[i].desc, {x: cx + 0.2, y: cy + 0.6, w: 3.9, h: 0.8, fontSize: 13, fontFace: FONT, color: C.text, margin: 0});
}
pn(s26, 26);

// ============ Slide 27: Scalable Architecture ============
const s27 = pres.addSlide();
s27.background = {color: C.bg};
tb(s27, "技术优势", "可扩展架构：模块化单体 → 微服务");
s27.addText("从模块化单体开始，稳定后再拆分", {x: 0.6, y: 1.1, w: 9, h: 0.4, fontSize: 16, fontFace: FONT, color: C.acc, bold: true, margin: 0});
cd(s27, 0.5, 1.7, 4.3, 3.5, {accent: C.pri});
s27.addText("当前：模块化单体", {x: 0.7, y: 1.8, w: 4, h: 0.4, fontSize: 16, fontFace: FONT, color: C.acc, bold: true, margin: 0});
const monolithBenefits = [
  "FastAPI模块化设计",
  "共享进程和数据库",
  "简化分布式事务",
  "快速迭代和调试",
  "降低运维复杂度"
];
for (let i = 0; i < monolithBenefits.length; i++) {
  s27.addText("•  " + monolithBenefits[i], {x: 0.8, y: 2.4 + i * 0.45, w: 3.8, h: 0.35, fontSize: 13, fontFace: FONT, color: C.text, margin: 0});
}
cd(s27, 5.2, 1.7, 4.3, 3.5, {accent: C.sec});
s27.addText("未来：微服务拆分", {x: 5.4, y: 1.8, w: 4, h: 0.4, fontSize: 16, fontFace: FONT, color: C.sec, bold: true, margin: 0});
const microserviceBenefits = [
  "模块边界稳定后拆分",
  "独立扩展和部署",
  "独立运维所有权",
  "按需引入Temporal等引擎",
  "渐进式演进"
];
for (let i = 0; i < microserviceBenefits.length; i++) {
  s27.addText("•  " + microserviceBenefits[i], {x: 5.5, y: 2.4 + i * 0.45, w: 3.8, h: 0.35, fontSize: 13, fontFace: FONT, color: C.text, margin: 0});
}
s27.addShape(pres.shapes.RECTANGLE, {x: 4.8, y: 2.8, w: 0.4, h: 0.04, fill: {color: C.muted}});
s27.addText("→", {x: 4.6, y: 2.5, w: 0.8, h: 0.6, fontSize: 24, fontFace: FONT, color: C.sec, bold: true, align: "center", valign: "middle", margin: 0});
pn(s27, 27);

// ============ Slide 28: Implementation Phases ============
const s28 = pres.addSlide();
s28.background = {color: C.bg};
tb(s28, "实施路径", "三阶段落地计划");
const phases = [
  {phase: "第一阶段", time: "1-2周", title: "内部闭环", desc: "验证平台稳定性和数字员工产出质量", items: ["部署3个数字员工", "内部使用验证", "建立工作流程"], color: C.pri},
  {phase: "第二阶段", time: "3-4周", title: "半公开", desc: "对外输出内容，收集市场反馈", items: ["内容对外发布", "收集外部反馈", "部署第4个员工"], color: C.sec},
  {phase: "第三阶段", time: "5-8周", title: "全面展示", desc: "将自运营成果转化为营销资产", items: ["官网展示数字员工", "客户互动体验", "包装营销素材"], color: C.acc}
];
for (let i = 0; i < phases.length; i++) {
  const cx = 0.5 + i * 3.1;
  cd(s28, cx, 1.2, 2.9, 4.0, {accent: phases[i].color});
  s28.addShape(pres.shapes.RECTANGLE, {x: cx, y: 1.2, w: 2.9, h: 0.6, fill: {color: phases[i].color}});
  s28.addText(phases[i].phase, {x: cx, y: 1.2, w: 2.9, h: 0.3, fontSize: 14, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
  s28.addText(phases[i].time, {x: cx, y: 1.5, w: 2.9, h: 0.3, fontSize: 11, fontFace: FONT, color: "A8CCE0", align: "center", valign: "middle", margin: 0});
  s28.addText(phases[i].title, {x: cx + 0.2, y: 2.0, w: 2.5, h: 0.4, fontSize: 16, fontFace: FONT, color: C.acc, bold: true, margin: 0});
  s28.addText(phases[i].desc, {x: cx + 0.2, y: 2.5, w: 2.5, h: 0.6, fontSize: 12, fontFace: FONT, color: C.muted, margin: 0});
  for (let j = 0; j < phases[i].items.length; j++) {
    s28.addText("•  " + phases[i].items[j], {x: cx + 0.2, y: 3.3 + j * 0.45, w: 2.5, h: 0.35, fontSize: 12, fontFace: FONT, color: C.text, margin: 0});
  }
}
pn(s28, 28);

// ============ Slide 29: Success Stories ============
const s29 = pres.addSlide();
s29.background = {color: C.bg};
tb(s29, "实施路径", "成功案例与客户见证");
s29.addText("自运营就是最好的案例", {x: 0.6, y: 1.1, w: 9, h: 0.4, fontSize: 18, fontFace: FONT, color: C.acc, bold: true, margin: 0});
cd(s29, 0.5, 1.7, 9, 3.5, {accent: C.gold});
s29.addText("演示话术参考", {x: 0.7, y: 1.8, w: 8.5, h: 0.4, fontSize: 16, fontFace: FONT, color: C.acc, bold: true, margin: 0});
s29.addText(
  '"我们的平台不是demo，我们自己就是第一个客户。你看到的这篇技术文章是我们平台的内容运营专员写的；这份竞品分析报告是市场研究分析师出的；刚才回答你问题的是客户咨询接待员。"',
  {x: 0.7, y: 2.4, w: 8.5, h: 0.9, fontSize: 13, fontFace: FONT, color: C.text, italic: true, margin: 0}
);
s29.addText(
  '"你不需要相信我们的PPT，你只需要看看我们的数字员工在做什么。"',
  {x: 0.7, y: 3.5, w: 8.5, h: 0.6, fontSize: 15, fontFace: FONT, color: C.acc, bold: true, italic: true, margin: 0}
);
s29.addText("狗食策略（Dogfooding）是科技行业验证产品的经典方法", {x: 0.7, y: 4.3, w: 8.5, h: 0.4, fontSize: 12, fontFace: FONT, color: C.muted, margin: 0});
pn(s29, 29);

// ============ Slide 30: Summary ============
const s30 = pres.addSlide();
s30.background = {color: C.dark};
s30.addShape(pres.shapes.RECTANGLE, {x: 0, y: 0, w: 0.12, h: 5.625, fill: {color: C.sec}});
s30.addShape(pres.shapes.RECTANGLE, {x: 0.12, y: 0, w: 0.04, h: 5.625, fill: {color: C.pri}});
s30.addShape(pres.shapes.OVAL, {x: 6.5, y: 3.5, w: 4, h: 4, fill: {color: C.acc}, transparency: 75});
s30.addText("总结", {x: 0.8, y: 0.3, w: 8, h: 0.5, fontSize: 30, fontFace: FONT, color: C.white, bold: true, margin: 0});
const summaryItems = [
  ["可管理", "岗位模板、组织架构、全生命周期管理", C.pri],
  ["可审计", "完整操作记录、风险分级、审批机制", C.sec],
  ["可协作", "目标驱动、动态委派、团队协作", C.acc]
];
for (let i = 0; i < summaryItems.length; i++) {
  const sy = 1.2 + i * 0.85;
  s30.addShape(pres.shapes.OVAL, {x: 0.8, y: sy + 0.08, w: 0.5, h: 0.5, fill: {color: summaryItems[i][2]}});
  s30.addText(String(i + 1), {x: 0.8, y: sy + 0.08, w: 0.5, h: 0.5, fontSize: 18, fontFace: FONT, color: C.white, bold: true, align: "center", valign: "middle", margin: 0});
  s30.addText(summaryItems[i][0], {x: 1.6, y: sy, w: 2.5, h: 0.65, fontSize: 20, fontFace: FONT, color: C.white, bold: true, valign: "middle", margin: 0});
  s30.addText(summaryItems[i][1], {x: 4.0, y: sy, w: 5.5, h: 0.65, fontSize: 16, fontFace: FONT, color: "A8CCE0", valign: "middle", margin: 0});
}
s30.addShape(pres.shapes.RECTANGLE, {x: 0.8, y: 4.0, w: 8.4, h: 0.04, fill: {color: "2A5A7A"}});
s30.addText("AI数字员工不是更聪明的工具，而是更可控的团队成员", {x: 0.6, y: 4.2, w: 8.8, h: 0.5, fontSize: 18, fontFace: FONT, color: C.gold, bold: true, margin: 0});
pn(s30, 30);

// ============ Slide 31: Next Steps ============
const s31 = pres.addSlide();
s31.background = {color: C.dark};
s31.addShape(pres.shapes.RECTANGLE, {x: 0, y: 0, w: 0.12, h: 5.625, fill: {color: C.sec}});
s31.addShape(pres.shapes.RECTANGLE, {x: 0.12, y: 0, w: 0.04, h: 5.625, fill: {color: C.pri}});
s31.addShape(pres.shapes.OVAL, {x: 6.5, y: -1, w: 5, h: 5, fill: {color: C.acc}, transparency: 70});
s31.addShape(pres.shapes.OVAL, {x: 7.5, y: 2, w: 4, h: 4, fill: {color: C.pri}, transparency: 75});
s31.addText("下一步", {x: 0.8, y: 0.8, w: 8, h: 0.6, fontSize: 36, fontFace: FONT, color: C.white, bold: true, margin: 0});
s31.addText("联系我们，开始您的AI数字员工之旅", {x: 0.8, y: 1.5, w: 8, h: 0.5, fontSize: 20, fontFace: FONT, color: "A8D8EA", bold: true, margin: 0});
s31.addShape(pres.shapes.RECTANGLE, {x: 0.8, y: 2.1, w: 2.5, h: 0.04, fill: {color: C.sec}});
const nextSteps = [
  "预约产品演示",
  "讨论落地场景",
  "制定实施计划",
  "启动试点项目"
];
for (let i = 0; i < nextSteps.length; i++) {
  s31.addText((i + 1) + ".  " + nextSteps[i], {x: 0.8, y: 2.5 + i * 0.5, w: 8, h: 0.4, fontSize: 16, fontFace: FONT, color: "A8CCE0", margin: 0});
}
s31.addText("感谢您的时间", {x: 0.8, y: 4.8, w: 8, h: 0.5, fontSize: 14, fontFace: FONT, color: "A8CCE0", margin: 0});
pn(s31, 31);

// Write file
pres.writeFile({fileName: "/home/wanggang/projects/ai-platform/AI数字员工平台-售前方案.pptx"})
  .then(() => console.log("PPT created successfully!"))
  .catch(err => console.error("Error:", err));
