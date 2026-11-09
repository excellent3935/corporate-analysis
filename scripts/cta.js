(function(){
const B=document.getElementById('ctaboard');if(!B)return;
const R=[...B.querySelectorAll('tbody tr[data-q]')];if(!R.length)return;
const D=R.map(r=>JSON.parse(r.dataset.c));
const U='https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json&events=1&symbols='+R.map(r=>encodeURIComponent(r.dataset.q)).join('|');
const num=v=>parseFloat(String(v).replace(/[%,+$]/g,''));
const fmt=v=>v<1000?'$'+v.toFixed(2):'$'+Math.round(v).toLocaleString('en-US');
const tag=s=>s>=0.5?'<span class="tag g">매수 '+(s>=0?'+':'')+s.toFixed(2)+'</span>':s>-0.5?'<span class="tag y">중립 '+(s>=0?'+':'')+s.toFixed(2)+'</span>':'<span class="tag b">매도 '+(s>=0?'+':'')+s.toFixed(2)+'</span>';
async function upd(){try{const j=await (await fetch(U,{cache:'no-store'})).json();const Q={};[].concat(j.FormattedQuoteResult.FormattedQuote||[]).forEach(q=>Q[q.symbol]=q);
R.forEach((r,i)=>{const q=Q[r.dataset.q];if(!q||q.last==null)return;let L=num(q.last),P=num(q.change_pct);const e=q.ExtendedMktQuote;if(q.curmktstatus!=='REG_MKT'&&e&&e.last){L=num(e.last);P=num(e.change_pct);}
if(isNaN(L))return;if(isNaN(P)){const pv=num(q.previous_day_closing);P=pv?(L-pv)/pv*100:0;}
const d=D[i],tds=r.children;
tds[1].innerHTML=fmt(L)+'<br><span class="'+(P>0?'up':P<0?'down':'')+'">'+(P>=0?'+':'')+P.toFixed(2)+'%</span>';
if(d.s200)tds[2].textContent=((L/d.s200-1)*100>=0?'+':'')+((L/d.s200-1)*100).toFixed(1)+'%';
const sg=d.s.map(x=>x[1]==null?x[2]:(L>x[1]?1:-1));
tds[3].innerHTML=sg.map((v,k)=>'<i class="'+(v>0?'pg':'pr')+'" title="'+d.s[k][0]+'"></i>').join('');
tds[5].innerHTML=tag(sg.reduce((a,b)=>a+b,0)/sg.length);});}catch(e){}}
upd();setInterval(()=>{if(!document.hidden)upd();},60000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)upd();});
})();
