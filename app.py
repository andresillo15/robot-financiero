# -*- coding: utf-8 -*-
"""app.py

Robot Financiero Inteligente con integración completa de Google Gemini (google-genai)
corregido para compatibilidad de Gradio (formato tuplas en Chatbot) y binding para Render.
"""

# BLOQUE 1 — Librerías y configuración visual (estilo Yahoo Finance)
import os
import warnings
from datetime import date, timedelta
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import gradio as gr
import yfinance as yf
import numpy_financial as npf

# Intentar importar el SDK oficial de Google GenAI
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

warnings.filterwarnings("ignore")
plt.rcParams["figure.facecolor"] = "#0B0E11"
plt.rcParams["axes.facecolor"] = "#0B0E11"
plt.rcParams["savefig.facecolor"] = "#0B0E11"
plt.rcParams["text.color"] = "#EAECEF"
plt.rcParams["axes.labelcolor"] = "#EAECEF"
plt.rcParams["xtick.color"] = "#848E9C"
plt.rcParams["ytick.color"] = "#848E9C"
plt.rcParams["axes.edgecolor"] = "#2B2F36"
plt.rcParams["grid.color"] = "#1E2329"
plt.rcParams["font.size"] = 10

# Colores estilo Yahoo Finance
YF = {
    "bg": "#0B0E11",
    "card": "#1E2329",
    "border": "#2B2F36",
    "text": "#EAECEF",
    "muted": "#848E9C",
    "green": "#0ECB81",
    "red": "#F6465D",
    "blue": "#3861FB",
    "yellow": "#F0B90B",
    "header": "#181A20",
}

ANIO_ACTUAL = date.today().year
ANIOS = [str(a) for a in range(ANIO_ACTUAL, 2014, -1)]

print("✅ BLOQUE 1 listo")

# BLOQUE 2 — Catálogo
CATALOGO = {
    "AAPL": "Apple Inc.", "MSFT": "Microsoft Corporation", "GOOGL": "Alphabet Inc. (Google)",
    "AMZN": "Amazon.com Inc.", "META": "Meta Platforms Inc.", "NVDA": "NVIDIA Corporation",
    "TSLA": "Tesla Inc.", "NFLX": "Netflix Inc.", "ADBE": "Adobe Inc.", "ORCL": "Oracle Corporation",
    "CRM": "Salesforce Inc.", "INTC": "Intel Corporation", "AMD": "Advanced Micro Devices",
    "KO": "The Coca-Cola Company", "PEP": "PepsiCo Inc.", "MCD": "McDonald's Corporation",
    "SBUX": "Starbucks Corporation", "NKE": "Nike Inc.", "WMT": "Walmart Inc.",
    "COST": "Costco Wholesale", "TGT": "Target Corporation", "HD": "The Home Depot",
    "JPM": "JPMorgan Chase & Co.", "BAC": "Bank of America", "V": "Visa Inc.",
    "MA": "Mastercard Inc.", "GS": "Goldman Sachs", "MS": "Morgan Stanley",
    "JNJ": "Johnson & Johnson", "PFE": "Pfizer Inc.", "UNH": "UnitedHealth Group",
    "ABBV": "AbbVie Inc.", "MRK": "Merck & Co.",
    "XOM": "Exxon Mobil Corporation", "CVX": "Chevron Corporation",
    "BA": "The Boeing Company", "CAT": "Caterpillar Inc.", "GE": "General Electric",
    "DIS": "The Walt Disney Company", "PG": "Procter & Gamble",
    "VZ": "Verizon Communications", "T": "AT&T Inc.", "IBM": "IBM Corporation",
}

OPCIONES = sorted([f"{n} ({t})" for t, n in CATALOGO.items()])
OPCIONES_MANUAL = ["Manual / PYME (ingresar datos)"] + OPCIONES

def ticker_de(opcion):
    if not opcion or "Manual" in str(opcion) or "PYME" in str(opcion):
        return ""
    return str(opcion).split("(")[-1].replace(")", "").strip()

def nombre_de(ticker):
    return CATALOGO.get(ticker, ticker or "Empresa manual")

print(f"✅ BLOQUE 2 — {len(CATALOGO)} empresas")

# BLOQUE 3 — Descarga de precios y estados financieros
def descargar_precios(opciones, anio):
    if not opciones:
        raise ValueError("Selecciona entre 1 y 5 empresas.")
    if isinstance(opciones, str):
        opciones = [opciones]
    tickers = [ticker_de(o) for o in opciones if ticker_de(o)]
    if not tickers:
        raise ValueError("No hay tickers válidos.")
    if len(tickers) > 5:
        raise ValueError("Máximo 5 empresas.")
    if len(set(tickers)) != len(tickers):
        raise ValueError("Empresas repetidas.")

    anio = int(anio)
    inicio = f"{anio}-01-01"
    fin = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d") if anio >= ANIO_ACTUAL else f"{anio+1}-01-01"

    datos = yf.download(tickers, start=inicio, end=fin, interval="1d", progress=False, auto_adjust=True, threads=False)
    if datos is None or datos.empty:
        raise ValueError("Sin datos de Yahoo Finance.")

    if isinstance(datos.columns, pd.MultiIndex):
        precios = datos["Close"].copy()
    else:
        precios = datos[["Close"]].copy()
        precios.columns = tickers

    precios = precios.dropna(how="all").dropna(axis=1, how="all")
    if precios.empty:
        raise ValueError("Datos vacíos tras limpieza.")
    cols = [t for t in tickers if t in precios.columns]
    return precios[cols]


def _buscar(df, claves):
    if df is None or getattr(df, "empty", True):
        return None
    idx = {str(i).lower(): i for i in df.index}
    for c in claves:
        for low, orig in idx.items():
            if c in low:
                val = df.loc[orig]
                val = val.iloc[0] if hasattr(val, "iloc") else val
                try:
                    f = float(val)
                    return f if pd.notna(f) else None
                except Exception:
                    pass
    return None


