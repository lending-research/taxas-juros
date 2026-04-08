function getBadge(cat){
  if(cat=='tradicional') return '<span class="bar-badge-pill b-trad">tradicional</span>';
  if(cat=='fintech') return '<span class="bar-badge-pill b-fintech">fintech</span>';
  if(cat=='cooperativa') return '<span class="bar-badge-pill b-coop">cooperativa</span>';
  if(cat=='financeira') return '<span class="bar-badge-pill b-fin">financeira</span>';
  return '<span class="bar-badge-pill b-trad">especializado</span>';
}
const charts={};
function toAnn(m){return((Math.pow(1+m/100,12)-1)*100);}
function avg(arr,idxs){var v=idxs.map(function(i){return arr[i];}).filter(function(x){return x!=null;});return v.length?v.reduce(function(a,b){return a+b;},0)/v.length:null;}

function renderPubMetrics(period){
  var m=PUBLICO,idxs=m.periods[period].idx,nuA=avg(m.raw['Nubank'],idxs);
  var trad=['Nubank','Bradesco','Santander','Caixa','Ita\u00fa','Banco do Brasil'];
  return trad.map(function(name){
    var a=avg(m.raw[name],idxs);if(a==null)return'';
    var diff=name!='Nubank'&&nuA?'+'+(a-nuA).toFixed(2)+' p.p. vs Nu':null;
    var cls=name=='Nubank'?'bnu':(a-nuA>0.2?'bdanger':'bwarn');
    return'<div class="mc"><div class="ml">'+name+'</div><div class="mv">'+a.toFixed(2)+'%</div><div class="ms">ao m\u00eas</div>'+(diff?'<div class="mb '+cls+'">'+diff+'</div>':'')+'</div>';
  }).join('');
}

function renderPubRanking(period){
  var m=PUBLICO,idxs=m.periods[period].idx;
  var ranked=m.banks.map(function(b){return{key:b.key,color:b.color,isNubank:b.isNubank,ahead:b.ahead,avg:avg(m.raw[b.key],idxs)};}).filter(function(b){return b.avg!=null;}).sort(function(a,b){return a.avg-b.avg;});
  var mn=ranked[0].avg,mx=ranked[ranked.length-1].avg,rng=mx-mn;
  var nuPos=ranked.findIndex(function(b){return b.isNubank;})+1;
  var ahead=ranked.filter(function(b,i){return i<nuPos-1;}).map(function(b){return b.key;}).join(', ');
  var rows=ranked.map(function(b,i){
    var pct=rng>0?(b.avg-mn)/rng:0,bw=Math.round(10+pct*88);
    var pill=b.isNubank?'<span class="bar-badge-pill b-nu">Nubank \u2605</span>':b.ahead?'<span class="bar-badge-pill b-ahead">\u00e0 frente</span>':getBadge(b.categoria);
    return'<div class="bar-row'+(b.isNubank?' nu-highlight':'')+'"><span class="bar-pos">#'+(i+1)+'</span><span class="bar-badge">'+pill+'</span><span class="bar-name'+(b.isNubank?' nu':'')+'">'+b.key+'</span><div class="bar-track"><div class="bar-fill" style="width:'+bw+'%;background:'+b.color+(b.isNubank?'':'99')+'"></div></div><span class="bar-val">'+b.avg.toFixed(2)+'%</span><span class="bar-ano">'+toAnn(b.avg).toFixed(1)+'% a.a.</span></div>';
  }).join('');
  var nu=avg(m.raw['Nubank'],idxs),bb=avg(m.raw['Banco do Brasil'],idxs),cx=avg(m.raw['Caixa'],idxs);
  var ins='<strong>'+m.periods[period].label+':</strong> Nubank em <strong>#'+nuPos+'\u00balugar</strong> com m\u00e9dia de <strong>'+nu.toFixed(2)+'% a.m.</strong>';
  if(ahead)ins+=' \u00c0 sua frente: '+ahead+'.';
  if(cx)ins+=' Caixa cobra '+(cx-nu).toFixed(2)+' p.p. a mais.';
  if(bb)ins+=' Banco do Brasil cobra '+(bb-nu).toFixed(2)+' p.p. a mais (~'+(toAnn(bb)-toAnn(nu)).toFixed(1)+' p.p. ao ano).';
  return{rows:rows,rankSub:m.periods[period].label+' \u2014 menor taxa = mais competitivo',ins:ins};
}

