(function(){
const DATA=__DATA__; // {섹터:{산업:[티커]}}  (분류: Finviz)
const $=id=>document.getElementById(id);
const root=$('hm'),box=$('hmbox'),st=$('hmst'),tip=$('hmtip'),lst=$('hmlist'),gsel=$('hmg'),ssel=$('hms'),zsel=$('hmz'),lgc=$('hmlogo');
if(!root)return;
const Q_URL='https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json&events=1&symbols=';
const META={},all=[];Object.keys(DATA).forEach(s=>Object.keys(DATA[s]).forEach(i=>DATA[s][i].forEach(t=>{META[t]={s,i};all.push(t);})));
let GR=[];const Q={},openSet=new Set();let lastOk=0,session='',mode='si',secF='',view='map',size='cap',logos=false;
try{mode=localStorage.getItem('hmMode')||mode;view=localStorage.getItem('hmView')||view;size=localStorage.getItem('hmSize')||size;logos=localStorage.getItem('hmLogo')==='1';}catch(e){}
gsel.value=mode;zsel.value=size;lgc.checked=logos;
ssel.innerHTML='<option value="">전체</option>'+Object.keys(DATA).map(s=>'<option value="'+s+'">'+s+'</option>').join('');
// ---- 색: Finviz와 동일한 -3% ~ +3% 7단계 (사이 값은 보간) ----
const STOPS=[[-3,[246,53,56]],[-2,[191,64,69]],[-1,[139,68,78]],[0,[65,69,84]],[1,[53,118,78]],[2,[47,158,79]],[3,[48,204,90]]];
function color(c){const v=Math.max(-3,Math.min(3,c));let k=1;while(k<STOPS.length-1&&v>STOPS[k][0])k++;const a=STOPS[k-1],b=STOPS[k],t=(v-a[0])/(b[0]-a[0]);return 'rgb('+[0,1,2].map(i=>Math.round(a[1][i]+(b[1][i]-a[1][i])*t)).join(',')+')';}
$('hmlg').innerHTML=STOPS.map(s=>'<span style="background:'+color(s[0])+'">'+(s[0]>0?'+':'')+s[0]+'%</span>').join('');
const num=v=>parseFloat(String(v).replace(/[%,+$]/g,''));
function cap(v){if(!v)return 0;const m=String(v).match(/^([\d.,]+)\s*([TBM]?)/i);if(!m)return 0;return parseFloat(m[1].replace(/,/g,''))*({T:1e12,B:1e9,M:1e6}[m[2].toUpperCase()]||1);}
const sum=a=>a.reduce((x,y)=>x+y.v,0),desc=(a,b)=>b.v-a.v,fc=c=>(c>=0?'+':'')+c.toFixed(2)+'%';
const logo=t=>'https://logo.finviz.com/'+t+'.svg';
// ---- 트리맵 (squarified) ----
function sq(items,x,y,w,h){const res=[];const tot=items.reduce((a,b)=>a+b.v,0);if(!tot||w<=0||h<=0)return res;const sc=w*h/tot;const arr=items.map(i=>({i,a:i.v*sc}));
const worst=(r,s)=>{const sm=r.reduce((a,b)=>a+b.a,0),mx=Math.max(...r.map(z=>z.a)),mn=Math.min(...r.map(z=>z.a));return Math.max(s*s*mx/(sm*sm),sm*sm/(s*s*mn));};
let k=0;while(k<arr.length){const s=Math.min(w,h);let row=[arr[k]];k++;while(k<arr.length){const t=row.concat(arr[k]);if(worst(t,s)<=worst(row,s)){row=t;k++;}else break;}
const sm=row.reduce((a,b)=>a+b.a,0);if(w>=h){const cw=sm/h;let cy=y;row.forEach(r=>{const ch=r.a/cw;res.push({i:r.i,x,y:cy,w:cw,h:ch});cy+=ch;});x+=cw;w-=cw;}else{const rh=sm/w;let cx=x;row.forEach(r=>{const cw=r.a/rh;res.push({i:r.i,x:cx,y,w:cw,h:rh});cx+=cw;});y+=rh;h-=rh;}}
return res;}
function tree(forceInd){const m=forceInd||mode;const leaf=t=>{const q=Q[t];return {t,v:size==='eq'?1:q.v,c:q.c};};
const out=[];Object.keys(DATA).forEach(s=>{if(secF&&s!==secF)return;const inds=[];Object.keys(DATA[s]).forEach(i=>{const L=DATA[s][i].filter(t=>Q[t]&&Q[t].v).map(leaf).sort(desc);if(L.length)inds.push({name:i,v:sum(L),kids:L});});
if(!inds.length)return;inds.sort(desc);out.push({name:s,v:sum(inds),kids:m==='si'?inds:[].concat(...inds.map(x=>x.kids)).sort(desc)});});
out.sort(desc);return m==='n'?[].concat(...out.map(leaves)).sort(desc):out;}
function lay(items,x,y,w,h,d,out,par,gi){sq(items,x,y,w,h).forEach(r=>{const n=r.i;if(n.t){out.c.push({n,x:r.x,y:r.y,w:r.w,h:r.h,gi});return;}
const H=d?11:14,hh=(r.h>H+22&&r.w>44)?H:0;if(hh)out.h.push({n,d,x:r.x,y:r.y,w:r.w,hh});const p=d?0:1;let g=gi;if(n.kids[0]&&n.kids[0].t){g=out.g.length;out.g.push({name:n.name,par:d?par:'',x:r.x,y:r.y,w:r.w,h:r.h,kids:n.kids});}
lay(n.kids,r.x+p,r.y+hh+p,r.w-p*2,r.h-hh-p*2,d+1,out,d?par:n.name,g);});}
function cellHTML(o,b,gi){const w=b.w,h=b.h;let tx='';
if(w>=22&&h>=14){let ls=0;if(logos&&w>=40&&h>=46)ls=Math.max(14,Math.min(40,w*0.4,h*0.32));const ah=h-(ls?ls+4:0);
const fs=Math.max(8,Math.min(40,w/Math.max(o.t.length*0.66,ah>=32&&w>=32?4.4:0),ah>=32?ah/2.4:ah/1.4));
if(ls)tx+='<img src="'+logo(o.t)+'" width="'+ls.toFixed(0)+'" height="'+ls.toFixed(0)+'" alt="" onerror="this.remove()">';
if(!ls||ah>=14)tx+='<b style="font-size:'+fs.toFixed(1)+'px">'+o.t+'</b>';
if(ah>=32&&w>=32)tx+='<i style="font-size:'+Math.max(8,fs*0.62).toFixed(1)+'px">'+fc(o.c)+'</i>';}
return '<div class="hc" data-t="'+o.t+'"'+(gi==null?'':' data-g="'+gi+'"')+' style="left:'+b.x.toFixed(1)+'px;top:'+b.y.toFixed(1)+'px;width:'+Math.max(w-1,0).toFixed(1)+'px;height:'+Math.max(h-1,0).toFixed(1)+'px;background:'+color(o.c)+'">'+tx+'</div>';}
function drawMap(){const W=box.clientWidth,H=box.clientHeight;if(!W||!H)return;const out={c:[],h:[],g:[]};lay(tree(),0,0,W,H,0,out,'',null);GR=out.g;
let h='';out.h.forEach(o=>{h+='<div class="hs d'+o.d+'"'+(o.d?'':' data-sec="'+o.n.name+'"')+' style="left:'+o.x.toFixed(1)+'px;top:'+o.y.toFixed(1)+'px;width:'+o.w.toFixed(1)+'px">'+o.n.name+'</div>';});
out.c.forEach(b=>{h+=cellHTML(b.n,b,b.gi);});box.innerHTML=h+'<div id="hmhl" class="hmhl"></div>';}
// ---- 목록 ----
function avg(a){const v=sum(a);return v?a.reduce((s,x)=>s+x.c*x.v,0)/v:0;}
function leaves(n){return n.t?[n]:[].concat(...n.kids.map(leaves));}
function row(o){const q=Q[o.t];return '<div class="lr" data-t="'+o.t+'">'+(logos?'<img src="'+logo(o.t)+'" width="20" height="20" alt="" onerror="this.style.visibility=\'hidden\'">':'<span class="lgx"></span>')+'<b>'+o.t+'</b><span class="nm">'+q.nm+'</span><span class="px">$'+q.l.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})+'</span><em class="'+(o.c>=0?'up':'down')+'">'+fc(o.c)+'</em><span class="cp">'+(q.cap||'-')+'</span></div>';}
function sumHTML(name,n,c){return '<summary><span class="ln">'+name+'</span><span class="lcn">'+n+'개</span><em class="'+(c>=0?'up':'down')+'">'+fc(c)+'</em></summary>';}
function drawList(){const T=tree('si');let h='';
T.forEach(s=>{const L=leaves(s),op=openSet.has(s.name)||secF;h+='<details class="ls" data-k="'+s.name+'"'+(op?' open':'')+'>'+sumHTML(s.name,L.length,avg(L));
s.kids.forEach(k=>{const kk=s.name+'|'+k.name;h+='<details class="li" data-k="'+kk+'"'+(openSet.has(kk)?' open':'')+'>'+sumHTML(k.name,k.kids.length,avg(k.kids));k.kids.forEach(x=>{h+=row(x);});h+='</details>';});h+='</details>';});
lst.innerHTML=h||'<div class="hmempty">불러오는 중…</div>';}
lst.addEventListener('toggle',e=>{const d=e.target;if(d.dataset&&d.dataset.k){d.open?openSet.add(d.dataset.k):openSet.delete(d.dataset.k);}},true);
function draw(){if(view==='list'){box.hidden=true;lst.hidden=false;drawList();}else{lst.hidden=true;box.hidden=false;drawMap();}
document.querySelectorAll('.hmvw .pill').forEach(b=>b.classList.toggle('on',b.dataset.v===view));}
// ---- 시세 (CNBC, 1분) ----
async function load(){try{const parts=[];for(let i=0;i<all.length;i+=100)parts.push(all.slice(i,i+100));
const res=await Promise.all(parts.map(p=>fetch(Q_URL+p.map(encodeURIComponent).join('|'),{cache:'no-store'}).then(r=>r.json()).then(j=>[].concat(j.FormattedQuoteResult.FormattedQuote||[]))));
let n=0,ses={};res.forEach(a=>a.forEach(q=>{if(q.last==null)return;let L=num(q.last),pv=num(q.previous_day_closing),C=num(q.change_pct),s=q.curmktstatus;
const e=q.ExtendedMktQuote;if(s!=='REG_MKT'&&e&&e.last){const el=num(e.last);if(!isNaN(el)){L=el;C=num(e.change_pct);}}
if(isNaN(C)&&pv)C=(L-pv)/pv*100;if(isNaN(L)||isNaN(C))return;Q[q.symbol]={v:cap(q.mktcapView),c:C,l:L,nm:q.name||q.symbol,cap:q.mktcapView,s:s};ses[s]=(ses[s]||0)+1;n++;}));
if(n>50){lastOk=Date.now();const top=Object.keys(ses).sort((a,b)=>ses[b]-ses[a])[0];session=top==='REG_MKT'?'정규장':top==='PRE_MKT'?'프리마켓':top==='POST_MKT'?'애프터마켓':'장 마감';draw();stamp();}}catch(e){stamp(true);}}
function stamp(err){const t=lastOk?new Date(lastOk).toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}):'--';st.innerHTML=(err?'<span class="dn">연결 지연 · 재시도 중</span> · ':'')+'<span class="live"></span>'+session+' · 1분마다 갱신 · 마지막 '+t;}
// ---- 상호작용 ----
function px(l){return '$'+l.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});}
function showTip(t,ev,gi){const q=Q[t];if(!q)return;const g=gi!=null&&GR[gi]?GR[gi]:null,mx=matchMedia('(max-width:560px)').matches?6:11;
let h=(g?'<div class="th">'+(g.par?g.par+' – ':'')+g.name+'</div>':'')+'<div class="tm"><b>'+t+'</b> <span>'+q.nm+'</span><div class="tp"><u>'+px(q.l)+'</u> <em class="'+(q.c>=0?'up':'down')+'">'+fc(q.c)+'</em></div><div class="ts">시총 '+(q.cap||'-')+'</div></div>';
if(g){const L=g.kids.slice(0,mx);if(g.kids.length>mx&&L.every(k=>k.t!==t)){L.pop();L.push(g.kids.find(k=>k.t===t));}
h+='<div class="tl">'+L.map(k=>{const z=Q[k.t];return '<div class="tr'+(k.t===t?' on':'')+'"><b>'+k.t+'</b><span>'+px(z.l)+'</span><em class="'+(z.c>=0?'up':'down')+'">'+fc(z.c)+'</em></div>';}).join('')+(g.kids.length>mx?'<div class="tmore">외 '+(g.kids.length-L.length)+'개 종목</div>':'')+'</div>';
const hl=$('hmhl');if(hl){hl.style.cssText='display:block;left:'+g.x+'px;top:'+g.y+'px;width:'+g.w+'px;height:'+g.h+'px';}}
tip.innerHTML=h;tip.style.display='block';
const r=root.getBoundingClientRect(),tw=tip.offsetWidth,th=tip.offsetHeight;let x=ev.clientX-r.left+16,y=ev.clientY-r.top+12;if(x+tw>r.width)x=ev.clientX-r.left-tw-16;if(y+th>r.height)y=r.height-th-4;tip.style.left=Math.max(0,x)+'px';tip.style.top=Math.max(0,y)+'px';}
function hideTip(){tip.style.display='none';const hl=$('hmhl');if(hl)hl.style.display='none';}
box.addEventListener('mousemove',e=>{const c=e.target.closest('.hc');if(c)showTip(c.dataset.t,e,c.dataset.g==null?null:+c.dataset.g);else hideTip();});
box.addEventListener('mouseleave',hideTip);
box.addEventListener('click',e=>{const s=e.target.closest('.hs[data-sec]');if(s){secF=secF?'':s.dataset.sec;ssel.value=secF;hideTip();draw();return;}const c=e.target.closest('.hc');if(c)showTip(c.dataset.t,e,c.dataset.g==null?null:+c.dataset.g);else hideTip();});
const sv=(k,v)=>{try{localStorage.setItem(k,v)}catch(e){}};
gsel.addEventListener('change',()=>{mode=gsel.value;sv('hmMode',mode);draw();});
zsel.addEventListener('change',()=>{size=zsel.value;sv('hmSize',size);draw();});
lgc.addEventListener('change',()=>{logos=lgc.checked;sv('hmLogo',logos?'1':'0');draw();});
ssel.addEventListener('change',()=>{secF=ssel.value;draw();});
document.querySelectorAll('.hmvw .pill').forEach(b=>b.addEventListener('click',()=>{view=b.dataset.v;sv('hmView',view);draw();}));
let rt;new ResizeObserver(()=>{clearTimeout(rt);rt=setTimeout(()=>{if(view==='map')drawMap();},120);}).observe(box);
load();setInterval(()=>{if(!document.hidden)load();},60000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)load();});
})();
