var currentLang = 'pt';

var TRANSLATIONS = {
  pt: {
    // Header
    'header-title': 'Comparativo de Taxas de Juros',
    'header-sub': 'Crédito Consignado · Prefixado · Pessoa Física · Bacen',
    // Hero
    'hero-pub': 'Onde o Nubank se posiciona no consignado público?',
    'hero-pub-sub': 'Dados diários do Bacen · Prefixado · Pessoa Física',
    'hero-inss': 'Onde o Nubank se posiciona no consignado inss?',
    'hero-inss-sub': 'Dados do Bacen · Prefixado · Pessoa Física',
    'hero-priv': 'Onde o Nubank se posiciona no consignado privado?',
    'hero-priv-sub': 'Dados do Bacen · Prefixado · Pessoa Física',
    // Chart titles
    'chart-title-pub': 'Evolução diária da taxa ao mês',
    'chart-sub-pub': 'Todos os players · menor taxa = mais competitivo',
    'chart-title-mon': 'Evolução da taxa ao mês',
    'chart-sub-mon': 'Nubank + players mais próximos · menor taxa = mais competitivo',
    // Ranking
    'ranking-title-pub': 'Ranking por taxa média',
    'ranking-title-mon': 'Ranking completo',
    // Period labels
    'media-periodo': 'Média do período',
    // Metric card sub
    'ao-mes': 'ao mês · média',
    'ao-mes-short': 'ao mês',
    // Badges
    'tradicional': 'tradicional',
    'fintech': 'fintech',
    'cooperativa': 'cooperativa',
    'financeira': 'financeira',
    'especializado': 'especializado',
    // Footer
    'footer': 'Fonte: Banco Central do Brasil — Histórico de Taxa de Juros · Gerado em ',
    // Insight prefix
    'insight-menor': 'menor taxa = mais competitivo',
    // Search
    'search-placeholder': 'Buscar banco...',
    // Lock screen
    'lock-title': 'Acesso restrito',
    'lock-sub': 'Insira a senha para continuar',
    'lock-btn': 'Entrar',
    'lock-error': 'Senha incorreta. Tente novamente.',
    'lock-placeholder': 'Senha',
  },
  en: {
    'header-title': 'Interest Rate Comparison',
    'header-sub': 'Payroll Credit · Fixed Rate · Individuals · Bacen',
    'hero-pub': 'Where does Nubank stand in public payroll credit?',
    'hero-pub-sub': 'Daily Bacen data · Fixed rate · Individuals',
    'hero-inss': 'Where does Nubank stand in INSS payroll credit?',
    'hero-inss-sub': 'Bacen data · Fixed rate · Individuals',
    'hero-priv': 'Where does Nubank stand in private payroll credit?',
    'hero-priv-sub': 'Bacen data · Fixed rate · Individuals',
    'chart-title-pub': 'Daily rate evolution (monthly)',
    'chart-sub-pub': 'All players · lower rate = more competitive',
    'chart-title-mon': 'Rate evolution (monthly)',
    'chart-sub-mon': 'Nubank + closest players · lower rate = more competitive',
    'ranking-title-pub': 'Average rate ranking',
    'ranking-title-mon': 'Full ranking',
    'media-periodo': 'Period average',
    'ao-mes': 'per month · avg',
    'ao-mes-short': 'per month',
    'tradicional': 'traditional',
    'fintech': 'fintech',
    'cooperativa': 'cooperative',
    'financeira': 'financial',
    'especializado': 'specialized',
    'footer': 'Source: Brazilian Central Bank — Interest Rate History · Generated on ',
    'insight-menor': 'lower rate = more competitive',
    'search-placeholder': 'Search bank...',
    'lock-title': 'Restricted access',
    'lock-sub': 'Enter password to continue',
    'lock-btn': 'Enter',
    'lock-error': 'Incorrect password. Please try again.',
    'lock-placeholder': 'Password',
  }
};

function t(key) {
  return (TRANSLATIONS[currentLang] || TRANSLATIONS['pt'])[key] || key;
}

