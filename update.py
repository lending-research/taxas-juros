"""
Dashboard de taxas de juros — Crédito Consignado.
3 modalidades: Público (dados diários), INSS e Privado (dados mensais).
"""

import json, urllib.request, urllib.parse, sys
from datetime import datetime, timedelta
from collections import defaultdict

# ── Configurações ─────────────────────────────────────────────────────────────

SEGMENTO = "PESSOA FÍSICA"

MODALIDADES = {
    "publico": "Cr\u00e9dito pessoal consignado p\u00fablico \u2013 Prefixado",
    "inss":    "Cr\u00e9dito pessoal consignado INSS \u2013 Prefixado",
    "privado": "Cr\u00e9dito pessoal consignado privado \u2013 Prefixado",
}

MODALIDADE_LABELS = {
    "publico": "Consignado P\u00fablico",
    "inss":    "Consignado INSS",
    "privado": "Consignado Privado",
}

# Players base sempre exibidos
BASE_INST = {
    "NU FINANCEIRA S.A. CFI":       "Nubank",
    "ITAU UNIBANCO S.A.":           "Ita\u00fa",
    "ITAÚ UNIBANCO S.A.":           "Ita\u00fa",
    "CAIXA ECONOMICA FEDERAL":      "Caixa",
    "BCO DO BRASIL S.A.":           "Banco do Brasil",
    "BCO COOPERATIVO SICREDI S.A.": "Sicredi",
    "BCO ARBI S.A.":                "Banco Arbi",
    "BANCO INTER":                  "Banco Inter",
    "BANCOSEGURO S.A.":             "BancoSeguro",
}

# Players relevantes por modalidade (além dos base)
INSS_EXTRA = {
    "BANCO INBURSA":               "Banco Inbursa",
    "PARATI - CFI S.A.":           "Parati CFI",
    "BCO PAULISTA S.A.":           "BCO Paulista",
    "BANCO SICOOB S.A.":           "Sicoob",
    "PICPAY BANK - BANCO M\u00daTIPLO S.A": "PicPay",
    "BCO DO ESTADO DO RS S.A.":    "Banrisul",
}

PRIVADO_EXTRA = {
    "BCO DAYCOVAL S.A":            "Daycoval",
    "COBUCCIO S.A. SCFI":          "Cobuccio",
    "BCO XP S.A.":                 "XP",
    "BCO VOLKSWAGEN S.A":          "Volkswagen",
    "PORTOSEG S.A. CFI":           "PortoSeg",
    "BCO SENFF S.A.":              "Senff",
    "BCO BANESTES S.A.":           "Banestes",
    "BANCO SICOOB S.A.":           "Sicoob",
    "BCO INDUSTRIAL DO BRASIL S.A.": "BCO Industrial",
    "BANCO DIGIO":                 "Digio",
}

CORES = {
    "Nubank":          "#7F77DD",
    "Ita\u00fa":            "#185FA5",
    "Caixa":           "#0F6E56",
    "Banco do Brasil": "#BA7517",
    "Sicredi":         "#1D9E75",
    "Banco Arbi":      "#D85A30",
    "Banco Inter":     "#D4537E",
    "BancoSeguro":     "#888780",
    "Banco Inbursa":   "#639922",
    "Parati CFI":      "#3B6D11",
    "BCO Paulista":    "#0C447C",
    "Sicoob":          "#533489",
    "PicPay":          "#D14520",
    "Banrisul":        "#A32D2D",
    "Daycoval":        "#5F5E5A",
    "Cobuccio":        "#BA7517",
    "XP":              "#2C2C2A",
    "Volkswagen":      "#185FA5",
    "PortoSeg":        "#D85A30",
    "Senff":           "#888780",
    "Banestes":        "#639922",
    "BCO Industrial":  "#3B6D11",
    "Digio":           "#D4537E",
}

DATA_FILE = "data.json"

# ── API ───────────────────────────────────────────────────────────────────────

