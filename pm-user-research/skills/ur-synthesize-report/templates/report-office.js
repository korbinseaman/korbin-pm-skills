/* Offline OOXML exports. ZIP entries are stored with CRC32, not renamed HTML. */
(() => {
  "use strict";
  const xml = value => String(value ?? "").replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&apos;"}[c]));
  const enc = new TextEncoder();
  const crcTable = Array.from({length:256}, (_, i) => { let c = i; for (let k=0;k<8;k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
  const crc32 = bytes => { let c = 0xffffffff; for (const b of bytes) c = crcTable[(c ^ b) & 255] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  const header = (size, fields) => { const out = new Uint8Array(size), view = new DataView(out.buffer); for (const [offset, value, length] of fields) length === 2 ? view.setUint16(offset, value, true) : view.setUint32(offset, value, true); return out; };
  function zip(files, mime) {
    const local = [], central = []; let offset = 0;
    for (const [path, content] of Object.entries(files)) {
      const name = enc.encode(path), bytes = typeof content === "string" ? enc.encode(content) : content, crc = crc32(bytes);
      const h = header(30, [[0,0x04034b50,4],[4,20,2],[6,0x800,2],[12,33,2],[14,crc,4],[18,bytes.length,4],[22,bytes.length,4],[26,name.length,2]]);
      local.push(h,name,bytes);
      central.push(header(46, [[0,0x02014b50,4],[4,20,2],[6,20,2],[8,0x800,2],[14,33,2],[16,crc,4],[20,bytes.length,4],[24,bytes.length,4],[28,name.length,2],[42,offset,4]]),name);
      offset += h.length + name.length + bytes.length;
    }
    const count = Object.keys(files).length, centralSize = central.reduce((sum, bytes) => sum + bytes.length, 0);
    return new Blob([...local,...central,header(22,[[0,0x06054b50,4],[8,count,2],[10,count,2],[12,centralSize,4],[16,offset,4]])], {type:mime});
  }
  const REL = "http://schemas.openxmlformats.org/package/2006/relationships", OREL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
  const relationships = entries => `<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="${REL}">${entries.map(([id,type,target]) => `<Relationship Id="${id}" Type="${OREL}/${type}" Target="${xml(target)}"/>`).join("")}</Relationships>`;
  const contentTypes = entries => `<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>${entries.map(([path,type]) => `<Override PartName="/${path}" ContentType="application/vnd.openxmlformats-officedocument.${type}"/>`).join("")}</Types>`;
  const intro = model => [`批次：${model.runId}`, `数据来源：合成模拟数据，不代表真实用户或市场总体。`, `筛选条件：${model.conditions}`, `当前样本：${model.sampleN}；分析类型：${model.mode === "conclusions" ? "报告分析结论" : model.mode === "quality" ? "问卷质量报告" : model.mode === "cross" ? "交叉分析" : "普通分析"}`];
  function blocks(model) {
    const out = [];
    for (const section of model.sections) {
      if (section.kind === "question") {
        out.push({title:section.title,note:section.note,rows:[["选项","人数","比例"],...section.items.map(item => [item.label,item.count,`${item.percent.toFixed(1)}%`])],items:section.items});
      } else {
        // Wide cross-tables are split into labeled column blocks without dropping data.
        for (let start=0;start<section.labels.length;start+=3) {
          const labels=section.labels.slice(start,start+3);
          out.push({title:section.title + (section.labels.length>3 ? `（选项 ${start+1}–${Math.min(start+3,section.labels.length)}）` : ""),note:section.note,rows:[["分组","组人数","有效 n / 空白",...labels],...section.rows.map(row => [row.label,row.groupN ?? row.base+row.missing,`${row.base} / ${row.missing}`,...row.values.slice(start,start+3).map(value => `${value}（${row.base ? (value/row.base*100).toFixed(1)+"%" : "—"}）`)])]});
        }
      }
    }
    return out;
  }
  function docx(model) {
    const p = (text,style="Normal") => `<w:p><w:pPr><w:pStyle w:val="${style}"/></w:pPr><w:r><w:t xml:space="preserve">${xml(text)}</w:t></w:r></w:p>`;
    const width = model.paper === "A3" ? 14570 : 9638;
    const table = rows => {
      const cols=rows[0].length, first=cols===3 ? width*0.55 : width*0.28, other=(width-first)/(cols-1), widths=rows[0].map((_,i)=>Math.floor(i===0?first:other));
      return `<w:tbl><w:tblPr><w:tblW w:w="${width}" w:type="dxa"/><w:tblLayout w:type="fixed"/><w:tblBorders>${["top","left","bottom","right","insideH","insideV"].map(side=>`<w:${side} w:val="single" w:sz="4" w:color="D9D9D9"/>`).join("")}</w:tblBorders><w:tblCellMar><w:top w:w="90" w:type="dxa"/><w:left w:w="110" w:type="dxa"/><w:bottom w:w="90" w:type="dxa"/><w:right w:w="110" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>${widths.map(w=>`<w:gridCol w:w="${w}"/>`).join("")}</w:tblGrid>${rows.map((row,index)=>`<w:tr>${index===0?'<w:trPr><w:tblHeader/></w:trPr>':""}${row.map((value,col)=>`<w:tc><w:tcPr><w:tcW w:w="${widths[col]}" w:type="dxa"/><w:vAlign w:val="center"/>${index===0?'<w:shd w:fill="EEF3F7"/>':""}</w:tcPr>${p(value)}</w:tc>`).join("")}</w:tr>`).join("")}</w:tbl>`;
    };
    const styles=`<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="Microsoft YaHei"/><w:sz w:val="22"/><w:color w:val="000000"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>${[["Title",36],["Heading1",28]].map(([id,size])=>`<w:style w:type="paragraph" w:styleId="${id}"><w:name w:val="${id==="Title"?"Title":"heading 1"}"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="280" w:after="180"/></w:pPr><w:rPr><w:b/><w:color w:val="000000"/><w:sz w:val="${size}"/></w:rPr></w:style>`).join("")}</w:styles>`;
    const narrative=model.narrative.flatMap(section=>[p(section.title+"（全批次）","Heading1"),...section.lines.map(line=>p(line))]).join("");
    const body=p(model.title,"Title")+intro(model).map(line=>p(line)).join("")+blocks(model).map(block=>p(block.title,"Heading1")+p(block.note)+table(block.rows)+p("")).join("")+narrative;
    return zip({"[Content_Types].xml":contentTypes([["word/document.xml","wordprocessingml.document.main+xml"],["word/styles.xml","wordprocessingml.styles+xml"]]),"_rels/.rels":relationships([["rId1","officeDocument","word/document.xml"]]),"word/_rels/document.xml.rels":relationships([["rId1","styles","styles.xml"]]),"word/styles.xml":styles,"word/document.xml":`<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>${body}<w:sectPr><w:pgSz w:w="${model.paper==="A3"?16838:11906}" w:h="${model.paper==="A3"?23811:16838}"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr></w:body></w:document>`},"application/vnd.openxmlformats-officedocument.wordprocessingml.document");
  }
  function xlsx(model) {
    const sheets=[{name:"报告说明",rows:[["项目","内容"],["报告",model.title],["批次",model.runId],["筛选条件",model.conditions],["可分析样本",model.sampleN],["来源","合成模拟数据，不代表真实用户或市场总体"],...model.narrative.flatMap(s=>s.lines.map(line=>[s.title+"（全批次）",line]))]}];
    blocks(model).forEach((block,index)=>sheets.push({name:`${model.mode==="cross"?"交叉":"题目"}${index+1}`,rows:[[block.title],[block.note],...block.rows]}));
    const colName=index=>{let str="",n=index+1;while(n){n--;str=String.fromCharCode(65+n%26)+str;n=Math.floor(n/26);}return str;};
    const files={"_rels/.rels":relationships([["rId1","officeDocument","xl/workbook.xml"]]),"[Content_Types].xml":contentTypes([["xl/workbook.xml","spreadsheetml.sheet.main+xml"],["xl/styles.xml","spreadsheetml.styles+xml"],...sheets.map((_,i)=>[`xl/worksheets/sheet${i+1}.xml`,"spreadsheetml.worksheet+xml"])])};
    files["xl/workbook.xml"]=`<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="${OREL}"><sheets>${sheets.map((s,i)=>`<sheet name="${xml(s.name)}" sheetId="${i+1}" r:id="rId${i+1}"/>`).join("")}</sheets></workbook>`;
    files["xl/_rels/workbook.xml.rels"]=relationships([...sheets.map((_,i)=>[`rId${i+1}`,"worksheet",`worksheets/sheet${i+1}.xml`]),[`rId${sheets.length+1}`,"styles","styles.xml"]]);
    files["xl/styles.xml"]='<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Microsoft YaHei"/></font><font><b/><sz val="11"/><name val="Microsoft YaHei"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FFEEF3F7"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"><alignment vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0"><alignment vertical="center" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>';
    sheets.forEach((sheet,index)=>{const cols=Math.max(...sheet.rows.map(row=>row.length));files[`xl/worksheets/sheet${index+1}.xml`]=`<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="${index?3:1}" topLeftCell="A${index?4:2}" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols>${Array.from({length:cols},(_,i)=>`<col min="${i+1}" max="${i+1}" width="${i===0?45:24}" customWidth="1"/>`).join("")}</cols><sheetData>${sheet.rows.map((row,i)=>`<row r="${i+1}">${row.map((value,j)=>typeof value==="number"?`<c r="${colName(j)}${i+1}" s="${i===(index?2:0)?1:0}"><v>${value}</v></c>`:`<c r="${colName(j)}${i+1}" t="inlineStr" s="${i===(index?2:0)?1:0}"><is><t xml:space="preserve">${xml(value)}</t></is></c>`).join("")}</row>`).join("")}</sheetData></worksheet>`;});
    return zip(files,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
  }
  function pptx(model) {
    const NS='xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="'+OREL+'" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"';
    const group='<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>';
    const slides=[];let shapeId=1;
    const box=(text,x,y,w,h,size=1400,color="263746",bold=false)=>`<p:sp><p:nvSpPr><p:cNvPr id="${++shapeId}" name="Text ${shapeId}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="${x}" y="${y}"/><a:ext cx="${w}" cy="${h}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr><p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0"><a:normAutofit/></a:bodyPr><a:lstStyle/>${String(text).split("\n").map(line=>`<a:p><a:r><a:rPr lang="zh-CN" sz="${size}" b="${bold?1:0}"><a:solidFill><a:srgbClr val="${color}"/></a:solidFill><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/></a:rPr><a:t>${xml(line)}</a:t></a:r></a:p>`).join("")}</p:txBody></p:sp>`;
    const rect=(x,y,w,h)=>`<p:sp><p:nvSpPr><p:cNvPr id="${++shapeId}" name="Bar ${shapeId}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="${x}" y="${y}"/><a:ext cx="${w}" cy="${h}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="0997F0"/></a:solidFill><a:ln><a:noFill/></a:ln></p:spPr></p:sp>`;
    const slide=(title,note,body)=>{shapeId=1;slides.push(`<p:sld ${NS}><p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:effectLst/></p:bgPr></p:bg><p:spTree>${group}${box(title,550000,380000,11100000,900000,2600,"172C3D",true)}${box(note,550000,1250000,11100000,600000,1100,"6B7A87")}${body()}${box(`${model.runId} · 合成模拟数据 · ${slides.length+1}`,550000,6350000,11000000,240000,900,"8B98A3")}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>`);};
    if(model.mode==="conclusions" && model.conclusionSlides?.length){
      model.conclusionSlides.slice(0,3).forEach((page,index)=>slide(page.title,"调研分析结论 · 全批次样本 n="+model.sampleN+" · 完整结论见 HTML",()=>{
        const lines=page.lines.map(line=>String(line).length>140?String(line).slice(0,138)+"…（详见HTML）":String(line));
        const items=page.chart?.items||[], chart=page.chart||{};
        let out=box(lines.join("\n\n"),550000,2050000,4800000,3850000,1500);
        out+=box(chart.title||"数据证据",5700000,1900000,5900000,800000,1400,"172C3D",true);
        out+=box(chart.note||"暂无题目统计",5700000,5450000,5900000,700000,1000,"6B7A87");
        if(!items.length)return out+box("暂无可配对的数据图表",5700000,3200000,5800000,600000,1500,"8B98A3");
        return out+items.slice(0,6).map((item,i)=>{
          const y=2800000+i*420000;
          return box(item.label,5700000,y,2200000,390000,1150)+rect(8000000,y+70000,Math.floor(Math.max(0,Math.min(100,item.percent))/100*2600000),180000)+box(item.percent.toFixed(1)+"%",10700000,y,950000,390000,1200);
        }).join("");
      }));
    } else {
    slide(model.title,"调研统计报告",()=>box(intro(model).join("\n"),650000,2200000,10800000,3400000,1900));
    for (const block of blocks(model)) {
      const bodyRows=block.rows.slice(1);
      for(let start=0;start<Math.max(1,bodyRows.length);start+=7){const pageRows=bodyRows.slice(start,start+7);slide(block.title+(bodyRows.length>7?`（${start+1}–${Math.min(start+7,bodyRows.length)}）`:""),block.note,()=>{
        if(block.items){const max=Math.max(...block.items.map(item=>item.count),1);return pageRows.map((row,i)=>{const item=block.items[start+i],y=2050000+i*540000;return box(item.label,550000,y,3700000,460000,1300)+rect(4400000,y+60000,Math.max(0,Math.floor(item.count/max*5300000)),240000)+box(`${item.count}（${item.percent.toFixed(1)}%）`,9900000,y,1700000,460000,1300);}).join("");}
        return [block.rows[0],...pageRows].map((row,i)=>row.map((value,j)=>box(value,550000+j*Math.floor(11100000/row.length),1950000+i*510000,Math.floor(11100000/row.length)-100000,460000,i?1100:1200,i?"354856":"0997F0",!i)).join("")).join("");
      });}
    }
    model.narrative.forEach(section=>{const lines=section.lines.flatMap(line=>Array.from({length:Math.max(1,Math.ceil(String(line).length/90))},(_,i)=>String(line).slice(i*90,(i+1)*90)));for(let start=0;start<lines.length;start+=6)slide(section.title+"（全批次）","研究者分析不随当前筛选自动改写",()=>box(lines.slice(start,start+6).join("\n\n"),650000,2000000,10800000,3900000,1500));});
    }
    const files={"_rels/.rels":relationships([["rId1","officeDocument","ppt/presentation.xml"]])};
    files["[Content_Types].xml"]=contentTypes([["ppt/presentation.xml","presentationml.presentation.main+xml"],["ppt/slideMasters/slideMaster1.xml","presentationml.slideMaster+xml"],["ppt/slideLayouts/slideLayout1.xml","presentationml.slideLayout+xml"],["ppt/theme/theme1.xml","theme+xml"],...slides.map((_,i)=>[`ppt/slides/slide${i+1}.xml`,"presentationml.slide+xml"])]);
    files["ppt/presentation.xml"]=`<p:presentation ${NS}><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rIdMaster"/></p:sldMasterIdLst><p:sldIdLst>${slides.map((_,i)=>`<p:sldId id="${256+i}" r:id="rId${i+1}"/>`).join("")}</p:sldIdLst><p:sldSz cx="12192000" cy="6858000" type="screen16x9"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>`;
    files["ppt/_rels/presentation.xml.rels"]=relationships([["rIdMaster","slideMaster","slideMasters/slideMaster1.xml"],...slides.map((_,i)=>[`rId${i+1}`,"slide",`slides/slide${i+1}.xml`])]);
    const colorMap='<p:clrMap accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" bg1="lt1" bg2="lt2" folHlink="folHlink" hlink="hlink" tx1="dk1" tx2="dk2"/>';
    files["ppt/slideMasters/slideMaster1.xml"]=`<p:sldMaster ${NS}><p:cSld><p:spTree>${group}</p:spTree></p:cSld>${colorMap}<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>`;
    files["ppt/slideMasters/_rels/slideMaster1.xml.rels"]=relationships([["rId1","slideLayout","../slideLayouts/slideLayout1.xml"],["rId2","theme","../theme/theme1.xml"]]);
    files["ppt/slideLayouts/slideLayout1.xml"]=`<p:sldLayout ${NS} type="blank" preserve="1"><p:cSld name="Blank"><p:spTree>${group}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>`;
    files["ppt/slideLayouts/_rels/slideLayout1.xml.rels"]=relationships([["rId1","slideMaster","../slideMasters/slideMaster1.xml"]]);
    const colors={dk1:"172C3D",lt1:"FFFFFF",dk2:"354856",lt2:"F3F6F8",accent1:"0997F0",accent2:"2DC3C8",accent3:"FFCB43",accent4:"FF794F",accent5:"6CCD48",accent6:"4EA3C5",hlink:"0997F0",folHlink:"7252A8"};
    files["ppt/theme/theme1.xml"]=`<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Research"><a:themeElements><a:clrScheme name="Research">${Object.entries(colors).map(([key,value])=>`<a:${key}><a:srgbClr val="${value}"/></a:${key}>`).join("")}</a:clrScheme><a:fontScheme name="Research"><a:majorFont><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/><a:cs typeface="Arial"/></a:majorFont><a:minorFont><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/><a:cs typeface="Arial"/></a:minorFont></a:fontScheme><a:fmtScheme name="Research"><a:fillStyleLst>${[1,2,3].map(()=>'<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>').join("")}</a:fillStyleLst><a:lnStyleLst>${[6350,12700,19050].map(w=>`<a:ln w="${w}"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln>`).join("")}</a:lnStyleLst><a:effectStyleLst>${[1,2,3].map(()=>'<a:effectStyle><a:effectLst/></a:effectStyle>').join("")}</a:effectStyleLst><a:bgFillStyleLst>${[1,2,3].map(()=>'<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>').join("")}</a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>`;
    slides.forEach((s,i)=>{files[`ppt/slides/slide${i+1}.xml`]=s;files[`ppt/slides/_rels/slide${i+1}.xml.rels`]=relationships([["rId1","slideLayout","../slideLayouts/slideLayout1.xml"]]);});
    return zip(files,"application/vnd.openxmlformats-officedocument.presentationml.presentation");
  }
  window.ReportOffice = {build:(format,model)=>({docx,pptx,xlsx}[format] || (()=>{throw new Error("不支持的格式");}))(model)};
})();
