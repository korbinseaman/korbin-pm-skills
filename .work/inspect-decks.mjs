import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "file:///C:/Users/mahai/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const [,, sourcePath, outDir] = process.argv;
if (!sourcePath || !outDir) throw new Error("usage: inspect-decks.mjs <source.pptx> <out-dir>");
await fs.mkdir(outDir, { recursive: true });
const deck = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
const snap = await deck.inspect({
  kind: "deck,slide,textbox,shape,image,table,chart,notes,layout",
  include: "id,slide,name,title,text,textPreview,textChars,textLines,bbox,bboxUnit,rows,cols,chartType,alt,isPlaceholder,placeholders",
  maxChars: 200000,
});
await fs.writeFile(path.join(outDir, "inspect.ndjson"), snap.ndjson, "utf8");
const montage = await deck.export({ format: "png", montage: true, scale: 1 });
console.log("montage", montage?.constructor?.name, Object.keys(montage ?? {}));
const asBytes = async (blob) => {
  if (blob instanceof Uint8Array) return blob;
  if (blob?.bytes instanceof Uint8Array) return blob.bytes;
  if (blob?.data instanceof Uint8Array) return blob.data;
  if (blob?.arrayBuffer) return new Uint8Array(await blob.arrayBuffer());
  throw new Error(`unknown export blob ${blob?.constructor?.name}: ${Object.keys(blob ?? {})}`);
};
await fs.writeFile(path.join(outDir, "montage.png"), await asBytes(montage));
for (let i = 0; i < deck.slides.items.length; i++) {
  const slide = deck.slides.getItem(i);
  const png = await slide.export({ format: "png", scale: 1 });
  await fs.writeFile(path.join(outDir, `slide-${String(i + 1).padStart(2, "0")}.png`), await asBytes(png));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(outDir, `slide-${String(i + 1).padStart(2, "0")}.json`), typeof layout === "string" ? layout : JSON.stringify(layout, null, 2), "utf8");
}
console.log(JSON.stringify({ sourcePath, slides: deck.slides.items.length, masters: deck.masters.items.length, layouts: deck.layouts.items.length }));
