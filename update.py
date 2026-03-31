"""
Script de atualização do dashboard de taxas de juros.
Busca dados da API do Banco Central e gera o index.html atualizado.
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
import sys

# ── Configurações ────────────────────────────────────────────────────────────

MODALIDADE = "Crédito pessoal consignado público - Prefixado"
SEGMENTO   = "Pessoa Física"

INSTITUICOES = {
    "NU FINANCEIRA S.A. CFI":      "Nubank",
    "ITAÚ UNIBANCO S.A.":          "Itaú",
    "CAIXA ECONOMICA FEDERAL":     "Caixa",
    "BCO DO BRASIL S.A.":          "Banco do Brasil",
    "BCO COOPERATIVO SICREDI S.A.":"Sicredi",
    "BCO ARBI S.A.":               "Banco Arbi",
    "BANCO INTER":                 "Banco Inter",
    "BANCOSEGURO S.A.":            "BancoSeguro",
}

CORES = {
    "Nubank":          "#7F77DD",
    "Sicredi":         "#1D9E75",
    "Banco Arbi":      "#D85A30",
    "Banco Inter":     "#D4537E",
    "BancoSeguro":     "#888780",
    "Caixa":           "#0F6E56",
    "Itaú":            "#185FA5",
    "Banco do Brasil": "#BA7517",
}

AHEAD = {"Sicredi", "Banco Arbi", "Banco Inter", "BancoSeguro"}

# ── Busca de dados ────────────────────────────────────────────────────────────

def fetch_bacen(data_inicio: str, data_fim: str) -> list:
    """Busca dados da API OData do Bacen para o período informado."""
    base = "https://olinda.bcb.gov.br/olinda/servico/taxaJuros/versao/v2/odata/TaxasJurosDiariaPorInicioPeriodo"
    params = {
        "$format": "json",
        "$filter": f"Modalidade eq '{MODALIDADE}' and Segmento eq '{SEGMENTO}'",
        "$select": "InicioPeriodo,InstituicaoFinanceira,TaxaJurosAoMes,TaxaJurosAoAno,Posicao",
        "$orderby": "InicioPeriodo asc,Posicao asc",
        "$top": "1000",
        "dataInicio": data_inicio,
        "dataFim": data_fim,
    }
    url = base + "?" + urllib.parse.urlencode(params)
    print(f"  Buscando: {url[:120]}...")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("value", [])

def build_series(records: list) -> dict:
    """
    Organiza os registros em séries por instituição, indexadas por data.
    Retorna: { "Nubank": {"2026-01-02": 1.60, ...}, ... }
    """
    series = {name: {} for name in INSTITUICOES.values()}
    for r in records:
        inst_raw = r.get("InstituicaoFinanceira", "")
        name = INSTITUICOES.get(inst_raw)
        if name is None:
            continue
        date = r.get("InicioPeriodo", "")[:10]  # "YYYY-MM-DD"
        taxa = r.get("TaxaJurosAoMes")
        if taxa is not None and date:
            series[name][date] = float(taxa)
    return series

def get_date_range(months_back: int = 4):
    today = datetime.today()
    start = today - timedelta(days=months_back * 31)
    return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

# ── Geração do HTML ───────────────────────────────────────────────────────────

def series_to_js(series: dict) -> str:
    """Converte séries em objeto JS com datas e valores alinhados."""
    # Coleta todas as datas únicas, ordena
    all_dates = sorted({d for s in series.values() for d in s})
    dates_js = json.dumps(all_dates)

    raw_js_parts = []
    for name, data in series.items():
        vals = [data.get(d) for d in all_dates]  # None se ausente
        vals_js = "[" + ",".join("null" if v is None else str(v) for v in vals) + "]"
        raw_js_parts.append(f"  '{name}': {vals_js}")

    raw_js = "{\n" + ",\n".join(raw_js_parts) + "\n}"
    return dates_js, raw_js, all_dates

def build_html(series: dict, generated_at: str) -> str:
    dates_js, raw_js, all_dates = series_to_js(series)
    
    # Monta label de período para cada data
    period_labels = []
    month_map = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
                 7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
    months_seen = {}
    month_seq = []
    for d in all_dates:
        dt = datetime.strptime(d, "%Y-%m-%d")
        key = (dt.year, dt.month)
        if key not in months_seen:
            months_seen[key] = len(month_seq)
            month_seq.append(key)
        period_labels.append(month_map[dt.month])

    period_labels_js = json.dumps(period_labels)

    # Monta lista de períodos disponíveis (últimos 3 meses + "tudo")
    periods_js_parts = []
    for i, (yr, mo) in enumerate(month_seq[-3:]):
        label = f"{month_map[mo]} {yr}"
        idxs = [j for j, d in enumerate(all_dates)
                if datetime.strptime(d, "%Y-%m-%d").month == mo
                and datetime.strptime(d, "%Y-%m-%d").year == yr]
        key = f"m{i}"
        periods_js_parts.append(f'"{key}": {{ label: "{label}", idx: {json.dumps(idxs)} }}')

    # Período "tudo"
    all_idxs = list(range(len(all_dates)))
    periods_js_parts.append(f'"all": {{ label: "Período completo ({len(all_dates)} pregões)", idx: {json.dumps(all_idxs)} }}')
    periods_js = "{\n  " + ",\n  ".join(periods_js_parts) + "\n}"

    # Primeiro período = mais recente
    first_period_key = f"m{len(month_seq[-3:])-1}"

    banks_js = json.dumps([
        {"key": name, "color": CORES[name], "isNubank": name == "Nubank", "ahead": name in AHEAD}
        for name in INSTITUICOES.values()
    ])

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Comparativo de Taxas de Juros — Consignado Público</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  :root {{
    --bg: #f5f4f0; --surface: #ffffff; --surface2: #f0efe9;
    --border: rgba(0,0,0,0.08); --border2: rgba(0,0,0,0.14);
    --text: #1a1a18; --text2: #5a5a56; --text3: #9a9a94;
    --nu: #7F77DD; --nu-light: #EEEDFE; --nu-dark: #534AB7;
    --radius: 12px; --radius-sm: 8px;
  }}
  body {{ font-family: 'DM Sans', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; padding: 0 0 4rem; }}
  header {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 1.25rem 2rem; display: flex; align-items: center; gap: 1rem; position: sticky; top: 0; z-index: 10; }}
  .logo {{ width: 34px; height: 34px; background: var(--nu); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600; color: white; flex-shrink: 0; }}
  .header-title {{ font-size: 14px; font-weight: 500; }}
  .header-sub {{ font-size: 11px; color: var(--text3); margin-top: 1px; }}
  .header-badge {{ margin-left: auto; font-size: 11px; font-weight: 500; padding: 3px 10px; background: var(--nu-light); color: var(--nu-dark); border-radius: 20px; white-space: nowrap; }}
  main {{ max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem; }}
  .hero {{ margin-bottom: 1.75rem; }}
  .hero h1 {{ font-size: 26px; font-weight: 600; line-height: 1.3; letter-spacing: -0.02em; }}
  .hero p {{ font-size: 13px; color: var(--text2); margin-top: 0.5rem; line-height: 1.6; }}
  .tabs {{ display: flex; gap: 6px; margin-bottom: 1.5rem; flex-wrap: wrap; }}
  .tab {{ font-size: 12px; font-family: 'DM Sans', sans-serif; padding: 5px 14px; border-radius: 20px; border: 1px solid var(--border2); background: transparent; color: var(--text2); cursor: pointer; transition: all .15s; }}
  .tab:hover {{ background: var(--surface2); }}
  .tab.active {{ background: var(--text); color: white; border-color: var(--text); }}
  .metric-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 1.5rem; }}
  @media(max-width:600px) {{ .metric-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
  .metric-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1rem 1.1rem; }}
  .metric-label {{ font-size: 10px; color: var(--text3); font-weight: 500; text-transform: uppercase; letter-spacing: .04em; margin-bottom: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .metric-value {{ font-size: 24px; font-weight: 600; font-family: 'DM Mono', monospace; letter-spacing: -0.02em; }}
  .metric-sub {{ font-size: 10px; color: var(--text3); margin-top: 3px; }}
  .metric-badge {{ display: inline-block; font-size: 10px; font-weight: 500; padding: 2px 7px; border-radius: 4px; margin-top: 5px; }}
  .badge-nu {{ background: var(--nu-light); color: var(--nu-dark); }}
  .badge-warn {{ background: #FFF3E0; color: #B45309; }}
  .badge-danger {{ background: #FFEBEE; color: #C62828; }}
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.5rem; margin-bottom: 1.25rem; }}
  .card-title {{ font-size: 14px; font-weight: 500; margin-bottom: 2px; }}
  .card-sub {{ font-size: 12px; color: var(--text3); margin-bottom: 1.25rem; }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 1.25rem; }}
  .legend-item {{ display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--text2); }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }}
  .chart-wrap {{ position: relative; width: 100%; height: 300px; }}
  .rank-header {{ display: flex; align-items: center; gap: 8px; font-size: 10px; font-weight: 500; color: var(--text3); text-transform: uppercase; letter-spacing: .06em; padding-bottom: 8px; border-bottom: 1px solid var(--border); margin-bottom: 4px; }}
  .rank-row {{ display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--border); }}
  .rank-row:last-child {{ border-bottom: none; }}
  .rank-num {{ font-size: 11px; color: var(--text3); width: 24px; text-align: right; font-family: 'DM Mono', monospace; flex-shrink: 0; }}
  .rank-badge-cell {{ width: 64px; flex-shrink: 0; }}
  .rank-badge {{ font-size: 9px; font-weight: 600; padding: 2px 6px; border-radius: 4px; white-space: nowrap; }}
  .badge-ahead {{ background: #E8F5E9; color: #2E7D32; }}
  .badge-nubank {{ background: var(--nu-light); color: var(--nu-dark); }}
  .badge-trad {{ background: var(--surface2); color: var(--text3); }}
  .rank-name {{ font-size: 13px; font-weight: 500; flex: 1; min-width: 0; }}
  .rank-name.nu {{ color: var(--nu-dark); }}
  .rank-bar-wrap {{ width: 150px; height: 6px; background: var(--surface2); border-radius: 3px; overflow: hidden; flex-shrink: 0; }}
  .rank-bar {{ height: 100%; border-radius: 3px; }}
  .rank-val {{ font-size: 12px; font-weight: 500; font-family: 'DM Mono', monospace; width: 56px; text-align: right; flex-shrink: 0; }}
  .rank-ano {{ font-size: 11px; color: var(--text3); font-family: 'DM Mono', monospace; width: 64px; text-align: right; flex-shrink: 0; }}
  @media(max-width:600px) {{ .rank-bar-wrap, .rank-ano {{ display: none; }} }}
  .insight {{ background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: var(--radius); padding: 1rem 1.25rem; font-size: 13px; color: #1E40AF; line-height: 1.7; }}
  .insight strong {{ font-weight: 600; }}
  .source {{ font-size: 11px; color: var(--text3); margin-top: 1.5rem; text-align: center; line-height: 1.8; }}
  .source a {{ color: var(--text3); }}
</style>
</head>
<body>
<header>
  <div class="logo">TX</div>
  <div>
    <div class="header-title">Comparativo de Taxas de Juros</div>
    <div class="header-sub">Consignado Público Prefixado · Pessoa Física · Bacen</div>
  </div>
  <div class="header-badge">Atualizado em {generated_at}</div>
</header>
<main>
  <div class="hero">
    <h1>Onde o Nubank se posiciona no consignado público?</h1>
    <p>Análise dos últimos pregões do Bacen para crédito pessoal consignado público prefixado — Pessoa Física. Atualizado automaticamente toda semana via GitHub Actions.</p>
  </div>
  <div class="tabs" id="tabs"></div>
  <div class="metric-grid" id="metric-grid"></div>
  <div class="card">
    <div class="card-title">Evolução diária da taxa ao mês</div>
    <div class="card-sub" id="chart-sub">Todos os players analisados</div>
    <div class="legend">
      <span class="legend-item"><span class="legend-dot" style="background:#7F77DD"></span>Nubank</span>
      <span class="legend-item"><span class="legend-dot" style="background:#1D9E75"></span>Sicredi</span>
      <span class="legend-item"><span class="legend-dot" style="background:#D85A30"></span>Banco Arbi</span>
      <span class="legend-item"><span class="legend-dot" style="background:#D4537E"></span>Banco Inter</span>
      <span class="legend-item"><span class="legend-dot" style="background:#888780"></span>BancoSeguro</span>
      <span class="legend-item"><span class="legend-dot" style="background:#0F6E56"></span>Caixa</span>
      <span class="legend-item"><span class="legend-dot" style="background:#185FA5"></span>Itaú</span>
      <span class="legend-item"><span class="legend-dot" style="background:#BA7517"></span>Banco do Brasil</span>
    </div>
    <div class="chart-wrap"><canvas id="lineChart"></canvas></div>
  </div>
  <div class="card">
    <div class="card-title">Ranking por taxa média</div>
    <div class="card-sub" id="rank-sub">Menor taxa = mais competitivo para o tomador</div>
    <div class="rank-header">
      <span style="width:24px"></span><span style="width:64px"></span>
      <span style="flex:1">Instituição</span>
      <span style="width:150px" class="rank-bar-hide"></span>
      <span style="width:56px;text-align:right">% a.m.</span>
      <span style="width:64px;text-align:right">% a.a.</span>
    </div>
    <div id="ranking-list"></div>
  </div>
  <div class="insight" id="insight-box"></div>
  <div class="source">
    Fonte: <a href="https://dadosabertos.bcb.gov.br/dataset/taxas-de-juros-de-operacoes-de-credito" target="_blank">Banco Central do Brasil</a> — Histórico de Taxa de Juros Diário<br>
    Modalidade: Crédito pessoal consignado público — Prefixado · Gerado em {generated_at}
  </div>
</main>
<script>
const raw = {raw_js};
const allDates = {dates_js};
const periodLabels = {period_labels_js};
const periods = {periods_js};
const banks = {banks_js};

function avg(arr, idxs) {{
  const valid = idxs.map(i => arr[i]).filter(v => v != null);
  return valid.length ? valid.reduce((a,b)=>a+b,0)/valid.length : null;
}}
function toAnnual(m) {{ return ((Math.pow(1+m/100,12)-1)*100); }}

let chart;

function buildTabs() {{
  const el = document.getElementById('tabs');
  el.innerHTML = '';
  const keys = Object.keys(periods);
  keys.forEach((k,i) => {{
    const btn = document.createElement('button');
    btn.className = 'tab' + (i === keys.length-2 ? ' active' : '');
    btn.textContent = periods[k].label;
    btn.onclick = function() {{ showPeriod(k, this); }};
    el.appendChild(btn);
  }});
}}

function buildChart(period) {{
  const ctx = document.getElementById('lineChart').getContext('2d');
  if (chart) chart.destroy();
  const idxs = periods[period].idx;
  const xLabels = idxs.map(i => allDates[i].slice(5));
  chart = new Chart(ctx, {{
    type: 'line',
    data: {{
      labels: xLabels,
      datasets: banks.map(b => ({{
        label: b.key,
        data: idxs.map(i => raw[b.key] ? raw[b.key][i] : null),
        borderColor: b.color,
        backgroundColor: b.color + '18',
        borderWidth: b.isNubank ? 2.5 : 1.5,
        pointRadius: b.isNubank ? 4 : 2,
        pointBackgroundColor: b.color,
        tension: 0.3, fill: false, spanGaps: true,
      }}))
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{ callbacks: {{ label: c => ` ${{c.dataset.label}}: ${{c.parsed.y != null ? c.parsed.y.toFixed(2)+'% a.m.' : '—'}}` }} }}
      }},
      scales: {{
        x: {{ grid: {{ color: 'rgba(0,0,0,0.04)' }}, ticks: {{ font: {{ size: 10, family: 'DM Mono' }}, color: '#9a9a94', maxTicksLimit: 15 }} }},
        y: {{ min: 1.40, max: 2.05, grid: {{ color: 'rgba(0,0,0,0.04)' }}, ticks: {{ font: {{ size: 10, family: 'DM Mono' }}, color: '#9a9a94', callback: v => v.toFixed(2)+'%' }} }}
      }}
    }}
  }});
}}

function buildMetrics(period) {{
  const idxs = periods[period].idx;
  const nuA = avg(raw['Nubank'], idxs);
  const configs = [
    {{ k:'Nubank', badge:'5º no ranking', cls:'badge-nu' }},
    {{ k:'Caixa', badge:`+${{(avg(raw['Caixa'],idxs)-nuA).toFixed(2)}} p.p. vs Nu`, cls:'badge-warn' }},
    {{ k:'Itaú', badge:`+${{(avg(raw['Itaú'],idxs)-nuA).toFixed(2)}} p.p. vs Nu`, cls:'badge-warn' }},
    {{ k:'Banco do Brasil', badge:`+${{(avg(raw['Banco do Brasil'],idxs)-nuA).toFixed(2)}} p.p. vs Nu`, cls:'badge-danger' }},
  ];
  const g = document.getElementById('metric-grid');
  g.innerHTML = '';
  configs.forEach(c => {{
    const a = avg(raw[c.k], idxs);
    const d = document.createElement('div');
    d.className = 'metric-card';
    d.innerHTML = `<div class="metric-label">${{c.k}}</div><div class="metric-value">${{a.toFixed(2)}}%</div><div class="metric-sub">ao mês · média</div><div class="metric-badge ${{c.cls}}">${{c.badge}}</div>`;
    g.appendChild(d);
  }});
}}

function buildRanking(period) {{
  const idxs = periods[period].idx;
  document.getElementById('rank-sub').textContent = periods[period].label + ' — menor taxa = mais competitivo';
  const ranked = banks.map(b => ({{ ...b, avg: avg(raw[b.key], idxs), annual: toAnnual(avg(raw[b.key], idxs)) }}))
    .filter(b => b.avg != null).sort((a,b) => a.avg - b.avg);
  const min = ranked[0].avg, max = ranked[ranked.length-1].avg, range = max - min;
  const list = document.getElementById('ranking-list');
  list.innerHTML = '';
  ranked.forEach((b, i) => {{
    const pct = range > 0 ? (b.avg-min)/range : 0;
    const bw = Math.round(10 + pct * 88);
    let bHtml, bCls;
    if (b.isNubank) {{ bHtml='Nubank ★'; bCls='badge-nubank'; }}
    else if (b.ahead) {{ bHtml='à frente'; bCls='badge-ahead'; }}
    else {{ bHtml='tradicional'; bCls='badge-trad'; }}
    const div = document.createElement('div');
    div.className = 'rank-row';
    div.innerHTML = `
      <span class="rank-num">#${{i+1}}</span>
      <span class="rank-badge-cell"><span class="rank-badge ${{bCls}}">${{bHtml}}</span></span>
      <span class="rank-name${{b.isNubank?' nu':''}}">${{b.key}}</span>
      <div class="rank-bar-wrap"><div class="rank-bar" style="width:${{bw}}%;background:${{b.color}}${{b.isNubank?'':'99'}}"></div></div>
      <span class="rank-val">${{b.avg.toFixed(2)}}%</span>
      <span class="rank-ano">${{b.annual.toFixed(1)}}% a.a.</span>`;
    list.appendChild(div);
  }});
}}

function buildInsight(period) {{
  const idxs = periods[period].idx;
  const nu = avg(raw['Nubank'], idxs);
  const si = avg(raw['Sicredi'], idxs);
  const ar = avg(raw['Banco Arbi'], idxs);
  const bi = avg(raw['Banco Inter'], idxs);
  const bb = avg(raw['Banco do Brasil'], idxs);
  const cx = avg(raw['Caixa'], idxs);
  document.getElementById('insight-box').innerHTML =
    `<strong>Leitura (${{periods[period].label}}):</strong> O Nubank ocupa o <strong>5º lugar</strong> entre os players analisados com média de <strong>${{nu.toFixed(2)}}% a.m.</strong> À sua frente: Sicredi (${{si.toFixed(2)}}%), Banco Arbi (${{ar.toFixed(2)}}%) e Banco Inter (${{bi ? bi.toFixed(2) : '—'}}%) — todos players de nicho. Frente aos grandes bancos tradicionais, o Nubank cobra ${{(cx-nu).toFixed(2)}} p.p. a menos que a Caixa e ${{(bb-nu).toFixed(2)}} p.p. a menos que o Banco do Brasil — diferença de ${{(toAnnual(bb)-toAnnual(nu)).toFixed(1)}} p.p. ao ano.`;
}}

function showPeriod(period, el) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  if (el) el.classList.add('active');
  buildChart(period);
  buildMetrics(period);
  buildRanking(period);
  buildInsight(period);
}}

buildTabs();
const defaultPeriod = Object.keys(periods).slice(-2)[0];
showPeriod(defaultPeriod);
document.querySelectorAll('.tab')[Object.keys(periods).length - 2].classList.add('active');
</script>
</body>
</html>"""
    return html


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== Atualizando dashboard de taxas de juros ===")

    data_inicio, data_fim = get_date_range(months_back=4)
    print(f"Período: {data_inicio} → {data_fim}")

    print("Buscando dados da API do Bacen...")
    try:
        records = fetch_bacen(data_inicio, data_fim)
        print(f"  {len(records)} registros recebidos.")
    except Exception as e:
        print(f"ERRO ao buscar dados: {e}", file=sys.stderr)
        sys.exit(1)

    if not records:
        print("Nenhum dado retornado. Verifique o endpoint.", file=sys.stderr)
        sys.exit(1)

    series = build_series(records)

    # Log de cobertura
    for name, data in series.items():
        print(f"  {name}: {len(data)} pregões, última data: {max(data) if data else 'n/a'}")

    generated_at = datetime.today().strftime("%d/%m/%Y")
    html = build_html(series, generated_at)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"index.html gerado com sucesso ({len(html):,} bytes).")


if __name__ == "__main__":
    main()
