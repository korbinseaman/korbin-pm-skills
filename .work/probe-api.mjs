import { FileBlob, PresentationFile } from "file:///C:/Users/mahai/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";
const deck=await PresentationFile.importPptx(await FileBlob.load("E:/projects/korbin-pm-skills/workspace/华为PPT模板-浅色版.pptx"));
const names=(o)=>[...new Set([...Object.getOwnPropertyNames(o),...Object.getOwnPropertyNames(Object.getPrototypeOf(o)??{})])].sort();
console.log('slides',names(deck.slides));
console.log('slide',names(deck.slides.getItem(0)));
console.log(deck.help("slides",{include:["index","notes"],maxChars:6000}).ndjson ?? deck.help("slides",{include:["index","notes"],maxChars:6000}));