def estados_yahoo(ticker):
    ticker = (ticker or "").upper().strip()
    vacio = {
        "ticker": ticker, "nombre": nombre_de(ticker) if ticker else "Manual",
        "sector": "N/D", "activo_corriente": 0, "pasivo_corriente": 0, "inventarios": 0,
        "activos_totales": 0, "pasivo_total": 0, "patrimonio": 0, "utilidades_retenidas": 0,
        "utilidad_neta": 0, "ventas": 0, "utilidad_operativa": 0, "valor_mercado_patrimonio": 0,
        "mensaje": "Completa los campos manualmente.",
    }
    if not ticker:
        return vacio
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        bs, fin = t.balance_sheet, t.financials
        mc = info.get("marketCap")
        try:
            mc = float(mc) if mc else 0
        except Exception:
            mc = 0
        return {
            "ticker": ticker,
            "nombre": info.get("longName") or nombre_de(ticker),
            "sector": info.get("sector", "N/D"),
            "activo_corriente": _buscar(bs, ["current assets", "total current assets"]) or 0,
            "pasivo_corriente": _buscar(bs, ["current liabilities", "total current liabilities"]) or 0,
            "inventarios": _buscar(bs, ["inventory", "inventories"]) or 0,
            "activos_totales": _buscar(bs, ["total assets"]) or 0,
            "pasivo_total": _buscar(bs, ["total liabilities net minority interest", "total liabilities"]) or 0,
            "patrimonio": _buscar(bs, ["stockholders equity", "total equity gross minority interest", "common stock equity"]) or 0,
            "utilidades_retenidas": _buscar(bs, ["retained earnings"]) or 0,
            "utilidad_neta": _buscar(fin, ["net income", "net income common stockholders"]) or 0,
            "ventas": _buscar(fin, ["total revenue", "operating revenue"]) or 0,
            "utilidad_operativa": _buscar(fin, ["ebit", "operating income"]) or 0,
            "valor_mercado_patrimonio": mc,
            "mensaje": f"Datos de {info.get('longName', ticker)} cargados desde Yahoo Finance. Revisa y completa si falta algo.",
        }
    except Exception as e:
        vacio["mensaje"] = f"Error al cargar {ticker}: {e}. Usa modo manual."
        return vacio

print("✅ BLOQUE 3 listo")

# BLOQUE 4 — Calculadora (interés, VAN, TIR, CAPM, WACC, EVA…)
def _pos(v, nom="Valor"):
    v = float(v)
    if v <= 0:
        raise ValueError(f"{nom} debe ser > 0")
    return v

def _tasa(v):
    v = float(v)
    if v <= -1:
        raise ValueError("Tasa inválida")
    return v

def fmt(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/A"
    s = f"{float(v):,.2f}"
    return "$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")

def interes_simple(c, r, t):
    c, r, t = _pos(c, "Capital"), _tasa(r), _pos(t, "Tiempo")
    i = c * r * t
    return i, c + i

def interes_compuesto(c, r, n):
    c, r, n = _pos(c, "Capital"), _tasa(r), _pos(n, "Periodos")
    m = c * (1 + r) ** n
    return m - c, m

def valor_futuro(vp, r, n):
    return _pos(vp, "VP") * (1 + _tasa(r)) ** _pos(n, "n")

def valor_presente(vf, r, n):
    return _pos(vf, "VF") / (1 + _tasa(r)) ** _pos(n, "n")

def vp_anualidad(cuota, r, n, tipo="ordinaria"):
    cuota, r, n = _pos(cuota, "Cuota"), _tasa(r), _pos(n, "n")
    f = n if abs(r) < 1e-12 else (1 - (1 + r) ** (-n)) / r
    if tipo == "anticipada":
        f *= 1 + r
    return cuota * f

def vf_anualidad(cuota, r, n, tipo="ordinaria"):
    cuota, r, n = _pos(cuota, "Cuota"), _tasa(r), _pos(n, "n")
    f = n if abs(r) < 1e-12 else ((1 + r) ** n - 1) / r
    if tipo == "anticipada":
        f *= 1 + r
    return cuota * f

def tabla_amortizacion(c, r, n):
    c, r, n = _pos(c, "Capital"), _tasa(r), int(_pos(n, "n"))
    cuota = c / n if abs(r) < 1e-12 else c * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
    saldo, filas = c, []
    for i in range(1, n + 1):
        inte = saldo * r
        amort = cuota - inte
        saldo = max(0.0, saldo - amort)
        filas.append({"Periodo": i, "Cuota": cuota, "Interés": inte, "Amortización": amort, "Saldo": saldo})
    return pd.DataFrame(filas), cuota

def conversion_tasas(tasa, m_or, m_des, tipo="nominal"):
    tasa, m_or, m_des = _tasa(tasa), int(_pos(m_or)), int(_pos(m_des))
    ef = (1 + tasa / m_or) ** m_or - 1 if tipo == "nominal" else tasa
    nom = m_des * ((1 + ef) ** (1 / m_des) - 1)
    efd = (1 + nom / m_des) ** m_des - 1
    return ef, nom, efd

def calcular_tir(flujos):
    f = [float(x) for x in flujos]
    if len(f) < 2:
        raise ValueError("Mínimo 2 flujos")
    tir = npf.irr(f)
    if np.isnan(tir):
        raise ValueError("No converge la TIR con estos flujos")
    return float(tir)

def calcular_van(flujos, tasa):
    tasa = _tasa(tasa)
    return float(sum(x / (1 + tasa) ** t for t, x in enumerate(flujos)))

def calcular_capm(rf, beta, rm):
    return _tasa(rf) + float(beta) * (_tasa(rm) - _tasa(rf))

