"""
Script de atualização do dashboard de taxas de juros.
Busca dados da API do Banco Central e gera o index.html atualizado.
Cobre 3 modalidades: Consignado Público, INSS e Privado.
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from collections import defaultdict
import sys

# ── Configurações ─────────────────────────────────────────────────────────────

SEGMENTO = "PESSOA FÍSICA"

MODALIDADES = {
    "publico": "Crédito pessoal consignado público \u2013 Prefixado",
    "inss":    "Crédito pessoal consignado INSS \u2013 Prefixado",
    "privado": "Crédito pessoal consignado privado \u2013 Prefixado",
}

MODALIDADE_LABELS = {
    "publico": "Consignado Público",
    "inss":    "Consignado INSS",
    "privado": "Consignado Privado",
}

# Players base (aparecem no público — incluídos em todas as abas se tiverem dados)
INSTITUICOES_BASE = {
    "NU FINANCEIRA S.A. CFI":       "Nubank",
    "ITAÚ UNIBANCO S.A.":           "Itaú",
    "CAIXA ECONOMICA FEDERAL":      "Caixa",
    "BCO DO BRASIL S.A.":           "Banco do Brasil",
    "BCO COOPERATIVO SICREDI S.A.": "Sicredi",
    "BCO ARBI S.A.":                "Banco Arbi",
    "BANCO INTER":                  "Banco Inter",
    "BANCOSEGURO S.A.":             "BancoSeguro",
}

CORES_BASE = {
    "Nubank":          "#7F77DD",
    "Itaú":            "#185FA5",
    "Caixa":           "#0F6E56",
    "Banco do Brasil": "#BA7517",
    "Sicredi":         "#1D9E75",
    "Banco Arbi":      "#D85A30",
    "Banco Inter":     "#D4537E",
    "BancoSeguro":     "#888780",
}

CORES_EXTRA = [
    "#639922","#3B6D11","#BA7517","#0C447C","#A32D2D",
    "#533489","#D14520","#0F6E56","#5F5E5A",
]

DATA_FILE = "data.json"

# ── Busca de dados ─────────────────────────────────────────────────────────────

def fetch_bacen(data_inicio: str, data_fim: str) -> list:
    base = "https://olinda.bcb.gov.br/olinda/servico/taxaJuros/versao/v2/odata/TaxasJurosDiariaPorInicioPeriodo"
    url = (
        f"{base}"
        f"?$format=json"
        f"&$top=10000"
        f"&dataInicio={data_inicio}"
        f"&dataFim={data_fim}"
    )
    print(f"  Buscando: {url}")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    all_records = data.get("value", [])
    print(f"  Total recebido: {len(all_records)}")
    return all_records

def build_series_for_modalidade(records: list, modalidade_str: str) -> dict:
    """Filtra registros por modalidade e organiza por instituição → data → taxa."""
    filtered = [
        r for r in records
        if "consignado" in r.get("Modalidade", "").lower()
        and "Prefixado" in r.get("Modalidade", "")
        and "SICA" in r.get("Segmento", "")
        and r.get("Modalidade", "") == modalidade_str
    ]
    series = {}
    for r in filtered:
        inst_raw = r.get("InstituicaoFinanceira", "")
        name = INSTITUICOES_BASE.get(inst_raw, inst_raw)
        date = r.get("InicioPeriodo", "")[:10]
        taxa = r.get("TaxaJurosAoMes")
        if taxa is not None and date:
            if name not in series:
                series[name] = {}
            series[name][date] = float(taxa)
    return series

def get_date_range(months_back: int = 2):
    today = datetime.today()
    start = today - timedelta(days=months_back * 31)
    return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

# ── Persistência ──────────────────────────────────────────────────────────────

def load_historical() -> dict:
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"  Histórico carregado para modalidades: {list(data.keys())}")
        return data
    except FileNotFoundError:
        print("  Nenhum histórico — iniciando do zero.")
        return {}

def merge_series(historical: dict, new_series: dict) -> dict:
    merged = {inst: dict(historical.get(inst, {})) for inst in set(list(historical.keys()) + list(new_series.keys()))}
    new_count = 0
    for inst, dates in new_series.items():
        for date, taxa in dates.items():
            if date not in merged.get(inst, {}):
                new_count += 1
            if inst not in merged:
                merged[inst] = {}
            merged[inst][date] = taxa
    print(f"  Novos registros: {new_count}")
    return merged

def save_historical(all_data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"  data.json salvo.")

# ── Geração do HTML ───────────────────────────────────────────────────────────

def get_color(name: str, used_colors: dict) -> str:
    if name in CORES_BASE:
        return CORES_BASE[name]
    if name not in used_colors:
        idx = len(used_colors)
        used_colors[name] = CORES_EXTRA[idx % len(CORES_EXTRA)]
    return used_colors[name]

def series_to_js(series: dict) -> tuple:
    all_dates = sorted({d for s in series.values() for d in s})
    dates_js = json.dumps(all_dates)
    used_colors = {}
    raw_js_parts = []
    banks_list = []
    for name, data in sorted(series.items(), key=lambda x: (x[0] != "Nubank", x[0])):
        vals = [data.get(d) for d in all_dates]
        vals_js = "[" + ",".join("null" if v is None else str(v) for v in vals) + "]"
        raw_js_parts.append(f"  {json.dumps(name)}: {vals_js}")
        color = get_color(name, used_colors)
        banks_list.append({
            "key": name, "color": color,
            "isNubank": name == "Nubank",
            "ahead": name in {"Sicredi", "Banco Arbi", "Banco Inter", "BancoSeguro"},
        })
    raw_js = "{\n" + ",\n".join(raw_js_parts) + "\n}"
    return dates_js, raw_js, all_dates, json.dumps(banks_list)

def build_periods_js(all_dates: list) -> tuple:
    month_map = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
                 7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
    months_seen = {}
    month_seq = []
    period_labels = []
    for d in all_dates:
        dt = datetime.strptime(d, "%Y-%m-%d")
        key = (dt.year, dt.month)
        if key not in months_seen:
            months_seen[key] = len(month_seq)
            month_seq.append(key)
        period_labels.append(month_map[dt.month])

    parts = []
    for i, (yr, mo) in enumerate(month_seq):
        label = f"{month_map[mo]} {yr}"
        idxs = [j for j, d in enumerate(all_dates)
                if datetime.strptime(d, "%Y-%m-%d").month == mo
                and datetime.strptime(d, "%Y-%m-%d").year == yr]
        parts.append(f'"m{i}": {{ "label": "{label}", "idx": {json.dumps(idxs)} }}')

    all_idxs = list(range(len(all_dates)))
    parts.append(f'"all": {{ "label": "Período completo ({len(all_dates)} pregões)", "idx": {json.dumps(all_idxs)} }}')
    last_month_key = f"m{len(month_seq)-1}"
    return "{" + ", ".join(parts) + "}", json.dumps(period_labels), last_month_key

def build_modal_js(series: dict) -> str:
    dates_js, raw_js, all_dates, banks_js = series_to_js(series)
    periods_js, period_labels_js, default_period = build_periods_js(all_dates)
    return json.dumps({
        "dates": json.loads(dates_js),
        "raw": {k: [series[k].get(d) for d in json.loads(dates_js)] for k in series},
        "banks": json.loads(banks_js),
        "periods": json.loads(periods_js),
        "defaultPeriod": default_period,
    })

def build_html(all_series: dict, generated_at: str) -> str:
    modals_data = {}
    for key, label in MODALIDADE_LABELS.items():
        series = all_series.get(key, {})
        if series:
            modals_data[key] = {
                "label": label,
                "dates": sorted({d for s in series.values() for d in s}),
                "series": series,
            }

    modals_js_parts = []
    for key, md in modals_data.items():
        dates_js, raw_js, all_dates, banks_js = series_to_js(md["series"])
        periods_js, period_labels_js, default_period = build_periods_js(all_dates)
        modals_js_parts.append(
            f'"{key}": {{'
            f'"label": {json.dumps(md["label"])},'
            f'"dates": {dates_js},'
            f'"raw": {raw_js},'
            f'"banks": {banks_js},'
            f'"periods": {periods_js},'
            f'"defaultPeriod": "{default_period}"'
            f'}}'
        )

    modals_js = "{\n" + ",\n".join(modals_js_parts) + "\n}"

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Comparativo de Taxas — Crédito Consignado</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#f5f4f0;--surface:#fff;--surface2:#f0efe9;
  --border:rgba(0,0,0,0.08);--border2:rgba(0,0,0,0.14);
  --text:#1a1a18;--text2:#5a5a56;--text3:#9a9a94;
  --nu:#7F77DD;--nu-light:#EEEDFE;--nu-dark:#534AB7;
  --radius:12px;
}}
body{{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;padding:0 0 4rem}}
header{{background:var(--surface);border-bottom:1px solid var(--border);padding:1.25rem 2rem;display:flex;align-items:center;gap:1rem;position:sticky;top:0;z-index:10}}
.logo{{width:34px;height:34px;background:var(--nu);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:600;color:#fff;flex-shrink:0}}
.header-title{{font-size:14px;font-weight:500}}
.header-sub{{font-size:11px;color:var(--text3);margin-top:1px}}
.header-badge{{margin-left:auto;font-size:11px;font-weight:500;padding:3px 10px;background:var(--nu-light);color:var(--nu-dark);border-radius:20px;white-space:nowrap}}
.modal-tabs{{background:var(--surface);border-bottom:1px solid var(--border);padding:0 2rem;display:flex;gap:0}}
.modal-tab{{font-size:13px;font-weight:500;padding:0.875rem 1.25rem;border:none;background:transparent;color:var(--text3);cursor:pointer;border-bottom:2px solid transparent;transition:all .15s}}
.modal-tab:hover{{color:var(--text2)}}
.modal-tab.active{{color:var(--nu-dark);border-bottom-color:var(--nu)}}
main{{max-width:960px;margin:0 auto;padding:1.75rem 1.5rem}}
.modal-panel{{display:none}}.modal-panel.active{{display:block}}
.hero{{margin-bottom:1.5rem}}
.hero h2{{font-size:22px;font-weight:600;letter-spacing:-0.02em;line-height:1.3}}
.hero p{{font-size:13px;color:var(--text2);margin-top:0.4rem;line-height:1.6}}
.period-tabs{{display:flex;gap:6px;margin-bottom:1.5rem;flex-wrap:wrap}}
.ptab{{font-size:12px;font-family:'DM Sans',sans-serif;padding:5px 14px;border-radius:20px;border:1px solid var(--border2);background:transparent;color:var(--text2);cursor:pointer;transition:all .15s}}
.ptab:hover{{background:var(--surface2)}}
.ptab.active{{background:var(--text);color:#fff;border-color:var(--text)}}
.metric-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:1.5rem}}
@media(max-width:600px){{.metric-grid{{grid-template-columns:repeat(2,1fr)}}}}
.metric-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:1rem 1.1rem}}
.metric-label{{font-size:10px;color:var(--text3);font-weight:500;text-transform:uppercase;letter-spacing:.04em;margin-bottom:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.metric-value{{font-size:24px;font-weight:600;font-family:'DM Mono',monospace;letter-spacing:-0.02em}}
.metric-sub{{font-size:10px;color:var(--text3);margin-top:3px}}
.metric-badge{{display:inline-block;font-size:10px;font-weight:500;padding:2px 7px;border-radius:4px;margin-top:5px}}
.badge-nu{{background:var(--nu-light);color:var(--nu-dark)}}
.badge-warn{{background:#FFF3E0;color:#B45309}}
.badge-danger{{background:#FFEBEE;color:#C62828}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:1.5rem;margin-bottom:1.25rem}}
.card-title{{font-size:14px;font-weight:500;margin-bottom:2px}}
.card-sub{{font-size:12px;color:var(--text3);margin-bottom:1.25rem}}
.legend{{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:1.25rem}}
.legend-item{{display:flex;align-items:center;gap:5px;font-size:11px;color:var(--text2)}}
.legend-dot{{width:10px;height:10px;border-radius:2px;flex-shrink:0}}
.chart-wrap{{position:relative;width:100%;height:280px}}
.rank-row{{display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid var(--border)}}
.rank-row:last-child{{border-bottom:none}}
.rank-num{{font-size:11px;color:var(--text3);width:24px;text-align:right;font-family:'DM Mono',monospace;flex-shrink:0}}
.rank-badge-cell{{width:64px;flex-shrink:0}}
.rank-badge{{font-size:9px;font-weight:600;padding:2px 6px;border-radius:4px;white-space:nowrap}}
.badge-ahead{{background:#E8F5E9;color:#2E7D32}}
.badge-nubank{{background:var(--nu-light);color:var(--nu-dark)}}
.badge-trad{{background:var(--surface2);color:var(--text3)}}
.rank-name{{font-size:13px;font-weight:500;flex:1;min-width:0}}
.rank-name.nu{{color:var(--nu-dark)}}
.rank-bar-wrap{{width:150px;height:6px;background:var(--surface2);border-radius:3px;overflow:hidden;flex-shrink:0}}
.rank-bar{{height:100%;border-radius:3px}}
.rank-val{{font-size:12px;font-weight:500;font-family:'DM Mono',monospace;width:56px;text-align:right;flex-shrink:0}}
.rank-ano{{font-size:11px;color:var(--text3);font-family:'DM Mono',monospace;width:64px;text-align:right;flex-shrink:0}}
@media(max-width:600px){{.rank-bar-wrap,.rank-ano{{display:none}}}}
.insight{{background:#EFF6FF;border:1px solid #BFDBFE;border-radius:var(--radius);padding:1rem 1.25rem;font-size:13px;color:#1E40AF;line-height:1.7}}
.insight strong{{font-weight:600}}
.source{{font-size:11px;color:var(--text3);margin-top:1.5rem;text-align:center;line-height:1.8}}
.source a{{color:var(--text3)}}
</style>
</head>
<body>
<header>
  <div class="logo">TX</div>
  <div>
    <div class="header-title">Comparativo de Taxas de Juros</div>
    <div class="header-sub">Crédito Consignado · Prefixado · Pessoa Física · Bacen</div>
  </div>
  <div class="header-badge">Atualizado em {generated_at}</div>
</header>

<div class="modal-tabs" id="modal-tabs">
  <button class="modal-tab active" onclick="showModal('publico',this)">Consignado Público</button>
  <button class="modal-tab" onclick="showModal('inss',this)">Consignado INSS</button>
  <button class="modal-tab" onclick="showModal('privado',this)">Consignado Privado</button>
</div>

<main>
  <div id="panel-publico" class="modal-panel active"></div>
  <div id="panel-inss" class="modal-panel"></div>
  <div id="panel-privado" class="modal-panel"></div>
  <div class="source">
    Fonte: <a href="https://dadosabertos.bcb.gov.br/dataset/taxas-de-juros-de-operacoes-de-credito" target="_blank">Banco Central do Brasil</a> — Histórico de Taxa de Juros · Gerado em {generated_at}
  </div>
</main>

<script>
const MODALS = {modals_js};
const charts = {{}};

function avg(arr, idxs) {{
  const valid = idxs.map(i => arr[i]).filter(v => v != null);
  return valid.length ? valid.reduce((a,b)=>a+b,0)/valid.length : null;
}}
function toAnn(m) {{ return ((Math.pow(1+m/100,12)-1)*100); }}

function buildPanel(key) {{
  const m = MODALS[key];
  if (!m) return '<div class="hero"><h2>Dados não disponíveis</h2></div>';

  const nuBank = m.banks.find(b => b.isNubank);
  const nuAvg = nuBank ? avg(m.raw[nuBank.key], m.periods[m.defaultPeriod].idx) : null;

  // Metric cards — Nubank + 3 tradicionais
  const metricInsts = ['Nubank','Caixa','Itaú','Banco do Brasil'];
  const metricCards = metricInsts.map(name => {{
    const b = m.banks.find(b => b.key === name);
    if (!b) return '';
    const a = avg(m.raw[name], m.periods[m.defaultPeriod].idx);
    if (a == null) return '';
    const diff = nuAvg != null && name !== 'Nubank' ? `+${{(a-nuAvg).toFixed(2)}} p.p. vs Nu` : (name==='Nubank'?'ranking':null);
    const cls = name==='Nubank'?'badge-nu': a-nuAvg > 0.2 ?'badge-danger':'badge-warn';
    const badge = name==='Nubank'?'Nubank':'';
    return `<div class="metric-card">
      <div class="metric-label">${{name}}</div>
      <div class="metric-value">${{a.toFixed(2)}}%</div>
      <div class="metric-sub">ao mês · média</div>
      ${{diff?`<div class="metric-badge ${{cls}}">${{diff}}</div>`:''}}
    </div>`;
  }}).join('');

  // Legend
  const legend = m.banks.map(b =>
    `<span class="legend-item"><span class="legend-dot" style="background:${{b.color}}"></span>${{b.key}}</span>`
  ).join('');

  // Period tabs
  const ptabs = Object.entries(m.periods).map(([pk, pv], i) =>
    `<button class="ptab${{pk===m.defaultPeriod?' active':''}}" onclick="updatePanel('${{key}}','${{pk}}',this)">${{pv.label}}</button>`
  ).join('');

  return `
    <div class="hero">
      <h2>Onde o Nubank se posiciona no ${{m.label.toLowerCase()}}?</h2>
      <p>Taxas médias por pregão do Bacen · Prefixado · Pessoa Física</p>
    </div>
    <div class="period-tabs" id="ptabs-${{key}}">${{ptabs}}</div>
    <div class="metric-grid" id="metrics-${{key}}">${{metricCards}}</div>
    <div class="card">
      <div class="card-title">Evolução diária da taxa ao mês</div>
      <div class="card-sub">Todos os players com dados nesta modalidade</div>
      <div class="legend">${{legend}}</div>
      <div class="chart-wrap"><canvas id="chart-${{key}}"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">Ranking por taxa média</div>
      <div class="card-sub" id="rank-sub-${{key}}">${{m.periods[m.defaultPeriod].label}} — menor taxa = mais competitivo</div>
      <div id="ranking-${{key}}"></div>
    </div>
    <div class="insight" id="insight-${{key}}"></div>`;
}}

function buildChart(key) {{
  const m = MODALS[key];
  if (!m) return;
  const period = getCurrentPeriod(key);
  const idxs = m.periods[period].idx;
  const ctx = document.getElementById('chart-'+key).getContext('2d');
  if (charts[key]) charts[key].destroy();
  charts[key] = new Chart(ctx, {{
    type:'line',
    data:{{
      labels: idxs.map(i => m.dates[i].slice(5)),
      datasets: m.banks.map(b => ({{
        label: b.key,
        data: idxs.map(i => m.raw[b.key] ? m.raw[b.key][i] : null),
        borderColor: b.color, backgroundColor: b.color+'18',
        borderWidth: b.isNubank?2.5:1.5,
        pointRadius: b.isNubank?4:2,
        pointBackgroundColor: b.color,
        tension:0.3, fill:false, spanGaps:true,
      }}))
    }},
    options:{{
      responsive:true, maintainAspectRatio:false,
      interaction:{{mode:'index',intersect:false}},
      plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:c=>` ${{c.dataset.label}}: ${{c.parsed.y!=null?c.parsed.y.toFixed(2)+'% a.m.':'—'}}`}}}}}},
      scales:{{
        x:{{grid:{{color:'rgba(0,0,0,0.04)'}},ticks:{{font:{{size:10,family:'DM Mono'}},color:'#9a9a94',maxTicksLimit:15}}}},
        y:{{grid:{{color:'rgba(0,0,0,0.04)'}},ticks:{{font:{{size:10,family:'DM Mono'}},color:'#9a9a94',callback:v=>v.toFixed(2)+'%'}}}}
      }}
    }}
  }});
}}

function buildRanking(key, period) {{
  const m = MODALS[key];
  if (!m) return;
  const idxs = m.periods[period].idx;
  document.getElementById('rank-sub-'+key).textContent = m.periods[period].label + ' — menor taxa = mais competitivo';
  const ranked = m.banks.map(b => ({{...b, avg:avg(m.raw[b.key],idxs), ann:toAnn(avg(m.raw[b.key],idxs))}}))
    .filter(b => b.avg!=null).sort((a,b)=>a.avg-b.avg);
  const min=ranked[0]?.avg, max=ranked[ranked.length-1]?.avg, range=max-min;
  const list = document.getElementById('ranking-'+key);
  list.innerHTML = '';
  ranked.forEach((b,i) => {{
    const pct = range>0?(b.avg-min)/range:0;
    const bw = Math.round(10+pct*88);
    let bHtml,bCls;
    if(b.isNubank){{bHtml='Nubank ★';bCls='badge-nubank';}}
    else if(b.ahead){{bHtml='à frente';bCls='badge-ahead';}}
    else{{bHtml='tradicional';bCls='badge-trad';}}
    const div=document.createElement('div');
    div.className='rank-row';
    div.innerHTML=`<span class="rank-num">#${{i+1}}</span>
      <span class="rank-badge-cell"><span class="rank-badge ${{bCls}}">${{bHtml}}</span></span>
      <span class="rank-name${{b.isNubank?' nu':''}}">${{b.key}}</span>
      <div class="rank-bar-wrap"><div class="rank-bar" style="width:${{bw}}%;background:${{b.color}}${{b.isNubank?'':'99'}}"></div></div>
      <span class="rank-val">${{b.avg.toFixed(2)}}%</span>
      <span class="rank-ano">${{b.ann.toFixed(1)}}% a.a.</span>`;
    list.appendChild(div);
  }});
}}

function buildMetrics(key, period) {{
  const m = MODALS[key];
  if (!m) return;
  const idxs = m.periods[period].idx;
  const nuAvg = avg(m.raw['Nubank'], idxs);
  const metricInsts = ['Nubank','Caixa','Itaú','Banco do Brasil'];
  const g = document.getElementById('metrics-'+key);
  if (!g) return;
  g.innerHTML = metricInsts.map(name => {{
    const a = avg(m.raw[name], idxs);
    if (a==null) return '';
    const diff = nuAvg!=null && name!=='Nubank' ? `+${{(a-nuAvg).toFixed(2)}} p.p. vs Nu` : null;
    const cls = name==='Nubank'?'badge-nu': (a-nuAvg)>0.2?'badge-danger':'badge-warn';
    return `<div class="metric-card">
      <div class="metric-label">${{name}}</div>
      <div class="metric-value">${{a.toFixed(2)}}%</div>
      <div class="metric-sub">ao mês · média</div>
      ${{diff?`<div class="metric-badge ${{cls}}">${{diff}}</div>`:''}}
    </div>`;
  }}).join('');
}}

function buildInsight(key, period) {{
  const m = MODALS[key];
  if (!m) return;
  const idxs = m.periods[period].idx;
  const nu = avg(m.raw['Nubank'], idxs);
  const bb = avg(m.raw['Banco do Brasil'], idxs);
  const cx = avg(m.raw['Caixa'], idxs);
  const el = document.getElementById('insight-'+key);
  if (!el || nu==null) return;
  const ranked = m.banks.map(b=>({...b,a:avg(m.raw[b.key],idxs)})).filter(b=>b.a!=null).sort((a,b)=>a.a-b.a);
  const nuPos = ranked.findIndex(b=>b.isNubank)+1;
  const ahead = ranked.filter((b,i)=>i<nuPos-1).map(b=>b.key).join(', ');
  el.innerHTML = `<strong>${{m.label}} · ${{m.periods[period].label}}:</strong> Nubank em <strong>#${{nuPos}}º lugar</strong> com média de <strong>${{nu.toFixed(2)}}% a.m.</strong>${{ahead?` À sua frente: ${{ahead}}.`:''}}${{cx?` Caixa cobra ${{(cx-nu).toFixed(2)}} p.p. a mais.`:''}}${{bb?` Banco do Brasil cobra ${{(bb-nu).toFixed(2)}} p.p. a mais (~${{(toAnn(bb)-toAnn(nu)).toFixed(1)}} p.p. ao ano).`:''}}`;
}}

const panelPeriods = {{}};
function getCurrentPeriod(key) {{
  return panelPeriods[key] || MODALS[key]?.defaultPeriod;
}}

function updatePanel(key, period, el) {{
  panelPeriods[key] = period;
  document.querySelectorAll('#ptabs-'+key+' .ptab').forEach(t=>t.classList.remove('active'));
  if(el) el.classList.add('active');
  buildChart(key);
  buildRanking(key, period);
  buildMetrics(key, period);
  buildInsight(key, period);
}}

function showModal(key, el) {{
  document.querySelectorAll('.modal-tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.modal-panel').forEach(p=>p.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('panel-'+key).classList.add('active');
  if (!charts[key]) {{
    const period = getCurrentPeriod(key);
    buildRanking(key, period);
    buildInsight(key, period);
    setTimeout(()=>buildChart(key), 50);
  }}
}}

// Init all panels
Object.keys(MODALS).forEach(key => {{
  document.getElementById('panel-'+key).innerHTML = buildPanel(key);
}});
// Build initial chart for first tab
setTimeout(()=>buildChart('publico'), 50);
const initPeriod = MODALS['publico']?.defaultPeriod;
if(initPeriod) {{ buildRanking('publico', initPeriod); buildInsight('publico', initPeriod); }}
</script>
</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== Atualizando dashboard de taxas de juros ===")

    # 1. Carrega histórico
    historical_all = load_historical()

    # 2. Busca dados novos
    data_inicio, data_fim = get_date_range(months_back=2)
    print(f"Buscando: {data_inicio} → {data_fim}")
    try:
        records = fetch_bacen(data_inicio, data_fim)
    except Exception as e:
        print(f"ERRO: {e}", file=sys.stderr)
        records = []

    # 3. Processa cada modalidade
    all_series = {}
    for key, modalidade_str in MODALIDADES.items():
        print(f"\n--- {MODALIDADE_LABELS[key]} ---")
        new_series = build_series_for_modalidade(records, modalidade_str)
        print(f"  Novos registros da API: {sum(len(v) for v in new_series.values())}")
        hist = historical_all.get(key, {})
        merged = merge_series(hist, new_series)
        all_series[key] = merged
        for name, data in merged.items():
            if data:
                print(f"  {name}: {len(data)} pregões | {min(data)} → {max(data)}")

    # 4. Salva histórico
    save_historical(all_series)

    # 5. Gera HTML
    generated_at = datetime.today().strftime("%d/%m/%Y")
    html = build_html(all_series, generated_at)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nindex.html gerado ({len(html):,} bytes).")


if __name__ == "__main__":
    main()
