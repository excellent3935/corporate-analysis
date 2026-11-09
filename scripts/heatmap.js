(function(){
const DATA=__DATA__;
const GICS={"Information Technology":"정보기술","Financials":"금융","Health Care":"헬스케어","Consumer Discretionary":"경기소비재","Communication Services":"커뮤니케이션","Industrials":"산업재","Consumer Staples":"필수소비재","Energy":"에너지","Utilities":"유틸리티","Real Estate":"부동산","Materials":"소재"};
const SEC={"Electronic Technology":"전자 기술","Technology Services":"기술 서비스","Health Technology":"의료 기술","Retail Trade":"소매업","Finance":"금융","Producer Manufacturing":"생산자 제조","Energy Minerals":"에너지 광물","Utilities":"유틸리티","Consumer Durables":"소비자 내구재","Health Services":"보건 서비스","Commercial Services":"상업 서비스","Consumer Non-Durables":"소비자 비내구재","Consumer Services":"소비자 서비스","Process Industries":"공정 산업","Transportation":"운송","Communications":"통신","Non-Energy Minerals":"비에너지 광물","Industrial Services":"산업 서비스","Distribution Services":"유통 서비스","Miscellaneous":"기타"};
const IND={"Information Technology Services":"정보기술 서비스","Internet Software/Services":"인터넷 소프트웨어·서비스","Packaged Software":"패키지 소프트웨어","Data Processing Services":"데이터 처리 서비스","Apparel/Footwear Retail":"의류·신발 소매","Specialty Stores":"전문 소매점","Electronics/Appliance Stores":"전자제품 매장","Discount Stores":"할인점","Internet Retail":"인터넷 소매","Food Retail":"식품 소매","Home Improvement Chains":"홈인테리어 체인","Drugstore Chains":"드럭스토어 체인","Real Estate Investment Trusts":"리츠","Multi-Line Insurance":"종합 보험","Insurance Brokers/Services":"보험 중개·서비스","Investment Managers":"자산운용","Finance/Rental/Leasing":"금융·렌탈·리스","Regional Banks":"지역 은행","Investment Banks/Brokers":"투자은행·증권","Property/Casualty Insurance":"손해보험","Major Banks":"대형 은행","Real Estate Development":"부동산 개발","Life/Health Insurance":"생명·건강보험","Wholesale Distributors":"도매 유통","Medical Distributors":"의료 유통","Food Distributors":"식품 유통","Semiconductors":"반도체","Electronic Components":"전자 부품","Electronic Equipment/Instruments":"전자 장비·계측","Aerospace & Defense":"항공우주·방산","Telecommunications Equipment":"통신 장비","Computer Processing Hardware":"컴퓨터 하드웨어","Computer Peripherals":"컴퓨터 주변기기","Electronic Production Equipment":"전자 생산 장비","Medical Specialties":"의료 전문","Pharmaceuticals: Major":"대형 제약","Biotechnology":"바이오기술","Financial Publishing/Services":"금융 출판·서비스","Advertising/Marketing Services":"광고·마케팅","Miscellaneous Commercial Services":"기타 상업 서비스","Electric Utilities":"전력","Gas Distributors":"가스","Water Utilities":"수도","Casinos/Gaming":"카지노·게임","Cable/Satellite TV":"케이블·위성TV","Restaurants":"레스토랑","Movies/Entertainment":"영화·엔터테인먼트","Hotels/Resorts/Cruise lines":"호텔·리조트·크루즈","Other Consumer Services":"기타 소비자 서비스","Publishing: Newspapers":"신문 출판","Broadcasting":"방송","Managed Health Care":"관리형 의료","Medical/Nursing Services":"의료·간호 서비스","Services to the Health Industry":"헬스케어 지원 서비스","Hospital/Nursing Management":"병원·요양 운영","Engineering & Construction":"엔지니어링·건설","Contract Drilling":"계약 시추","Environmental Services":"환경 서비스","Oilfield Services/Equipment":"유전 서비스·장비","Oil & Gas Pipelines":"석유·가스 파이프라인","Trucks/Construction/Farm Machinery":"트럭·건설·농기계","Industrial Machinery":"산업 기계","Electrical Products":"전기 제품","Building Products":"건축 자재","Industrial Conglomerates":"복합 기업","Auto Parts: OEM":"자동차 부품","Oil & Gas Production":"석유·가스 생산","Integrated Oil":"종합 석유","Oil Refining/Marketing":"정유·판매","Homebuilding":"주택 건설","Motor Vehicles":"자동차","Tools & Hardware":"공구·철물","Recreational Products":"레저 용품","Investment Trusts/Mutual Funds":"투자신탁·펀드","Food: Major Diversified":"식품(종합)","Household/Personal Care":"생활·개인용품","Food: Meat/Fish/Dairy":"육류·수산·유제품","Tobacco":"담배","Apparel/Footwear":"의류·신발","Food: Specialty/Candy":"특수식품·캔디","Beverages: Non-Alcoholic":"음료(비알코올)","Beverages: Alcoholic":"주류","Chemicals: Agricultural":"농업 화학","Industrial Specialties":"산업 특수소재","Chemicals: Specialty":"특수 화학","Containers/Packaging":"용기·포장","Chemicals: Major Diversified":"종합 화학","Pulp & Paper":"펄프·제지","Agricultural Commodities/Milling":"농산물·제분","Other Metals/Minerals":"기타 금속·광물","Construction Materials":"건설 자재","Precious Metals":"귀금속","Steel":"철강","Airlines":"항공","Trucking":"트럭 운송","Railroads":"철도","Air Freight/Couriers":"항공화물·택배","Other Transportation":"기타 운송","Specialty Telecommunications":"특수 통신","Wireless Telecommunications":"무선 통신"};
const $=id=>document.getElementById(id);
const root=$('hm'),box=$('hmbox'),st=$('hmst'),tip=$('hmtip'),lst=$('hmlist'),gsel=$('hmg'),ssel=$('hms');
if(!root)return;
const Q_URL='https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json&events=1&symbols=';
const all=[];Object.keys(DATA).forEach(s=>DATA[s].forEach(t=>all.push({t,g:s})));
const Q={},META={};let lastOk=0,session='',mode='si',secF='',view='map',hasTV=false;
const openSet=new Set();
try{mode=localStorage.getItem('hmMode')||mode;view=localStorage.getItem('hmView')||view;}catch(e){}
all.forEach(o=>{META[o.t]={l:null,s:GICS[o.g]||o.g,i:''};});
gsel.value=mode;
// ---- 색: 등락률 구간별로 진하기가 달라짐 (±1.5 / ±3.5 / ±5.5 기준) ----
const POS=[[0,[60,64,72]],[1.5,[38,106,92]],[3.5,[16,150,118]],[5.5,[0,200,140]]],NEG=[[0,[60,64,72]],[1.5,[124,50,60]],[3.5,[192,44,60]],[5.5,[255,66,82]]];
function color(c){if(Math.abs(c)<0.005)return 'rgb(60,64,72)';const S=c>0?POS:NEG,a=Math.abs(c);let k=1;while(k<S.length-1&&a>S[k][0])k++;const p=S[k-1],q=S[k],t=Math.min(1,(a-p[0])/(q[0]-p[0]));return 'rgb('+[0,1,2].map(i=>Math.round(p[1][i]+(q[1][i]-p[1][i])*t)).join(',')+')';}
$('hmlg').innerHTML=[-5.5,-3.5,-1.5,0,1.5,3.5,5.5].map(v=>'<span><i style="background:'+color(v)+'"></i>'+(v>0?'+':'')+v+'%</span>').join('');
const num=v=>parseFloat(String(v).replace(/[%,+$]/g,''));
function cap(v){if(!v)return 0;const m=String(v).match(/^([\d.,]+)\s*([TBM]?)/i);if(!m)return 0;return parseFloat(m[1].replace(/,/g,''))*({T:1e12,B:1e9,M:1e6}[m[2].toUpperCase()]||1);}
const sum=a=>a.reduce((x,y)=>x+y.v,0),desc=(a,b)=>b.v-a.v,fc=c=>(c>=0?'+':'')+c.toFixed(2)+'%';
const logo=t=>{const l=META[t]&&META[t].l;return l?'https://s3-symbol-logo.tradingview.com/'+l+'--big.svg':'';};
// ---- 트리맵 ----
function sq(items,x,y,w,h){const res=[];const tot=items.reduce((a,b)=>a+b.v,0);if(!tot||w<=0||h<=0)return res;const sc=w*h/tot;const arr=items.map(i=>({i,a:i.v*sc}));
const worst=(r,s)=>{const sm=r.reduce((a,b)=>a+b.a,0),mx=Math.max(...r.map(z=>z.a)),mn=Math.min(...r.map(z=>z.a));return Math.max(s*s*mx/(sm*sm),sm*sm/(s*s*mn));};
let k=0;while(k<arr.length){const s=Math.min(w,h);let row=[arr[k]];k++;while(k<arr.length){const t=row.concat(arr[k]);if(worst(t,s)<=worst(row,s)){row=t;k++;}else break;}
const sm=row.reduce((a,b)=>a+b.a,0);if(w>=h){const cw=sm/h;let cy=y;row.forEach(r=>{const ch=r.a/cw;res.push({i:r.i,x,y:cy,w:cw,h:ch});cy+=ch;});x+=cw;w-=cw;}else{const rh=sm/w;let cx=x;row.forEach(r=>{const cw=r.a/rh;res.push({i:r.i,x:cx,y,w:cw,h:rh});cx+=cw;});y+=rh;h-=rh;}}
return res;}
function tree(forceInd){const st0=all.filter(o=>Q[o.t]&&Q[o.t].v).map(o=>({t:o.t,v:Q[o.t].v,c:Q[o.t].c}));
const f=secF?st0.filter(x=>META[x.t].s===secF):st0;const m=forceInd||mode;
if(m==='n')return f.sort(desc);
const bs={};f.forEach(x=>{const s=META[x.t].s;(bs[s]=bs[s]||[]).push(x);});
return Object.keys(bs).map(s=>{const a=bs[s];let kids;
if(m==='si'&&a.some(x=>META[x.t].i)){const bi={};a.forEach(x=>{const i=META[x.t].i||'기타';(bi[i]=bi[i]||[]).push(x);});kids=Object.keys(bi).map(i=>({name:i,v:sum(bi[i]),kids:bi[i].sort(desc)})).sort(desc);}else kids=a.sort(desc);
return {name:s,v:sum(a),kids};}).sort(desc);}
function lay(items,x,y,w,h,d,out){sq(items,x,y,w,h).forEach(r=>{const n=r.i;if(n.t){out.c.push({n,x:r.x,y:r.y,w:r.w,h:r.h});return;}
const hh=(r.h>(d?12:15)+26&&r.w>50)?(d?12:15):0;if(hh)out.h.push({n,d,x:r.x,y:r.y,w:r.w,hh});lay(n.kids,r.x+1,r.y+hh+1,r.w-2,r.h-hh-2,d+1,out);});}
function cellHTML(o,b){const w=b.w,h=b.h,lg=logo(o.t);let tx='';
if(w>=24&&h>=15){let ls=0;if(lg&&w>=44&&h>=50)ls=Math.max(14,Math.min(42,w*0.42,h*0.36));const ah=h-(ls?ls+6:0);
const fs=Math.max(8,Math.min(26,w/Math.max(o.t.length*0.68,ah>=34&&w>=34?4.6:0),ah>=34?ah/2.5:ah/1.5));
if(ls)tx+='<img src="'+lg+'" width="'+ls.toFixed(0)+'" height="'+ls.toFixed(0)+'" alt="" onerror="this.remove()">';
if(!ls||ah>=16)tx+='<b style="font-size:'+fs.toFixed(1)+'px">'+o.t+'</b>';
if(ah>=34&&w>=34)tx+='<i style="font-size:'+Math.max(8,fs*0.72).toFixed(1)+'px">'+fc(o.c)+'</i>';}
return '<div class="hc" data-t="'+o.t+'" style="left:'+b.x.toFixed(1)+'px;top:'+b.y.toFixed(1)+'px;width:'+Math.max(w-1,0).toFixed(1)+'px;height:'+Math.max(h-1,0).toFixed(1)+'px;background:'+color(o.c)+'">'+tx+'</div>';}
function drawMap(){const W=box.clientWidth,H=box.clientHeight;if(!W||!H)return;const out={c:[],h:[]};lay(tree(),0,0,W,H,0,out);
let h='';out.h.forEach(o=>{h+='<div class="hs d'+o.d+'"'+(o.d?'':' data-sec="'+o.n.name+'"')+' style="left:'+o.x.toFixed(1)+'px;top:'+o.y.toFixed(1)+'px;width:'+o.w.toFixed(1)+'px">'+o.n.name+'</div>';});
out.c.forEach(b=>{h+=cellHTML(b.n,b);});box.innerHTML=h;}
// ---- 목록 ----
function avg(a){const v=sum(a);return v?a.reduce((s,x)=>s+x.c*x.v,0)/v:0;}
function leaves(n){return n.t?[n]:[].concat(...n.kids.map(leaves));}
function row(o){const q=Q[o.t],lg=logo(o.t);return '<div class="lr" data-t="'+o.t+'">'+(lg?'<img src="'+lg+'" width="20" height="20" alt="" onerror="this.style.visibility=\'hidden\'">':'<span class="lgx"></span>')+'<b>'+o.t+'</b><span class="nm">'+q.nm+'</span><span class="px">$'+q.l.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})+'</span><em class="'+(o.c>=0?'up':'down')+'">'+fc(o.c)+'</em><span class="cp">'+(q.cap||'-')+'</span></div>';}
function sumHTML(key,name,n,c,cls){return '<summary><span class="ln">'+name+'</span><span class="lcn">'+n+'개</span><em class="'+(c>=0?'up':'down')+'">'+fc(c)+'</em></summary>';}
function drawList(){const T=tree(hasTV?'si':'s');let h='';
T.forEach(s=>{const L=leaves(s),ks=s.name,op=openSet.has(ks)||secF;h+='<details class="ls" data-k="'+ks+'"'+(op?' open':'')+'>'+sumHTML(ks,s.name,L.length,avg(L));
s.kids.forEach(k=>{if(k.t){h+=row(k);return;}const kk=ks+'|'+k.name;h+='<details class="li" data-k="'+kk+'"'+(openSet.has(kk)?' open':'')+'>'+sumHTML(kk,k.name,k.kids.length,avg(k.kids));k.kids.forEach(x=>{h+=row(x);});h+='</details>';});h+='</details>';});
lst.innerHTML=h||'<div class="hmempty">불러오는 중…</div>';}
lst.addEventListener('toggle',e=>{const d=e.target;if(d.dataset&&d.dataset.k){d.open?openSet.add(d.dataset.k):openSet.delete(d.dataset.k);}},true);
function draw(){fillSel();if(view==='list'){box.hidden=true;lst.hidden=false;drawList();}else{lst.hidden=true;box.hidden=false;drawMap();}
document.querySelectorAll('.hmvw .pill').forEach(b=>b.classList.toggle('on',b.dataset.v===view));}
function fillSel(){const cur=ssel.value;const secs=[...new Set(all.filter(o=>Q[o.t]).map(o=>META[o.t].s))];const sig=secs.sort().join('|');if(ssel.dataset.sig===sig)return;ssel.dataset.sig=sig;ssel.innerHTML='<option value="">전체</option>'+secs.map(s=>'<option value="'+s+'">'+s+'</option>').join('');ssel.value=secs.indexOf(secF)>=0?secF:'';if(ssel.value!==secF)secF='';}
// ---- 시세 ----
async function load(){try{const syms=all.map(o=>o.t),parts=[];for(let i=0;i<syms.length;i+=100)parts.push(syms.slice(i,i+100));
const res=await Promise.all(parts.map(p=>fetch(Q_URL+p.map(encodeURIComponent).join('|'),{cache:'no-store'}).then(r=>r.json()).then(j=>[].concat(j.FormattedQuoteResult.FormattedQuote||[]))));
let n=0,ses={};res.forEach(a=>a.forEach(q=>{if(q.last==null)return;let L=num(q.last),pv=num(q.previous_day_closing),C=num(q.change_pct),s=q.curmktstatus;
const e=q.ExtendedMktQuote;if(s!=='REG_MKT'&&e&&e.last){const el=num(e.last);if(!isNaN(el)){L=el;C=num(e.change_pct);}}
if(isNaN(C)&&pv)C=(L-pv)/pv*100;if(isNaN(L)||isNaN(C))return;Q[q.symbol]={v:cap(q.mktcapView),c:C,l:L,nm:q.name||q.symbol,cap:q.mktcapView,s:s};ses[s]=(ses[s]||0)+1;n++;}));
if(n>50){lastOk=Date.now();const top=Object.keys(ses).sort((a,b)=>ses[b]-ses[a])[0];session=top==='REG_MKT'?'정규장':top==='PRE_MKT'?'프리마켓':top==='POST_MKT'?'애프터마켓':'장 마감';draw();stamp();}}catch(e){stamp(true);}}
function stamp(err){const t=lastOk?new Date(lastOk).toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}):'--';st.innerHTML=(err?'<span class="dn">연결 지연 · 재시도 중</span> · ':'')+'<span class="live"></span>'+session+' · 1분마다 갱신 · 마지막 '+t;}
// ---- 트레이딩뷰 분류·로고 (하루 한 번만 받아 브라우저에 저장) ----
async function loadMeta(){let M=null;try{const c=JSON.parse(localStorage.getItem('hmMeta4')||'null');if(c&&Date.now()-c.ts<6048e5)M=c.m;}catch(e){}
if(!M){try{const body={filter:[{left:'name',operation:'in_range',right:all.map(o=>o.t)},{left:'type',operation:'equal',right:'stock'},{left:'exchange',operation:'in_range',right:['NASDAQ','NYSE','AMEX']}],columns:['name','logoid','industry','sector'],sort:{sortBy:'market_cap_basic',sortOrder:'desc'},range:[0,1000]};
const j=await fetch('https://scanner.tradingview.com/america/scan',{method:'POST',body:JSON.stringify(body)}).then(r=>r.json());M={};j.data.forEach(x=>{const d=x.d;if(!M[d[0]])M[d[0]]=[d[1],d[3],d[2]];});if(Object.keys(M).length<300)M=null;else{try{localStorage.setItem('hmMeta4',JSON.stringify({ts:Date.now(),m:M}));}catch(e){}}}catch(e){M=null;}}
if(!M)return;M.CBOE=M.CBOE||['cboe-global-markets','Finance','Investment Banks/Brokers'];
Object.keys(M).forEach(t=>{if(!META[t])return;const d=M[t];META[t]={l:d[0]||null,s:SEC[d[1]]||d[1]||META[t].s,i:IND[d[2]]||d[2]||''};});hasTV=true;ssel.dataset.sig='';secF='';ssel.value='';draw();}
// ---- 상호작용 ----
function showTip(t,ev){const q=Q[t];if(!q)return;const m=META[t];tip.innerHTML='<b>'+t+'</b> <span>'+q.nm+'</span><br>'+m.s+(m.i?' › '+m.i:'')+' · 시총 '+(q.cap||'-')+'<br><u>$'+q.l.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})+'</u> <em class="'+(q.c>=0?'up':'down')+'">'+fc(q.c)+'</em>';tip.style.display='block';
const r=root.getBoundingClientRect(),tw=tip.offsetWidth,th=tip.offsetHeight;let x=ev.clientX-r.left+14,y=ev.clientY-r.top+14;if(x+tw>r.width)x=ev.clientX-r.left-tw-14;if(y+th>r.height)y=ev.clientY-r.top-th-14;tip.style.left=Math.max(0,x)+'px';tip.style.top=Math.max(0,y)+'px';}
box.addEventListener('mousemove',e=>{const c=e.target.closest('.hc');if(c)showTip(c.dataset.t,e);else tip.style.display='none';});
box.addEventListener('mouseleave',()=>tip.style.display='none');
box.addEventListener('click',e=>{const s=e.target.closest('.hs[data-sec]');if(s){secF=secF?'':s.dataset.sec;ssel.value=secF;tip.style.display='none';draw();return;}const c=e.target.closest('.hc');if(c)showTip(c.dataset.t,e);else tip.style.display='none';});
gsel.addEventListener('change',()=>{mode=gsel.value;try{localStorage.setItem('hmMode',mode)}catch(e){}draw();});
ssel.addEventListener('change',()=>{secF=ssel.value;draw();});
document.querySelectorAll('.hmvw .pill').forEach(b=>b.addEventListener('click',()=>{view=b.dataset.v;try{localStorage.setItem('hmView',view)}catch(e){}draw();}));
let rt;new ResizeObserver(()=>{clearTimeout(rt);rt=setTimeout(()=>{if(view==='map')drawMap();},120);}).observe(box);
load();loadMeta();setInterval(()=>{if(!document.hidden)load();},60000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)load();});
})();
