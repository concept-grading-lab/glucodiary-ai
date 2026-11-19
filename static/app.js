'use strict';
let csrf='',dashboard=null,account=null,services={},currentPage='overview';
const el=id=>document.getElementById(id);
const $=(selector,root=document)=>root.querySelector(selector);
const all=(selector,root=document)=>Array.from(root.querySelectorAll(selector));
const html=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const label={before_breakfast:'Before breakfast',before_lunch:'Before lunch',before_dinner:'Before dinner',before_sleep:'Before sleep',other:'Other'};
const fmt=(value)=>{try{return new Date(value).toLocaleString('en-GB',{dateStyle:'medium',timeStyle:'short'})}catch{return value}};
const dayfmt=(value)=>new Date(value+'T12:00:00').toLocaleDateString('en-GB',{day:'numeric',month:'short',weekday:'short'});
function notice(message,bad=false){const f=el('flash');f.textContent=message;f.classList.toggle('bad',bad);f.hidden=false;window.scrollTo({top:0,behavior:'smooth'});}
async function api(path,method='GET',payload){
  const opt={method,credentials:'same-origin',headers:{}};
  if(payload!==undefined){opt.headers['Content-Type']='application/json';opt.body=JSON.stringify(payload)}
  if(!['GET','HEAD'].includes(method))opt.headers['X-CSRF-Token']=csrf;
  let res;
  try{res=await fetch(path,opt)}catch(e){throw Error('Connection error. Please check the server and your internet connection.')}
  const data=await res.json().catch(()=>({}));
  if(!res.ok)throw Error(typeof data.detail==='string'?data.detail:`Request failed (${res.status})`);
  return data;
}
async function init(){
  if('serviceWorker' in navigator){navigator.serviceWorker.register('/sw.js').catch(()=>{});}
  // A login session cookie may exist. CSRF is deliberately not stored in browser storage.
  try{const r=await api('/api/me');
    // CSRF must come from the session login response. A reload fetches a new CSRF token
    // via a read-only authenticated endpoint; it cannot be used by another origin.
    const c=await api('/api/auth/csrf');csrf=c.csrf;
    await authenticated(r);
  }catch{el('loginView').hidden=false;el('appView').hidden=true;try{el('bootstrapCard').hidden=!(await api('/api/setup/status')).needs_setup}catch{}}
}
async function authenticated(data){
  account=data.user;services=data.services||{};
  el('loginView').hidden=true;el('appView').hidden=false;el('signout').hidden=false;
  el('welcomeEmail').textContent=`SIGNED IN · ${account.email}`;
  await reload();fillSettings();showPage(currentPage);
}
async function reload(){dashboard=await api('/api/dashboard');account=dashboard.profile;renderOverview();renderReadings();renderSchedule();renderMedication();fillSettings();}
function showPage(page){currentPage=page;all('.page').forEach(x=>x.hidden=x.dataset.page!==page);all('.nav').forEach(x=>x.classList.toggle('active',x.dataset.tab===page));el('sectionTitle').textContent=({overview:'Overview',readings:'Glucose diary',schedule:'Test calendar',medication:'Supplement tracker',insights:'AI insights',food:'Meal ideas',settings:'Reminders & settings'})[page]||page;el('flash').hidden=true;if(page==='food')loadFood();}
function stat(label,value,foot){return `<div class="stat"><small>${html(label)}</small><strong>${html(value)}</strong><span>${html(foot)}</span></div>`}
function renderOverview(){
  if(!dashboard)return;
  const s=dashboard.summary,by=s.summary_by_occasion;
  const avg=by.before_breakfast?by.before_breakfast.average.toFixed(2):'—';
  const completed=dashboard.tasks.filter(t=>t.complete).length;
  el('stats').innerHTML=stat('Recorded readings',s.total_readings,'Saved measurements')+stat('Before-breakfast average',avg,'mmol/L · recorded only')+stat('Completed slots',`${completed}/${s.scheduled}`,'Entire scheduled period')+stat('Due but unrecorded',s.missing_due,'Not counted as normal');
  const nd=new Date();const todayLocal=`${nd.getFullYear()}-${String(nd.getMonth()+1).padStart(2,'0')}-${String(nd.getDate()).padStart(2,'0')}`;
  let upcoming=dashboard.tasks.filter(x=>!x.complete&&x.day>=todayLocal).slice(0,5);
  if(upcoming.length===0)upcoming=dashboard.tasks.filter(x=>!x.complete).slice(-5);
  el('nextTasks').innerHTML=upcoming.length?upcoming.map(x=>`<div class="item"><div><b>${html(dayfmt(x.day))}</b><br><span class="muted">${html(label[x.occasion])}</span></div><span class="tag">Scheduled</span></div>`).join(''):'<p class="muted">No upcoming slots in this plan.</p>';
  drawChart(dashboard.readings);
}
function drawChart(readings){
  const svg=el('overviewChart');while(svg.firstChild)svg.removeChild(svg.firstChild);
  const width=660,height=240,pad={left:44,right:19,top:16,bottom:36};
  const data=[...readings].sort((a,b)=>a.measured_at.localeCompare(b.measured_at)).slice(-30);
  const NS='http://www.w3.org/2000/svg';const add=(tag,attrs={},txt)=>{const n=document.createElementNS(NS,tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,String(v)));if(txt!==undefined)n.textContent=txt;svg.appendChild(n);return n};
  if(!data.length){add('text',{x:width/2,y:120,fill:'#728b99','font-size':14,'text-anchor':'middle'},'Your glucose chart will appear after your first reading.');return}
  let lo=Math.max(0,Math.min(...data.map(x=>x.value_mmol))-2),hi=Math.max(...data.map(x=>x.value_mmol))+2;
  if(hi-lo<1)hi=lo+1;
  const xs=i=>pad.left+(data.length===1?.5:i/(data.length-1))*(width-pad.left-pad.right);
  const ys=v=>height-pad.bottom-(v-lo)/(hi-lo)*(height-pad.top-pad.bottom);
  for(let i=0;i<5;i++){let y=pad.top+i*(height-pad.top-pad.bottom)/4;add('line',{x1:pad.left,y1:y,x2:width-pad.right,y2:y,stroke:'#e4ecef'});add('text',{x:pad.left-8,y:y+4,fill:'#8097a3','font-size':11,'text-anchor':'end'},(hi-(hi-lo)*i/4).toFixed(1))}
  if(data.length>1)add('polyline',{points:data.map((d,i)=>`${xs(i)},${ys(d.value_mmol)}`).join(' '),fill:'none',stroke:'#218b89','stroke-width':2.8,'stroke-linejoin':'round'});
  data.forEach((d,i)=>add('circle',{cx:xs(i),cy:ys(d.value_mmol),r:4.3,fill:'#fff',stroke:'#218b89','stroke-width':2.8}));
  const indices=[0,Math.floor((data.length-1)/2),data.length-1];[...new Set(indices)].forEach(i=>add('text',{x:xs(i),y:height-10,fill:'#718896','font-size':11,'text-anchor':'middle'},new Date(data[i].measured_at).toLocaleDateString('en-GB',{day:'numeric',month:'short'})));
}
function renderReadings(){
 const by=dashboard.summary.summary_by_occasion;
 el('occasionAverages').innerHTML=Object.keys(by).length?Object.entries(by).map(([key,val])=>`<div class="item"><div>${html(label[key]||key)}<br><small class="muted">${val.count} readings · range ${val.minimum}–${val.maximum}</small></div><strong>${val.average.toFixed(2)}</strong></div>`).join(''):'<p class="muted">No readings yet. Add one using the form.</p>';
 el('readingRows').innerHTML=dashboard.readings.map(r=>`<tr><td>${html(fmt(r.measured_at))}</td><td>${html(label[r.occasion])}</td><td><b>${html(r.value_mmol)}</b></td><td>${html(r.note||'—')}</td><td><button class="del-reading" data-id="${r.id}" aria-label="Delete reading">Delete</button></td></tr>`).join('')||'<tr><td colspan="5">No measurements yet.</td></tr>';
 all('.del-reading').forEach(x=>x.addEventListener('click',async()=>{if(!confirm('Delete this entry?'))return;try{await api('/api/readings/'+x.dataset.id,'DELETE');await reload();notice('Reading removed.')}catch(e){notice(e.message,true)}}));
}
function renderSchedule(){el('taskRows').innerHTML=dashboard.tasks.map(t=>`<tr><td>${html(dayfmt(t.day))}</td><td>${html(label[t.occasion])}</td><td><span class="tag ${t.complete?'done':'missing'}">${t.complete?'Recorded':'Not recorded'}</span></td><td>${html(t.reminder_utc?new Date(t.reminder_utc).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'}):'Not activated')}</td></tr>`).join('')||'<tr><td colspan="4">No schedule loaded.</td></tr>';}
function renderMedication(){
 const mlist=dashboard.medications;
 el('medNote').textContent=mlist.length?`Your saved regimen: ${mlist[0].units} × ${mlist[0].strength_iu.toLocaleString()} IU of ${mlist[0].medication_name} on the listed dates, according to the original doctor's plan. Confirm any future over-the-counter course with your clinician or pharmacist; no automatic maintenance dose is generated.`:'No medication/supplement regimen has been recorded for this account. Do not follow another person’s prescription.';
 el('medRows').innerHTML=dashboard.medications.map(m=>`<div class="med-row"><span><b>${html(dayfmt(m.day))}</b> · ${html(m.units)} × ${html(m.strength_iu.toLocaleString())} IU · with lunch</span><select class="dose-select" data-id="${m.id}" aria-label="Dose status"><option value="scheduled" ${m.status==='scheduled'?'selected':''}>Scheduled</option><option value="taken" ${m.status==='taken'?'selected':''}>Taken</option><option value="skipped" ${m.status==='skipped'?'selected':''}>Not taken</option></select></div>`).join('')||'<p>No medication schedule loaded.</p>';all('.dose-select').forEach(x=>x.addEventListener('change',async()=>{try{await api('/api/medications/'+x.dataset.id,'PUT',{status:x.value});await reload();notice('Dose status saved.')}catch(e){notice(e.message,true)}}))}