function buildPublico(period){
  var m=PUBLICO;
  document.getElementById('metrics-pub').innerHTML=renderPubMetrics(period);
  var rk=renderPubRanking(period);
  document.getElementById('rank-sub-pub').textContent=rk.rankSub;
  document.getElementById('rank-pub').innerHTML=rk.rows;
  document.getElementById('ins-pub').innerHTML=rk.ins;
  document.querySelectorAll('#ptabs-pub .ptab').forEach(function(t){t.classList.remove('active');});
  var tab=document.querySelector('#ptabs-pub [data-period="'+period+'"]');
  if(tab)tab.classList.add('active');
  buildPubChart(period);
}

function buildPubChart(period){
  var m=PUBLICO,idxs=m.periods[period].idx;
  var cb=m.chart_banks||m.banks;
  var ctx=document.getElementById('chart-pub').getContext('2d');
  if(charts.pub)charts.pub.destroy();
  charts.pub=new Chart(ctx,{type:'line',data:{labels:idxs.map(function(i){return m.dates[i].slice(5);}),datasets:cb.map(function(b){return{label:b.key,data:idxs.map(function(i){return m.raw[b.key]?m.raw[b.key][i]:null;}),borderColor:b.color,backgroundColor:b.color+'18',borderWidth:b.isNubank?2.5:1.5,pointRadius:b.isNubank?4:2,pointBackgroundColor:b.color,tension:.3,fill:false,spanGaps:true};})},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:false},tooltip:{callbacks:{label:function(c){return' '+c.dataset.label+': '+(c.parsed.y!=null?c.parsed.y.toFixed(2)+'% a.m.':'--');}}}},scales:{x:{grid:{color:'rgba(0,0,0,0.04)'},ticks:{font:{size:10,family:'DM Mono'},color:'#9a9a94',maxTicksLimit:15}},y:{grid:{color:'rgba(0,0,0,0.04)'},ticks:{font:{size:10,family:'DM Mono'},color:'#9a9a94',callback:function(v){return v.toFixed(2)+'%';}}}}}}); 
}

function initPublico(){
  var m=PUBLICO;
  var cb=m.chart_banks||m.banks;var legend=cb.map(function(b){return'<span class="li"><span class="ld" style="background:'+b.color+'"></span>'+b.key+'</span>';}).join('');
  var ptabs=Object.entries(m.periods).map(function(e){var pk=e[0],pv=e[1];return'<button class="ptab" data-period="'+pk+'" onclick="buildPublico(\''+pk+'\')">'+pv.label+'</button>';}).join('');
  document.getElementById('p-publico').innerHTML='<div class="hero"><h2>Onde o Nubank se posiciona no consignado p\u00fablico?</h2><p>Dados di\u00e1rios do Bacen \u00b7 Prefixado \u00b7 Pessoa F\u00edsica</p></div><div class="ptabs" id="ptabs-pub">'+ptabs+'</div><div class="mgrid" id="metrics-pub"></div><div class="card"><div class="ct">Evolu\u00e7\u00e3o di\u00e1ria da taxa ao m\u00eas</div><div class="cs">Todos os players \u00b7 menor taxa = mais competitivo</div><div class="legend">'+legend+'</div><div class="cw"><canvas id="chart-pub"></canvas></div></div><div class="card"><div class="ct">Ranking por taxa m\u00e9dia</div><div class="cs" id="rank-sub-pub"></div><div id="rank-pub"></div></div><div class="insight" id="ins-pub"></div>';
  buildPublico(m.defaultPeriod);
}