def fetch_bacen(data_inicio, data_fim):
    base = "https://olinda.bcb.gov.br/olinda/servico/taxaJuros/versao/v2/odata/TaxasJurosDiariaPorInicioPeriodo"
    url = f"{base}?$format=json&$top=10000&dataInicio={data_inicio}&dataFim={data_fim}"
    print(f"  Buscando: {url}")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    records = data.get("value", [])
    print(f"  Total recebido: {len(records)}")
    return records

def get_inst_map(modkey):
    m = dict(BASE_INST)
    if modkey == "inss":
        m.update(INSS_EXTRA)
    elif modkey == "privado":
        m.update(PRIVADO_EXTRA)
    return m

def build_series(records, modkey):
    modalidade_str = MODALIDADES[modkey]
    inst_map = get_inst_map(modkey)
    # Also try with hyphen in case API varies
    modalidade_alt = modalidade_str.replace("–", "-")
    filtered = [r for r in records
                if "consignado" in r.get("Modalidade","").lower()
                and "Prefixado" in r.get("Modalidade","")
                and "SICA" in r.get("Segmento","")
                and (r.get("Modalidade","") == modalidade_str
                     or r.get("Modalidade","") == modalidade_alt)]
    print(f"    [{modkey}] registros filtrados: {len(filtered)}")
    series = {}
    for r in filtered:
        raw = r.get("InstituicaoFinanceira","")
        # For publico: only mapped institutions
        # For inss/privado: include all institutions
        if modkey == "publico":
            name = inst_map.get(raw)
            if not name:
                continue
        else:
            name = inst_map.get(raw, raw)  # fallback to raw name
        date = r.get("InicioPeriodo","")[:10]
        taxa = r.get("TaxaJurosAoMes")
        if taxa is not None and date:
            if name not in series:
                series[name] = {}
            series[name][date] = float(taxa)
    return series

def get_date_range(months_back=2):
    today = datetime.today()
    start = today - timedelta(days=months_back * 31)
    return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

# ── Persistência ──────────────────────────────────────────────────────────────

def load_historical():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def merge_series(historical, new_series):
    merged = {inst: dict(historical.get(inst, {})) for inst in set(list(historical.keys()) + list(new_series.keys()))}
    for inst, dates in new_series.items():
        if inst not in merged:
            merged[inst] = {}
        for date, taxa in dates.items():
            merged[inst][date] = taxa
    return merged