function fillSettings(){if(!account)return;const f=el('reminderForm');f.elements.breakfast_time.value=account.times.before_breakfast;f.elements.lunch_time.value=account.times.before_lunch;f.elements.dinner_time.value=account.times.before_dinner;f.elements.sleep_time.value=account.times.before_sleep;f.elements.email_enabled.checked=account.email_enabled;f.elements.push_enabled.checked=account.push_enabled;f.elements.alerts_confirmed.checked=account.alerts_confirmed;el('aiConsent').checked=account.ai_consent;el('aiStatus').textContent=services.ai_configured?'AI provider configured':'AI key missing';el('aiDetail').textContent=services.ai_configured?'After you consent, three LLM agents will run with a deterministic evidence step. This may incur API charges.':'AI provider key not configured; your charts and numerical summaries still work.';el('servicesSummary').innerHTML=`Email transport: <b>${services.email_configured?'Configured':'Not configured'}</b><br>Push keys: <b>${services.push_configured?'Configured':'Not configured'}</b><br>AI provider: <b>${services.ai_configured?'Configured':'Not configured'}</b>`;el('runAgents').disabled=!services.ai_configured;}
const ALLERGENS=['milk','eggs','peanuts','tree nuts','soya','wheat/gluten','sesame','fish','crustaceans','molluscs','celery','mustard','lupin','sulphites'];
function fillFood(){el('foodEnabled').checked=account.food_enabled;el('cuisine').value=account.cuisine||'Indian';el('avoid').value=(account.avoid||[]).join(', ');el('allergyChecks').innerHTML=ALLERGENS.map(a=>`<label><input type="checkbox" value="${html(a)}" ${account.allergens.includes(a)?'checked':''}> ${html(a)}</label>`).join('')}
async function loadFood(){fillFood();const data=await api('/api/food');el('recipes').innerHTML=data.recipes.length?data.recipes.map(r=>`<div class="recipe"><b>${html(r.name)}</b><p>${html(r.ingredients.join(', '))}</p></div>`).join(''):`<p class="muted">${data.enabled?'No matching illustrative recipes. Recheck exclusions.':'Meal ideas are off. Enable them if you would like suggestions.'}</p>`;}
async function enablePush(){try{
 if(!('serviceWorker' in navigator)||!('PushManager' in window))throw Error('Web Push unavailable. On iPhone, install this HTTPS site to Home Screen first.');
 const r=await api('/api/push/vapid');if(!r.configured)throw Error('Server Web Push keys are not configured.');
 const permission=await Notification.requestPermission();if(permission!=='granted')throw Error('Notification permission was not granted.');
 const reg=await navigator.serviceWorker.ready;
 const base64=r.public_key.replace(/-/g,'+').replace(/_/g,'/');const raw=atob(base64+'='.repeat((4-base64.length%4)%4));const key=Uint8Array.from(raw,c=>c.charCodeAt(0));
 let sub=await reg.pushManager.getSubscription();if(!sub)sub=await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:key});
 await api('/api/push/subscribe','POST',sub.toJSON());notice('Push subscription saved. Enable push reminders in your settings and send a test.');
 }catch(e){notice(e.message,true)}}
