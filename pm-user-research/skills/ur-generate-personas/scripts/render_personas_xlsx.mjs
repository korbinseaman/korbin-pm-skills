import fs from "node:fs/promises";
import { pathToFileURL } from "node:url";

const [, , dataPath, outputPath, artifactToolPath, previewPath] = process.argv;
if (!dataPath || !outputPath || !artifactToolPath) {
  console.error("用法：node render_personas_xlsx.mjs <personas.json> <output.xlsx> <artifact_tool.mjs>");
  process.exit(2);
}

const { SpreadsheetFile, Workbook } = await import(pathToFileURL(artifactToolPath).href);
const data = JSON.parse(await fs.readFile(dataPath, "utf8"));
const personas = data.personas ?? [];
const fieldOrder = [];
for (const persona of personas) {
  for (const key of Object.keys(persona)) {
    if (!fieldOrder.includes(key)) fieldOrder.push(key);
  }
}
const matrix = [fieldOrder, ...personas.map((persona) => fieldOrder.map((key) => persona[key] ?? ""))];
const workbook = Workbook.create();
const sheet = workbook.worksheets.add("画像总表");
sheet.showGridLines = false;
sheet.getRange("A1").values = [["全量用户画像"]];
sheet.getRange("A2").values = [[`调研课题：${data.topic ?? ""}；画像总数：${personas.length}人；全部为合成画像`]];
const endColumn = (index) => {
  let value = index + 1;
  let result = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    value = Math.floor((value - 1) / 26);
  }
  return result;
};
const lastColumn = endColumn(fieldOrder.length - 1);
const lastRow = matrix.length + 3;
sheet.getRange(`A4:${lastColumn}${lastRow}`).values = matrix;
sheet.getRange(`A1:${lastColumn}${lastRow}`).format.font = { name: "Arial", size: 10, color: "#1F2937" };
sheet.getRange(`A1:${lastColumn}1`).format.font = { name: "Arial", size: 15, bold: true, color: "#1F2937" };
sheet.getRange(`A2:${lastColumn}2`).format.font = { name: "Arial", size: 10, italic: true, color: "#6B7280" };
sheet.getRange(`A4:${lastColumn}4`).format = {
  fill: "#1F4E78",
  font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
sheet.getRange(`A5:${lastColumn}${lastRow}`).format = {
  verticalAlignment: "center",
  wrapText: true,
  borders: { insideHorizontal: { style: "thin", color: "#D9E2F3" } },
};
sheet.getRange(`A4:${lastColumn}${lastRow}`).format.autofitColumns();
sheet.getRange(`A4:${lastColumn}${lastRow}`).format.autofitRows();
const widthByField = {
  "画像编号": 12, "姓名": 12, "年龄": 9, "性别": 9, "居住地": 20,
  "婚姻状况": 12, "职业": 16, "专业": 16, "月收入": 16, "可支配收入": 16,
  "通用行为": 42, "使用设备": 26, "相关使用经验": 22, "使用阶段": 14,
  "系统App使用习惯": 42, "相关产品或功能使用习惯": 48, "判断": 52,
};
for (let index = 0; index < fieldOrder.length; index += 1) {
  const column = endColumn(index);
  sheet.getRange(`${column}1:${column}${lastRow}`).format.columnWidth = widthByField[fieldOrder[index]] ?? 20;
}
sheet.getRange(`A5:${lastColumn}${lastRow}`).format.rowHeight = 54;
sheet.freezePanes.freezeRows(4);
sheet.freezePanes.freezeColumns(2);
const table = sheet.tables.add(`A4:${lastColumn}${lastRow}`, true, "PersonasTable");
table.showFilterButton = true;
table.showBandedColumns = false;

const summary = workbook.worksheets.add("构成摘要");
summary.showGridLines = false;
summary.getRange("A1").values = [["用户画像构成摘要"]];
const nameLengths = new Map();
for (const persona of personas) {
  const label = `${String(persona["姓名"] ?? "").trim().length}字全名`;
  nameLengths.set(label, (nameLengths.get(label) ?? 0) + 1);
}
const nameLengthText = ["2字全名", "3字全名", "4字全名"]
  .map((label) => `${label}${nameLengths.get(label) ?? 0}人`)
  .join("、");
summary.getRange("A2:B7").values = [
  ["调研课题", data.topic ?? ""],
  ["画像总数", personas.length],
  ["全量用户ID", personas.map((persona) => persona["画像编号"]).join("、")],
  ["数据性质", "合成画像，不代表真实人口或产品用户分布"],
  ["姓名结构", nameLengthText],
  ["画像明细", "请查看“画像总表”工作表或 persons/ 目录"],
];
const allocations = data.generation_spec?.group_allocation ?? [];
const summaryRows = [["用户群体", "人数", "占比"]];
for (const item of allocations) summaryRows.push([item.audience_group ?? "", item.count ?? 0, item.share ?? 0]);
const summaryLastRow = 8 + summaryRows.length;
summary.getRange(`A9:C${summaryLastRow}`).values = summaryRows;
summary.getRange("A1:C1").format.font = { name: "Arial", size: 15, bold: true, color: "#1F2937" };
summary.getRange("A9:C9").format = { fill: "#1F4E78", font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center" };
summary.getRange(`A1:C${summaryLastRow}`).format.font = { name: "Arial", size: 10, color: "#1F2937" };
summary.getRange("A1:C1").format.font = { name: "Arial", size: 15, bold: true, color: "#1F2937" };
summary.getRange(`B10:B${summaryLastRow}`).format.numberFormat = "#,##0";
summary.getRange(`C10:C${summaryLastRow}`).format.numberFormat = "0.0%";
summary.getRange("A2:A7").format.font = { name: "Arial", size: 10, bold: true, color: "#1F2937" };
summary.getRange("B2:B7").format.wrapText = true;
summary.getRange(`A1:A${summaryLastRow}`).format.columnWidth = 24;
summary.getRange(`B1:B${summaryLastRow}`).format.columnWidth = 72;
summary.getRange(`C1:C${summaryLastRow}`).format.columnWidth = 14;
summary.getRange(`A1:C${summaryLastRow}`).format.autofitRows();
summary.freezePanes.freezeRows(9);
const summaryTable = summary.tables.add(`A9:C${summaryLastRow}`, true, "PersonaGroupSummary");
summaryTable.showFilterButton = true;

workbook.recalculate();
if (previewPath) {
  const preview = await workbook.render({ sheetName: "画像总表", range: `A1:${lastColumn}${lastRow}`, scale: 1, format: "png" });
  await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
}
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
