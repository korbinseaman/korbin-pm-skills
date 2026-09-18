(() => {
  const data = JSON.parse(document.getElementById("report-interactive-data").textContent || "{}");
  const questions = data.questions || [];
  const responses = data.responses || [];
  const saved = window.__reportState || { filters: window.__reportFilters || [] };
  const tabs = ["ordinary", "cross", "conclusions", "quality"];
  let analysisTab = tabs.includes(saved.analysisTab) ? saved.analysisTab : "ordinary";
  const active = (saved.filters || []).map(filter => ({ question_id: filter.question_id, values: Array.isArray(filter.values) ? filter.values : filter.value ? [filter.value] : [] })).filter(filter => filter.question_id && filter.values.length);
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? "").replace(/[&<>\"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
  const split = value => String(value ?? "").split(/[；;]/).map(item => item.trim()).filter(Boolean);
  const palette = ["#1495ff", "#29c5cc", "#ffbf35", "#ff8045", "#77c942", "#899ba8"];
  const questionViews = saved.questionViews || {};
  let groupIds = saved.groupIds || [], targetIds = saved.targetIds || [];
  const questionById = id => questions.find(question => question.id === id);
  const choiceValues = (question, value) => question && (question.type === "multi_choice" || question.type === "ranking") ? split(value) : value === undefined || value === null || value === "" ? [] : [String(value)];
  const valuesFor = question => [...new Set([...(question?.options || []), ...responses.flatMap(row => choiceValues(question, row.answers[question.id]))])];
  const selectOptions = (select, items, selected) => { select.innerHTML = items.map(item => `<option value="${esc(item.value ?? item)}"${String(item.value ?? item) === String(selected) ? " selected" : ""}>${esc(item.label ?? item)}</option>`).join(""); };
  const applyQuestionOptions = (select, selected) => selectOptions(select, questions.map(question => ({ value: question.id, label: `${question.id} · ${question.question}` })), selected);
  const filterQuestion = $("filter-question"), filterValues = $("filter-value"), chartQuestion = $("chart-question"), chartType = $("chart-type"), crossGroup = $("cross-group"), crossTarget = $("cross-target");
  const setFilterValues = () => {
    const question = questionById(filterQuestion.value);
    const values = question ? valuesFor(question) : [];
    const selected = active.find(filter => filter.question_id === question?.id)?.values || [];
    selectOptions(filterValues, values);
    [...filterValues.options].forEach(option => { option.selected = selected.includes(option.value); });
    $("filter-options").innerHTML = values.map(value => `<label class="check-option"><input type="checkbox" value="${esc(value)}"${selected.includes(value) ? " checked" : ""}><span>${esc(value)}</span></label>`).join("") || '<p class="empty">没有可筛选的选项。</p>';
    $("filter-options").querySelectorAll("input").forEach(input => input.addEventListener("change", () => { const option = [...filterValues.options].find(option => option.value === input.value); if (option) option.selected = input.checked; }));
  };
  const hasChoice = (row, question, label) => choiceValues(question, row.answers[question.id]).includes(String(label));
  const matches = (row, filter) => { const question = questionById(filter.question_id); return question && filter.values.some(value => hasChoice(row, question, value)); };
  const filtered = () => responses.filter(row => active.every(filter => matches(row, filter)));
  const distributionFor = (question, subset) => {
    const raw = subset.map(row => row.answers[question.id]).filter(value => value !== undefined && value !== null && value !== "");
    const ranking = question.type === "ranking" ? raw.map(split) : [];
    const observed = question.type === "multi_choice" ? raw.flatMap(value => choiceValues(question, value)) : question.type === "ranking" ? ranking.map(items => items[0]).filter(Boolean) : raw.map(String);
    const counts = new Map(); observed.forEach(value => counts.set(String(value), (counts.get(String(value)) || 0) + 1));
    const order = [...new Set([...(question.options || []), ...counts.keys()])];
    const distribution = order.map(label => ({ label, count: counts.get(label) || 0, percent: raw.length ? (counts.get(label) || 0) / raw.length * 100 : 0 }));
    let note = `实际分母 ${raw.length}；筛选样本中空白/未作答 ${subset.length - raw.length}。`;
    if (question.type === "multi_choice") note += " 多选题的百分比合计可超过 100%。";
    if (question.type === "ranking") { const averages = order.map(label => { const positions = ranking.map(items => items.indexOf(label) + 1).filter(Boolean); return positions.length ? `${label} ${ (positions.reduce((sum, item) => sum + item, 0) / positions.length).toFixed(2) }` : ""; }).filter(Boolean); note += ` 以下按第一选择统计；平均名次：${averages.join("；") || "无有效名次"}。`; }
    if ((question.type === "likert_scale" || question.type === "nps") && raw.length) { const nums = raw.map(Number).filter(Number.isFinite); if (nums.length) { const mean = nums.reduce((sum, item) => sum + item, 0) / nums.length; const variance = nums.length > 1 ? nums.reduce((sum, item) => sum + (item - mean) ** 2, 0) / (nums.length - 1) : null; note += ` 均值 ${mean.toFixed(2)}；标准差 ${variance === null ? "样本不足" : Math.sqrt(variance).toFixed(2)}。`; } }
    return { distribution, base: raw.length, note };
  };
  const chartSvg = (items, type, title) => {
    if (!items.some(item => item.count)) return '<p class="empty">当前筛选下没有可绘制的回答。</p>';
    const max = 100;
    if (type === "pie" || type === "donut") {
      const total = items.reduce((sum,item)=>sum+item.count,0), cx=160,cy=150,r=112;
      let angle=-Math.PI/2;
      const arcs=items.map((item,i)=>{
        if(!item.count)return "";
        const next=angle+item.count/total*Math.PI*2, x1=cx+r*Math.cos(angle),y1=cy+r*Math.sin(angle),x2=cx+r*Math.cos(next),y2=cy+r*Math.sin(next);
        const tip=esc(item.label)+" · "+item.count+"（"+(item.count/total*100).toFixed(1)+"%）";
        const arc=item.count===total ? '<circle cx="'+cx+'" cy="'+cy+'" r="'+r+'" fill="'+palette[i%palette.length]+'"><title>'+tip+'</title></circle>' : '<path d="M '+cx+' '+cy+' L '+x1+' '+y1+' A '+r+' '+r+' 0 '+(next-angle>Math.PI?1:0)+' 1 '+x2+' '+y2+' Z" fill="'+palette[i%palette.length]+'"><title>'+tip+'</title></path>';
        const middle=(angle+next)/2, lr=type==="donut"?94:68; const label=item.count/total>=.04?'<text x="'+(cx+lr*Math.cos(middle))+'" y="'+(cy+lr*Math.sin(middle))+'" text-anchor="middle" dominant-baseline="middle" class="slice-percent">'+(item.count/total*100).toFixed(1)+'%</text>':""; angle=next;return arc+label;
      }).join("");
      const hole=type==="donut" ? '<circle cx="160" cy="150" r="72" fill="white"/><text x="160" y="146" text-anchor="middle" class="center-label">'+'100%'+'</text><text x="160" y="168" text-anchor="middle" class="center-note">占比合计</text>':"";
      return '<div class="viz"><svg viewBox="0 0 840 '+Math.max(310,items.length*31+35)+'" role="img" aria-label="'+esc(title)+(type==="pie"?"饼图":"圆环图")+'">'+arcs+hole+items.map((item,i)=>'<g transform="translate(330 '+(38+i*31)+')"><circle r="6" cy="-4" fill="'+palette[i%palette.length]+'"/><text x="18" class="legend"><title>'+esc(item.label)+'</title>'+esc(String(item.label).slice(0,29))+' · '+(item.count/total*100).toFixed(1)+'%</text></g>').join("")+'</svg></div>';
    }
    if(type==="column"){
      const step=700/Math.max(items.length,1),height=320;
      return '<div class="viz"><svg viewBox="0 0 800 320" role="img" aria-label="'+esc(title)+'柱状图"><line x1="45" x2="780" y1="265" y2="265" class="grid"/>'+items.map((item,i)=>{const h=item.percent/max*210,x=55+i*step,w=Math.min(58,step*.6);return '<rect x="'+x+'" y="'+(265-h)+'" width="'+w+'" height="'+h+'" rx="3" fill="'+palette[0]+'"/><text x="'+(x+w/2)+'" y="'+(253-h)+'" text-anchor="middle" class="value">'+item.percent.toFixed(1)+'%</text><text x="'+(x+w/2)+'" y="290" text-anchor="middle" class="axis"><title>'+esc(item.label)+'</title>'+esc(String(item.label).slice(0,8))+'</text>';}).join("")+'</svg></div>';
    }
    if (type === "line") { const width = 760, height = 290, left = 48, bottom = 50, usableW = width - left - 20, usableH = height - bottom - 28; const points = items.map((item, index) => [left + (items.length === 1 ? usableW / 2 : index * usableW / (items.length - 1)), 28 + usableH - item.percent / max * usableH]); const path = points.map((point, index) => `${index ? "L" : "M"}${point[0].toFixed(1)},${point[1].toFixed(1)}`).join(" "); return `<div class="viz"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(title)}折线图"><line x1="${left}" y1="${28 + usableH}" x2="${width - 20}" y2="${28 + usableH}" class="grid"/><line x1="${left}" y1="28" x2="${left}" y2="${28 + usableH}" class="grid"/><path d="${path}" class="line-path"/>${points.map((point, index) => `<g><circle cx="${point[0]}" cy="${point[1]}" r="5" class="line-dot"/><text x="${point[0]}" y="${point[1] - 11}" text-anchor="middle" class="value">${items[index].percent.toFixed(1)}%</text><text x="${point[0]}" y="${height - 20}" text-anchor="middle" class="axis">${esc(String(items[index].label).slice(0, 9))}</text></g>`).join("")}</svg></div>`; }
    const height = Math.max(220, items.length * 42 + 40); return `<div class="viz"><svg viewBox="0 0 760 ${height}" role="img" aria-label="${esc(title)}条形图">${items.map((item, index) => { const y = 18 + index * 42, width = item.percent / max * 420; return `<text x="0" y="${y + 18}" class="axis">${esc(String(item.label).slice(0, 24))}</text><rect x="250" y="${y}" width="${width}" height="25" rx="8" fill="${palette[0]}"/><text x="${258 + width}" y="${y + 18}" class="value">${item.percent.toFixed(1)}%</text>`; }).join("")}</svg></div>`;
  };
  const renderFilters = () => { const chips = $("active-filters"); chips.innerHTML = active.length ? active.map((filter, index) => `<button type="button" class="filter-chip" data-index="${index}">${esc(questionById(filter.question_id)?.id)}：${esc(filter.values.join("、"))} ×</button>`).join("") : '<span class="empty">尚未添加筛选条件</span>'; chips.querySelectorAll("button").forEach(button => button.addEventListener("click", () => { active.splice(Number(button.dataset.index), 1); setFilterValues(); renderAll(); })); };
  const modes=[["table","表格"],["pie","饼图"],["donut","圆环"],["column","柱状"],["bar","条形"],["line","折线"]];
  const questionCard=(question,subset)=>{
    const result=distributionFor(question,subset),mode=questionViews[question.id]||"table";
    const typeNames={single_choice:"单选题",multi_choice:"多选题",likert_scale:"量表题",ranking:"排序题",nps:"NPS"};
    const note=result.note+(mode==="line"?" 折线仅展示选项占比序列，不表示时间趋势。":"")+((mode==="pie"||mode==="donut")&&question.type==="multi_choice"?" 饼图/圆环按选择人次归一化；表格仍使用有效受访者分母。":"");
    return '<section class="question-card" id="question-'+esc(question.id)+'"><h3>'+esc(question.id)+'：'+esc(question.question)+' <small>['+esc(typeNames[question.type]||question.type)+']</small></h3><div class="table-wrap"><table class="frequency-table"><thead><tr><th>选项</th><th>小计</th><th>比例</th></tr></thead><tbody>'+result.distribution.map(item=>'<tr><td>'+esc(item.label)+'</td><td>'+item.count+'</td><td><div class="ratio"><span class="ratio-track"><span style="width:'+Math.min(item.percent,100)+'%"></span></span><span>'+item.percent.toFixed(1)+'%</span></div></td></tr>').join("")+'</tbody><tfoot><tr><th>本题有效填写人次</th><th>'+result.base+'</th><td></td></tr></tfoot></table></div><div class="question-modes" data-export-exclude aria-label="'+esc(question.id)+'图表类型">'+modes.map(([value,label])=>'<button type="button" data-question="'+esc(question.id)+'" data-chart="'+value+'" aria-pressed="'+(mode===value)+'">'+label+'</button>').join("")+'</div>'+(mode==="table"?"":chartSvg(result.distribution,mode,question.question))+'<p class="helper">'+esc(note)+'</p></section>';
  };
  const renderChart = () => {
    const subset=filtered();
    $("filter-status").textContent="当前筛选样本："+subset.length+" / "+responses.length;
    $("view-context").textContent=active.length?"筛选条件："+active.map(f=>f.question_id+" = "+f.values.join(" / ")).join("；")+" · n = "+subset.length:"全体可分析样本 · n = "+subset.length;
    $("ordinary-questions").innerHTML=questions.map(q=>questionCard(q,subset)).join("")||'<p class="empty">没有封闭题。</p>';
    $("ordinary-questions").querySelectorAll("button[data-chart]").forEach(button=>button.addEventListener("click",()=>{questionViews[button.dataset.question]=button.dataset.chart;renderChart();}));
  };
  const crossData = (groupId=crossGroup.value,targetId=crossTarget.value) => {
    const group = questionById(groupId), target = questionById(targetId), subset = filtered();
    if (!group || !target || group.id === target.id) return { group, target, rows: [], labels: [], warning: "请选择两个不同的题目进行交叉分析。" };
    const labels = valuesFor(target);
    const rows = valuesFor(group).map(groupLabel => {
      const members = subset.filter(row => hasChoice(row, group, groupLabel));
      const answered = members.filter(row => choiceValues(target, row.answers[target.id]).length);
      return { label: groupLabel, groupN: members.length, base: answered.length, missing: members.length - answered.length, values: labels.map(targetLabel => answered.filter(row => hasChoice(row, target, targetLabel)).length) };
    });
    const warnings = ["每格百分比的分母为该组实际回答目标题的人数；空组保留为 —。"];
    if (target.type === "multi_choice" || target.type === "ranking") warnings.push("目标题按是否选择统计，行内百分比可超过 100%。");
    if (group.type === "multi_choice" || group.type === "ranking") warnings.push("分组非互斥，同一回答可进入多个组，组人数不可相加作为总样本。");
    if (rows.some(row => row.base > 0 && row.base < 10)) warnings.push("部分组有效样本少于 10，仅供探索性观察。");
    warnings.push(`筛选样本 ${subset.length}；分组题空白 ${subset.filter(row => !choiceValues(group, row.answers[group.id]).length).length}。仅描述合成样本，不作显著性或总体推断。`);
    return { group, target, rows, labels, warning: warnings.join(" ") };
  };
  const crossResults=()=> {
    const ids=groupIds.length?groupIds:[crossGroup.value],targets=targetIds.length?targetIds:[crossTarget.value];
    if(ids.length===1)return targets.map(id=>crossData(ids[0],id));
    const groups=ids.map(questionById),subset=filtered();
    const combinations=groups.reduce((sets,q)=>sets.flatMap(set=>valuesFor(q).map(value=>[...set,value])),[[]]);
    return targets.map(id=>{
      const target=questionById(id);
      if(!target||ids.includes(id))return {rows:[],labels:[],warning:"X 和 Y 必须使用不同题目。"};
      const labels=valuesFor(target),rows=combinations.map(combo=>{
        const members=subset.filter(row=>groups.every((q,i)=>hasChoice(row,q,combo[i]))),answered=members.filter(row=>choiceValues(target,row.answers[target.id]).length);
        return {label:combo.join(" / "),groupN:members.length,base:answered.length,missing:members.length-answered.length,values:labels.map(label=>answered.filter(row=>hasChoice(row,target,label)).length)};
      });
      return {group:{id:ids.join(" × ")},target,labels,rows,warning:"按 X 选项组合分组，百分比分母为各组实际回答 Y 的人数。空组保留；多选分组可重叠，多选目标题比例可超过100%。小组仅供探索，不作总体推断。"};
    });
  };
  const renderCross = () => {
    $("cross-table").innerHTML=crossResults().map(result=>'<section class="cross-result"><h3>'+esc(result.group?.id||"X")+' × '+esc(result.target?.id||"Y")+' · '+esc(result.target?.question||"")+'</h3>'+(!result.rows.length?'<p class="empty">'+esc(result.warning)+'</p>':'<div class="table-wrap"><table><thead><tr><th>分组 / 选项</th><th>组人数</th><th>有效分母</th><th>空白</th>'+result.labels.map(label=>'<th>'+esc(label)+'</th>').join("")+'</tr></thead><tbody>'+result.rows.map(row=>'<tr><th>'+esc(row.label)+'</th><td>'+row.groupN+'</td><td>'+row.base+'</td><td>'+row.missing+'</td>'+row.values.map(value=>'<td>'+value+'<br><small>'+(row.base?(value/row.base*100).toFixed(1)+"%":"—")+'</small></td>').join("")+'</tr>').join("")+'</tbody></table></div><p class="helper">'+esc(result.warning)+'</p>')+'</section>').join("");
    const chips=(ids,kind)=>ids.map(id=>'<button type="button" data-kind="'+kind+'" data-id="'+esc(id)+'">'+esc(id)+' ×</button>').join("");
    $("cross-groups").innerHTML=chips(groupIds,"group");$("cross-targets").innerHTML=chips(targetIds,"target");
    for(const id of ["cross-groups","cross-targets"])$(id).querySelectorAll("button").forEach(button=>button.addEventListener("click",()=>{const ids=button.dataset.kind==="group"?groupIds:targetIds;ids.splice(ids.indexOf(button.dataset.id),1);renderCross();}));
  };
  const renderAll = () => { renderFilters(); renderChart(); renderCross(); };
  const showTab = name => {
    analysisTab = tabs.includes(name) ? name : "ordinary";
    $("sample-filters").hidden = !["ordinary", "cross"].includes(analysisTab);
    $("filter-status").hidden = !["ordinary", "cross"].includes(analysisTab);
    $("view-context").hidden = !["ordinary", "cross"].includes(analysisTab);
    for (const tab of tabs) {
      const selected = tab === analysisTab;
      $("tab-" + tab).setAttribute("aria-selected", String(selected));
      $("tab-" + tab).setAttribute("tabindex", selected ? "0" : "-1");
      $("panel-" + tab).hidden = !selected;
    }
  };
  for (const tab of tabs) {
    $("tab-" + tab).addEventListener("click", () => showTab(tab));
    $("tab-" + tab).addEventListener("keydown", event => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const next = event.key === "Home" ? tabs[0] : event.key === "End" ? tabs[tabs.length - 1] : tabs[(tabs.indexOf(analysisTab) + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length];
      showTab(next); $("tab-" + next).focus();
    });
  }
  showTab(analysisTab);
  applyQuestionOptions(filterQuestion, saved.filterQuestion || questions[0]?.id); applyQuestionOptions(chartQuestion, saved.chartQuestion || questions[0]?.id); applyQuestionOptions(crossGroup, saved.crossGroup || questions[0]?.id); applyQuestionOptions(crossTarget, saved.crossTarget || questions[1]?.id || questions[0]?.id); selectOptions(chartType, [{value:"bar",label:"柱状图"},{value:"line",label:"折线图"},{value:"pie",label:"饼图"}], saved.chartType || "bar"); setFilterValues();
  filterQuestion.addEventListener("change", setFilterValues); chartQuestion.addEventListener("change", renderChart); chartType.addEventListener("change", renderChart); crossGroup.addEventListener("change", renderCross); crossTarget.addEventListener("change", renderCross);
  $("add-filter").addEventListener("click", () => { const values = [...filterValues.selectedOptions].map(option => option.value); if (!filterQuestion.value || !values.length) return; const index = active.findIndex(filter => filter.question_id === filterQuestion.value); if (index >= 0) active.splice(index, 1); active.push({ question_id: filterQuestion.value, values }); renderAll(); });
  $("clear-filters").addEventListener("click", () => { active.splice(0); setFilterValues(); renderAll(); });
  const download = (name, blob) => { const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); };
  $("export-cross-csv").addEventListener("click", () => {
    const conditions=active.map(filter=>filter.question_id+" = "+filter.values.join(" / ")).join("；")||"全体可分析样本";
    const lines=[["run_id","筛选条件","分组题","目标题","分组选项","组人数","有效分母","空白","目标题选项","人数","百分比"]];
    crossResults().filter(result=>result.group&&result.target).forEach(result=>result.rows.forEach(row=>result.labels.forEach((label,index)=>lines.push([document.body.dataset.runId,conditions,result.group.id,result.target.id,row.label,row.groupN,row.base,row.missing,label,row.values[index],row.base?(row.values[index]/row.base*100).toFixed(1)+"%":"—"]))));
    const safeCell=value=>{let str=String(value);if(/^[=+@-]/.test(str))str="'"+str;return '"'+str.replace(/"/g,'""')+'"';};
    download("cross_"+document.body.dataset.runId+".csv",new Blob(["\ufeff",lines.map(line=>line.map(safeCell).join(",")).join("\r\n")],{type:"text/csv;charset=utf-8"}));
  });
  $("add-cross-group").addEventListener("click",()=>{if(!groupIds.includes(crossGroup.value)&&groupIds.length<2)groupIds.push(crossGroup.value);renderCross();});
  $("add-cross-target").addEventListener("click",()=>{if(!targetIds.includes(crossTarget.value)&&targetIds.length<10)targetIds.push(crossTarget.value);renderCross();});
  $("swap-cross").addEventListener("click",()=>{if(targetIds.length>2){$("cross-note").textContent="交换后 X 最多两题，请先减少 Y 题目。";return;}const x=groupIds.length?groupIds:[crossGroup.value];groupIds=targetIds.length?targetIds:[crossTarget.value];targetIds=x;renderCross();});
  $("calculate-cross").addEventListener("click",renderCross);
  const conclusionSlides=data.conclusion_deck || [];
  $("conclusion-slides").innerHTML=conclusionSlides.map((slide,i)=>'<section class="conclusion-slide"><div class="slide-copy"><span class="eyebrow">结论 '+(i+1)+' / '+conclusionSlides.length+'</span><h3>'+esc(slide.title)+'</h3><ul>'+slide.lines.map(line=>'<li>'+esc(line)+'</li>').join("")+'</ul></div><div class="slide-evidence"><h4>'+esc(slide.chart?.title||"数据证据")+'</h4>'+chartSvg(slide.chart?.items||[],"bar",slide.chart?.title||"数据证据")+'<p class="helper">'+esc(slide.chart?.note||"暂无可配对的题目统计。")+'</p></div></section>').join("");
  const officeModel=()=>({
    title:document.title,runId:document.body.dataset.runId,conditions:["conclusions","quality"].includes(analysisTab)?"全体可分析样本（结论及质量报告不随筛选变化）":active.map(f=>f.question_id+" = "+f.values.join(" / ")).join("；")||"全体可分析样本",sampleN:["conclusions","quality"].includes(analysisTab)?responses.length:filtered().length,mode:analysisTab,paper:$("export-paper").value,
    conclusionSlides:analysisTab==="conclusions"?conclusionSlides:undefined,
    sections:analysisTab==="conclusions"?[]:analysisTab==="cross"?crossResults().filter(r=>r.group&&r.target).map(r=>({kind:"cross",title:r.group.id+" × "+r.target.id+" · "+r.target.question,note:r.warning,labels:r.labels,rows:r.rows})):questions.map(q=>{const r=distributionFor(q,analysisTab==="quality"?responses:filtered());return {kind:"question",title:q.id+" · "+q.question,note:r.note,items:r.distribution};}),
    narrative:analysisTab==="conclusions"?conclusionSlides.map(slide=>({title:slide.title,lines:slide.lines})):analysisTab==="quality"?[...document.querySelectorAll("#panel-quality .report-section")].filter(node=>!node.querySelector("#full-batch-charts")).map(node=>({title:node.querySelector("h2")?.textContent||"",lines:[...node.querySelectorAll("h3,p,li,tr")].map(p=>p.tagName.toLowerCase()==="tr"?[...p.children].map(cell=>cell.textContent.trim()).join(" | "):p.textContent.trim()).filter(Boolean)})):[]
  });
  $("download-conclusion-ppt").addEventListener("click",()=>{
    try{const model={...officeModel(),mode:"conclusions",sampleN:responses.length,conditions:"全体可分析样本（结论不随筛选变化）",sections:[],conclusionSlides,narrative:[]};download("调研分析结论_"+model.runId+".pptx",window.ReportOffice.build("pptx",model));$("download-status").textContent="三页结论 PPT 已生成，图表采用全批次有效回答百分比。";}
    catch(error){$("download-status").textContent="结论 PPT 生成失败："+error.message;}
  });
  const dialog=$("export-dialog");
  $("open-export").addEventListener("click",()=>dialog.showModal());
  $("close-export").addEventListener("click",()=>dialog.close());
  $("confirm-export").addEventListener("click",()=>{
    try{const format=$("export-format").value,model=officeModel();download("report_"+model.runId+"."+format,window.ReportOffice.build(format,model));$("download-status").textContent="已生成 "+format.toUpperCase()+" 报告（当前分析页与当前筛选条件）；研究结论保留全批次口径。";dialog.close();}
    catch(error){$("export-error").textContent="导出失败："+error.message;}
  });
  window.ReportAnalysis={distributionFor,crossData,crossResults,officeModel,chartSvg};
  renderAll();
})();