def calcular_wacc(ke, kd, e, d, tax):
    ke, kd = _tasa(ke), _tasa(kd)
    e, d = _pos(e, "E"), max(0.0, float(d))
    tax = max(0.0, min(1.0, float(tax)))
    v = e + d
    if v == 0:
        raise ValueError("E+D = 0")
    return (e / v) * ke + (d / v) * kd * (1 - tax)

def calcular_eva(nopat, wacc, capital):
    return float(nopat) - _tasa(wacc) * _pos(capital, "Capital")

print("✅ BLOQUE 4 listo")

# BLOQUE 5 — Diagnóstico (razones, DuPont, Z de Altman)
def calcular_diagnostico(ac, pc, inv, un, ven, at, pat, pt, ur, uo, vm):
    ac, pc, inv = float(ac or 0), float(pc or 0), float(inv or 0)
    un, ven, at = float(un or 0), float(ven or 0), float(at or 0)
    pat, pt, ur = float(pat or 0), float(pt or 0), float(ur or 0)
    uo, vm = float(uo or 0), float(vm or 0)
    if at <= 0:
        raise ValueError("Activos totales debe ser > 0")

    rc = None if pc == 0 else ac / pc
    pa = None if pc == 0 else (ac - inv) / pc
    ktn = ac - pc
    mn = None if ven == 0 else un / ven
    roa_v = None if at == 0 else un / at
    roe_v = None if pat == 0 else un / pat
    end = None if at == 0 else pt / at
    mult = None if pat == 0 else at / pat
    rot = None if at == 0 else ven / at
    dupont = None if None in (mn, rot, mult) else mn * rot * mult

    z = None
    if at > 0 and pt > 0:
        z = 1.2 * (ktn / at) + 1.4 * (ur / at) + 3.3 * (uo / at) + 0.6 * (vm / pt) + 1.0 * (ven / at)

    if z is None:
        z_info = {"zona": "No calculable", "color": YF["muted"], "rec": "Faltan datos."}
    elif z > 2.99:
        z_info = {"zona": "Zona Segura", "color": YF["green"], "rec": "Situación sólida. Bajo riesgo de insolvencia."}
    elif z >= 1.81:
        z_info = {"zona": "Zona Gris", "color": YF["yellow"], "rec": "Zona intermedia. Vigilar liquidez y deuda."}
    else:
        z_info = {"zona": "Zona de Riesgo", "color": YF["red"], "rec": "Riesgo elevado. Revisar liquidez y endeudamiento."}

    def p(x):
        return f"{x*100:.2f}%" if x is not None else "N/D"
    def n(x):
        return f"{x:,.2f}" if x is not None else "N/D"

    md = f"""
### Diagnóstico financiero
| Indicador | Valor |
| :--- | :---: |
| Razón Corriente | {n(rc)} |
| Prueba Ácida | {n(pa)} |
| Capital Trabajo Neto | {n(ktn)} |
| Margen Neto | {p(mn)} |
| ROA | {p(roa_v)} |
| ROE | {p(roe_v)} |
| Endeudamiento | {p(end)} |
| ROE DuPont | {p(dupont)} |
| **Z de Altman** | **{n(z)}** |

**Clasificación Z:** <span style="color:{z_info['color']};font-weight:700">{z_info['zona']}</span>

{z_info['rec']}
"""
    razones = {
        "razon_corriente": rc, "prueba_acida": pa, "ktn": ktn, "margen_neto": mn,
        "roa": roa_v, "roe": roe_v, "endeudamiento": end, "dupont": dupont, "z": z,
    }
    return {"razones": razones, "z_info": z_info, "texto_md": md}

print("✅ BLOQUE 5 listo")

# BLOQUE 6 — Riesgo de mercado + 6 riesgos + simulación de decisión
def metricas_mercado(serie, nombre="Activo"):
    s = serie.dropna()
    if len(s) < 10:
        raise ValueError("Pocos datos de precio")
    ret = s.pct_change().dropna()
    mu, sig = float(ret.mean()), float(ret.std(ddof=1))
    vol_a = sig * np.sqrt(252)
    cv = abs(vol_a / (mu * 252)) if abs(mu) > 1e-12 else float("inf")
    var95 = -(mu - 1.65 * sig)
    var99 = -(mu - 2.33 * sig)
    dd = float((s / s.cummax() - 1).min())
    return {
        "nombre": nombre, "mu_diario": mu, "sigma_diario": sig,
        "volatilidad_anual": vol_a, "coeficiente_variacion": cv,
        "var_1d_95": var95, "var_1d_99": var99, "max_drawdown": dd,
        "retorno_total": float(s.iloc[-1] / s.iloc[0] - 1),
        "retornos": ret, "n_obs": len(s),
    }

def seis_riesgos(m=None, razones=None, sector="N/D"):
    m, razones = m or {}, razones or {}
    vol, rc, end, roe = m.get("volatilidad_anual"), razones.get("razon_corriente"), razones.get("endeudamiento"), razones.get("roe")
    out = {}
    if vol is None:
        out["mercado"] = ("medio", "Sin precios")
    else:
        out["mercado"] = ("alto" if vol > 0.45 else "medio" if vol > 0.25 else "bajo", f"Vol {vol*100:.1f}%")
    if end is None:
        out["credito"] = ("medio", "Sin endeudamiento")
    else:
        out["credito"] = ("alto" if end > 0.7 else "medio" if end > 0.45 else "bajo", f"Deuda {end*100:.0f}%")
    if rc is None:
        out["liquidez"] = ("medio", "Sin RC")
    else:
        out["liquidez"] = ("alto" if rc < 1 else "medio" if rc < 1.5 else "bajo", f"RC {rc:.2f}")
    sec = (sector or "").lower()
    alto = any(x in sec for x in ("energy", "retail", "auto", "airline"))
    out["operacional"] = ("medio" if alto else "bajo", f"Sector {sector}")
    out["legal"] = ("medio", "Regulación de valores / sector")
    out["reputacional"] = ("medio" if (roe is not None and roe < 0) else "bajo", "Según ROE y señales")
    return out

