(function(){
const DATA=__DATA__;
const KO={"Information Technology":"정보기술","Financials":"금융","Health Care":"헬스케어","Consumer Discretionary":"경기소비재","Communication Services":"커뮤니케이션","Industrials":"산업재","Consumer Staples":"필수소비재","Energy":"에너지","Utilities":"유틸리티","Real Estate":"부동산","Materials":"소재"};
const root=document.getElementById('hm'),box=document.getElementById('hmbox'),st=document.getElementById('hmst'),tip=document.getElementById('hmtip');
if(!root)return;
const U='https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json&events=1&symbols=';
const all=[];Object.keys(DATA).forEach(s=>DATA[s].forEach(t=>all.push({t,s})));
const Q={};let lastOk=0,session='';
const num=v=>parseFloat(String(v).replace(/[%,+$]/g,''));
function cap(v){if(!v)return 0;const m=String(v).match(/^([\d.,]+)\s*([TBM]?)/i);if(!m)return 0;const x=parseFloat(m[1].replace(/,/g,''));return x*({T:1e12,B:1e9,M:1e6}[m[2].toUpperCase()]||1);}
function color(c){const a=Math.min(Math.abs(c)/3,1),n=[58,62,70],p=c>=0?[8,153,129]:[242,54,69];const m=(i)=>Math.round(n[i]+(p[i]-n[i])*(0.18+0.82*a*(Math.abs(c)<0.005?0:1)));if(Math.abs(c)<0.005)return 'rgb(58,62,70)';return 'rgb('+m(0)+','+m(1)+','+m(2)+')';}
function sq(items,x,y,w,h){const res=[];const tot=items.reduce((a,b)=>a+b.v,0);if(!tot||w<=0||h<=0)return res;const sc=w*h/tot;const arr=items.map(i=>({i,a:i.v*sc}));
const worst=(r,s)=>{const sum=r.reduce((a,b)=>a+b.a,0),mx=Math.max(...r.map(z=>z.a)),mn=Math.min(...r.map(z=>z.a));return Math.max(s*s*mx/(sum*sum),sum*sum/(s*s*mn));};
let k=0;while(k<arr.length){const s=Math.min(w,h);let row=[arr[k]];k++;while(k<arr.length){const t=row.concat(arr[k]);if(worst(t,s)<=worst(row,s)){row=t;k++;}else break;}
const sum=row.reduce((a,b)=>a+b.a,0);if(w>=h){const cw=sum/h;let cy=y;row.forEach(r=>{const ch=r.a/cw;res.push({i:r.i,x,y:cy,w:cw,h:ch});cy+=ch;});x+=cw;w-=cw;}else{const rh=sum/w;let cx=x;row.forEach(r=>{const cw=r.a/rh;res.push({i:r.i,x:cx,y,w:cw,h:rh});cx+=cw;});y+=rh;h-=rh;}}
return res;}
function draw(){const W=box.clientWidth,H=box.clientHeight;if(!W||!H)return;
const groups={};all.forEach(o=>{const q=Q[o.t];if(!q||!q.v)return;(groups[o.s]=groups[o.s]||[]).push({t:o.t,v:q.v,c:q.c});});
const gs=Object.keys(groups).map(s=>({s,v:groups[s].reduce((a,b)=>a+b.v,0),it:groups[s].sort((a,b)=>b.v-a.v)})).sort((a,b)=>b.v-a.v);
let h='';sq(gs,0,0,W,H).forEach(r=>{const g=r.i,hd=r.h>34&&r.w>60?15:0,pad=1;
if(hd)h+='<div class="hs" style="left:'+r.x.toFixed(1)+'px;top:'+r.y.toFixed(1)+'px;width:'+r.w.toFixed(1)+'px">'+(KO[g.s]||g.s)+'</div>';
sq(g.it,r.x+pad,r.y+hd+pad,r.w-pad*2,r.h-hd-pad*2).forEach(b=>{const o=b.i,w=b.w,hh=b.h;let tx='';
if(w>=24&&hh>=15){const fs=Math.max(8,Math.min(26,w/Math.max(o.t.length*0.68,hh>=34&&w>=34?4.6:0),hh/(hh>=34?2.5:1.5)));tx='<b style="font-size:'+fs.toFixed(1)+'px">'+o.t+'</b>'+(hh>=34&&w>=34?'<i style="font-size:'+Math.max(8,fs*0.72).toFixed(1)+'px">'+(o.c>=0?'+':'')+o.c.toFixed(2)+'%</i>':'');}
h+='<div class="hc" data-t="'+o.t+'" style="left:'+b.x.toFixed(1)+'px;top:'+b.y.toFixed(1)+'px;width:'+Math.max(w-1,0).toFixed(1)+'px;height:'+Math.max(hh-1,0).toFixed(1)+'px;background:'+color(o.c)+'">'+tx+'</div>';});});
box.innerHTML=h;}
async function load(){try{const syms=all.map(o=>o.t),parts=[];for(let i=0;i<syms.length;i+=100)parts.push(syms.slice(i,i+100));
const res=await Promise.all(parts.map(p=>fetch(U+p.map(encodeURIComponent).join('|'),{cache:'no-store'}).then(r=>r.json()).then(j=>[].concat(j.FormattedQuoteResult.FormattedQuote||[]))));
let n=0,ses={};res.forEach(a=>a.forEach(q=>{if(q.last==null)return;let L=num(q.last),pv=num(q.previous_day_closing),C=num(q.change_pct),tm=q.last_time,s=q.curmktstatus;
const e=q.ExtendedMktQuote;if(s!=='REG_MKT'&&e&&e.last){const el=num(e.last);if(!isNaN(el)){L=el;C=num(e.change_pct);tm=e.last_time;}}
if(isNaN(C)&&pv)C=(L-pv)/pv*100;if(isNaN(L)||isNaN(C))return;Q[q.symbol]={v:cap(q.mktcapView),c:C,l:L,nm:q.shortName&&q.name?q.name:q.symbol,cap:q.mktcapView,tm:tm,s:s};ses[s]=(ses[s]||0)+1;n++;}));
if(n>50){lastOk=Date.now();const top=Object.keys(ses).sort((a,b)=>ses[b]-ses[a])[0];session=top==='REG_MKT'?'정규장':top==='PRE_MKT'?'프리마켓':top==='POST_MKT'?'애프터마켓':'장 마감';draw();stamp();}}catch(e){stamp(true);}}
function stamp(err){const t=lastOk?new Date(lastOk).toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}):'--';st.innerHTML=(err?'<span class="dn">연결 지연 · 재시도 중</span> · ':'')+'<span class="live"></span>'+session+' · 1분마다 갱신 · 마지막 '+t;}
function showTip(t,ev){const q=Q[t];if(!q)return;const a=all.find(o=>o.t===t);tip.innerHTML='<b>'+t+'</b> <span>'+q.nm+'</span><br>'+(KO[a.s]||a.s)+' · 시총 '+(q.cap||'-')+'<br><u>$'+q.l.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})+'</u> <em class="'+(q.c>=0?'up':'down')+'">'+(q.c>=0?'+':'')+q.c.toFixed(2)+'%</em>';tip.style.display='block';
const r=root.getBoundingClientRect(),tw=tip.offsetWidth,th=tip.offsetHeight;let x=ev.clientX-r.left+14,y=ev.clientY-r.top+14;if(x+tw>r.width)x=ev.clientX-r.left-tw-14;if(y+th>r.height)y=ev.clientY-r.top-th-14;tip.style.left=Math.max(0,x)+'px';tip.style.top=Math.max(0,y)+'px';}
box.addEventListener('mousemove',e=>{const c=e.target.closest('.hc');if(c)showTip(c.dataset.t,e);else tip.style.display='none';});
box.addEventListener('mouseleave',()=>tip.style.display='none');
box.addEventListener('click',e=>{const c=e.target.closest('.hc');if(c)showTip(c.dataset.t,e);else tip.style.display='none';});
let rt;new ResizeObserver(()=>{clearTimeout(rt);rt=setTimeout(draw,120);}).observe(box);
load();setInterval(()=>{if(!document.hidden)load();},60000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)load();});
})();
