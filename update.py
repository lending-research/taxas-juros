"""
Dashboard de taxas de juros — Crédito Consignado.
3 modalidades: Público (dados diários), INSS e Privado (dados mensais).
"""

import json, urllib.request, urllib.parse, sys
from datetime import datetime, timedelta
from collections import defaultdict
import os as _os

# Load JS dashboard code from sibling file
_JS_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "dashboard.js")
JS_CODE = open(_JS_PATH, encoding="utf-8").read()

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
    "IT\u00c1U UNIBANCO S.A.":           "Ita\u00fa",
    "ITAÚ UNIBANCO S.A.":           "Ita\u00fa",
    "BANCO IT\u00c1U CONSIGNADO S.A.":  "Ita\u00fa",
    "BANCO ITAÚ CONSIGNADO S.A.":   "Ita\u00fa",
    "CAIXA ECONOMICA FEDERAL":      "Caixa",
    "BCO DO BRASIL S.A.":           "Banco do Brasil",
    "BCO COOPERATIVO SICREDI S.A.": "Sicredi",
    "BCO ARBI S.A.":                "Banco Arbi",
    "BANCO INTER":                  "Banco Inter",
    "BANCOSEGURO S.A.":             "BancoSeguro",
    "BCO BRADESCO S.A.":            "Bradesco",
    "BCO SANTANDER (BRASIL) S.A.":  "Santander",
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
    "Bradesco":        "#CC0000",
    "Santander":       "#EC0000",
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

# Categorias das instituições para badge no ranking
CATEGORIAS = {
    # Fintechs / digitais
    "Nubank":          "fintech",
    "Banco Inter":     "fintech",
    "BancoSeguro":     "fintech",
    "Digio":           "fintech",
    "PicPay":          "fintech",
    "XP":              "fintech",
    "C6":              "fintech",
    "Neon":            "fintech",
    "BCO C6 CONSIG":   "fintech",
    "BANCO DIGIO":     "fintech",
    "NEON FINANCEIRA - SCFI S.A.": "fintech",
    "PICPAY BANK - BANCO M\u00daTIPLO S.A": "fintech",
    "BCO XP S.A.":     "fintech",

    # Cooperativas
    "Sicredi":         "cooperativa",
    "Sicoob":          "cooperativa",
    "BCO COOPERATIVO SICREDI S.A.": "cooperativa",
    "BANCO SICOOB S.A.": "cooperativa",
    "BRB - CFI S/A":   "cooperativa",
    "Banrisul":        "cooperativa",
    "BCO DO ESTADO DO RS S.A.": "cooperativa",
    "Banestes":        "cooperativa",
    "BCO BANESTES S.A.": "cooperativa",
    "BCO DO EST. DE SE S.A.": "cooperativa",

    # Bancos tradicionais grandes (nomes mapeados E nomes raw da API)
    "Itaú":            "tradicional",
    "Caixa":           "tradicional",
    "Banco do Brasil": "tradicional",
    "Bradesco":        "tradicional",
    "Santander":       "tradicional",
    "Itau":            "tradicional",
    "BCO BRADESCO S.A.": "tradicional",
    "BCO SANTANDER (BRASIL) S.A.": "tradicional",
    "ITAÚ UNIBANCO S.A.": "tradicional",
    "BANCO ITAÚ CONSIGNADO S.A.": "tradicional",
    "CAIXA ECONOMICA FEDERAL": "tradicional",
    "BCO DO BRASIL S.A.": "tradicional",

    # Bancos médios / especializados em consignado
    "Banco Arbi":      "especializado",
    "Banco Inbursa":   "especializado",
    "BCO ARBI S.A.":   "especializado",
    "BANCO INBURSA":   "especializado",
    "BCO BMG S.A.":    "especializado",
    "BANCO PAN":       "especializado",
    "PAN FINAN":       "especializado",
    "BCO DAYCOVAL S.A": "especializado",
    "Daycoval":        "especializado",
    "BCO PAULISTA S.A.": "especializado",
    "BCO Paulista":    "especializado",
    "BCO SAFRA S.A.":  "especializado",
    "BCO Industrial":  "especializado",
    "BCO INDUSTRIAL DO BRASIL S.A.": "especializado",
    "BCO MERCANTIL DO BRASIL S.A.": "especializado",
    "BCO AGIBANK S.A.": "especializado",
    "BANCO BARI S.A.": "especializado",
    "BCO BV S.A.":     "especializado",
    "BANCO BTG PACTUAL S.A.": "especializado",
    "BCO PINE S.A.":   "especializado",
    "BCO DO NORDESTE DO BRASIL S.A.": "especializado",
    "BCO DO EST. DO PA S.A.": "especializado",

    # CFIs / financeiras especializadas em consignado
    "Parati CFI":      "financeira",
    "PARATI - CFI S.A.": "financeira",
    "PortoSeg":        "financeira",
    "PORTOSEG S.A. CFI": "financeira",
    "Cobuccio":        "financeira",
    "COBUCCIO S.A. SCFI": "financeira",
    "Senff":           "financeira",
    "BCO SENFF S.A.":  "financeira",
    "Volkswagen":      "financeira",
    "BCO VOLKSWAGEN S.A": "financeira",
    "FACTA S.A. CFI":  "financeira",
    "GAZINCRED S.A. SCFI": "financeira",
    "MIDWAY S.A. - SCFI": "financeira",
    "AL5 S.A. SCFI":   "financeira",
    "RPW S.A. SCFI":   "financeira",
    "VALOR S/A SCFI":  "financeira",
    "NEGRESCO S.A. - CFI": "financeira",
    "SANTINVEST S.A. - CFI": "financeira",
    "ZEMA CFI S/A":    "financeira",
    "HS FINANCEIRA":   "financeira",
    "BECKER FINANCEIRA SA - CFI": "financeira",
    "LECCA CFI S.A.":  "financeira",
    "PEFISA S.A. - C.F.I.": "financeira",
    "FINAC ALFA S.A. CFI": "financeira",
    "FINANC ALFA S.A. CFI": "financeira",
    "BCO CSF S.A.":    "financeira",
    "BANCO SEMEAR":    "financeira",
    "NOVO BCO CONTINENTAL S.A. - BM": "financeira",
}

