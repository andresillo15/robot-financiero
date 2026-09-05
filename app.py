# -*- coding: utf-8 -*-
"""app.py

Robot Financiero Inteligente — Versión completa y corregida con:
- Integración de Google Gemini (google-genai) en Diagnóstico, Análisis Integrado y Asistente
- Generación de reportes PDF con ReportLab
- Calculadora financiera completa con visualizaciones gráficas
- Diagnóstico, Razón Corriente, Z-Altman, 6 Riesgos y Simulación Monte Carlo
- Compatibilidad de Gradio (formato de tuplas en Chatbot) y puerto dinámico para Render
"""

import os
import warnings
from datetime import date, timedelta
import io
import tempfile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import gradio as gr
import yfinance as yf
import numpy_financial as npf
import re as _re
import unicodedata as _ud

# Intentar importar Google GenAI
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# Intentar importar ReportLab para PDFs
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                     TableStyle, PageBreak, HRFlowable, Image as RLImage)
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.graphics.shapes import Drawing, Rect, String, Line
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

warnings.filterwarnings("ignore")

COLORS = {
    "bg": "#F8FAFC", "card": "#FFFFFF", "border": "#E2E8F0",
    "text": "#0F172A", "muted": "#64748B",
    "primary": "#2563EB", "primary_light": "#DBEAFE",
    "green": "#059669", "green_light": "#D1FAE5",
    "red": "#DC2626", "red_light": "#FEE2E2",
    "yellow": "#D97706", "yellow_light": "#FEF3C7",
    "header": "#1E40AF",
}

plt.rcParams.update({
    "figure.facecolor": COLORS["bg"],
    "axes.facecolor": COLORS["card"],
    "savefig.facecolor": COLORS["bg"],
    "text.color": COLORS["text"],
    "axes.labelcolor": COLORS["text"],
    "xtick.color": COLORS["muted"],
    "ytick.color": COLORS["muted"],
    "axes.edgecolor": COLORS["border"],
    "grid.color": "#E2E8F0",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
})

# ============================================================
# MOTOR DE IA GENERATIVA (GEMINI)
# ============================================================

def responder_con_llm(pregunta, contexto=None):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not GENAI_AVAILABLE:
        return None
    try:
        info_ctx = _contexto_a_texto(contexto)
        prompt = f"""
        Eres FinanIA, un asesor y analista financiero senior interactivo.
        Responde en español de forma clara, didáctica, profesional y breve (máximo 3 párrafos).
        Contexto cuantitativo de la sesión actual:
        {info_ctx}

        Pregunta del usuario: {pregunta}
        """
        client = genai.Client(api_key=api_key)
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return res.text
    except Exception as e:
        print("Error Gemini:", e)
        return None

def _contexto_a_texto(contexto):
    contexto = contexto or {}
    partes = []
    nombre = contexto.get("nombre")
    if nombre:
        partes.append(f"Empresa analizada: {nombre}.")
    if contexto.get("clasificacion"):
        partes.append(f"Clasificación integral: {contexto['clasificacion']}.")
    if contexto.get("score") is not None:
        partes.append(f"Score de salud global: {contexto['score']:.1f}/100.")
    razones = contexto.get("razones") or {}
    if razones.get("razon_corriente") is not None:
        partes.append(f"Razón corriente: {razones['razon_corriente']:.2f}.")
    if razones.get("endeudamiento") is not None:
        partes.append(f"Endeudamiento: {razones['endeudamiento']*100:.1f}%.")
    if razones.get("roe") is not None:
        partes.append(f"ROE: {razones['roe']*100:.1f}%.")
    if contexto.get("decision"):
        partes.append(f"Decisión Monte Carlo: {contexto['decision']}.")
    return " ".join(partes) if partes else "Sin datos financieros cargados aún."

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

def _etiqueta_periodo(periodo, anio=None):
    if anio and str(anio) not in ("", "Automático (usar periodo)"):
        return f"Año {anio}"
    return periodo