function toggleLang() {
  currentLang = currentLang === 'pt' ? 'en' : 'pt';
  var btn = document.getElementById('lang-btn');
  if (btn) btn.textContent = currentLang === 'pt' ? 'EN' : 'PT';

  // Update static header elements
  applyLangToStatic();

  // Re-render active panel
  var activePanel = document.querySelector('.panel.active');
  if (activePanel) {
    var key = activePanel.id.replace('p-', '');
    if (key === 'publico') {
      initPublico();
    } else {
      var data = key === 'inss' ? INSS : PRIVADO;
      initMonthly(key, data);
    }
  }

  // Update modal tab labels
  document.querySelectorAll('.mtab[data-pt]').forEach(function(btn) {
    btn.textContent = currentLang === 'pt' ? btn.getAttribute('data-pt') : btn.getAttribute('data-en');
  });

  // Update period tabs
  updatePeriodTabLabels();
}

function applyLangToStatic() {
  var ht = document.querySelector('.ht');
  if (ht) ht.textContent = t('header-title');
  var hs = document.querySelector('.hs');
  if (hs) hs.textContent = t('header-sub');
  var footer = document.querySelector('.source');
  if (footer) {
    var link = footer.querySelector('a');
    var linkHtml = link ? link.outerHTML : '';
    footer.innerHTML = t('footer') + '<br>' + linkHtml;
  }
  // Update search placeholders
  document.querySelectorAll('input[placeholder]').forEach(function(inp) {
    if (inp.type === 'text') inp.placeholder = t('search-placeholder');
  });
}

function updatePeriodTabLabels() {
  document.querySelectorAll('.ptab[data-period]').forEach(function(btn) {
    var orig = btn.getAttribute('data-label') || btn.textContent;
    btn.setAttribute('data-label', orig);
    btn.textContent = translatePeriodLabel(orig);
  });
}

// ── Password / lock screen ────────────────────────────────────────────────────
function checkPwd(){
  var v=document.getElementById('pwd-input').value;
  if(v==='juros'){
    document.getElementById('lock-screen').style.display='none';
    sessionStorage.setItem('auth','1');
  } else {
    document.getElementById('pwd-error').textContent='Senha incorreta. Tente novamente.';
    document.getElementById('pwd-input').value='';
    document.getElementById('pwd-input').focus();
  }
}
if(sessionStorage.getItem('auth')==='1'){
  document.addEventListener('DOMContentLoaded',function(){
    var ls=document.getElementById('lock-screen');
    if(ls) ls.style.display='none';
  });
}
setTimeout(function(){
  var inp=document.getElementById('pwd-input');
  if(inp) inp.focus();
},100);

function filterRanking(inputEl,listId){
  var q=inputEl.value.toLowerCase().trim();
  var container=document.getElementById(listId);
  if(!container) return;
  container.querySelectorAll('.bar-row').forEach(function(row){
    if(row.hasAttribute('data-nu')){row.style.display='';return;}
    var el=row.querySelector('.bar-name');
    var name=el?(el.textContent||'').toLowerCase():'';
    row.style.display=(!q||name.indexOf(q)>=0)?'':'none';
  });
}
function searchBox(listId){
  return '<div style="margin-bottom:12px"><input type="text" placeholder="Buscar banco..." oninput="filterRanking(this,\''+listId+'\')" style="width:100%;padding:7px 14px;border:0.5px solid var(--border2);border-radius:20px;font-size:12px;font-family:DM Sans,sans-serif;background:var(--surface2);color:var(--text);outline:none" /></div>';
}
function translatePeriodLabel(label) {
  if (currentLang === 'pt') return label;
  var months = {
    'Jan': 'Jan', 'Fev': 'Feb', 'Mar': 'Mar', 'Abr': 'Apr',
    'Mai': 'May', 'Jun': 'Jun', 'Jul': 'Jul', 'Ago': 'Aug',
    'Set': 'Sep', 'Out': 'Oct', 'Nov': 'Nov', 'Dez': 'Dec'
  };
  // Replace Portuguese month abbreviation
  return label.replace(/^(Jan|Fev|Mar|Abr|Mai|Jun|Jul|Ago|Set|Out|Nov|Dez)/, function(m) {
    return months[m] || m;
  }).replace('Média do período', t('media-periodo'));
}
function getBadge(cat){
  var labels = {
    'tradicional': currentLang==='en'?'traditional':'tradicional',
    'fintech': 'fintech',
    'cooperativa': currentLang==='en'?'cooperative':'cooperativa',
    'financeira': currentLang==='en'?'financial':'financeira',
    'especializado': currentLang==='en'?'specialized':'especializado',
  };
  var cls = {'tradicional':'b-trad','fintech':'b-fintech','cooperativa':'b-coop','financeira':'b-fin','especializado':'b-trad'};
  var label = labels[cat] || cat;
  var c = cls[cat] || 'b-trad';
  return '<span class="bar-badge-pill '+c+'">'+label+'</span>';
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
    return'<div class="mc"><div class="ml">'+name+'</div><div class="mv">'+a.toFixed(2)+'%</div><div class="ms">'+t('ao-mes')+'</div>'+(diff?'<div class="mb '+cls+'">'+diff+'</div>':'')+'</div>';
  }).join('');
}

