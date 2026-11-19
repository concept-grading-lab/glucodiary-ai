'use strict';
const assert=require('node:assert/strict');
const test=require('node:test');
const fs=require('node:fs');
const path=require('node:path');
const c=require('../docs/demo-core.js');
const index=fs.readFileSync(path.join(__dirname,'../docs/index.html'),'utf8');
const app=fs.readFileSync(path.join(__dirname,'../docs/demo.js'),'utf8');
test('public portfolio demo has an independent static home page and no auth form',()=>{
  assert.match(index,/id="app"/);assert.match(index,/No sign-in required/);assert.doesNotMatch(index,/<input[^>]*type="password"/);
});
test('public demo static assets use GitHub Pages relative paths',()=>{
  assert.match(index,/href="\.\/demo.css"/);assert.match(index,/src="\.\/demo-core.js"/);assert.match(index,/src="\.\/demo.js"/);
});
test('public demo does not call backend or external AI service',()=>{
  assert.doesNotMatch(app,/fetch\(|XMLHttpRequest|OPENAI_API_KEY|api\.openai\.com/);
});
test('synthetic clinician plan contains 28 uniquely dated testing tasks',()=>{
  const tasks=c.makeTasks(); assert.equal(tasks.length,28);assert.equal(new Set(tasks.map(t=>t.id)).size,28);
  assert.equal(tasks.filter(t=>t.occasion==='before_breakfast').length,14);
  assert.deepEqual(tasks.slice(0,6).map(t=>t.occasion),['before_breakfast','before_lunch','before_breakfast','before_dinner','before_breakfast','before_sleep']);
});
test('synthetic dataset never embeds real private patient data',()=>{
  assert.equal(c.START,'2026-10-05');assert.equal(c.starterReadings().every(r=>r.origin==='synthetic'),true);
  assert.doesNotMatch(index+c.starterReadings().map(r=>JSON.stringify(r)).join('')+app,/@gmail\.com|STRIVIT-|2026-11-/gi);
});
test('numeric analytics and progress agree with ground truth',()=>{
  const rs=c.starterReadings(),s=c.summaries(rs),p=c.taskProgress(rs);
  assert.equal(p.total,28);assert.equal(p.completed,rs.length);assert.equal(p.missing,28-rs.length);
  assert.ok(s.avg>6&&s.avg<9);assert.ok(s.max>s.min);
});
test('new reading changes averages and scheduled progress',()=>{
  const rs=c.starterReadings(),before=c.taskProgress(rs).completed;
  const newRows=c.addReading(rs,{date:'2026-10-10',occasion:'before_breakfast',time:'08:00',value:7.4});
  assert.equal(newRows.length,rs.length+1);assert.equal(c.taskProgress(newRows).completed,before+1);
  assert.equal(newRows.at(-1).value,7.4);
});
test('duplicate reading is rejected and does not alter state',()=>{
  const rs=c.starterReadings(),t=rs[0];assert.throws(()=>c.addReading(rs,{date:t.date,occasion:t.occasion,time:'08:00',value:7}),/already a reading/);
  assert.equal(c.starterReadings().length,rs.length);
});
test('invalid dates, contexts, values, and times are rejected',()=>{
  const rs=[];const base={date:'2026-10-05',occasion:'before_breakfast',time:'07:15',value:7.1};
  for(const problem of [{date:'no-date'},{occasion:'before_anything'},{value:0},{value:'abc'},{value:45},{time:'25:00'}])
    assert.throws(()=>c.addReading(rs,{...base,...problem}));
});
test('analysis correctly uses separate before-meal categories',()=>{
  const fast=c.summaries(c.starterReadings(),'before_breakfast');const other=c.summaries(c.starterReadings(),'before_dinner');
  assert.ok(fast.count>0&&other.count>0);assert.notEqual(fast.avg,other.avg);
});
test('food suggestions are opt-in in the UI',()=>{assert.match(index,/id="foodEnabled"/);assert.match(index,/id="foodBody" hidden/);});
test('recipe filtering excludes declared allergens',()=>{
  assert.equal(c.matchRecipes('Indian',['milk']).some(r=>r.name.includes('Paneer')),false);
  assert.equal(c.matchRecipes('Indian',['peanut']).some(r=>r.name.includes('Peanut')),false);
  assert.equal(c.matchRecipes('Mediterranean',['wheat','sesame']).some(r=>r.name.includes('pita')),false);
});
test('ingredient exclusions and cuisine preference are respected',()=>{
  assert.equal(c.matchRecipes('Indian',[],'ginger').some(r=>r.name.includes('chilla')),false);
  assert.equal(c.matchRecipes('Mediterranean',[]).every(r=>r.cuisine==='Mediterranean'),true);
});
test('supplement example is generic and optional',()=>{
  assert.equal(c.SUPPLEMENTS.length,4);assert.match(index,/id="supplementEnabled"/);assert.match(index,/id="supplementBody" hidden/);
});
test('agent trace is accurately labelled as simulated, not real model execution',()=>{
  assert.match(index,/not by a live language model/);assert.match(app,/rule-based public simulation/);
});
test('impossible calendar dates and dates outside the demo window are rejected',()=>{
  const input={date:'2026-10-05',occasion:'before_breakfast',time:'07:40',value:7.1};
  for(const date of ['2026-02-30','2026-10-04','2026-10-19','2026-13-01']){
    assert.throws(()=>c.addReading([],{...input,date}),/date|period/i);
  }
});
test('sample times match the stated testing occasion',()=>{
  const readings=c.starterReadings();
  for(const r of readings) assert.equal(r.time,c.EXAMPLE_TIMES[r.occasion]);
  assert.equal(c.EXAMPLE_TIMES.before_sleep,'22:00');
  assert.equal(c.EXAMPLE_TIMES.before_lunch,'12:10');
});
test('example-prefill and reset code maintain time and UI consistency',()=>{
  assert.match(app,/Core\.EXAMPLE_TIMES\[open\.occasion\]/);
  assert.match(app,/\$\('chartContext'\)\.value='before_breakfast'/);
  assert.match(app,/\$\('reminderPreview'\)\.hidden=true/);
});
test('mobile graph has responsive dimensions rather than overflowing',()=>{
  const css=fs.readFileSync(path.join(__dirname,'../docs/demo.css'),'utf8');
  assert.match(css,/#glucoseChart\s*\{[^}]*width:100%/s);
  assert.match(css,/\.demo-shell\s*\{grid-template-columns:minmax\(0,1fr\)/s);
});
test('sample data remain unlinked to actual personal details in all public demo assets',()=>{
  const css=fs.readFileSync(path.join(__dirname,'../docs/demo.css'),'utf8');
  const publicSource=[index,app,css,fs.readFileSync(path.join(__dirname,'../docs/demo-core.js'),'utf8')].join('\n');
  assert.doesNotMatch(publicSource,/[A-Z0-9._%+-]+@gmail\.com|STRIVIT|20,000 IU/gi);
});
