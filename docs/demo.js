'use strict';
/* Browser-only, no-sign-in recruiter demonstration. No network requests. */
const Core=window.GlucoCore;
const STORAGE_KEY='glucodiary-public-synthetic-v2';
const allTasks=Core.makeTasks();
const dates=Array.from({length:Core.DAYS},(_,i)=>Core.isoAdd(Core.START,i));
const $=id=>document.getElementById(id);
let state=load();
let toastTimeout;
function fresh(){return {readings:Core.starterReadings(),foodEnabled:false,supplementEnabled:false,supplementTaken:{'2026-10-06':true},cuisine:'Indian',allergies:[],excluded:''}}
function load(){
  try{
    const raw=localStorage.getItem(STORAGE_KEY);if(!raw)return fresh();
    const data=JSON.parse(raw);
    if(!Array.isArray(data.readings))return fresh();
    data.readings=data.readings.filter(r=>dates.includes(r.date)&&Core.OCCASIONS.includes(r.occasion)&&Number.isFinite(r.value)&&r.value>0&&r.value<=40&&/^([01]\d|2[0-3]):[0-5]\d$/.test(r.time)&&/^(seed-[bx]-\d{1,2}|added-2026-10-\d\d-before_(breakfast|lunch|dinner|sleep))$/.test(r.id));
    data.foodEnabled=!!data.foodEnabled;data.supplementEnabled=!!data.supplementEnabled;
    data.supplementTaken=data.supplementTaken&&typeof data.supplementTaken==='object'?data.supplementTaken:{};
    data.allergies=Array.isArray(data.allergies)?data.allergies.filter(x=>['milk','peanut','tree nut','sesame','wheat','soy','egg','fish'].includes(x)):[];
    data.cuisine=['Indian','Mediterranean','Any'].includes(data.cuisine)?data.cuisine:'Indian';
    data.excluded=typeof data.excluded==='string'?data.excluded.slice(0,160):'';
    return data;
  }catch(_e){return fresh()}
}
function save(){try{localStorage.setItem(STORAGE_KEY,JSON.stringify(state))}catch(_e){} }
function displayDate(date){return new Date(date+'T12:00:00Z').toLocaleDateString('en-GB',{day:'numeric',month:'short',timeZone:'UTC'})}
function fmt(num,dp=1){return num===null?'—':num.toFixed(dp)}
function notify(msg,bad=false){const t=$('toast');t.textContent=msg;t.classList.toggle('bad',bad);t.hidden=false;clearTimeout(toastTimeout);toastTimeout=setTimeout(()=>{t.hidden=true},5500)}
function activate(tab){
  document.querySelectorAll('.tab').forEach(b=>{const is=b.dataset.tab===tab;b.classList.toggle('active',is);b.setAttribute('aria-selected',String(is))});
  document.querySelectorAll('.tab-panel').forEach(p=>p.hidden=p.id!==`panel-${tab}`);
  if(tab==='dashboard')renderDashboard();if(tab==='record')renderRecord();if(tab==='schedule')renderSchedule();if(tab==='medications')renderSupplements();if(tab==='food')renderFood();
}
function renderDashboard(){
  const stats=Core.summaries(state.readings),p=Core.taskProgress(state.readings,allTasks),fast=Core.summaries(state.readings,'before_breakfast');
  $('metrics').innerHTML=`<div class="metric"><span>Recorded measurements</span><strong>${stats.count}</strong><small>Synthetic readings</small></div><div class="metric"><span>Mean glucose</span><strong>${fmt(stats.avg,2)}</strong><small>mmol/L · descriptive</small></div><div class="metric"><span>Before-breakfast mean</span><strong>${fmt(fast.avg,2)}</strong><small>mmol/L · ${fast.count} samples</small></div><div class="metric"><span>Planned checks complete</span><strong>${p.completed}/${p.total}</strong><small>${p.missing} not recorded</small></div>`;
  const percent=Math.round(100*p.completed/p.total);$('completionPercent').textContent=percent+'%';$('completionRing').style.setProperty('--pct',percent+'%');
  $('completionCounts').textContent=`${p.completed} recorded · ${p.missing} not recorded`;
  $('recentReadings').innerHTML=stats.rows.slice(-6).reverse().map(r=>`<tr><td>${displayDate(r.date)}</td><td>${Core.LABELS[r.occasion]}</td><td><b>${r.value.toFixed(1)} mmol/L</b></td></tr>`).join('')||'<tr><td colspan="3">No example readings</td></tr>';
  drawChart();
}
function drawChart(){
  const data=Core.summaries(state.readings,$('chartContext').value),rows=data.rows;
  const svg=$('glucoseChart'),NS='http://www.w3.org/2000/svg';svg.replaceChildren();
  const add=(tag,attr={},txt)=>{let el=document.createElementNS(NS,tag);Object.entries(attr).forEach(([k,v])=>el.setAttribute(k,String(v)));if(txt!==undefined)el.textContent=txt;svg.append(el);return el};
  if(!rows.length){add('text',{x:250,y:120,fill:'#7e9490','font-size':17},'No readings in this category');$('chartSummary').textContent='Try adding an example reading.';return}
  const lo=Math.min(...rows.map(r=>r.value)),hi=Math.max(...rows.map(r=>r.value)),min=Math.max(0,lo-1.1),max=hi+1.1;
  const xp=i=>55+(rows.length===1?.5:i/(rows.length-1))*585,yp=v=>220-(v-min)/(max-min)*185;
  for(let n=0;n<5;n++){const val=max-n*(max-min)/4,y=yp(val);add('line',{x1:55,y1:y,x2:640,y2:y,stroke:'#e0ebe8','stroke-width':1});add('text',{x:45,y:y+4,'text-anchor':'end',fill:'#829b97','font-size':11},val.toFixed(1))}
  if(rows.length>1)add('polyline',{points:rows.map((r,i)=>`${xp(i)},${yp(r.value)}`).join(' '),stroke:'#0c8a7c',fill:'none','stroke-width':3.5,'stroke-linejoin':'round','stroke-linecap':'round'});
  rows.forEach((r,i)=>{const e=add('circle',{cx:xp(i),cy:yp(r.value),r:5,fill:'#fff',stroke:'#0b8b7f','stroke-width':3});const title=document.createElementNS(NS,'title');title.textContent=`${r.date} ${Core.LABELS[r.occasion]}: ${r.value.toFixed(1)} mmol/L`;e.append(title);
    if(rows.length<=8||i===0||i===rows.length-1||i%Math.ceil(rows.length/5)===0)add('text',{x:xp(i),y:251,'text-anchor':'middle',fill:'#809593','font-size':10},displayDate(r.date))});
  $('chartSummary').textContent=`${rows.length} ${rows.length===1?'reading':'readings'} · mean ${fmt(data.avg,2)} mmol/L · first ${fmt(data.first)}, latest ${fmt(data.last)}. These are observations, not a clinical judgement.`;
}
function renderRecord(){
  const sorted=Core.summaries(state.readings).rows.slice().reverse();
  $('entryRows').innerHTML=sorted.map(r=>`<tr><td>${displayDate(r.date)} ${r.time}</td><td>${Core.LABELS[r.occasion]}</td><td><b>${r.value.toFixed(1)}</b> mmol/L</td><td><button type="button" class="text-button" data-remove="${r.id}" aria-label="Remove ${displayDate(r.date)} ${Core.LABELS[r.occasion]} reading">Delete</button></td></tr>`).join('')||'<tr><td colspan="4">No readings yet</td></tr>';
}
function renderSchedule(){
  const p=Core.taskProgress(state.readings,allTasks);$('scheduledCount').textContent=p.total;$('scheduledCompleted').textContent=p.completed;$('scheduledMissing').textContent=p.missing;
  const has=new Set(state.readings.map(r=>r.date+'|'+r.occasion));
  $('scheduleRows').innerHTML=dates.map(date=>{
    const slots=allTasks.filter(t=>t.date===date);
    return `<tr><td><b>${displayDate(date)}</b></td>${slots.map(t=>`<td>${Core.LABELS[t.occasion]} <span class="status-mini ${has.has(t.id)?'yes':'no'}">${has.has(t.id)?'● Recorded':'○ Missing'}</span></td>`).join('')}</tr>`
  }).join('');
}
function renderSupplements(){
  $('supplementEnabled').checked=state.supplementEnabled;$('supplementBody').hidden=!state.supplementEnabled;
  $('supplementList').innerHTML=Core.SUPPLEMENTS.map((d,i)=>`<div class="supplement-row"><span>Week ${i+1} · ${displayDate(d)} · with lunch</span><label><input type="checkbox" data-supp="${d}" ${state.supplementTaken[d]?'checked':''}><span>${state.supplementTaken[d]?'Recorded as taken':'Mark as taken'}</span></label></div>`).join('');
}
const ALLERGIES=['milk','peanut','tree nut','sesame','wheat','soy','egg','fish'];
function renderFood(){
  $('foodEnabled').checked=state.foodEnabled;$('foodBody').hidden=!state.foodEnabled;$('cuisine').value=state.cuisine;$('excludedIngredients').value=state.excluded;
  $('allergyChoices').innerHTML=ALLERGIES.map(a=>`<label><input type="checkbox" data-allergy="${a}" ${state.allergies.includes(a)?'checked':''}><span>${a[0].toUpperCase()+a.slice(1)}</span></label>`).join('');
  const list=Core.matchRecipes(state.cuisine,state.allergies,state.excluded);
  $('recipeResults').innerHTML=list.map(r=>`<div class="recipe-card"><h4>${r.name}</h4><p>${r.description}</p><small>${r.cuisine} · ${r.ingredients.join(', ')}</small></div>`).join('')||'<p class="muted-sm">No example meals match your selections. Try adjusting filters.</p>';
}
function runTrace(){
  const d=Core.evidence(state.readings);
  const info=d.fastingChange===null?'Not enough fasting readings for a comparison':`${Math.abs(d.fastingChange).toFixed(1)} mmol/L ${d.fastingChange>0?'higher':d.fastingChange<0?'lower':'unchanged'} from first to latest before-breakfast example`;
  const rows=[
    {title:'01 · Evidence agent (deterministic)',message:'Loads recorded synthetic values and their meal/bedtime contexts. Calculates statistics in code, not by asking a language model to estimate.',detail:`Readings: ${d.readings} | Scheduled: ${d.schedule.total} | Matched: ${d.schedule.completed} | Missing: ${d.schedule.missing}`},
    {title:'02 · Pattern agent (rule-based public simulation)',message:'Looks only at comparable before-breakfast measurements. It does not infer why values changed.',detail:`Fasting readings: ${d.fastingCount} | Mean: ${fmt(d.fastingMean,2)} mmol/L | Comparison: ${info}`},
    {title:'03 · Explanation agent (template-based public simulation)',message:`There are ${d.readings} recorded sample readings. ${d.schedule.missing} scheduled slots have no recorded sample. The fasting comparison is descriptive and may reflect many unrecorded factors.`,detail:'Every figure comes from the evidence stage; there are no invented medical causes.'},
    {title:'04 · Safety-review stage (deterministic)',message:'Checks that the output contains no diagnosis, medication adjustments, glucose target recommendations or assumed reasons for a change.',detail:'PUBLIC DEMO: no live LLM call; not a medically validated safety check.'}
  ];
  const container=$('agentTrace');container.replaceChildren();
  rows.forEach(row=>{const box=document.createElement('article');box.className='trace-step';const title=document.createElement('h4');title.textContent=row.title;const p=document.createElement('p');p.textContent=row.message;const detail=document.createElement('code');detail.textContent=row.detail;box.append(title,p,detail);container.append(box)});
}
function init(){
  const host=window.location.hostname.toLowerCase();
  if(host.endsWith('.github.io')){const owner=host.split('.')[0];const repo=window.location.pathname.split('/').filter(Boolean)[0]||owner+'.github.io';const link=$('repoLink');link.href=`https://github.com/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`;link.hidden=false;}
  document.querySelectorAll('.tab').forEach(button=>button.addEventListener('click',()=>activate(button.dataset.tab)));
  document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>activate(b.dataset.go)));
  $('chartContext').addEventListener('change',drawChart);
  $('readingDate').value=dates.at(-1);
  $('readingForm').addEventListener('submit',e=>{
    e.preventDefault();try{state.readings=Core.addReading(state.readings,{date:$('readingDate').value,time:$('readingTime').value,occasion:$('readingOccasion').value,value:$('readingValue').value});save();renderRecord();notify('Example reading saved. The analytics and calendar will recalculate.');$('readingValue').value='';}
    catch(err){notify(err.message,true)}
  });
  $('entryRows').addEventListener('click',e=>{const btn=e.target.closest('[data-remove]');if(!btn)return;state.readings=state.readings.filter(r=>r.id!==btn.dataset.remove);save();renderRecord();notify('Example reading removed.');});
  $('sampleAdd').addEventListener('click',()=>{const open=allTasks.find(t=>!state.readings.some(r=>r.date===t.date&&r.occasion===t.occasion));if(!open){activate('record');notify('Every planned slot has a sample; delete an entry to try adding it again.');return}
    $('readingDate').value=open.date;$('readingOccasion').value=open.occasion;$('readingTime').value=Core.EXAMPLE_TIMES[open.occasion];$('readingValue').value='7.4';activate('record');notify('The form is prefilled with a fictional 7.4 mmol/L example. Press Save to update the analysis.');});
  $('resetDemo').addEventListener('click',()=>{state=fresh();save();$('chartContext').value='before_breakfast';$('reminderPreview').hidden=true;renderAll();activate('dashboard');notify('Fictional dataset reset to its original values.')});
  $('supplementEnabled').addEventListener('change',e=>{state.supplementEnabled=e.target.checked;save();renderSupplements()});
  $('supplementList').addEventListener('change',e=>{const input=e.target.closest('[data-supp]');if(!input)return;state.supplementTaken[input.dataset.supp]=input.checked;save();renderSupplements()});
  $('previewReminder').addEventListener('click',()=>{$('reminderPreview').hidden=false;$('reminderPreview').textContent='Preview only — Example notification: “Your clinician-confirmed supplement reminder is due with lunch today. Record whether you took it.” No email or iPhone push was sent.'});
  $('foodEnabled').addEventListener('change',e=>{state.foodEnabled=e.target.checked;save();renderFood()});
  $('cuisine').addEventListener('change',e=>{state.cuisine=e.target.value;save();renderFood()});
  $('excludedIngredients').addEventListener('input',e=>{state.excluded=e.target.value.slice(0,160);save();const list=Core.matchRecipes(state.cuisine,state.allergies,state.excluded);$('recipeResults').innerHTML=list.map(r=>`<div class="recipe-card"><h4>${r.name}</h4><p>${r.description}</p><small>${r.cuisine} · ${r.ingredients.join(', ')}</small></div>`).join('')||'<p class="muted-sm">No example meals match your selections.</p>'});
  $('allergyChoices').addEventListener('change',e=>{const input=e.target.closest('[data-allergy]');if(!input)return;state.allergies=input.checked?[...new Set([...state.allergies,input.dataset.allergy])]:state.allergies.filter(a=>a!==input.dataset.allergy);save();renderFood()});
  $('runTrace').addEventListener('click',runTrace);
  renderAll();activate('dashboard');
}
function renderAll(){renderDashboard();renderRecord();renderSchedule();renderSupplements();renderFood();$('agentTrace').innerHTML='<p class="muted-sm">Run the workflow to inspect each stage and the source data behind the summary.</p>'}
init();