def get_categoria(name):
    # Try direct lookup first
    if name in CATEGORIAS:
        return CATEGORIAS[name]
    # Try via BASE_INST mapping (raw API name → friendly name → categoria)
    friendly = BASE_INST.get(name)
    if friendly and friendly in CATEGORIAS:
        return CATEGORIAS[friendly]
    # Heuristics for unmapped names
    name_upper = name.upper()
    if any(x in name_upper for x in ['SICREDI','SICOOB','COOPERAT','BANRISUL','BANESTES']):
        return "cooperativa"
    if any(x in name_upper for x in ['BRADESCO','SANTANDER','ITAÚ','ITAU','CAIXA','BCO DO BRASIL']):
        return "tradicional"
    if any(x in name_upper for x in ['NUBANK','INTER','DIGIO','NEON','PICPAY','C6 CONSIG','XP']):
        return "fintech"
    if any(x in name_upper for x in ['CFI','SCFI','FINANC','FINAN','FINANCEIRA','CREDITO','CRÉDITO']):
        return "financeira"
    return "especializado"


DATA_FILE = "data.json"

# ── API ───────────────────────────────────────────────────────────────────────

def fetch_bacen_window(data_inicio, data_fim, segmento_filter=None):
    """Busca dados para uma janela de datas, ordenado por data desc para pegar os mais recentes primeiro."""
    base = "https://olinda.bcb.gov.br/olinda/servico/taxaJuros/versao/v2/odata/TaxasJurosDiariaPorInicioPeriodo"
    params = f"?$format=json&$top=10000&$orderby=InicioPeriodo%20desc&dataInicio={data_inicio}&dataFim={data_fim}"
    if segmento_filter:
        params += f"&$filter=Segmento%20eq%20%27{urllib.parse.quote(segmento_filter)}%27"
    url = base + params
    print(f"  GET {data_inicio} \u2192 {data_fim}{' ['+segmento_filter+']' if segmento_filter else ''}")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    records = data.get("value", [])
    print(f"  Recebido: {len(records)} registros")
    return records