function buildMonthly(key,data,period){
  var pd=data.ranked[period]||{rows:[],nuPos:null,totalPlayers:0};
  var rows=pd.rows||[],nuRow=rows.find(function(r){return r.isNubank;}),nuRate=nuRow?nuRow.rate:null;
  var nuGlobalPos=pd.nuPos,totalPlayers=pd.totalPlayers,label=key=='inss'?'Consignado INSS':'Consignado Privado';
  var always=['Nubank','Bradesco','Santander','Caixa','Ita\u00fa','Banco do Brasil'];
  var cards=always.map(function(name){
    var r=rows.find(function(r){return r.name==name;});if(!r)return'';
    var diff=name!='Nubank'&&nuRate?'+'+(r.rate-nuRate).toFixed(2)+' p.p. vs Nu':null;
    var cls=name=='Nubank'?'bnu':((r.rate-nuRate)>0.5?'bdanger':'bwarn');
    return'<div class="mc"><div class="ml">'+name+'</div><div class="mv">'+r.rate.toFixed(2)+'%</div><div class="ms">ao m\u00eas</div>'+(diff?'<div class="mb '+cls+'">'+diff+'</div>':'')+'</div>';
  }).join('');
  var mn=rows.length?rows[0].rate:0,mx=rows.length?rows[rows.length-1].rate:0,rng=mx-mn;
  var barRows=rows.map(function(r){
    var pct=rng>0?(r.rate-mn)/rng:0,bw=Math.round(10+pct*88);
    var pill=r.isNubank?'<span class="bar-badge-pill b-nu">Nubank \u2605</span>':r.ahead?'<span class="bar-badge-pill b-ahead">\u00e0 frente</span>':getBadge(r.categoria);
    return'<div class="bar-row'+(r.isNubank?' nu-highlight':'')+'"><span class="bar-pos">#'+r.pos+'</span><span class="bar-badge">'+pill+'</span><span class="bar-name'+(r.isNubank?' nu':'')+'">'+r.name+'</span><div class="bar-track"><div class="bar-fill" style="width:'+bw+'%;background:'+r.color+(r.isNubank?'':'99')+'"></div></div><span class="bar-val">'+r.rate.toFixed(2)+'%</span><span class="bar-ano">'+toAnn(r.rate).toFixed(1)+'% a.a.</span></div>';
  }).join('');
  var ahead=rows.filter(function(r){return r.ahead;}).map(function(r){return r.name;}).join(', ');
  var bbRow=rows.find(function(r){return r.name=='Banco do Brasil';});
  var ins='<strong>'+label+' \u00b7 '+data.periods[period].label+':</strong> Nubank em <strong>#'+(nuGlobalPos||'?')+'\u00ba lugar</strong> de '+totalPlayers+' institui\u00e7\u00f5es';
  if(nuRate)ins+=' com taxa de <strong>'+nuRate.toFixed(2)+'% a.m.</strong>';
  if(ahead)ins+=' \u00c0 sua frente: '+ahead+'.';
  if(bbRow&&nuRate)ins+=' Banco do Brasil cobra '+(bbRow.rate-nuRate).toFixed(2)+' p.p. a mais (~'+(toAnn(bbRow.rate)-toAnn(nuRate)).toFixed(1)+' p.p. ao ano).';
  var noteText=key=='inss'?'Dados semanais do Bacen':'Dados semanais \u00b7 taxas no privado s\u00e3o maiores';
  document.getElementById('metrics-'+key).innerHTML=cards;
  document.getElementById('bars-'+key).innerHTML=barRows;
  document.getElementById('rank-sub-'+key).textContent=totalPlayers+' institui\u00e7\u00f5es \u00b7 '+noteText;
  document.getElementById('ins-'+key).innerHTML=ins;
  document.querySelectorAll('#ptabs-'+key+' .ptab').forEach(function(t){t.classList.remove('active');});
  var tab=document.querySelector('#ptabs-'+key+' [data-period="'+period+'"]');
  if(tab)tab.classList.add('active');
  buildMonthlyChart(key,data,period);
}

