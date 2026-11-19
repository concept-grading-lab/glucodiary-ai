/* GlucoDiary AI public portfolio demo — deterministic, synthetic data only. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.GlucoCore = api;
})(typeof window === 'undefined' ? null : window, function () {
  'use strict';
  const START = '2026-10-05';
  const DAYS = 14;
  const OCCASIONS = ['before_breakfast','before_lunch','before_dinner','before_sleep'];
  const LABELS = {before_breakfast:'Before breakfast',before_lunch:'Before lunch',before_dinner:'Before dinner',before_sleep:'Before sleep'};
  const NEXT = ['before_lunch','before_dinner','before_sleep'];
  const EXAMPLE_TIMES = {before_breakfast:'07:40',before_lunch:'12:10',before_dinner:'18:10',before_sleep:'22:00'};
  const isoAdd = (start, offset) => {const d=new Date(start+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+offset);return d.toISOString().slice(0,10)};
  function makeTasks(){
    const out=[];
    for(let i=0;i<DAYS;i++){
      const date=isoAdd(START,i);
      for(const occasion of ['before_breakfast',NEXT[i%3]]) out.push({id:`${date}|${occasion}`,date,occasion});
    }
    return out;
  }
  const morning=[8.9,8.5,8.3,8.1,7.9,7.8,7.8,7.4,7.5,7.2,7.0,7.2,6.9,6.8];
  const extra=[7.5,8.1,null,7.0,7.3,7.1,6.8,null,7.0,6.5,6.4,null,6.6,6.2];
  function starterReadings(){
    const out=[];
    for(let i=0;i<DAYS;i++){
      const date=isoAdd(START,i);
      if(i!==5 && i!==11)out.push({id:`seed-b-${i}`,date,occasion:'before_breakfast',value:morning[i],time:EXAMPLE_TIMES.before_breakfast,origin:'synthetic'});
      if(extra[i]!==null)out.push({id:`seed-x-${i}`,date,occasion:NEXT[i%3],value:extra[i],time:EXAMPLE_TIMES[NEXT[i%3]],origin:'synthetic'});
    }
    return out;
  }
  function average(rows){return rows.length?rows.reduce((sum,r)=>sum+r.value,0)/rows.length:null}
  function summaries(readings, occasion='all'){
    const rows=readings.filter(r=>occasion==='all'||r.occasion===occasion).sort((a,b)=>a.date.localeCompare(b.date)||a.time.localeCompare(b.time));
    if(!rows.length) return {rows,count:0,avg:null,min:null,max:null,first:null,last:null,change:null};
    const vals=rows.map(r=>r.value);
    return {rows,count:rows.length,avg:average(rows),min:Math.min(...vals),max:Math.max(...vals),first:vals[0],last:vals.at(-1),change:vals.at(-1)-vals[0]};
  }
  function taskProgress(readings,tasks=makeTasks()){
    const present=new Set(readings.map(r=>`${r.date}|${r.occasion}`));
    const completed=tasks.filter(t=>present.has(t.id)).length;
    return {total:tasks.length,completed,missing:tasks.length-completed};
  }
  function addReading(readings,input){
    const date=String(input.date||''); const occasion=String(input.occasion||''); const value=Number(input.value),time=String(input.time||'08:00');
    if(!/^\d{4}-\d\d-\d\d$/.test(date) || !Number.isFinite(Date.parse(date+'T12:00:00Z')) || new Date(date+'T12:00:00Z').toISOString().slice(0,10)!==date) throw Error('Choose a valid test date.');
    if(date<START || date>isoAdd(START,DAYS-1)) throw Error('Choose a date within the fictional two-week demo period.');
    if(!OCCASIONS.includes(occasion)) throw Error('Choose a testing occasion.');
    if(!Number.isFinite(value)||value<=0||value>40) throw Error('Enter a numeric glucose value greater than 0 and up to 40 mmol/L.');
    if(!/^([01]\d|2[0-3]):[0-5]\d$/.test(time)) throw Error('Enter a valid time (HH:MM).');
    if(readings.some(r=>r.date===date && r.occasion===occasion)) throw Error('There is already a reading for this date and occasion. Delete that entry first to replace it.');
    return [...readings,{id:`added-${date}-${occasion}`,date,occasion,value:Math.round(value*10)/10,time,origin:'demo-entry'}];
  }
  function evidence(readings){
    const prog=taskProgress(readings), all=summaries(readings),fast=summaries(readings,'before_breakfast');
    return {schedule:prog,readings:all.count,overallMean:all.avg,fastingCount:fast.count,fastingMean:fast.avg,fastingChange:fast.change};
  }
  const RECIPES=[
    {name:'Moong dal chilla',cuisine:'Indian',ingredients:['moong dal','ginger','coriander','spices'],allergens:[],description:'Savoury lentil pancakes with fresh herbs'},
    {name:'Vegetable dal and brown rice',cuisine:'Indian',ingredients:['masoor dal','brown rice','spinach','tomato'],allergens:[],description:'Comforting lentils and vegetables with a measured rice portion'},
    {name:'Paneer bhurji with salad',cuisine:'Indian',ingredients:['paneer','milk','tomato','onion','spices'],allergens:['milk'],description:'Spiced paneer with chopped vegetables'},
    {name:'Peanut vegetable poha',cuisine:'Indian',ingredients:['flattened rice','peanuts','peas','onion'],allergens:['peanut'],description:'Vegetable-based flattened-rice dish'},
    {name:'Chickpea cucumber bowl',cuisine:'Mediterranean',ingredients:['chickpeas','cucumber','olive oil','lemon'],allergens:[],description:'Fresh chickpea and vegetable bowl'},
    {name:'Wholewheat pita and hummus',cuisine:'Mediterranean',ingredients:['wheat','chickpeas','tahini','sesame'],allergens:['wheat','sesame'],description:'Pita with hummus and crunchy salad'},
    {name:'Greek-style yoghurt bowl',cuisine:'Mediterranean',ingredients:['yoghurt','milk','berries','walnuts'],allergens:['milk','tree nut'],description:'Yoghurt topped with fruit and nuts'}
  ];
  function matchRecipes(cuisine,allergies=[],excluded=''){
    const banned=excluded.toLowerCase().split(',').map(s=>s.trim()).filter(Boolean);
    const a=new Set(allergies.map(s=>s.toLowerCase()));
    return RECIPES.filter(r=>(cuisine==='Any'||r.cuisine===cuisine)&&!r.allergens.some(x=>a.has(x))&&!r.ingredients.some(x=>banned.some(b=>x.toLowerCase().includes(b))));
  }
  const SUPPLEMENTS=['2026-10-06','2026-10-13','2026-10-20','2026-10-27'];
  return {START,DAYS,OCCASIONS,LABELS,makeTasks,starterReadings,summaries,taskProgress,addReading,evidence,matchRecipes,SUPPLEMENTS,EXAMPLE_TIMES,isoAdd};
});