def texto_riesgos(m, riesgos):
    em = {"bajo": "🟢", "medio": "🟡", "alto": "🔴"}
    md = f"""### Riesgo de mercado — {m['nombre']}
| Indicador | Valor |
| :--- | :---: |
| Retorno periodo | {m['retorno_total']*100:+.2f}% |
| Volatilidad anual | {m['volatilidad_anual']*100:.2f}% |
| CV | {m['coeficiente_variacion']:.2f} |
| VaR 1d 95% | {m['var_1d_95']*100:.2f}% |
| VaR 1d 99% | {m['var_1d_99']*100:.2f}% |
| Máx Drawdown | {m['max_drawdown']*100:.2f}% |

### 6 riesgos empresariales
| Riesgo | Nivel | Detalle |
| :--- | :---: | :--- |
"""
    labels = {
        "mercado": "1. Mercado", "credito": "2. Crédito", "liquidez": "3. Liquidez",
        "operacional": "4. Operacional", "legal": "5. Legal", "reputacional": "6. Reputacional",
    }
    for k, lab in labels.items():
        niv, det = riesgos[k]
        md += f"| {lab} | {em.get(niv,'⚪')} **{niv.upper()}** | {det} |\n"
    return md

def simulacion_decision(mu, sigma, n=2000, umbral=0.30, horizonte=252):
    n = max(1000, int(n))
    rng = np.random.default_rng(42)
    shocks = rng.normal(mu, sigma, size=(n, horizonte))
    dist = np.prod(1 + shocks, axis=1) - 1
    p_bad = float(np.mean(dist < 0))
    ret_e = float(np.mean(dist))
    if p_bad > umbral:
        decision, motivo = "rechazar", f"P(pérdida)={p_bad*100:.1f}% > umbral {umbral*100:.0f}%"
    elif p_bad > umbral / 2:
        decision, motivo = "revisar", f"P(pérdida)={p_bad*100:.1f}% zona intermedia"
    else:
        decision = "aceptar" if ret_e > 0 else "revisar"
        motivo = f"P(pérdida)={p_bad*100:.1f}%, retorno esp. {ret_e*100:.1f}%"
    detalle = f"""**Decisión: {decision.upper()}**

{motivo}

- Escenarios: {n} | Horizonte: {horizonte} días
- μ diario: {mu:.6f} | σ diario: {sigma:.6f}
- Retorno esperado: {ret_e*100:.2f}%
- P5: {np.percentile(dist,5)*100:.2f}% | P95: {np.percentile(dist,95)*100:.2f}%
"""
    return {"decision": decision, "probabilidad_desfavorable": p_bad, "retorno_esperado": ret_e,
            "distribucion": dist, "detalle": detalle}

print("✅ BLOQUE 6 listo")

# BLOQUE 7 — Integrado, IA (Google Gemini) y chatbot
def analisis_integrado(diag, pack_riesgo):
    razones = (diag or {}).get("razones") or {}
    z_info = (diag or {}).get("z_info") or {}
    m = (pack_riesgo or {}).get("metricas") or {}
    riesgos = (pack_riesgo or {}).get("riesgos") or {}
    score = 50.0
    z, rc, end, roe, vol = razones.get("z"), razones.get("razon_corriente"), razones.get("endeudamiento"), razones.get("roe"), m.get("volatilidad_anual")
    if z is not None:
        score += 20 if z > 2.99 else (5 if z >= 1.81 else -25)
    if rc is not None:
        score += 10 if rc >= 1.5 else (-15 if rc < 1 else 0)
    if end is not None:
        score += -15 if end > 0.7 else (-5 if end > 0.45 else 5)
    if roe is not None:
        score += 10 if roe >= 0.12 else (-10 if roe < 0.05 else 3)
    if vol is not None:
        score += -15 if vol > 0.45 else (-5 if vol > 0.25 else 5)
    if riesgos:
        mapa = {"bajo": 20, "medio": 50, "alto": 80}
        avg = np.mean([mapa.get(v[0], 50) for v in riesgos.values()])
        score += (50 - avg) / 5
    score = float(np.clip(score, 0, 100))
    if score >= 70:
        clasif, color, msg = "saludable", YF["green"], "Diagnóstico **SALUDABLE**. Solidez y riesgo controlado."
    elif score >= 45:
        clasif, color, msg = "precaucion", YF["yellow"], "Diagnóstico en **PRECAUCIÓN**. Señales mixtas; revisar debilidades."
    else:
        clasif, color, msg = "alerta", YF["red"], "Diagnóstico en **ALERTA**. Vulnerabilidades materiales."
    md = f"""## Análisis integrado <span style="color:{color}">● {clasif.upper()}</span>

{msg}

**Score:** {score:.1f} / 100

| Clave | Valor |
| :--- | :---: |
| Z Altman | {z:.2f if isinstance(z, (int, float)) else 'N/D'} |
| Zona Z | {z_info.get('zona', 'N/D')} |
| Razón corriente | {rc:.2f if isinstance(rc, (int, float)) else 'N/D'} |
| ROE | {f'{roe*100:.2f}%' if isinstance(roe, (int, float)) else 'N/D'} |
| Endeudamiento | {f'{end*100:.2f}%' if isinstance(end, (int, float)) else 'N/D'} |
| Volatilidad | {f'{vol*100:.2f}%' if isinstance(vol, (int, float)) else 'N/D'} |
"""
    return {"clasificacion": clasif, "score": score, "texto_md": md, "z_info": z_info, "razones": razones}