def fetch_bacen(data_inicio, data_fim):
    """Busca em janelas de 7 dias para garantir que dados recentes nao sejam cortados pelo limite de 10000."""
    from datetime import datetime, timedelta
    all_records = []
    start = datetime.strptime(data_inicio, "%Y-%m-%d")
    end   = datetime.strptime(data_fim,   "%Y-%m-%d")
    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=6), end)
        w0 = cursor.strftime("%Y-%m-%d")
        w1 = window_end.strftime("%Y-%m-%d")
        try:
            records = fetch_bacen_window(w0, w1, segmento_filter="PESSOA F\u00cdSICA")
            all_records.extend(records)
            if len(records) >= 10000:
                print(f"  AVISO: limite atingido em {w0}\u2192{w1}")
        except Exception as e:
            print(f"  ERRO {w0}: {e}")
        cursor = window_end + timedelta(days=1)
    print(f"  Total combinado: {len(all_records)} registros")
    return all_records


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
        # For all modalidades: include all institutions, using mapped name if available
        name = inst_map.get(raw, raw)
        date = r.get("InicioPeriodo","")[:10]
        taxa = r.get("TaxaJurosAoMes")
        if taxa is not None and date:
            if name not in series:
                series[name] = {}
            series[name][date] = float(taxa)
    return series

def get_date_range(months_back=4):
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
    periods["all"] = {"label": "M\u00e9dia do per\u00edodo", "idx": all_idxs}
    default = f"m{len(month_seq)-1}"

    # Calculate overall average per institution to determine who's ahead of Nubank
    overall_avgs = {}
    for name, dates in series.items():
        vals = [v for v in dates.values() if v is not None]
        if vals:
            overall_avgs[name] = sum(vals) / len(vals)
    nu_overall = overall_avgs.get("Nubank", 999)

    banks = []
    raw = {}
    nu_avgs = {}
    for name in sorted(series.keys(), key=lambda n: (n != "Nubank", n)):
        vals = [series[name].get(d) for d in all_dates]
        raw[name] = vals
        avg_rate = overall_avgs.get(name, 999)
        banks.append({"key": name, "color": get_color(name), "isNubank": name == "Nubank",
                      "ahead": avg_rate < nu_overall and name != "Nubank",
                      "categoria": get_categoria(name)})
        for pk, pv in periods.items():
            idxs = pv["idx"]
            valid = [vals[i] for i in idxs if vals[i] is not None]
            if valid:
                nu_avgs.setdefault(pk, {})[name] = sum(valid)/len(valid)


    # chart_banks: always Nubank + the 5 big traditional banks
    CHART_FIXED = {"Nubank", "Banco do Brasil", "Santander", "Caixa", "Bradesco", "Itaú"}
    chart_banks = [b for b in banks if b["key"] in CHART_FIXED]


    return {"type": "daily", "dates": all_dates, "raw": raw, "banks": banks,
            "chart_banks": chart_banks,
            "periods": periods, "defaultPeriod": default, "avgs": nu_avgs}

