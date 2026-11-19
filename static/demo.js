'use strict';
const measurements=[
{day:'2026-11-02',occasion:'before_breakfast',glucose:8.5},{day:'2026-11-03',occasion:'before_dinner',glucose:8.1},
{day:'2026-11-04',occasion:'before_lunch',glucose:6.9},{day:'2026-11-05',occasion:'before_breakfast',glucose:8.2},
{day:'2026-11-06',occasion:'before_sleep',glucose:7.3},{day:'2026-11-07',occasion:'before_breakfast',glucose:7.9},
{day:'2026-11-08',occasion:'before_dinner',glucose:7.5},{day:'2026-11-09',occasion:'before_lunch',glucose:6.8},
{day:'2026-11-10',occasion:'before_breakfast',glucose:7.6},{day:'2026-11-11',occasion:'before_sleep',glucose:7.0},
{day:'2026-11-12',occasion:'before_breakfast',glucose:7.4},{day:'2026-11-13',occasion:'before_dinner',glucose:6.9}];
const labels={before_breakfast:'Before breakfast',before_lunch:'Before lunch',before_dinner:'Before dinner',before_sleep:'Before sleep'};
function render(){const oc=document.querySelector('#context').value;const rows=measurements.filter(x=>oc==='all'||x.occasion===oc);
const avg=rows.length?rows.reduce((s,x)=>s+x.glucose,0)/rows.length:null;
document.querySelector('#demoStats').innerHTML=`<div class="stat"><small>Readings in view</small><strong>${rows.length}</strong><span>Fabricated sample values</span></div><div class="stat"><small>Average (mmol/L)</small><strong>${avg===null?'—':avg.toFixed(2)}</strong><span>Arithmetic mean only</span></div><div class="stat"><small>Highest recorded</small><strong>${rows.length?Math.max(...rows.map(x=>x.glucose)).toFixed(1):'—'}</strong><span>mmol/L</span></div><div class="stat"><small>Lowest recorded</small><strong>${rows.length?Math.min(...rows.map(x=>x.glucose)).toFixed(1):'—'}</strong><span>mmol/L</span></div>`;
document.querySelector('#demoTable').innerHTML=rows.map(x=>`<tr><td>${x.day}</td><td>${labels[x.occasion]}</td><td><b>${x.glucose.toFixed(1)}</b></td></tr>`).join('');
const svg=document.querySelector('#demoChart'),NS='http://www.w3.org/2000/svg';svg.replaceChildren();const add=(tag,attrs,txt)=>{let a=document.createElementNS(NS,tag);Object.entries(attrs).forEach(([k,v])=>a.setAttribute(k,v));if(txt!==undefined)a.textContent=txt;svg.appendChild(a)};
if(!rows.length){add('text',{x:100,y:100},'No matching readings');return}
const mn=Math.min(...rows.map(x=>x.glucose))-1,mx=Math.max(...rows.map(x=>x.glucose))+1;
const x=i=>52+(rows.length===1?.5:i/(rows.length-1))*580,y=v=>190-(v-mn)/(mx-mn)*155;
for(let k=0;k<4;k++){let h=35+k*155/3;add('line',{x1:52,y1:h,x2:632,y2:h,stroke:'#e1e9ec'});add('text',{x:40,y:h+4,'text-anchor':'end',fill:'#7a8e98','font-size':12},(mx-(mx-mn)*k/3).toFixed(1))}
if(rows.length>1)add('polyline',{points:rows.map((d,i)=>`${x(i)},${y(d.glucose)}`).join(' '),fill:'none',stroke:'#218b89','stroke-width':3});rows.forEach((d,i)=>add('circle',{cx:x(i),cy:y(d.glucose),r:4,fill:'#fff',stroke:'#218b89','stroke-width':3}));}
document.querySelector('#context').addEventListener('change',render);render();