function buildMonthlyChart(key,data,period){
  if(!data.dates||!data.raw) return;
  var canvasEl=document.getElementById('chart-'+key);
  if(!canvasEl) return;
  var idxs=data.periods[period].idx;
  var cb=data.chart_banks||data.banks||[];
  var ctx=canvasEl.getContext('2d');
  if(charts[key]) charts[key].destroy();
  charts[key]=new Chart(ctx,{type:'line',data:{labels:idxs.map(function(i){return data.dates[i].slice(5);}),datasets:cb.map(function(b){return{label:b.key,data:idxs.map(function(i){return data.raw[b.key]?data.raw[b.key][i]:null;}),borderColor:b.color,backgroundColor:b.color+'18',borderWidth:b.isNubank?2.5:1.5,pointRadius:b.isNubank?4:3,pointBackgroundColor:b.color,tension:.3,fill:false,spanGaps:true};})},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:false},tooltip:{callbacks:{label:function(c){return' '+c.dataset.label+': '+(c.parsed.y!=null?c.parsed.y.toFixed(2)+'% a.m.':'--');}}}},scales:{x:{grid:{color:'rgba(0,0,0,0.04)'},ticks:{font:{size:10,family:'DM Mono'},color:'#9a9a94',maxTicksLimit:15}},y:{grid:{color:'rgba(0,0,0,0.04)'},ticks:{font:{size:10,family:'DM Mono'},color:'#9a9a94',callback:function(v){return v.toFixed(2)+'%';}}}}}});
}

function initMonthly(key,data){
  var label=key=='inss'?'Consignado INSS':'Consignado Privado';
  var cb=data.chart_banks||data.banks||[];
  var legend=cb.map(function(b){return'<span class="li"><span class="ld" style="background:'+b.color+'"></span>'+b.key+'</span>';}).join('');
  var ptabs=Object.entries(data.periods).map(function(e){var pk=e[0],pv=e[1];return'<button class="ptab" data-period="'+pk+'" onclick="buildMonthly(\''+key+'\','+key.toUpperCase()+',\''+pk+'\')">'+pv.label+'</button>';}).join('');
  document.getElementById('p-'+key).innerHTML=
    '<div class="hero"><h2>Onde o Nubank se posiciona no '+label.toLowerCase()+'?</h2><p>Dados do Bacen \u00b7 Prefixado \u00b7 Pessoa F\u00edsica</p></div>'+
    '<div class="ptabs" id="ptabs-'+key+'">'+ptabs+'</div>'+
    '<div class="mgrid" id="metrics-'+key+'"></div>'+
    '<div class="card"><div class="ct">Evolu\u00e7\u00e3o da taxa ao m\u00eas</div><div class="cs">Nubank + players mais pr\u00f3ximos \u00b7 menor taxa = mais competitivo</div><div class="legend">'+legend+'</div><div class="cw"><canvas id="chart-'+key+'"></canvas></div></div>'+
    '<div class="card"><div class="ct">Ranking completo</div><div class="cs" id="rank-sub-'+key+'"></div><div id="bars-'+key+'"></div></div>'+
    '<div class="insight" id="ins-'+key+'"></div>';
  buildMonthly(key,data,data.defaultPeriod);
}

var initialized={};
function showModal(key,el){
  document.querySelectorAll('.mtab').forEach(function(t){t.classList.remove('active');});
  document.querySelectorAll('.panel').forEach(function(p){p.classList.remove('active');});
  el.classList.add('active');
  document.getElementById('p-'+key).classList.add('active');
  if(!initialized[key]){initialized[key]=true;if(key=='publico')initPublico();else if(key=='inss')initMonthly('inss',INSS);else if(key=='privado')initMonthly('privado',PRIVADO);}
}
initPublico();
initialized['publico']=true;