def save_historical(all_data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

# ── HTML ──────────────────────────────────────────────────────────────────────

def get_color(name):
    return CORES.get(name, "#888780")

def build_publico_data(series):
    """Dados diários — gráfico de linha com abas por mês."""
    all_dates = sorted({d for s in series.values() for d in s})
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

    periods = {}
    for i, (yr, mo) in enumerate(month_seq):
        label = f"{month_map[mo]} {yr}"
        idxs = [j for j, d in enumerate(all_dates)
                if datetime.strptime(d, "%Y-%m-%d").month == mo
                and datetime.strptime(d, "%Y-%m-%d").year == yr]
        periods[f"m{i}"] = {"label": label, "idx": idxs}
    all_idxs = list(range(len(all_dates)))
    periods["all"] = {"label": f"Per\u00edodo completo ({len(all_dates)} preg\u00f5es)", "idx": all_idxs}
    default = f"m{len(month_seq)-1}"

    banks = []
    raw = {}
    nu_avgs = {}
    for name in sorted(series.keys(), key=lambda n: (n != "Nubank", n)):
        vals = [series[name].get(d) for d in all_dates]
        raw[name] = vals
        banks.append({"key": name, "color": get_color(name), "isNubank": name == "Nubank",
                      "ahead": name in {"Sicredi","Banco Arbi","Banco Inter","BancoSeguro"}})
        for pk, pv in periods.items():
            idxs = pv["idx"]
            valid = [vals[i] for i in idxs if vals[i] is not None]
            if valid:
                nu_avgs.setdefault(pk, {})[name] = sum(valid)/len(valid)

    return {"type": "daily", "dates": all_dates, "raw": raw, "banks": banks,
            "periods": periods, "defaultPeriod": default, "avgs": nu_avgs}

def build_monthly_data(series, modkey):
    """Dados mensais — barras por mês, todos os players rankeados."""
    all_dates = sorted({d for s in series.values() for d in s})
    month_map_short = {"01":"Jan","02":"Fev","03":"Mar","04":"Abr","05":"Mai","06":"Jun",
                       "07":"Jul","08":"Ago","09":"Set","10":"Out","11":"Nov","12":"Dez"}

    periods = {}
    for d in all_dates:
        mo = d[5:7]
        yr = d[:4]
        label = f"{month_map_short[mo]} {yr}"
        periods[d] = {"label": label, "date": d}
    periods["all"] = {"label": "M\u00e9dia do per\u00edodo", "date": "all"}
    default = all_dates[-1] if all_dates else "all"

    inst_map = get_inst_map(modkey)
    known_names = set(inst_map.values())
    always_show = {"Nubank", "Caixa", "It\u00e1u", "Banco do Brasil"}

    ranked_per_period = {}
    for pk in list(periods.keys()):
        all_rows = []
        for name, dates in series.items():
            if pk == "all":
                vals = [v for v in dates.values() if v is not None]
                rate = round(sum(vals)/len(vals), 2) if vals else None
            else:
                rate = dates.get(pk)
            if rate is not None:
                all_rows.append({"name": name, "rate": rate,
                                 "color": get_color(name), "isNubank": name == "Nubank"})
        all_rows.sort(key=lambda r: r["rate"])

        nu_idx = next((i for i, r in enumerate(all_rows) if r["isNubank"]), None)
        nu_global_pos = (nu_idx + 1) if nu_idx is not None else None
        total = len(all_rows)

        for i, r in enumerate(all_rows):
            r["pos"] = i + 1
            r["ahead"] = nu_idx is not None and i < nu_idx

        # Show: ahead of Nubank + always_show + known mapped names
        shown = [r for r in all_rows
                 if r["ahead"] or r["name"] in always_show or r["name"] in known_names]

        ranked_per_period[pk] = {"rows": shown, "nuPos": nu_global_pos, "totalPlayers": total}

    return {"type": "monthly", "periods": periods, "defaultPeriod": default,
            "ranked": ranked_per_period}


def build_html(all_data, generated_at):
    publico = build_publico_data(all_data.get("publico", {}))
    inss    = build_monthly_data(all_data.get("inss", {}), "inss")
    privado = build_monthly_data(all_data.get("privado", {}), "privado")

    publico_js  = json.dumps(publico,  ensure_ascii=False)
    inss_js     = json.dumps(inss,     ensure_ascii=False)
    privado_js  = json.dumps(privado,  ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Comparativo de Taxas \u2014 Cr\u00e9dito Consignado</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{--bg:#f5f4f0;--surface:#fff;--surface2:#f0efe9;--border:rgba(0,0,0,0.08);--border2:rgba(0,0,0,0.14);--text:#1a1a18;--text2:#5a5a56;--text3:#9a9a94;--nu:#7F77DD;--nu-light:#EEEDFE;--nu-dark:#534AB7;--r:12px}}
body{{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;padding-bottom:4rem}}
header{{background:var(--surface);border-bottom:1px solid var(--border);padding:1.25rem 2rem;display:flex;align-items:center;gap:1rem;position:sticky;top:0;z-index:10}}
.logo{{width:34px;height:34px;background:var(--nu);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:600;color:#fff;flex-shrink:0}}
.ht{{font-size:14px;font-weight:500}}.hs{{font-size:11px;color:var(--text3);margin-top:1px}}
.hb{{margin-left:auto;font-size:11px;font-weight:500;padding:3px 10px;background:var(--nu-light);color:var(--nu-dark);border-radius:20px;white-space:nowrap}}
.mtabs{{background:var(--surface);border-bottom:1px solid var(--border);padding:0 2rem;display:flex}}
.mtab{{font-size:13px;font-weight:500;padding:.875rem 1.25rem;border:none;background:transparent;color:var(--text3);cursor:pointer;border-bottom:2px solid transparent;transition:all .15s}}
.mtab:hover{{color:var(--text2)}}.mtab.active{{color:var(--nu-dark);border-bottom-color:var(--nu)}}
main{{max-width:960px;margin:0 auto;padding:1.75rem 1.5rem}}
.panel{{display:none}}.panel.active{{display:block}}
.hero{{margin-bottom:1.5rem}}
.hero h2{{font-size:22px;font-weight:600;letter-spacing:-0.02em;line-height:1.3}}
.hero p{{font-size:13px;color:var(--text2);margin-top:.4rem;line-height:1.6}}
.ptabs{{display:flex;gap:6px;margin-bottom:1.5rem;flex-wrap:wrap}}
.ptab{{font-size:12px;font-family:'DM Sans',sans-serif;padding:5px 14px;border-radius:20px;border:1px solid var(--border2);background:transparent;color:var(--text2);cursor:pointer;transition:all .15s}}
.ptab:hover{{background:var(--surface2)}}.ptab.active{{background:var(--text);color:#fff;border-color:var(--text)}}
.mgrid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:1.5rem}}
@media(max-width:600px){{.mgrid{{grid-template-columns:repeat(2,1fr)}}}}
.mc{{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:1rem 1.1rem}}
.ml{{font-size:10px;color:var(--text3);font-weight:500;text-transform:uppercase;letter-spacing:.04em;margin-bottom:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.mv{{font-size:24px;font-weight:600;font-family:'DM Mono',monospace;letter-spacing:-0.02em}}
.ms{{font-size:10px;color:var(--text3);margin-top:3px}}
.mb{{display:inline-block;font-size:10px;font-weight:500;padding:2px 7px;border-radius:4px;margin-top:5px}}
.bnu{{background:var(--nu-light);color:var(--nu-dark)}}.bwarn{{background:#FFF3E0;color:#B45309}}.bdanger{{background:#FFEBEE;color:#C62828}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:1.5rem;margin-bottom:1.25rem}}
.ct{{font-size:14px;font-weight:500;margin-bottom:2px}}.cs{{font-size:12px;color:var(--text3);margin-bottom:1.25rem}}
.legend{{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:1.25rem}}
.li{{display:flex;align-items:center;gap:5px;font-size:11px;color:var(--text2)}}
.ld{{width:10px;height:10px;border-radius:2px;flex-shrink:0}}
.cw{{position:relative;width:100%;height:280px}}
/* Bar chart rows */
.bar-table{{width:100%;border-collapse:collapse}}
.bar-row{{display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:.5px solid var(--border)}}
.bar-row:last-child{{border-bottom:none}}
.bar-pos{{font-size:11px;color:var(--text3);width:20px;text-align:right;font-family:'DM Mono',monospace;flex-shrink:0}}
.bar-badge{{width:60px;flex-shrink:0}}
.bar-badge-pill{{font-size:9px;font-weight:600;padding:2px 6px;border-radius:4px;white-space:nowrap}}
.b-nu{{background:var(--nu-light);color:var(--nu-dark)}}.b-ahead{{background:#E8F5E9;color:#2E7D32}}.b-trad{{background:var(--surface2);color:var(--text3)}}
.bar-name{{font-size:13px;font-weight:500;flex:1;min-width:0}}
.bar-name.nu{{color:var(--nu-dark)}}
.bar-track{{flex:1;height:8px;background:var(--surface2);border-radius:4px;overflow:hidden;max-width:200px;flex-shrink:0}}
.bar-fill{{height:100%;border-radius:4px;transition:width .4s}}
.bar-val{{font-size:13px;font-weight:500;font-family:'DM Mono',monospace;width:52px;text-align:right;flex-shrink:0}}
.bar-ano{{font-size:11px;color:var(--text3);font-family:'DM Mono',monospace;width:64px;text-align:right;flex-shrink:0}}
@media(max-width:600px){{.bar-track,.bar-ano{{display:none}}}}
.nu-highlight{{background:linear-gradient(90deg,#EEEDFE44,transparent);border-radius:6px}}
.insight{{background:#EFF6FF;border:1px solid #BFDBFE;border-radius:var(--r);padding:1rem 1.25rem;font-size:13px;color:#1E40AF;line-height:1.7;margin-bottom:1.25rem}}
.insight strong{{font-weight:600}}
.source{{font-size:11px;color:var(--text3);margin-top:1.5rem;text-align:center;line-height:1.8}}
.source a{{color:var(--text3)}}
.note{{font-size:11px;color:var(--text3);background:var(--surface2);border-radius:6px;padding:6px 10px;margin-bottom:1rem;display:inline-block}}
</style>
</head>
<body>
<header>
  <div class="logo">TX</div>
  <div><div class="ht">Comparativo de Taxas de Juros</div><div class="hs">Cr\u00e9dito Consignado \u00b7 Prefixado \u00b7 Pessoa F\u00edsica \u00b7 Bacen</div></div>
  <div class="hb">Atualizado em {generated_at}</div>
</header>
<div class="mtabs">
  <button class="mtab active" onclick="showModal('publico',this)">Consignado P\u00fablico</button>
  <button class="mtab" onclick="showModal('inss',this)">Consignado INSS</button>
  <button class="mtab" onclick="showModal('privado',this)">Consignado Privado</button>
</div>
<main>
  <div id="p-publico" class="panel active"></div>
  <div id="p-inss" class="panel"></div>
  <div id="p-privado" class="panel"></div>
  <div class="source">Fonte: <a href="https://dadosabertos.bcb.gov.br/dataset/taxas-de-juros-de-operacoes-de-credito" target="_blank">Banco Central do Brasil</a> \u2014 Hist\u00f3rico de Taxa de Juros \u00b7 Gerado em {generated_at}</div>
</main>
<script>
const PUBLICO = {publico_js};
const INSS    = {inss_js};
const PRIVADO = {privado_js};
const charts  = {{}};

function toAnn(m){{ return ((Math.pow(1+m/100,12)-1)*100); }}
function avg(arr,idxs){{ const v=idxs.map(i=>arr[i]).filter(x=>x!=null); return v.length?v.reduce((a,b)=>a+b,0)/v.length:null; }}

// ── Consignado Público (daily line chart) ─────────────────────────────────────
function buildPublico(period) {{
  const m = PUBLICO;
  const idxs = m.periods[period].idx;
  const panel = document.getElementById('p-publico');

  // Metric cards
  const nuA = avg(m.raw['Nubank'], idxs);
  const trad = ['Nubank','Caixa','Ita\u00fa','Banco do Brasil'];
  const cards = trad.map(name => {{
    const a = avg(m.raw[name], idxs);
    if (a==null) return '';
    const diff = name!='Nubank' && nuA ? '+' + (a-nuA).toFixed(2)+' p.p. vs Nu' : null;
    const cls = name=='Nubank'?'bnu':(a-nuA>0.2?'bdanger':'bwarn');
    return '<div class="mc"><div class="ml">'+name+'</div><div class="mv">'+a.toFixed(2)+'%</div><div class="ms">ao m\u00eas \u00b7 m\u00e9dia</div>'+(diff?'<div class="mb '+cls+'">'+diff+'</div>':'')+'</div>';
  }}).join('');

  // Period tabs
  const ptabs = Object.entries(m.periods).map(([pk,pv]) =>
    '<button class="ptab'+(pk==period?' active':'')+'" onclick="buildPublico(\''+pk+'\',this);updateTab(\'ptabs-pub\',this)">'+pv.label+'</button>'
  ).join('');

  // Legend
  const legend = m.banks.map(b=>'<span class="li"><span class="ld" style="background:'+b.color+'"></span>'+b.key+'</span>').join('');

  panel.innerHTML =
    '<div class="hero"><h2>Onde o Nubank se posiciona no consignado p\u00fablico?</h2><p>Dados di\u00e1rios do Bacen \u00b7 Prefixado \u00b7 Pessoa F\u00edsica</p></div>'+
    '<div class="ptabs" id="ptabs-pub">'+ptabs+'</div>'+
    '<div class="mgrid">'+cards+'</div>'+
    '<div class="card"><div class="ct">Evolu\u00e7\u00e3o di\u00e1ria da taxa ao m\u00eas</div><div class="cs">Todos os players \u00b7 menor taxa = mais competitivo</div>'+
    '<div class="legend">'+legend+'</div><div class="cw"><canvas id="chart-pub"></canvas></div></div>'+
    '<div class="card"><div class="ct">Ranking por taxa m\u00e9dia</div><div class="cs" id="rank-sub-pub"></div><div id="rank-pub"></div></div>'+
    '<div class="insight" id="ins-pub"></div>';

  buildPubChart(period);
  buildPubRanking(period);
  buildPubInsight(period);
}}

function buildPubChart(period) {{
  const m = PUBLICO;
  const idxs = m.periods[period].idx;
  const ctx = document.getElementById('chart-pub').getContext('2d');
  if(charts.pub) charts.pub.destroy();
  charts.pub = new Chart(ctx, {{
    type:'line',
    data:{{
      labels: idxs.map(i=>m.dates[i].slice(5)),
      datasets: m.banks.map(b=>({{'label':b.key,'data':idxs.map(i=>m.raw[b.key]?m.raw[b.key][i]:null),'borderColor':b.color,'backgroundColor':b.color+'18','borderWidth':b.isNubank?2.5:1.5,'pointRadius':b.isNubank?4:2,'pointBackgroundColor':b.color,'tension':.3,'fill':false,'spanGaps':true}}))
    }},
    options:{{responsive:true,maintainAspectRatio:false,interaction:{{mode:'index',intersect:false}},plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:c=>` ${{c.dataset.label}}: ${{c.parsed.y!=null?c.parsed.y.toFixed(2)+'% a.m.':'--'}}`}}}}}},scales:{{x:{{grid:{{color:'rgba(0,0,0,0.04)'}},ticks:{{font:{{size:10,family:'DM Mono'}},color:'#9a9a94',maxTicksLimit:15}}}},y:{{grid:{{color:'rgba(0,0,0,0.04)'}},ticks:{{font:{{size:10,family:'DM Mono'}},color:'#9a9a94',callback:v=>v.toFixed(2)+'%'}}}}}}}}
  }});
}}

function buildPubRanking(period) {{
  const m = PUBLICO;
  const idxs = m.periods[period].idx;
  document.getElementById('rank-sub-pub').textContent = m.periods[period].label + ' \u2014 menor taxa = mais competitivo';
  const ranked = m.banks.map(b=>({{'key':b.key,'color':b.color,'isNubank':b.isNubank,'ahead':b.ahead,'avg':avg(m.raw[b.key],idxs)}})
  ).filter(b=>b.avg!=null).sort((a,b)=>a.avg-b.avg);
  const mn=ranked[0].avg, mx=ranked[ranked.length-1].avg, rng=mx-mn;
  document.getElementById('rank-pub').innerHTML = ranked.map((b,i)=>{{
    const pct=rng>0?(b.avg-mn)/rng:0, bw=Math.round(10+pct*88);
    const pill=b.isNubank?'<span class="bar-badge-pill b-nu">Nubank \u2605</span>':b.ahead?'<span class="bar-badge-pill b-ahead">\u00e0 frente</span>':'<span class="bar-badge-pill b-trad">trad.</span>';
    return '<div class="bar-row'+(b.isNubank?' nu-highlight':'')+'"><span class="bar-pos">#'+(i+1)+'</span><span class="bar-badge">'+pill+'</span><span class="bar-name'+(b.isNubank?' nu':'')+'">'+b.key+'</span><div class="bar-track"><div class="bar-fill" style="width:'+bw+'%;background:'+b.color+(b.isNubank?'':'99')+'"></div></div><span class="bar-val">'+b.avg.toFixed(2)+'%</span><span class="bar-ano">'+toAnn(b.avg).toFixed(1)+'% a.a.</span></div>';
  }}).join('');
}}

function buildPubInsight(period) {{
  const m=PUBLICO, idxs=m.periods[period].idx;
  const nu=avg(m.raw['Nubank'],idxs), bb=avg(m.raw['Banco do Brasil'],idxs), cx=avg(m.raw['Caixa'],idxs);
  const ranked=m.banks.map(b=>({{'key':b.key,'isNubank':b.isNubank,'avg':avg(m.raw[b.key],idxs)}})).filter(b=>b.avg!=null).sort((a,b)=>a.avg-b.avg);
  const nuPos=ranked.findIndex(b=>b.isNubank)+1;
  const ahead=ranked.filter((b,i)=>i<nuPos-1).map(b=>b.key).join(', ');
  let t='<strong>'+m.periods[period].label+':</strong> Nubank em <strong>#'+nuPos+'\u00ba lugar</strong> com m\u00e9dia de <strong>'+nu.toFixed(2)+'% a.m.</strong>';
  if(ahead) t+=' \u00c0 sua frente: '+ahead+'.';
  if(cx) t+=' Caixa cobra '+(cx-nu).toFixed(2)+' p.p. a mais.';
  if(bb) t+=' Banco do Brasil cobra '+(bb-nu).toFixed(2)+' p.p. a mais (~'+(toAnn(bb)-toAnn(nu)).toFixed(1)+' p.p. ao ano).';
  document.getElementById('ins-pub').innerHTML=t;
}}

// ── INSS / Privado (monthly bar chart) ───────────────────────────────────────
function buildMonthly(key, data, period) {{
  const panel = document.getElementById('p-'+key);
  const label = key=='inss'?'Consignado INSS':'Consignado Privado';
  const periodData = data.ranked[period] || {rows:[], nuPos:null, totalPlayers:0};
  const ranked = periodData.rows || [];
  const nuRow = ranked.find(r=>r.isNubank);
  const nuRate = nuRow ? nuRow.rate : null;
  const nuGlobalPos = periodData.nuPos;
  const totalPlayers = periodData.totalPlayers;

  // Metric cards: Nubank + Caixa + Itaú + Banco do Brasil
  const trad = ['Nubank','Caixa','Ita\u00fa','Banco do Brasil'];
  const allRanked = data.ranked[period] || [];
  const cards = trad.map(name=>{{
    const r = allRanked.find(r=>r.name==name);
    if(!r) return '';
    const diff = name!='Nubank'&&nuRate?'+' + (r.rate-nuRate).toFixed(2)+' p.p. vs Nu':null;
    const cls = name=='Nubank'?'bnu':(r.rate-nuRate>0.5?'bdanger':'bwarn');
    return '<div class="mc"><div class="ml">'+name+'</div><div class="mv">'+r.rate.toFixed(2)+'%</div><div class="ms">ao m\u00eas</div>'+(diff?'<div class="mb '+cls+'">'+diff+'</div>':'')+'</div>';
  }}).join('');

  // Period tabs
  const ptabs = Object.entries(data.periods).map(([pk,pv])=>
    '<button class="ptab'+(pk==period?' active':'')+'" onclick="buildMonthly(\''+key+'\','+key.toUpperCase()+',\''+pk+'\');updateTab(\'ptabs-'+key+'\',this)">'+pv.label+'</button>'
  ).join('');

  // Bar rows
  const mn=ranked[0]?.rate||0, mx=ranked[ranked.length-1]?.rate||0, rng=mx-mn;
  const rows = ranked.map((r,i)=>{{
    const pct=rng>0?(r.rate-mn)/rng:0, bw=Math.round(10+pct*88);
    const pill=r.isNubank?'<span class="bar-badge-pill b-nu">Nubank \u2605</span>':r.ahead?'<span class="bar-badge-pill b-ahead">\u00e0 frente</span>':'<span class="bar-badge-pill b-trad">trad.</span>';
    return '<div class="bar-row'+(r.isNubank?' nu-highlight':'')+'"><span class="bar-pos">#'+(i+1)+'</span><span class="bar-badge">'+pill+'</span><span class="bar-name'+(r.isNubank?' nu':'')+'">'+r.name+'</span><div class="bar-track"><div class="bar-fill" style="width:'+bw+'%;background:'+r.color+(r.isNubank?'':'99')+'"></div></div><span class="bar-val">'+r.rate.toFixed(2)+'%</span><span class="bar-ano">'+toAnn(r.rate).toFixed(1)+'% a.a.</span></div>';
  }}).join('');

  // Insight
  const nuPos = nuGlobalPos || (nuRow ? nuRow.pos : '?');
  const ahead = ranked.filter(r=>r.ahead).map(r=>r.name).join(', ');
  const bbRow = ranked.find(r=>r.name=='Banco do Brasil');
  let ins = '<strong>'+label+' \u00b7 '+data.periods[period].label+':</strong> Nubank em <strong>#'+nuPos+'\u00ba lugar</strong>';
  if(nuRate) ins += ' com taxa de <strong>'+nuRate.toFixed(2)+'% a.m.</strong>';
  if(ahead) ins += ' \u00c0 sua frente: '+ahead+'.';
  if(bbRow&&nuRate) ins += ' Banco do Brasil cobra '+(bbRow.rate-nuRate).toFixed(2)+' p.p. a mais (~'+(toAnn(bbRow.rate)-toAnn(nuRate)).toFixed(1)+' p.p. ao ano).';

  const noteText = key=='inss'?'Dados mensais consolidados do Bacen \u2014 m\u00e9dia do per\u00edodo':'Dados mensais consolidados do Bacen \u2014 m\u00e9dia do per\u00edodo. No consignado privado as taxas s\u00e3o significativamente maiores que no p\u00fablico.';

  panel.innerHTML =
    '<div class="hero"><h2>Onde o Nubank se posiciona no '+label.toLowerCase()+'?</h2><p>Dados mensais do Bacen \u00b7 Prefixado \u00b7 Pessoa F\u00edsica</p></div>'+
    '<div class="ptabs" id="ptabs-'+key+'">'+ptabs+'</div>'+
    '<div class="mgrid">'+cards+'</div>'+
    '<div class="card"><div class="ct">Ranking de taxas \u2014 '+data.periods[period].label+'</div>'+
    '<div class="cs">Menor taxa = mais competitivo para o tomador \u00b7 <span class="note">'+noteText+'</span></div>'+
    '<div id="bars-'+key+'">'+rows+'</div></div>'+
    '<div class="insight">'+ins+'</div>';
}}

// ── Navigation ────────────────────────────────────────────────────────────────
function updateTab(containerId, el) {{
  document.querySelectorAll('#'+containerId+' .ptab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
}}

const initialized = {{}};
function showModal(key, el) {{
  document.querySelectorAll('.mtab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('p-'+key).classList.add('active');
  if (!initialized[key]) {{
    initialized[key] = true;
    if (key=='publico') {{
      buildPublico(PUBLICO.defaultPeriod);
    }} else if (key=='inss') {{
      buildMonthly('inss', INSS, INSS.defaultPeriod);
    }} else if (key=='privado') {{
      buildMonthly('privado', PRIVADO, PRIVADO.defaultPeriod);
    }}
  }}
  if (key=='publico' && !charts.pub) setTimeout(()=>buildPubChart(PUBLICO.defaultPeriod),50);
}}

// Init
buildPublico(PUBLICO.defaultPeriod);
initialized['publico'] = true;
setTimeout(()=>buildPubChart(PUBLICO.defaultPeriod),50);
</script>
</body>
</html>"""

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== Atualizando dashboard ===")
    historical = load_historical()
    data_inicio, data_fim = get_date_range(months_back=2)
    print(f"Buscando: {data_inicio} \u2192 {data_fim}")

    try:
        records = fetch_bacen(data_inicio, data_fim)
    except Exception as e:
        print(f"ERRO: {e}", file=sys.stderr)
        records = []

    all_series = {}
    for key in MODALIDADES:
        print(f"\n--- {MODALIDADE_LABELS[key]} ---")
        new_series = build_series(records, key)
        print(f"  API: {sum(len(v) for v in new_series.values())} registros")
        hist = historical.get(key, {})
        merged = merge_series(hist, new_series)
        all_series[key] = merged
        for name, data in merged.items():
            if data:
                print(f"  {name}: {len(data)} datas | {min(data)} \u2192 {max(data)}")

    save_historical(all_series)

    generated_at = datetime.today().strftime("%d/%m/%Y")
    html = build_html(all_series, generated_at)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nindex.html gerado ({len(html):,} bytes).")

if __name__ == "__main__":
    main()