def analisis_ia(integ, sim):
    api_key = os.getenv("GEMINI_API_KEY")
    c = (integ or {}).get("clasificacion", "N/D")
    score = (integ or {}).get("score", 0)
    d = (sim or {}).get("decision", "N/D")
    p = (sim or {}).get("probabilidad_desfavorable")
    r = (sim or {}).get("retorno_esperado")
    
    if not api_key:
        return f"""### Panel IA (Modo respaldo sin API Key)

* **Clasificación integrada:** {c} (Score: {score:.1f}/100)
* **Decisión Montecarlo:** {d}
* **P(desfavorable):** {(p*100 if p is not None else 0):.1f}%
* **Retorno esperado:** {(r*100 if r is not None else 0):.1f}%

> *Configura GEMINI_API_KEY en Environment de Render para análisis generativo en tiempo real.*"""

    if not GENAI_AVAILABLE:
        return "⚠️ Falta instalar el paquete `google-genai`. Añádelo a requirements.txt."

    prompt = f"""
    Actúa como asesor y analista financiero cuantitativo senior. Genera una conclusión ejecutiva estructurada (máximo 3 párrafos breves) con los siguientes datos:
    - Estado de solvencia/salud: {c} (Score: {score:.1f}/100)
    - Recomendación de simulación Montecarlo: {d}
    - Probabilidad de pérdida proyectada: {(p*100 if p is not None else 0):.1f}%
    - Rendimiento esperado proyectado: {(r*100 if r is not None else 0):.1f}%

    Estructura la respuesta:
    1. **Diagnóstico Integral:** Evalúa la solidez, liquidez y riesgo de quiebra.
    2. **Perfil Riesgo-Rendimiento:** Interpreta la probabilidad de pérdida frente al retorno.
    3. **Recomendación Accionable:** Decisión fundamentada de inversión o reestructuración.
    """
    try:
        client = genai.Client(api_key=api_key)
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return "### 🤖 Diagnóstico Financiero con Gemini\n\n" + res.text
    except Exception as e:
        return f"Error al generar informe con Gemini: {e}"

CONCEPTOS = {
    "wacc": "WACC = costo promedio de deuda y equity. Rentabilidad mínima para no destruir valor.",
    "eva": "EVA > 0 crea valor; EVA < 0 destruye valor.",
    "roe": "ROE = Utilidad neta / Patrimonio.",
    "roa": "ROA = Utilidad neta / Activos totales.",
    "z altman": "Z>2.99 segura | 1.81–2.99 gris | <1.81 riesgo.",
    "z de altman": "Z>2.99 segura | 1.81–2.99 gris | <1.81 riesgo.",
    "var": "VaR = pérdida máxima esperada a un horizonte y confianza.",
    "volatilidad": "Mide oscilación del precio. Anual ≈ σ diaria × √252.",
    "montecarlo": "Miles de escenarios aleatorios calibrados con datos reales.",
    "tir": "Tasa que hace VAN = 0.",
    "van": "Valor actual neto de los flujos. VAN>0 sugiere valor.",
    "capm": "Ke = Rf + β×(Rm−Rf).",
    "razon corriente": "Activo corriente / Pasivo corriente. >1.5 suele ser saludable.",
    "dupont": "ROE = margen × rotación × apalancamiento.",
}

def chatbot_responder(pregunta, contexto=None):
    if not pregunta or not str(pregunta).strip():
        return "Escribe una pregunta sobre la empresa analizada, finanzas corporativas o métricas."
    
    api_key = os.getenv("GEMINI_API_KEY")
    contexto = contexto or {}
    
    if not api_key or not GENAI_AVAILABLE:
        q = pregunta.lower()
        for k, v in CONCEPTOS.items():
            if k in q:
                return f"**{k.upper()}**\n\n{v}"
        if any(x in q for x in ("zona", "riesgo", "altman", "quiebra")):
            zi = contexto.get("z_info") or {}
            if zi:
                return f"Z de Altman: **{zi.get('zona','N/D')}**\n\n{zi.get('rec','')}"
            if contexto.get("clasificacion"):
                return f"Clasificación integrada: **{contexto['clasificacion']}**"
        if "decisión" in q or "decision" in q or "simula" in q:
            if contexto.get("decision"):
                return f"La simulación recomendó: **{contexto['decision'].upper()}**"
        return "Modo básico activo. Puedes preguntar por WACC, EVA, ROE, Z Altman, VaR, TIR o VAN."

    prompt = f"""
    Eres un tutor y asesor financiero inteligente experto.
    Contexto financiero actual de la sesión del usuario:
    - Clasificación: {contexto.get('clasificacion', 'No calculada')}
    - Decisión Montecarlo: {contexto.get('decision', 'No calculada')}
    - Zona Z Altman: {((contexto.get('z_info') or {}).get('zona', 'N/D'))}

    Pregunta del usuario: "{pregunta}"

    Responde de forma clara, profesional, concisa y educativa en español. Si la consulta tiene que ver con los datos de la empresa cargada, fundamenta tu explicación con el contexto actual.
    """
    try:
        client = genai.Client(api_key=api_key)
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return res.text
    except Exception as e:
        return f"Error en el asistente: {e}"

print("✅ BLOQUE 7 listo")