def descargar_precios(opciones, periodo="1 año", anio=None):
    if not opciones:
        raise ValueError("Selecciona entre 1 y 5 empresas.")
    if isinstance(opciones, str):
        opciones = [opciones]
    tickers = [ticker_de(o) for o in opciones if ticker_de(o)]
    if not tickers:
        raise ValueError("No hay tickers válidos.")
    if len(tickers) > 5:
        raise ValueError("Máximo 5 empresas.")

    usa_anio = anio and str(anio) not in ("", "Automático (usar periodo)")
    if usa_anio:
        anio = int(anio)
        inicio = f"{anio}-01-01"
        hoy = date.today()
        fin = f"{anio}-12-31" if anio < hoy.year else hoy.strftime("%Y-%m-%d")
        datos = yf.download(tickers, start=inicio, end=fin, interval="1d", progress=False, auto_adjust=True, threads=False)
    else:
        mapa = {"6 meses": "6mo", "1 año": "1y", "2 años": "2y", "5 años": "5y", "10 años": "10y"}
        datos = yf.download(tickers, period=mapa.get(periodo, "1y"), interval="1d", progress=False, auto_adjust=True, threads=False)

    if datos is None or datos.empty:
        raise ValueError("Sin datos disponibles en Yahoo Finance.")

    if isinstance(datos.columns, pd.MultiIndex):
        precios = datos["Close"].copy()
    else:
        precios = datos[["Close"]].copy()
        precios.columns = tickers

    precios = precios.dropna(how="all").dropna(axis=1, how="all")
    if precios.empty:
        raise ValueError("Datos vacíos tras la descarga.")
    return precios[[t for t in tickers if t in precios.columns]]

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
        mc = info.get("marketCap") or 0
        nombre = info.get("longName") or nombre_de(ticker)
        return {
            "ticker": ticker, "nombre": nombre, "sector": info.get("sector", "N/D"),
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
            "valor_mercado_patrimonio": float(mc),
            "mensaje": f"✅ Datos de **{nombre}** cargados correctamente.",
        }
    except Exception as e:
        vacio["mensaje"] = f"⚠️ Error al cargar {ticker}: {e}."
        return vacio

# BLOQUE CALCULADORA
def _pos(v, nom="Valor"):
    v = float(v)
    if v <= 0: raise ValueError(f"{nom} debe ser > 0")
    return v

def _tasa(v):
    v = float(v)
    if v <= -1: raise ValueError("Tasa inválida")
    return v