def build_monthly_data(series, modkey):
    """Dados com serie temporal diaria + ranking mensal."""
    month_map_short = {"01":"Jan","02":"Fev","03":"Mar","04":"Abr","05":"Mai","06":"Jun",
                       "07":"Jul","08":"Ago","09":"Set","10":"Out","11":"Nov","12":"Dez"}

    # All individual dates for time series chart
    all_dates = sorted({d for s in series.values() for d in s})

    # Month keys for period tabs
    month_keys = sorted({d[:7] for d in all_dates})

    periods = {}
    for mk in month_keys:
        yr, mo = mk[:4], mk[5:7]
        idxs = [i for i, d in enumerate(all_dates) if d[:7] == mk]
        periods[mk] = {"label": f"{month_map_short[mo]} {yr}", "idx": idxs}
    all_idxs = list(range(len(all_dates)))
    periods["all"] = {"label": "Média do período", "idx": all_idxs}
    default = month_keys[-1] if month_keys else "all"

    # Overall average per institution (for chart_banks selection)
    overall_avgs = {}
    for name, dates in series.items():
        vals = [v for v in dates.values() if v is not None]
        if vals:
            overall_avgs[name] = sum(vals) / len(vals)
    nu_overall = overall_avgs.get("Nubank", 999)

    # Build banks list and raw time series
    banks = []
    raw = {}
    for name in sorted(series.keys(), key=lambda n: (n != "Nubank", n)):
        vals = [series[name].get(d) for d in all_dates]
        raw[name] = vals
        avg_rate = overall_avgs.get(name, 999)
        banks.append({"key": name, "color": get_color(name), "isNubank": name == "Nubank",
                      "ahead": avg_rate < nu_overall and name != "Nubank",
                      "categoria": get_categoria(name)})

    # chart_banks: always Nubank + the 5 big traditional banks
    CHART_FIXED = {"Nubank", "Banco do Brasil", "Santander", "Caixa", "Bradesco", "Ita\u00fa"}
    chart_banks = [b for b in banks if b["key"] in CHART_FIXED]

    # Ranked per period (monthly averages for bar chart)
    ranked_per_period = {}
    for pk, pv in periods.items():
        idxs = pv["idx"]
        all_rows = []
        for name in series:
            vals = [raw[name][i] for i in idxs if raw[name][i] is not None] if name in raw else []
            if vals:
                rate = round(sum(vals)/len(vals), 2)
                all_rows.append({"name": name, "rate": rate,
                                 "color": get_color(name), "isNubank": name == "Nubank",
                                 "categoria": get_categoria(name)})
        all_rows.sort(key=lambda r: r["rate"])
        nu_idx = next((i for i, r in enumerate(all_rows) if r["isNubank"]), None)
        for i, r in enumerate(all_rows):
            r["pos"] = i + 1
            r["ahead"] = nu_idx is not None and i < nu_idx
        ranked_per_period[pk] = {
            "rows": all_rows,
            "nuPos": (nu_idx + 1) if nu_idx is not None else None,
            "totalPlayers": len(all_rows)
        }

    return {"type": "monthly", "dates": all_dates, "raw": raw,
            "banks": banks, "chart_banks": chart_banks,
            "periods": periods, "defaultPeriod": default,
            "ranked": ranked_per_period}