# BLOQUE 8 — Funciones conectadas a la UI
def pipeline_mercado(opciones, anio):
    try:
        precios = descargar_precios(opciones, anio)
        tickers = list(precios.columns)
        base = precios.apply(lambda s: s.dropna().iloc[0])
        p100 = (precios / base) * 100
        rets = precios.pct_change().dropna(how="all")
        vol = rets.std() * np.sqrt(252)
        ret = (precios.iloc[-1] / base - 1) * 100
        dd = (precios / precios.cummax() - 1).min() * 100

        fig1, ax1 = plt.subplots(figsize=(9, 4))
        for i, c in enumerate(tickers):
            color = YF["green"] if ret[c] >= 0 else YF["red"]
            if len(tickers) > 1:
                color = [YF["blue"], YF["green"], YF["yellow"], YF["red"], "#A855F7"][i % 5]
            ax1.plot(p100.index, p100[c], lw=2, color=color, label=nombre_de(c))
        ax1.axhline(100, color=YF["muted"], ls="--", lw=1)
        ax1.set_title(f"Performance Base 100 — {anio}", color=YF["text"])
        ax1.legend(facecolor=YF["card"], edgecolor=YF["border"], labelcolor=YF["text"], fontsize=8)
        ax1.grid(True, alpha=0.25)
        plt.tight_layout()

        fig2, ax2 = plt.subplots(figsize=(9, 3.5))
        for i, c in enumerate(tickers):
            color = [YF["blue"], YF["green"], YF["yellow"], YF["red"], "#A855F7"][i % 5]
            ax2.plot(rets.index, rets[c] * 100, lw=0.9, alpha=0.85, color=color, label=nombre_de(c))
        ax2.axhline(0, color=YF["muted"], ls="--")
        ax2.set_title("Variación diaria %", color=YF["text"])
        ax2.legend(facecolor=YF["card"], edgecolor=YF["border"], labelcolor=YF["text"], fontsize=8)
        ax2.grid(True, alpha=0.25)
        plt.tight_layout()

        md = "### Resumen tipo cotización\n\n| Símbolo | Empresa | Retorno | Volatilidad | Drawdown |\n| :---: | :--- | :---: | :---: | :---: |\n"
        for c in tickers:
            flecha = "▲" if ret[c] >= 0 else "▼"
            color = YF["green"] if ret[c] >= 0 else YF["red"]
            md += f"| **{c}** | {nombre_de(c)} | <span style='color:{color}'>{flecha} {ret[c]:+.1f}%</span> | {vol[c]*100:.1f}% | {dd[c]:.1f}% |\n"
        md += "\n> Datos: Yahoo Finance. Histórico ≠ futuro."
        m0 = metricas_mercado(precios[tickers[0]], tickers[0])
        return fig1, fig2, md, precios, tickers, m0
    except Exception as e:
        fig, ax = plt.subplots(figsize=(6, 2))
        ax.set_facecolor(YF["bg"])
        ax.text(0.5, 0.5, f"Error: {e}", ha="center", va="center", color=YF["red"], wrap=True)
        ax.axis("off")
        return fig, fig, f"### Error\n{e}", None, [], {}

def simular_inv(precios, tickers, monto, p1, p2, p3, p4, p5, anio):
    if precios is None or not tickers:
        return "Primero ejecuta el análisis de mercado."
    try:
        pesos = np.array([float(x or 0) for x in (p1, p2, p3, p4, p5)[:len(tickers)]])
        if pesos.sum() <= 0:
            raise ValueError("Asigna porcentajes")
        pesos = pesos / pesos.sum()
        monto = float(monto)
        filas, total = [], 0.0
        for t, w in zip(tickers, pesos):
            s = precios[t].dropna()
            inv = monto * w
            vf = inv * (s.iloc[-1] / s.iloc[0])
            total += vf
            filas.append((nombre_de(t), w*100, inv, vf, (vf/inv - 1)*100))
        md = "| Empresa | % | Invertido | Final | Resultado |\n| :--- | :---: | :---: | :---: |\n"
        for n, w, inv, vf, g in filas:
            c = YF["green"] if g >= 0 else YF["red"]
            md += f"| {n} | {w:.0f}% | ${inv:,.0f} | ${vf:,.0f} | <span style='color:{c}'>{g:+.1f}%</span> |\n"
        gt = (total/monto - 1)*100
        c = YF["green"] if gt >= 0 else YF["red"]
        md += f"\n**Total** ${monto:,.0f} → **${total:,.0f}** (<span style='color:{c}'>{gt:+.1f}%</span>) — año {anio}"
        return md
    except Exception as e:
        return f"Error: {e}"

def cargar_estados(opcion):
    d = estados_yahoo(ticker_de(opcion))
    return (d["activo_corriente"], d["pasivo_corriente"], d["inventarios"], d["utilidad_neta"],
            d["ventas"], d["activos_totales"], d["patrimonio"], d["pasivo_total"],
            d["utilidades_retenidas"], d["utilidad_operativa"], d["valor_mercado_patrimonio"],
            d["mensaje"], d["sector"])

def run_diag(ac, pc, inv, un, ven, at, pat, pt, ur, uo, vm):
    try:
        r = calcular_diagnostico(ac, pc, inv, un, ven, at, pat, pt, ur, uo, vm)
        return r["texto_md"], r
    except Exception as e:
        return f"### Error\n{e}", {}

def run_riesgo(precios, tickers, diag, sector):
    try:
        if precios is None or not tickers:
            return "Ejecuta primero Análisis de Mercado.", {}, None
        m = metricas_mercado(precios[tickers[0]], tickers[0])
        riesgos = seis_riesgos(m, (diag or {}).get("razones"), sector or "N/D")
        md = texto_riesgos(m, riesgos)
        fig, ax = plt.subplots(figsize=(8, 3.5))
        ax.hist(m["retornos"]*100, bins=40, color=YF["blue"], alpha=0.9, edgecolor=YF["bg"])
        ax.set_title("Distribución rendimientos diarios %", color=YF["text"])
        ax.grid(True, alpha=0.2)
        plt.tight_layout()
        return md, {"metricas": m, "riesgos": riesgos}, fig
    except Exception as e:
        fig, ax = plt.subplots(figsize=(5, 2)); ax.axis("off")
        return f"Error: {e}", {}, fig

def run_sim(pack, n, umbral):
    try:
        m = (pack or {}).get("metricas") or {}
        if not m:
            return "Calcula Riesgo primero.", {}, None
        sim = simulacion_decision(m["mu_diario"], m["sigma_diario"], int(n or 2000), float(umbral or 0.3))
        fig, ax = plt.subplots(figsize=(8, 3.5))
        ax.hist(sim["distribucion"]*100, bins=40, color=YF["green"], alpha=0.85, edgecolor=YF["bg"])
        ax.axvline(0, color=YF["red"], ls="--")
        ax.set_title(f"Montecarlo → {sim['decision'].upper()}", color=YF["text"])
        ax.grid(True, alpha=0.2)
        plt.tight_layout()
        return sim["detalle"], sim, fig
    except Exception as e:
        fig, ax = plt.subplots(figsize=(5, 2)); ax.axis("off")
        return f"Error: {e}", {}, fig

