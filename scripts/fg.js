(function(){
const $=id=>document.getElementById(id);if(!$('fgnum'))return;
const lab=s=>s<25?'극단적 공포':s<45?'공포':s<=55?'중립':s<75?'탐욕':'극단적 탐욕';
const col=s=>s<25?'#dc2626':s<45?'#f97316':s<=55?'#a3a3a3':s<75?'#84cc16':'#16a34a';
const RT={'extreme fear':'극단적 공포','fear':'공포','neutral':'중립','greed':'탐욕','extreme greed':'극단적 탐욕'};
const COMP=[['market_momentum_sp500','시장 모멘텀','S&P500 vs 125일선'],['stock_price_strength','주가 강도','52주 신고가-신저가'],['stock_price_breadth','주가 폭','상승·하락 거래량'],['put_call_options','풋·콜 옵션','5일 평균 비율'],['market_volatility_vix','시장 변동성','VIX vs 50일선'],['junk_bond_demand','정크본드 수요','수익률 스프레드'],['safe_haven_demand','안전자산 수요','주식 vs 국채 수익률']];
function spark(v,w,h,c){const lo=Math.min(...v),hi=Math.max(...v),r=hi-lo||1,p=v.map((x,i)=>[i*w/(v.length-1),h-3-(x-lo)/r*(h-6)]);const d='M'+p.map(a=>a[0].toFixed(1)+','+a[1].toFixed(1)).join(' L');return '<svg class="spk" viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="none"><path d="'+d+' L'+w+','+h+' L0,'+h+' Z" fill="'+c+'" fill-opacity=".08"/><path d="'+d+'" fill="none" stroke="'+c+'" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>';}
async function upd(){try{const j=await (await fetch('https://production.dataviz.cnn.io/index/fearandgreed/graphdata',{cache:'no-store'})).json();const f=j.fear_and_greed;if(!f||f.score==null)return;const s=f.score,c=col(s),L=lab(s);
const t=Math.PI*(1-s/100),n=$('fgneedle');if(n){n.setAttribute('x2',(110+62*Math.cos(t)).toFixed(1));n.setAttribute('y2',(104-62*Math.sin(t)).toFixed(1));}
$('fgnum').innerHTML='<b style="color:'+c+'">'+Math.round(s)+'</b><div style="color:'+c+'">'+L+'</div>';
const h=(j.fear_and_greed_historical&&j.fear_and_greed_historical.data||[]).map(p=>Math.round(p.y)).slice(-70);if(h.length>5)$('fgspk').innerHTML=spark(h,260,46,c);
const rows=[['현재',s],['전일 종가',f.previous_close],['1주 전',f.previous_1_week],['1개월 전',f.previous_1_month],['1년 전',f.previous_1_year]];
$('fghist').innerHTML='<tr><td colspan="3" style="font-weight:700;color:var(--ink)">시점별 비교</td></tr>'+rows.map(r=>'<tr><td>'+r[0]+'</td><td style="text-align:right;font-weight:700">'+Math.round(r[1])+'</td><td style="color:var(--muted)">'+lab(r[1])+'</td></tr>').join('');
$('fgcomp').innerHTML='<tr><td colspan="3" style="font-weight:700;color:var(--ink)">7개 구성 지표</td></tr>'+COMP.map(k=>{const x=j[k[0]]||{},v=Math.round(x.score||0),cc=col(v);return '<tr><td><b>'+k[1]+'</b><br><span style="font-size:12px;color:var(--muted)">'+k[2]+'</span></td><td><span class="bar"><span style="width:'+v+'%;background:'+cc+'"></span></span> '+v+'</td><td style="font-size:12.5px;color:'+cc+';font-weight:700">'+(RT[String(x.rating).toLowerCase()]||'-')+'</td></tr>';}).join('');
const ts=new Date(f.timestamp);$('fgasof').innerHTML='Fear &amp; Greed Index · CNN 기준 '+ts.toLocaleString('ko-KR',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false})+' · <span class="livedot"></span>1분마다 갱신';
}catch(e){}}
upd();setInterval(()=>{if(!document.hidden)upd();},60000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)upd();});
})();