def build_html(all_data, generated_at):
    publico = build_publico_data(all_data.get("publico", {}))
    inss    = build_monthly_data(all_data.get("inss", {}), "inss")
    privado = build_monthly_data(all_data.get("privado", {}), "privado")

    publico_js = json.dumps(publico, ensure_ascii=False)
    inss_js    = json.dumps(inss,    ensure_ascii=False)
    privado_js = json.dumps(privado, ensure_ascii=False)

    # JS is built as a plain string (not inside f-string) to avoid brace conflicts
    js = (
        "const PUBLICO=" + publico_js + ";\n"
        "const INSS="    + inss_js    + ";\n"
        "const PRIVADO=" + privado_js + ";\n"
        + JS_CODE
    )

    return (
        """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Comparativo de Taxas \u2014 Cr\u00e9dito Consignado</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#f5f4f0;--surface:#fff;--surface2:#f0efe9;--border:rgba(0,0,0,0.08);--border2:rgba(0,0,0,0.14);--text:#1a1a18;--text2:#5a5a56;--text3:#9a9a94;--nu:#7F77DD;--nu-light:#EEEDFE;--nu-dark:#534AB7;--r:12px}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;padding-bottom:4rem}
header{background:var(--surface);border-bottom:1px solid var(--border);padding:1.25rem 2rem;display:flex;align-items:center;gap:1rem;position:sticky;top:0;z-index:10}
.logo{width:34px;height:34px;background:var(--nu);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:600;color:#fff;flex-shrink:0}
.ht{font-size:14px;font-weight:500}.hs{font-size:11px;color:var(--text3);margin-top:1px}
.hb{margin-left:auto;font-size:11px;font-weight:500;padding:3px 10px;background:var(--nu-light);color:var(--nu-dark);border-radius:20px;white-space:nowrap}
.mtabs{background:var(--surface);border-bottom:1px solid var(--border);padding:0 2rem;display:flex}
.mtab{font-size:13px;font-weight:500;padding:.875rem 1.25rem;border:none;background:transparent;color:var(--text3);cursor:pointer;border-bottom:2px solid transparent;transition:all .15s}
.mtab:hover{color:var(--text2)}.mtab.active{color:var(--nu-dark);border-bottom-color:var(--nu)}
main{max-width:960px;margin:0 auto;padding:1.75rem 1.5rem}
.panel{display:none}.panel.active{display:block}
.hero{margin-bottom:1.5rem}
.hero h2{font-size:22px;font-weight:600;letter-spacing:-0.02em;line-height:1.3}
.hero p{font-size:13px;color:var(--text2);margin-top:.4rem;line-height:1.6}
.ptabs{display:flex;gap:6px;margin-bottom:1.5rem;flex-wrap:wrap}
.ptab{font-size:12px;font-family:'DM Sans',sans-serif;padding:5px 14px;border-radius:20px;border:1px solid var(--border2);background:transparent;color:var(--text2);cursor:pointer;transition:all .15s}
.ptab:hover{background:var(--surface2)}.ptab.active{background:var(--text);color:#fff;border-color:var(--text)}
.mgrid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;margin-bottom:1.5rem}
@media(max-width:700px){.mgrid{grid-template-columns:repeat(3,1fr)}}@media(max-width:480px){.mgrid{grid-template-columns:repeat(2,1fr)}}
.mc{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:1rem 1.1rem}
.ml{font-size:10px;color:var(--text3);font-weight:500;text-transform:uppercase;letter-spacing:.04em;margin-bottom:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mv{font-size:24px;font-weight:600;font-family:'DM Mono',monospace;letter-spacing:-0.02em}
.ms{font-size:10px;color:var(--text3);margin-top:3px}
.mb{display:inline-block;font-size:10px;font-weight:500;padding:2px 7px;border-radius:4px;margin-top:5px}
.bnu{background:var(--nu-light);color:var(--nu-dark)}.bwarn{background:#FFF3E0;color:#B45309}.bdanger{background:#FFEBEE;color:#C62828}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:1.5rem;margin-bottom:1.25rem}
.ct{font-size:14px;font-weight:500;margin-bottom:2px}.cs{font-size:12px;color:var(--text3);margin-bottom:1.25rem}
.legend{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:1.25rem}
.li{display:flex;align-items:center;gap:5px;font-size:11px;color:var(--text2)}
.ld{width:10px;height:10px;border-radius:2px;flex-shrink:0}
.cw{position:relative;width:100%;height:280px}
.bar-row{display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:.5px solid var(--border)}
.bar-row:last-child{border-bottom:none}
.bar-pos{font-size:11px;color:var(--text3);width:24px;text-align:right;font-family:'DM Mono',monospace;flex-shrink:0}
.bar-badge{width:64px;flex-shrink:0}
.bar-badge-pill{font-size:9px;font-weight:600;padding:2px 6px;border-radius:4px;white-space:nowrap}
.b-nu{background:var(--nu-light);color:var(--nu-dark)}.b-ahead{background:#E8F5E9;color:#2E7D32}.b-trad{background:#F3F4F6;color:#6B7280}.b-fintech{background:#EFF6FF;color:#1D4ED8}.b-coop{background:#F0FDF4;color:#15803D}.b-fin{background:#FFF7ED;color:#C2410C}
.bar-name{font-size:13px;font-weight:500;flex:1;min-width:0}
.bar-name.nu{color:var(--nu-dark)}
.bar-track{flex:1;height:7px;background:var(--surface2);border-radius:4px;overflow:hidden;max-width:200px;flex-shrink:0}
.bar-fill{height:100%;border-radius:4px}
.bar-val{font-size:12px;font-weight:500;font-family:'DM Mono',monospace;width:52px;text-align:right;flex-shrink:0}
.bar-ano{font-size:11px;color:var(--text3);font-family:'DM Mono',monospace;width:64px;text-align:right;flex-shrink:0}
@media(max-width:600px){.bar-track,.bar-ano{display:none}}
.nu-highlight{background:linear-gradient(90deg,#EEEDFE33,transparent);border-radius:6px}
.insight{background:#EFF6FF;border:1px solid #BFDBFE;border-radius:var(--r);padding:1rem 1.25rem;font-size:13px;color:#1E40AF;line-height:1.7;margin-bottom:1.25rem}
.insight strong{font-weight:600}
.source{font-size:11px;color:var(--text3);margin-top:1.5rem;text-align:center;line-height:1.8}
.source a{color:var(--text3)}
</style>
</head>
<body>
<div id="lock-screen" style="position:fixed;inset:0;background:#f5f4f0;display:flex;align-items:center;justify-content:center;z-index:9999">
  <div style="background:#fff;border:1px solid rgba(0,0,0,0.08);border-radius:16px;padding:2.5rem 2rem;width:320px;text-align:center">
    <div style="width:44px;height:44px;background:#EEEDFE;border-radius:10px;display:flex;align-items:center;justify-content:center;margin:0 auto 1.25rem">
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><rect x="4" y="9" width="12" height="9" rx="2" stroke="#7C3AED" stroke-width="1.5"/><path d="M7 9V6a3 3 0 016 0v3" stroke="#7C3AED" stroke-width="1.5" stroke-linecap="round"/></svg>
    </div>
    <div style="font-size:15px;font-weight:600;color:#1a1a18;margin-bottom:4px">Acesso restrito</div>
    <div style="font-size:12px;color:#9a9a94;margin-bottom:1.5rem">Insira a senha para continuar</div>
    <input id="pwd-input" type="password" placeholder="Senha" onkeydown="if(event.key==='Enter')checkPwd()" style="width:100%;padding:9px 14px;border:1px solid rgba(0,0,0,0.14);border-radius:10px;font-size:13px;font-family:DM Sans,sans-serif;outline:none;box-sizing:border-box;text-align:center;letter-spacing:0.1em" />
    <div id="pwd-error" style="font-size:11px;color:#C62828;margin-top:6px;min-height:16px"></div>
    <button onclick="checkPwd()" style="margin-top:8px;width:100%;padding:9px;background:#7C3AED;color:#fff;border:none;border-radius:10px;font-size:13px;font-weight:600;font-family:DM Sans,sans-serif;cursor:pointer">Entrar</button>
  </div>
</div>
<header>
  <div class="logo">TX</div>
  <div><div class="ht">Comparativo de Taxas de Juros</div><div class="hs">Cr\u00e9dito Consignado \u00b7 Prefixado \u00b7 Pessoa F\u00edsica \u00b7 Bacen</div></div>
  <div style="margin-left:auto;display:flex;align-items:center;gap:8px"><span style="display:inline-flex;align-items:center;gap:6px;font-size:10px;font-weight:600;padding:5px 12px 5px 8px;background:#F3F0FF;color:#5B21B6;border-radius:20px;letter-spacing:0.04em;border:1px solid #DDD6FE;white-space:nowrap"><svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="6.5" stroke="#7C3AED" stroke-width="1"/><path d="M7 3.5C7 3.5 8.5 5 8.5 7C8.5 9 7 10.5 7 10.5C7 10.5 5.5 9 5.5 7C5.5 5 7 3.5 7 3.5Z" stroke="#7C3AED" stroke-width="1" stroke-linejoin="round"/><path d="M3.5 7H10.5" stroke="#7C3AED" stroke-width="1"/></svg>Powered by AI | Research Team</span><div class="hb">Atualizado em """
        + generated_at +
        """</div></div>
</header>
<div class="mtabs" style="justify-content:space-between;align-items:center">
  <div style="display:flex">
  <button class="mtab active" onclick="showModal('publico',this)" data-pt="Consignado P\u00fablico" data-en="Public Payroll">Consignado P\u00fablico</button>
  <button class="mtab" onclick="showModal('inss',this)" data-pt="Consignado INSS" data-en="INSS Payroll">Consignado INSS</button>
  <button class="mtab" onclick="showModal('privado',this)" data-pt="Consignado Privado" data-en="Private Payroll">Consignado Privado</button>
  </div>
  <button id="lang-btn" onclick="toggleLang()" style="font-size:11px;font-weight:600;padding:4px 12px;border:1px solid var(--border2);border-radius:20px;background:transparent;color:var(--text2);cursor:pointer;white-space:nowrap;margin-right:4px">EN</button>
</div>
<main>
  <div id="p-publico" class="panel active"></div>
  <div id="p-inss" class="panel"></div>
  <div id="p-privado" class="panel"></div>
  <div class="source">Fonte: <a href="https://dadosabertos.bcb.gov.br/dataset/taxas-de-juros-de-operacoes-de-credito" target="_blank">Banco Central do Brasil</a> \u2014 Hist\u00f3rico de Taxa de Juros \u00b7 Gerado em """
        + generated_at +
        """</div>
</main>
<script>
"""
        + js +
        """
</script>
</body>
</html>"""
    )


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