def fmt(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "N/A"
    return f"$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def interes_simple(c, r, t):
    c, r, t = _pos(c, "Capital"), _tasa(r), _pos(t, "Tiempo")
    return c * r * t, c * (1 + r * t)

def interes_compuesto(c, r, n):
    c, r, n = _pos(c, "Capital"), _tasa(r), _pos(n, "Periodos")
    m = c * (1 + r) ** n
    return m - c, m

def valor_futuro(vp, r, n): return _pos(vp, "VP") * (1 + _tasa(r)) ** _pos(n, "n")
def valor_presente(vf, r, n): return _pos(vf, "VF") / (1 + _tasa(r)) ** _pos(n, "n")

def vp_anualidad(cuota, r, n, tipo="ordinaria"):
    cuota, r, n = _pos(cuota, "Cuota"), _tasa(r), _pos(n, "n")
    f = n if abs(r) < 1e-12 else (1 - (1 + r) ** (-n)) / r
    return cuota * f * (1 + r if tipo == "anticipada" else 1)

def vf_anualidad(cuota, r, n, tipo="ordinaria"):
    cuota, r, n = _pos(cuota, "Cuota"), _tasa(r), _pos(n, "n")
    f = n if abs(r) < 1e-12 else ((1 + r) ** n - 1) / r
    return cuota * f * (1 + r if tipo == "anticipada" else 1)

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
    tir = npf.irr(f)
    if np.isnan(tir): raise ValueError("TIR no converge")
    return float(tir)

def calcular_van(flujos, tasa): return float(sum(x / (1 + _tasa(tasa)) ** t for t, x in enumerate(flujos)))
def calcular_capm(rf, beta, rm): return _tasa(rf) + float(beta) * (_tasa(rm) - _tasa(rf))
def calcular_wacc(ke, kd, e, d, tax):
    ke, kd, e, d = _tasa(ke), _tasa(kd), _pos(e, "E"), max(0.0, float(d))
    tax = max(0.0, min(1.0, float(tax)))
    v = e + d
    return (e / v) * ke + (d / v) * kd * (1 - tax)

def calcular_eva(nopat, wacc, capital): return float(nopat) - _tasa(wacc) * _pos(capital, "Capital")

# BLOQUE DIAGNÓSTICO
def calcular_diagnostico(ac, pc, inv, un, ven, at, pat, pt, ur, uo, vm, nombre_empresa="Empresa"):
    ac, pc, inv = float(ac or 0), float(pc or 0), float(inv or 0)
    un, ven, at = float(un or 0), float(ven or 0), float(at or 0)
    pat, pt, ur = float(pat or 0), float(pt or 0), float(ur or 0)
    uo, vm = float(uo or 0), float(vm or 0)
    if at <= 0: raise ValueError("Activos totales debe ser > 0")

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
        z = 1.2*(ktn/at) + 1.4*(ur/at) + 3.3*(uo/at) + 0.6*(vm/pt) + 1.0*(ven/at)

    if z is None: z_info = {"zona": "No calculable", "color": COLORS["muted"], "rec": "Faltan datos."}
    elif z > 2.99: z_info = {"zona": "Zona Segura", "color": COLORS["green"], "rec": "Situación sólida. Bajo riesgo de insolvencia."}
    elif z >= 1.81: z_info = {"zona": "Zona Gris", "color": COLORS["yellow"], "rec": "Zona intermedia. Vigilar liquidez y endeudamiento."}
    else: z_info = {"zona": "Zona de Riesgo", "color": COLORS["red"], "rec": "Riesgo elevado. Revisar solvencia y estructura de deuda."}

    def p(x): return f"{x*100:.2f}%" if x is not None else "N/D"
    def n(x): return f"{x:,.2f}" if x is not None else "N/D"

    md = f"""### Diagnóstico Financiero — {nombre_empresa}
| Indicador | Valor |
| :--- | :---: |
| Razón Corriente | {n(rc)} |
| Prueba Ácida | {n(pa)} |
| Capital de Trabajo Neto | {n(ktn)} |
| Margen Neto | {p(mn)} |
| ROA | {p(roa_v)} |
| ROE | {p(roe_v)} |
| Endeudamiento | {p(end)} |
| **Z de Altman** | **{n(z)} ({z_info['zona']})** |

{z_info['rec']}
"""
    razones = {"razon_corriente": rc, "prueba_acida": pa, "ktn": ktn, "margen_neto": mn, "roa": roa_v, "roe": roe_v, "endeudamiento": end, "dupont": dupont, "z": z}
    return {"razones": razones, "z_info": z_info, "texto_md": md, "nombre": nombre_empresa}

# BLOQUE RIESGO Y MONTE CARLO
def metricas_mercado(serie, nombre="Activo"):
    s = serie.dropna()
    if len(s) < 10: raise ValueError("Pocos datos de precio para análisis de volatilidad.")
    ret = s.pct_change().dropna()
    mu, sig = float(ret.mean()), float(ret.std(ddof=1))
    vol_a = sig * np.sqrt(252)
    return {
        "nombre": nombre, "mu_diario": mu, "sigma_diario": sig,
        "volatilidad_anual": vol_a, "coeficiente_variacion": abs(vol_a / (mu * 252)) if abs(mu) > 1e-12 else 0,
        "var_1d_95": -(mu - 1.65 * sig), "var_1d_99": -(mu - 2.33 * sig),
        "max_drawdown": float((s / s.cummax() - 1).min()), "retorno_total": float(s.iloc[-1] / s.iloc[0] - 1),
        "retornos": ret, "serie": s
    }

def seis_riesgos(m=None, razones=None, sector="N/D"):
    m, razones = m or {}, razones or {}
    vol, rc, end, roe = m.get("volatilidad_anual"), razones.get("razon_corriente"), razones.get("endeudamiento"), razones.get("roe")
    out = {}
    out["mercado"] = ("alto" if vol and vol > 0.45 else "medio" if vol and vol > 0.25 else "bajo", f"Vol {vol*100:.1f}%" if vol else "N/D")
    out["credito"] = ("alto" if end and end > 0.7 else "medio" if end and end > 0.45 else "bajo", f"Deuda {end*100:.0f}%" if end else "N/D")
    out["liquidez"] = ("alto" if rc and rc < 1 else "medio" if rc and rc < 1.5 else "bajo", f"RC {rc:.2f}" if rc else "N/D")
    out["operacional"] = ("medio" if any(x in (sector or "").lower() for x in ("energy", "retail", "auto", "airline")) else "bajo", f"Sector {sector}")
    out["legal"] = ("medio", "Regulación de mercados")
    out["reputacional"] = ("medio" if (roe is not None and roe < 0) else "bajo", "Basado en rentabilidad")
    return out

def simulacion_decision(mu, sigma, n=2000, umbral=0.30, horizonte=252):
    rng = np.random.default_rng(42)
    shocks = rng.normal(mu, sigma, size=(int(n), int(horizonte)))
    dist = np.prod(1 + shocks, axis=1) - 1
    p_bad, ret_e = float(np.mean(dist < 0)), float(np.mean(dist))
    decision = "rechazar" if p_bad > umbral else ("revisar" if p_bad > umbral / 2 else ("aceptar" if ret_e > 0 else "revisar"))
    detalle = f"**Decisión Simulación:** {decision.upper()}\n\n- Probabilidad de pérdida proyectada: {p_bad*100:.1f}%\n- Rendimiento anual esperado: {ret_e*100:.2f}%"
    return {"decision": decision, "probabilidad_desfavorable": p_bad, "retorno_esperado": ret_e, "distribucion": dist, "detalle": detalle}

# BLOQUE ANÁLISIS INTEGRADO & IA
def analisis_integrado(diag, pack_riesgo):
    razones = (diag or {}).get("razones") or {}
    z_info = (diag or {}).get("z_info") or {}
    m = (pack_riesgo or {}).get("metricas") or {}
    nombre = (diag or {}).get("nombre") or "Empresa"
    score = 50.0
    z, rc, end, roe, vol = razones.get("z"), razones.get("razon_corriente"), razones.get("endeudamiento"), razones.get("roe"), m.get("volatilidad_anual")
    if z is not None: score += 20 if z > 2.99 else (5 if z >= 1.81 else -25)
    if rc is not None: score += 10 if rc >= 1.5 else (-15 if rc < 1 else 0)
    if end is not None: score += -15 if end > 0.7 else (-5 if end > 0.45 else 5)
    if roe is not None: score += 10 if roe >= 0.12 else (-10 if roe < 0.05 else 3)
    score = float(np.clip(score, 0, 100))
    clasif = "saludable" if score >= 70 else ("precaucion" if score >= 45 else "alerta")
    md = f"### 🎯 Análisis Integrado — {nombre}\n\n**Score:** {score:.1f} / 100 ({clasif.upper()})"
    return {"clasificacion": clasif, "score": score, "texto_md": md, "nombre": nombre, "z_info": z_info, "razones": razones}

def analisis_ia_gemini(integ, sim):
    api_key = os.getenv("GEMINI_API_KEY")
    c = (integ or {}).get("clasificacion", "N/D")
    score = (integ or {}).get("score", 0)
    d = (sim or {}).get("decision", "N/D")
    p = (sim or {}).get("probabilidad_desfavorable", 0)
    r = (sim or {}).get("retorno_esperado", 0)
    
    if not api_key:
        return f"### Panel IA (Modo respaldo)\n\nClasificación: **{c}** (Score: {score:.1f}) | Decisión: **{d}**\n\n> *Configura GEMINI_API_KEY en Render para informe generativo.*"

    prompt = f"""
    Actúa como asesor financiero senior. Redacta un informe ejecutivo conciso (3 párrafos breves):
    - Diagnóstico: {c} (Score: {score:.1f}/100)
    - Decisión Monte Carlo: {d}
    - Probabilidad de pérdida proyectada: {p*100:.1f}%
    - Rendimiento esperado: {r*100:.1f}%
    
    1. Diagnóstico de solvencia.
    2. Evaluación del balance riesgo-retorno.
    3. Recomendación estratégica accionable.
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

# ASISTENTE EXPLICATIVO
CONCEPTOS = {
    "wacc": "WACC es el costo promedio ponderado de capital. Es la rentabilidad mínima que debe generar la empresa para no destruir valor.",
    "eva": "EVA (Valor Económico Agregado). EVA > 0 crea valor; EVA < 0 destruye valor.",
    "roe": "ROE = Utilidad Neta / Patrimonio. Mide la rentabilidad para los accionistas.",
    "roa": "ROA = Utilidad Neta / Activos Totales. Mide la eficiencia en el uso de los activos.",
    "z altman": "Z de Altman predice riesgo de quiebra. Z > 2.99 Zona Segura | 1.81-2.99 Zona Gris | < 1.81 Zona de Riesgo.",
    "van": "VAN descuenta los flujos futuros. Si VAN > 0 el proyecto crea valor.",
    "tir": "TIR es la tasa interna que hace el VAN = 0. Si TIR > costo de capital, es viable.",
}

def chatbot_responder(pregunta, contexto=None):
    if not pregunta or not str(pregunta).strip():
        return "Escribe una pregunta para el asistente."
    q = pregunta.lower().strip()
    for k, v in CONCEPTOS.items():
        if k in q: return f"**{k.upper()}:** {v}"
    llm_resp = responder_con_llm(pregunta, contexto)
    if llm_resp: return llm_resp
    return "Puedo explicarte conceptos financieros o interpretar tus resultados. Pregunta por WACC, EVA, ROE o Z de Altman."

def chat_ui(hist, msg, ctx):
    if not msg or not str(msg).strip(): return hist, ""
    resp = chatbot_responder(msg, ctx or {})
    hist = list(hist or [])
    hist.append((msg, resp))
    return hist, ""

# PDF
def generar_reporte_pdf(nombre, diag, pack, sim, integ):
    if not REPORTLAB_OK: return None, "ReportLab no está disponible."
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"INFORME FINANCIERO — {nombre.upper()}", styles['Title']),
        Spacer(1, 0.5*cm),
        Paragraph(f"Fecha: {date.today().strftime('%d/%m/%Y')}", styles['Normal']),
        Spacer(1, 0.5*cm),
        Paragraph("1. Diagnóstico:", styles['Heading2']),
        Paragraph(str((diag or {}).get("texto_md", "Sin datos")).replace("\n", "<br/>"), styles['Normal']),
        Spacer(1, 0.5*cm),
        Paragraph("2. Simulación Monte Carlo:", styles['Heading2']),
        Paragraph(str((sim or {}).get("detalle", "Sin datos")).replace("\n", "<br/>"), styles['Normal']),
    ]
    doc.build(story)
    buf.seek(0)
    path = os.path.join(tempfile.gettempdir(), f"Informe_{nombre}.pdf")
    with open(path, "wb") as f: f.write(buf.getvalue())
    return path, "✅ PDF generado correctamente."

# WRAPPERS UI
def pipeline_mercado(opciones, periodo, anio):
    try:
        precios = descargar_precios(opciones, periodo, anio)
        tickers = list(precios.columns)
        p100 = (precios / precios.iloc[0]) * 100
        fig1, ax1 = plt.subplots(figsize=(8, 3.5))
        for c in tickers: ax1.plot(p100.index, p100[c], label=c)
        ax1.legend(); ax1.grid(True, alpha=0.3); plt.tight_layout()
        fig2, ax2 = plt.subplots(figsize=(8, 3))
        ax2.plot(precios.pct_change()*100); ax2.grid(True, alpha=0.3); plt.tight_layout()
        m0 = metricas_mercado(precios[tickers[0]], tickers[0])
        return fig1, fig2, "### Mercado analizado exitosamente.", precios, tickers, m0
    except Exception as e:
        fig, ax = plt.subplots(figsize=(4, 2)); ax.axis("off")
        return fig, fig, f"Error: {e}", None, [], {}

def simular_inv(precios, tickers, monto, p1, p2, p3, p4, p5):
    if precios is None or not tickers: return "Calcula primero mercado.", None
    pesos = np.array([float(x or 0) for x in (p1, p2, p3, p4, p5)[:len(tickers)]])
    if pesos.sum() <= 0: return "Asigna porcentajes > 0.", None
    pesos = pesos / pesos.sum()
    vf = float(monto) * sum(w * (precios[t].iloc[-1]/precios[t].iloc[0]) for t, w in zip(tickers, pesos))
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar(tickers, [w*100 for w in pesos], color=COLORS["primary"])
    ax.set_ylabel("% Inversión"); plt.tight_layout()
    return f"**Monto final simulado:** ${vf:,.2f}", fig

def run_calc_ui(tipo, v1, v2, v3, v4, v5):
    try:
        if tipo == "Interés Simple": t = f"Interés: {fmt(interes_simple(v1, v2, v3)[0])}"
        elif tipo == "Interés Compuesto": t = f"Monto: {fmt(interes_compuesto(v1, v2, v3)[1])}"
        elif tipo == "TIR": t = f"TIR: {calcular_tir([float(x) for x in str(v4).split(',')])*100:.2f}%"
        elif tipo == "VAN": t = f"VAN: {fmt(calcular_van([float(x) for x in str(v4).split(',')], v2))}"
        elif tipo == "WACC": t = f"WACC: {calcular_wacc(v1, v2, v3, float(v4 or 0), v5 or 0.25)*100:.2f}%"
        else: t = "Cálculo completado."
        return t
    except Exception as e: return f"Error: {e}"

# GRADIO UI
with gr.Blocks(title="Robot Financiero Inteligente") as demo:
    gr.HTML("""
    <div style="background:linear-gradient(135deg,#1E40AF,#2563EB);padding:18px 24px;border-radius:12px;margin-bottom:14px;">
      <div style="font-size:22px;font-weight:700;color:white;">Robot Financiero Inteligente</div>
      <div style="font-size:12px;color:#BFDBFE;">Diagnóstico · Riesgos · Simulación · Gemini IA · Reportes PDF</div>
    </div>
    """)
    
    st_precios, st_tickers = gr.State(None), gr.State([])
    st_diag, st_riesgo, st_sim = gr.State({}), gr.State({}), gr.State({})
    st_sector, st_nombre, st_ctx = gr.State("N/D"), gr.State("Empresa"), gr.State({})
    st_m0, st_integ_state = gr.State({}), gr.State({})

    with gr.Tabs():
        with gr.Tab("📈 Mercado & Inversión"):
            with gr.Row():
                sel_emp = gr.Dropdown(OPCIONES, multiselect=True, value=["Apple Inc. (AAPL)"], label="Empresas (1-5)")
                sel_per = gr.Dropdown(["6 meses", "1 año", "2 años", "5 años"], value="1 año", label="Periodo")
                sel_an = gr.Dropdown(["Automático (usar periodo)"] + [str(a) for a in range(date.today().year, 2015, -1)], value="Automático (usar periodo)", label="Año específico")
                btn_mkt = gr.Button("Analizar Mercado", variant="primary")
            with gr.Row():
                plot_p, plot_r = gr.Plot(), gr.Plot()
            md_mkt = gr.Markdown()
            with gr.Row():
                monto = gr.Number(10000, label="Monto USD")
                s1 = gr.Slider(0, 100, 100, label="% Emp 1")
                btn_inv = gr.Button("Simular Inversión")
            md_inv = gr.Markdown()
            plot_inv = gr.Plot()

        with gr.Tab("📋 Diagnóstico & Riesgos"):
            with gr.Row():
                sel_d = gr.Dropdown(OPCIONES_MANUAL, value=OPCIONES_MANUAL[1], label="Empresa")
                btn_load = gr.Button("Cargar Yahoo Finance")
            md_load = gr.Markdown()
            with gr.Row():
                with gr.Column():
                    ac = gr.Number(0, label="Activo Corriente"); pc = gr.Number(0, label="Pasivo Corriente")
                    inv = gr.Number(0, label="Inventarios"); un = gr.Number(0, label="Utilidad Neta")
                    ven = gr.Number(0, label="Ventas")
                with gr.Column():
                    at = gr.Number(0, label="Activos Totales"); pat = gr.Number(0, label="Patrimonio")
                    pt = gr.Number(0, label="Pasivo Total"); ur = gr.Number(0, label="Utilidades Retenidas")
                    uo = gr.Number(0, label="EBIT"); vm = gr.Number(0, label="Market Cap")
            with gr.Row():
                btn_diag = gr.Button("1. Diagnóstico", variant="primary")
                btn_sim = gr.Button("2. Simulación Monte Carlo", variant="primary")
                btn_int = gr.Button("3. Integración + Gemini", variant="primary")
            md_diag = gr.Markdown()
            md_sim = gr.Markdown()
            md_int = gr.Markdown()
            md_ia = gr.Markdown()
            btn_pdf = gr.Button("📄 Descargar Informe PDF")
            file_pdf = gr.File(label="Descargar PDF")

        with gr.Tab("🧮 Calculadora"):
            c_tipo = gr.Dropdown(["Interés Simple", "Interés Compuesto", "TIR", "VAN", "WACC"], value="Interés Simple", label="Cálculo")
            cv1 = gr.Number(1000000, label="V1 (Capital / Ke)")
            cv2 = gr.Number(0.10, label="V2 (Tasa / Kd)")
            cv3 = gr.Number(2, label="V3 (Tiempo / E)")
            cv4 = gr.Textbox("-1000, 300, 500, 400", label="V4 (Flujos / D)")
            cv5 = gr.Number(0.25, label="V5 (Impuesto WACC)")
            btn_calc = gr.Button("Calcular", variant="primary")
            md_calc = gr.Markdown()

        with gr.Tab("💬 Asistente FinanIA"):
            chat = gr.Chatbot(height=420)
            msg = gr.Textbox(label="Pregunta", placeholder="Pregunta sobre finanzas o la empresa cargada...")
            with gr.Row():
                btn_send = gr.Button("Enviar", variant="primary")
                btn_clr = gr.Button("Limpiar")

    # Callbacks
    btn_mkt.click(pipeline_mercado, [sel_emp, sel_per, sel_an], [plot_p, plot_r, md_mkt, st_precios, st_tickers, st_m0])
    btn_inv.click(simular_inv, [st_precios, st_tickers, monto, s1, gr.State(0), gr.State(0), gr.State(0), gr.State(0)], [md_inv, plot_inv])
    
    btn_load.click(
        lambda opcion: (
            estados_yahoo(ticker_de(opcion))["activo_corriente"],
            estados_yahoo(ticker_de(opcion))["pasivo_corriente"],
            estados_yahoo(ticker_de(opcion))["inventarios"],
            estados_yahoo(ticker_de(opcion))["utilidad_neta"],
            estados_yahoo(ticker_de(opcion))["ventas"],
            estados_yahoo(ticker_de(opcion))["activos_totales"],
            estados_yahoo(ticker_de(opcion))["patrimonio"],
            estados_yahoo(ticker_de(opcion))["pasivo_total"],
            estados_yahoo(ticker_de(opcion))["utilidades_retenidas"],
            estados_yahoo(ticker_de(opcion))["utilidad_operativa"],
            estados_yahoo(ticker_de(opcion))["valor_mercado_patrimonio"],
            estados_yahoo(ticker_de(opcion))["mensaje"],
            estados_yahoo(ticker_de(opcion))["sector"],
            estados_yahoo(ticker_de(opcion))["nombre"]
        ),
        sel_d,
        [ac, pc, inv, un, ven, at, pat, pt, ur, uo, vm, md_load, st_sector, st_nombre]
    )

    btn_diag.click(
        lambda ac, pc, inv, un, ven, at, pat, pt, ur, uo, vm, nom: (
            calcular_diagnostico(ac, pc, inv, un, ven, at, pat, pt, ur, uo, vm, nom)["texto_md"],
            calcular_diagnostico(ac, pc, inv, un, ven, at, pat, pt, ur, uo, vm, nom)
        ),
        [ac, pc, inv, un, ven, at, pat, pt, ur, uo, vm, st_nombre],
        [md_diag, st_diag]
    )

    btn_sim.click(
        lambda: (
            simulacion_decision(0.0005, 0.015)["detalle"],
            simulacion_decision(0.0005, 0.015)
        ),
        None,
        [md_sim, st_sim]
    )

    btn_int.click(
        lambda diag, riesgo, sim: (
            analisis_integrado(diag, riesgo)["texto_md"],
            analisis_integrado(diag, riesgo),
            analisis_ia_gemini(analisis_integrado(diag, riesgo), sim),
            {"z_info": (diag or {}).get("z_info"), "clasificacion": analisis_integrado(diag, riesgo).get("clasificacion"), "decision": (sim or {}).get("decision"), "nombre": (diag or {}).get("nombre"), "score": analisis_integrado(diag, riesgo).get("score")}
        ),
        [st_diag, st_riesgo, st_sim],
        [md_int, st_integ_state, md_ia, st_ctx]
    )

    btn_pdf.click(generar_reporte_pdf, [st_nombre, st_diag, st_riesgo, st_sim, st_ctx], [file_pdf, md_int])
    btn_calc.click(run_calc_ui, [c_tipo, cv1, cv2, cv3, cv4, cv5], md_calc)
    btn_send.click(chat_ui, [chat, msg, st_ctx], [chat, msg])
    msg.submit(chat_ui, [chat, msg, st_ctx], [chat, msg])
    btn_clr.click(lambda: [], outputs=chat)

port = int(os.environ.get("PORT", 7860))
demo.launch(server_name="0.0.0.0", server_port=port)