def run_integ(diag, pack, sim):
    try:
        if not diag or not pack:
            return "Necesitas Diagnóstico y Riesgo.", {}, "IA pendiente", {}
        integ = analisis_integrado(diag, pack)
        ia = analisis_ia(integ, sim or {})
        ctx = {
            "z_info": diag.get("z_info"),
            "clasificacion": integ.get("clasificacion"),
            "decision": (sim or {}).get("decision"),
        }
        return integ["texto_md"], integ, ia, ctx
    except Exception as e:
        return f"Error: {e}", {}, "IA N/D", {}

def run_calc(tipo, v1, v2, v3, v4, v5):
    try:
        if tipo == "Interés Simple":
            i, m = interes_simple(v1, v2, v3)
            return f"**Interés:** {fmt(i)}  |  **Monto:** {fmt(m)}"
        if tipo == "Interés Compuesto":
            i, m = interes_compuesto(v1, v2, v3)
            return f"**Interés:** {fmt(i)}  |  **Monto:** {fmt(m)}"
        if tipo == "Valor Futuro":
            return f"**VF:** {fmt(valor_futuro(v1, v2, v3))}"
        if tipo == "Valor Presente":
            return f"**VP:** {fmt(valor_presente(v1, v2, v3))}"
        if tipo == "Anualidad VP":
            return f"**VP:** {fmt(vp_anualidad(v1, v2, v3, v4 or 'ordinaria'))}"
        if tipo == "Anualidad VF":
            return f"**VF:** {fmt(vf_anualidad(v1, v2, v3, v4 or 'ordinaria'))}"
        if tipo == "Amortización":
            df, cuota = tabla_amortizacion(v1, v2, int(v3))
            return f"**Cuota:** {fmt(cuota)}\n\n" + df.head(10).to_string(index=False)
        if tipo == "Conversión de tasas":
            ef, nom, efd = conversion_tasas(v1, int(v2), int(v3), v4 or "nominal")
            return f"Efectiva: {ef*100:.4f}% | Nominal dest: {nom*100:.4f}% | Ef. dest: {efd*100:.4f}%"
        if tipo == "TIR":
            raw = str(v4 if v4 not in (None, "", "ordinaria") else v1)
            fl = [float(x.strip()) for x in raw.replace(";", ",").split(",") if x.strip()]
            return f"**TIR:** {calcular_tir(fl)*100:.4f}%"
        if tipo == "VAN":
            raw = str(v4 if v4 not in (None, "", "ordinaria") else v1)
            fl = [float(x.strip()) for x in raw.replace(";", ",").split(",") if x.strip()]
            van = calcular_van(fl, float(v2))
            return f"**VAN:** {fmt(van)} → {'viable' if van>0 else 'no viable' if van<0 else 'equilibrio'}"
        if tipo == "CAPM":
            return f"**Ke:** {calcular_capm(v1, v2, v3)*100:.4f}%"
        if tipo == "WACC":
            d = float(v4) if str(v4).replace(".","").replace("-","").isdigit() or _is_float(v4) else 0
            return f"**WACC:** {calcular_wacc(v1, v2, v3, d, v5 or 0.25)*100:.4f}%"
        if tipo == "EVA":
            e = calcular_eva(v1, v2, v3)
            return f"**EVA:** {fmt(e)} → {'creando' if e>0 else 'destruyendo' if e<0 else 'equilibrio'} valor"
        return "Elige un cálculo"
    except Exception as e:
        return f"**Error:** {e}"

def _is_float(x):
    try:
        float(x); return True
    except Exception:
        return False

def chat_ui(hist, msg, ctx):
    if not msg or not str(msg).strip():
        return hist, ""
    resp = chatbot_responder(msg, ctx or {})
    hist = list(hist or [])
    hist.append((msg, resp))
    return hist, ""

print("✅ BLOQUE 8 listo")

# BLOQUE 9 — UI estilo Yahoo Finance y lanzamiento
CSS = """
.gradio-container { background: #0B0E11 !important; color: #EAECEF !important; font-family: Inter, system-ui, sans-serif !important; }
.dark, .gr-block, .gr-form, .gr-panel { background: #0B0E11 !important; }
footer { display: none !important; }
"""