function localDateInput(){const d=new Date();d.setMinutes(d.getMinutes()-d.getTimezoneOffset());return d.toISOString().slice(0,16)}
function bind(){
 el('loginForm').addEventListener('submit',async e=>{e.preventDefault();const f=new FormData(e.target);try{const r=await api('/api/auth/login','POST',{email:f.get('email'),password:f.get('password')});csrf=r.csrf;const m=await api('/api/me');await authenticated(m)}catch(err){el('loginError').textContent=err.message}});
 el('bootstrapForm').addEventListener('submit',async e=>{e.preventDefault();const f=new FormData(e.target);try{const r=await api('/api/setup','POST',{setup_token:f.get('setup_token'),email:f.get('email'),password:f.get('password')});csrf=r.csrf;await authenticated(await api('/api/me'));notice('Private account created. Remove the bootstrap token from server settings after setup.')}catch(err){el('loginError').textContent=err.message}});
 el('signout').addEventListener('click',async()=>{try{await api('/api/auth/logout','POST');}finally{csrf='';dashboard=null;el('appView').hidden=true;el('loginView').hidden=false;el('signout').hidden=true;el('loginForm').reset()}});
 all('.nav').forEach(btn=>btn.addEventListener('click',()=>showPage(btn.dataset.tab)));
 el('readingForm').elements.measured_at.value=localDateInput();
 el('readingForm').addEventListener('submit',async e=>{e.preventDefault();const f=new FormData(e.target);try{const when=new Date(f.get('measured_at'));if(Number.isNaN(when.getTime()))throw Error('Enter a valid measurement date/time.');await api('/api/readings','POST',{value:Number(f.get('value')),unit:'mmol/L',occasion:f.get('occasion'),measured_at:when.toISOString(),note:f.get('note')});e.target.elements.value.value='';e.target.elements.note.value='';await reload();notice('Reading saved to your account.')}catch(err){notice(err.message,true)}});
 el('loadPlan').addEventListener('click',async()=>{if(!confirm('Load the example 2026 monitoring calendar? It is specific to a personal doctor-provided diary and must not be treated as a universal monitoring recommendation.'))return;try{await api('/api/plan/load-example','POST');await reload();notice('Your example monitoring plan is loaded.')}catch(e){notice(e.message,true)}});
 el('reminderForm').addEventListener('submit',async e=>{e.preventDefault();const f=new FormData(e.target);try{const r=await api('/api/reminder-settings','PUT',{breakfast_time:f.get('breakfast_time'),lunch_time:f.get('lunch_time'),dinner_time:f.get('dinner_time'),sleep_time:f.get('sleep_time'),email_enabled:f.get('email_enabled')!==null,push_enabled:f.get('push_enabled')!==null,alerts_confirmed:f.get('alerts_confirmed')!==null});await reload();notice(r.note)}catch(err){notice(err.message,true)}});
 el('enablePush').addEventListener('click',enablePush);
 el('testNotify').addEventListener('click',async()=>{try{let r=await api('/api/reminders/test','POST');notice('Email: '+r.email+' | Push: '+r.push)}catch(e){notice(e.message,true)}});
 el('aiConsent').addEventListener('change',async e=>{try{await api('/api/consent/ai','PUT',{enabled:e.target.checked});account.ai_consent=e.target.checked;notice('Your AI consent preference was saved.')}catch(err){notice(err.message,true)}});
 el('runAgents').addEventListener('click',async()=>{el('runAgents').disabled=true;el('runAgents').textContent='Running agents…';try{const r=await api('/api/agents/run','POST');el('insightOutput').hidden=false;el('insightText').textContent=JSON.stringify(r,null,2);const trace=await api('/api/agents/runs/'+r.run_id);el('traceOutput').hidden=false;el('traceText').textContent=JSON.stringify(trace.steps,null,2);notice('Agent execution finished: '+r.status)}catch(err){notice(err.message,true)}finally{el('runAgents').disabled=!services.ai_configured;el('runAgents').textContent='Run AI agents'}});
 el('foodForm').addEventListener('submit',async e=>{e.preventDefault();try{let allergens=all('#allergyChecks input:checked').map(x=>x.value),avoid=el('avoid').value.split(',').map(x=>x.trim()).filter(Boolean);await api('/api/food','PUT',{enabled:el('foodEnabled').checked,allergies_confirmed:el('foodAllergyConfirmed').checked,cuisine:el('cuisine').value,allergens,avoid});await reload();await loadFood();notice('Optional food preferences saved.')}catch(err){notice(err.message,true)}});
 el('passwordForm').addEventListener('submit',async e=>{e.preventDefault();const f=new FormData(e.target);try{const r=await api('/api/auth/change-password','POST',{current_password:f.get('current_password'),new_password:f.get('new_password')});notice(r.message);setTimeout(()=>location.reload(),1500)}catch(err){notice(err.message,true)}});
}
// Native fetch needs an authenticated, read-only CSRF retrieval endpoint after a page reload.
bind();init();