function renderPubRanking(period){
  var m=PUBLICO,idxs=m.periods[period].idx;
  var ranked=m.banks.map(function(b){return{key:b.key,color:b.color,isNubank:b.isNubank,ahead:b.ahead,categoria:b.categoria,avg:avg(m.raw[b.key],idxs)};}).filter(function(b){return b.avg!=null;}).sort(function(a,b){return a.avg-b.avg;});
  var mn=ranked[0].avg,mx=ranked[ranked.length-1].avg,rng=mx-mn;
  var nuPos=ranked.findIndex(function(b){return b.isNubank;})+1;
  var ahead=ranked.filter(function(b,i){return i<nuPos-1;}).map(function(b){return b.key;}).join(', ');
  var rows=ranked.map(function(b,i){
    var pct=rng>0?(b.avg-mn)/rng:0,bw=Math.round(10+pct*88);
    var pill=b.isNubank?'<span class="bar-badge-pill b-nu">Nubank \u2605</span>':getBadge(b.categoria);
    return'<div class="bar-row'+(b.isNubank?' nu-highlight':'')+'" '+(b.isNubank?' data-nu="1" ':'')+' data-name="'+b.key.toLowerCase()+'">'+'<span class="bar-pos">#'+(i+1)+'</span><span class="bar-badge">'+pill+'</span><span class="bar-name'+(b.isNubank?' nu':'')+'">'+b.key+'</span><div class="bar-track"><div class="bar-fill" style="width:'+bw+'%;background:'+b.color+(b.isNubank?'':'99')+'"></div></div><span class="bar-val">'+b.avg.toFixed(2)+'%</span><span class="bar-ano">'+toAnn(b.avg).toFixed(1)+'% a.a.</span></div>';
  }).join('');
  var nu=avg(m.raw['Nubank'],idxs),bb=avg(m.raw['Banco do Brasil'],idxs),cx=avg(m.raw['Caixa'],idxs);
  var ins='<strong>'+m.periods[period].label+':</strong> Nubank em <strong>#'+nuPos+'\u00balugar</strong> com m\u00e9dia de <strong>'+nu.toFixed(2)+'% a.m.</strong>';
  if(ahead)ins+=' \u00c0 sua frente: '+ahead+'.';
  if(cx)ins+=' Caixa cobra '+(cx-nu).toFixed(2)+' p.p. a mais.';
  if(bb)ins+=' Banco do Brasil cobra '+(bb-nu).toFixed(2)+' p.p. a mais (~'+(toAnn(bb)-toAnn(nu)).toFixed(1)+' p.p. ao ano).';
  var sh=searchBox('rank-pub');
  return{rows:sh+rows,rankSub:m.periods[period].label+' \u2014 menor taxa = mais competitivo',ins:ins};
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
  var ptabs=Object.entries(m.periods).map(function(e){var pk=e[0],pv=e[1];return'<button class="ptab" data-period="'+pk+'" onclick="buildPublico(\''+pk+'\')">'+translatePeriodLabel(pv.label)+'</button>';}).join('');
  document.getElementById('p-publico').innerHTML='<div class="hero"><h2>'+t('hero-pub')+'</h2><p>'+t('hero-pub-sub')+'</p></div><div class="ptabs" id="ptabs-pub">'+ptabs+'</div><div class="mgrid" id="metrics-pub"></div><div class="card"><div class="ct">'+t('chart-title-pub')+'</div><div class="cs">'+t('chart-sub-pub')+'</div><div class="legend">'+legend+'</div><div class="cw"><canvas id="chart-pub"></canvas></div></div><div class="card"><div class="ct">'+t('ranking-title-pub')+'</div><div class="cs" id="rank-sub-pub"></div><div id="rank-pub"></div></div><div class="insight" id="ins-pub"></div>';
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
    return'<div class="mc"><div class="ml">'+name+'</div><div class="mv">'+r.rate.toFixed(2)+'%</div><div class="ms">'+t('ao-mes')+'</div>'+(diff?'<div class="mb '+cls+'">'+diff+'</div>':'')+'</div>';
  }).join('');
  var mn=rows.length?rows[0].rate:0,mx=rows.length?rows[rows.length-1].rate:0,rng=mx-mn;
  var barRows=rows.map(function(r){
    var pct=rng>0?(r.rate-mn)/rng:0,bw=Math.round(10+pct*88);
    var pill=r.isNubank?'<span class="bar-badge-pill b-nu">Nubank \u2605</span>':getBadge(r.categoria);
    return'<div class="bar-row'+(r.isNubank?' nu-highlight':'')+'" '+(r.isNubank?' data-nu="1" ':'')+' data-name="'+r.name.toLowerCase()+'">'+'<span class="bar-pos">#'+r.pos+'</span><span class="bar-badge">'+pill+'</span><span class="bar-name'+(r.isNubank?' nu':'')+'">'+r.name+'</span><div class="bar-track"><div class="bar-fill" style="width:'+bw+'%;background:'+r.color+(r.isNubank?'':'99')+'"></div></div><span class="bar-val">'+r.rate.toFixed(2)+'%</span><span class="bar-ano">'+toAnn(r.rate).toFixed(1)+'% a.a.</span></div>';
  }).join('');
  var ahead=rows.filter(function(r){return r.ahead;}).map(function(r){return r.name;}).join(', ');
  var bbRow=rows.find(function(r){return r.name=='Banco do Brasil';});
  var ins='<strong>'+label+' \u00b7 '+data.periods[period].label+':</strong> Nubank em <strong>#'+(nuGlobalPos||'?')+'\u00ba lugar</strong> de '+totalPlayers+' institui\u00e7\u00f5es';
  if(nuRate)ins+=' com taxa de <strong>'+nuRate.toFixed(2)+'% a.m.</strong>';
  if(ahead)ins+=' \u00c0 sua frente: '+ahead+'.';
  if(bbRow&&nuRate)ins+=' Banco do Brasil cobra '+(bbRow.rate-nuRate).toFixed(2)+' p.p. a mais (~'+(toAnn(bbRow.rate)-toAnn(nuRate)).toFixed(1)+' p.p. ao ano).';
  var noteText=key=='inss'?'Dados semanais do Bacen':'Dados semanais \u00b7 taxas no privado s\u00e3o maiores';
  document.getElementById('metrics-'+key).innerHTML=cards;
  document.getElementById('bars-'+key).innerHTML=searchBox('bars-'+key)+barRows;
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
  var ptabs=Object.entries(data.periods).map(function(e){var pk=e[0],pv=e[1];return'<button class="ptab" data-period="'+pk+'" onclick="buildMonthly(\''+key+'\','+key.toUpperCase()+',\''+pk+'\')">'+translatePeriodLabel(pv.label)+'</button>';}).join('');
  document.getElementById('p-'+key).innerHTML=
    '<div class="hero"><h2>'+(key==='inss'?t('hero-inss'):t('hero-priv'))+'</h2><p>'+(key==='inss'?t('hero-inss-sub'):t('hero-priv-sub'))+'</p></div>'+
    '<div class="ptabs" id="ptabs-'+key+'">'+ptabs+'</div>'+
    '<div class="mgrid" id="metrics-'+key+'"></div>'+
    '<div class="card"><div class="ct">'+t('chart-title-mon')+'</div><div class="cs">'+t('chart-sub-mon')+'</div><div class="legend">'+legend+'</div><div class="cw"><canvas id="chart-'+key+'"></canvas></div></div>'+
    '<div class="card"><div class="ct">'+t('ranking-title-mon')+'</div><div class="cs" id="rank-sub-'+key+'"></div><div id="bars-'+key+'"></div></div>'+
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