with gr.Blocks(title="Robot Financiero | Yahoo-style", css=CSS) as demo:
    gr.HTML("""
    <div style="background:#181A20;border-bottom:1px solid #2B2F36;padding:16px 20px;border-radius:8px;margin-bottom:12px;">
      <div style="display:flex;align-items:center;gap:12px;">
        <div style="width:36px;height:36px;border-radius:8px;background:#3861FB;display:flex;align-items:center;justify-content:center;font-weight:800;color:white;">RF</div>
        <div>
          <div style="font-size:20px;font-weight:700;color:#EAECEF;letter-spacing:-0.3px;">Robot Financiero Inteligente</div>
          <div style="font-size:12px;color:#848E9C;">Diagnóstico · Riesgo · Datos Yahoo Finance · Simulación · IA Gemini</div>
        </div>
      </div>
    </div>
    """)

    st_precios, st_tickers = gr.State(None), gr.State([])
    st_diag, st_riesgo, st_sim = gr.State({}), gr.State({}), gr.State({})
    st_sector, st_ctx = gr.State("N/D"), gr.State({})
    st_m0, st_integ_state = gr.State({}), gr.State({})

    with gr.Tabs():
        with gr.Tab("📈 Mercado"):
            with gr.Row():
                sel_emp = gr.Dropdown(OPCIONES, multiselect=True, value=["Apple Inc. (AAPL)", "Microsoft Corporation (MSFT)"], label="Símbolos (1–5)")
                sel_anio = gr.Dropdown(ANIOS, value=str(ANIO_ACTUAL), label="Año")
                btn_mkt = gr.Button("Analizar", variant="primary")
            with gr.Row():
                plot_p = gr.Plot()
                plot_r = gr.Plot()
            md_mkt = gr.Markdown()
            gr.Markdown("#### Simulador de inversión")
            with gr.Row():
                monto = gr.Number(1000, label="Monto USD")
                s1 = gr.Slider(0, 100, 50, label="% 1")
                s2 = gr.Slider(0, 100, 50, label="% 2")
                s3 = gr.Slider(0, 100, 0, label="% 3")
                s4 = gr.Slider(0, 100, 0, label="% 4")
                s5 = gr.Slider(0, 100, 0, label="% 5")
            btn_inv = gr.Button("Simular")
            md_inv = gr.Markdown()

        with gr.Tab("📋 Diagnóstico"):
            with gr.Row():
                sel_d = gr.Dropdown(OPCIONES_MANUAL, value=OPCIONES_MANUAL[1], label="Empresa")
                btn_load = gr.Button("Cargar Yahoo Finance")
            md_load = gr.Markdown()
            with gr.Row():
                with gr.Column():
                    ac = gr.Number(0, label="Activo Corriente")
                    pc = gr.Number(0, label="Pasivo Corriente")
                    inv = gr.Number(0, label="Inventarios")
                    un = gr.Number(0, label="Utilidad Neta")
                    ven = gr.Number(0, label="Ventas")
                with gr.Column():
                    at = gr.Number(0, label="Activos Totales")
                    pat = gr.Number(0, label="Patrimonio")
                    pt = gr.Number(0, label="Pasivo Total")
                    ur = gr.Number(0, label="Utilidades Retenidas")
                    uo = gr.Number(0, label="EBIT")
                    vm = gr.Number(0, label="Market Cap / Patrimonio mercado")
            btn_diag = gr.Button("Calcular diagnóstico", variant="primary")
            md_diag = gr.Markdown()

        with gr.Tab("⚠ Riesgo"):
            btn_risk = gr.Button("Calcular 6 riesgos + VaR", variant="primary")
            md_risk = gr.Markdown()
            plot_h = gr.Plot()
            with gr.Row():
                n_esc = gr.Number(2000, label="Escenarios Montecarlo")
                umbral = gr.Slider(0.05, 0.5, 0.30, step=0.05, label="Umbral P(pérdida)")
            btn_sim = gr.Button("Simular decisión", variant="primary")
            md_sim = gr.Markdown()
            plot_mc = gr.Plot()

        with gr.Tab("🎯 Integrado + IA"):
            btn_int = gr.Button("Generar análisis integrado", variant="primary")
            md_int = gr.Markdown()
            md_ia = gr.Markdown()

        with gr.Tab("🧮 Calculadora"):
            tipo = gr.Dropdown(
                ["Interés Simple", "Interés Compuesto", "Valor Futuro", "Valor Presente",
                 "Anualidad VP", "Anualidad VF", "Amortización", "Conversión de tasas",
                 "TIR", "VAN", "CAPM", "WACC", "EVA"],
                value="Interés Simple", label="Cálculo")
            with gr.Row():
                v1 = gr.Number(1_000_000, label="V1")
                v2 = gr.Number(0.12, label="V2")
                v3 = gr.Number(2, label="V3")
            with gr.Row():
                v4 = gr.Textbox("ordinaria", label="V4 (tipo o flujos TIR/VAN)")
                v5 = gr.Number(0.35, label="V5 (impuesto WACC)")
            gr.Markdown("TIR/VAN → flujos en V4: `-10000000, 3000000, 3500000, 4000000` · WACC → V1=Ke V2=Kd V3=E V4=D V5=tax")
            btn_c = gr.Button("Calcular", variant="primary")
            md_c = gr.Markdown()

        with gr.Tab("💬 Asistente"):
            chat = gr.Chatbot(height=400)
            msg = gr.Textbox(label="Pregunta", placeholder="¿Por qué la simulación dio ese resultado?")
            with gr.Row():
                btn_send = gr.Button("Enviar", variant="primary")
                btn_clr = gr.Button("Limpiar")

    btn_mkt.click(pipeline_mercado, [sel_emp, sel_anio], [plot_p, plot_r, md_mkt, st_precios, st_tickers, st_m0])
    btn_inv.click(simular_inv, [st_precios, st_tickers, monto, s1, s2, s3, s4, s5, sel_anio], md_inv)
    btn_load.click(cargar_estados, sel_d, [ac, pc, inv, un, ven, at, pat, pt, ur, uo, vm, md_load, st_sector])
    btn_diag.click(run_diag, [ac, pc, inv, un, ven, at, pat, pt, ur, uo, vm], [md_diag, st_diag])
    btn_risk.click(run_riesgo, [st_precios, st_tickers, st_diag, st_sector], [md_risk, st_riesgo, plot_h])
    btn_sim.click(run_sim, [st_riesgo, n_esc, umbral], [md_sim, st_sim, plot_mc])
    btn_int.click(run_integ, [st_diag, st_riesgo, st_sim], [md_int, st_integ_state, md_ia, st_ctx])
    btn_c.click(run_calc, [tipo, v1, v2, v3, v4, v5], md_c)
    btn_send.click(chat_ui, [chat, msg, st_ctx], [chat, msg])
    msg.submit(chat_ui, [chat, msg, st_ctx], [chat, msg])
    btn_clr.click(lambda: [], outputs=chat)

port = int(os.environ.get("PORT", 7860))
demo.launch(server_name="0.0.0.0", server_port=port)
