(function(){
const C=[...document.querySelectorAll('.tcard[data-q]')];if(!C.length)return;
const U='https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json&events=1&symbols='+C.map(c=>encodeURIComponent(c.dataset.q)).join('|');
const num=v=>parseFloat(String(v).replace(/[%,+$]/g,''));
const fmt=v=>v<1000?'$'+v.toFixed(2):'$'+Math.round(v).toLocaleString('en-US');
async function upd(){try{const j=await (await fetch(U,{cache:'no-store'})).json();const Q={};[].concat(j.FormattedQuoteResult.FormattedQuote||[]).forEach(q=>Q[q.symbol]=q);
C.forEach(c=>{const q=Q[c.dataset.q];if(!q||q.last==null)return;let L=num(q.last),P=num(q.change_pct);const e=q.ExtendedMktQuote;if(q.curmktstatus!=='REG_MKT'&&e&&e.last){L=num(e.last);P=num(e.change_pct);}
if(isNaN(L))return;if(isNaN(P)){const pv=num(q.previous_day_closing);P=pv?(L-pv)/pv*100:0;}
const px=c.querySelector('.tl-px');if(!px)return;px.firstChild.nodeValue=fmt(L)+' ';const s=px.querySelector('span');s.textContent=(P>=0?'+':'')+P.toFixed(2)+'%';s.className=P>0?'up':P<0?'down':'';});}catch(e){}}
upd();setInterval(()=>{if(!document.hidden)upd();},60000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)upd();});
})();
