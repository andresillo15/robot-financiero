# -*- coding: utf-8 -*-
"""app.py

Robot Financiero Inteligente — Versión definitiva con:
- Integración conversacional profunda con Google Gemini (memoria multi-turno, razonamiento analítico y tono pedagógico)
- Diagnóstico financiero completo (Z de Altman, KTN, DuPont, razones de liquidez/solvencia)
- Análisis de riesgo de mercado, 6 riesgos empresariales y simulación Monte Carlo
- Calculadora financiera interactiva (interés, amortización, TIR, VAN, WACC, EVA)
- Generación de reportes ejecutivos en PDF (ReportLab)
- Compatibilidad nativa de Gradio (formato de mensajes por diccionario) y puerto dinámico para Render
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
# ASISTENTE CONVERSACIONAL AVANZADO (ESTILO GEMINI)
# ============================================================

SYSTEM_PROMPT_FINANIA = """
Eres FinanIA, un analista financiero sénior, consultor cuantitativo y asesor corporativo experto.
Tu objetivo es responder como un tutor y colaborador de alto nivel: reflexivo, pedagógico, agudo, técnico pero cercano y empático.

Reglas clave para tus respuestas:
1. No des respuestas genéricas ni de una sola línea. Desarrolla explicaciones con sustancia y estructura clara (usa viñetas, tablas comparativas o negritas).
2. Cuando el usuario pregunte por conceptos (WACC, ROE, TIR, VAN, Z-Altman, VaR, Monte Carlo, etc.):
   - Explica el concepto y su fórmula conceptual sin rodeos.
   - Detalla CÓMO interpretarlo (qué significa si es alto/bajo/positivo/negativo).
   - Explica el IMPACTO en la toma de decisiones financieras o de inversión.
3. Si en el contexto hay una empresa cargada o cálculos previos, fundamenta SIEMPRE tu análisis con esos números reales.
4. Mantén coherencia y memoria a lo largo del hilo conversacional.
"""

def _contexto_a_texto(contexto):
    contexto = contexto or {}
    partes = []
    nombre = contexto.get("nombre")
    if nombre:
        partes.append(f"Empresa analizada: {nombre}.")
    if contexto.get("clasificacion"):
        partes.append(f"Clasificación integral de salud: {contexto['clasificacion']}.")
    if contexto.get("score") is not None:
        partes.append(f"Score global de salud financiera: {contexto['score']:.1f}/100.")
    razones = contexto.get("razones") or {}
    if razones.get("razon_corriente") is not None:
        partes.append(f"Razón corriente: {razones['razon_corriente']:.2f}.")
    if razones.get("endeudamiento") is not None:
        partes.append(f"Nivel de endeudamiento: {razones['endeudamiento']*100:.1f}%.")
    if razones.get("roe") is not None:
        partes.append(f"ROE: {razones['roe']*100:.1f}%.")
    if razones.get("z") is not None:
        partes.append(f"Z-Score de Altman: {razones['z']:.2f} (Zona: {((contexto.get('z_info') or {}).get('zona', 'N/D'))}).")
    if contexto.get("decision"):
        partes.append(f"Veredicto Simulación Monte Carlo: {contexto['decision'].upper()}.")
    return " ".join(partes) if partes else "Sin datos financieros cargados aún en la sesión."

def responder_con_llm(historial_chat, pregunta_actual, contexto=None):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not GENAI_AVAILABLE:
        return None
    try:
        info_ctx = _contexto_a_texto(contexto)
        
        # Primer mensaje con el system prompt y el contexto dinámico
        mensajes_para_gemini = [
            {"role": "user", "parts": [f"{SYSTEM_PROMPT_FINANIA}\n\n[CONTEXTO ACTUAL DE LA APLICACIÓN]\n{info_ctx}"]},
            {"role": "model", "parts": ["Entendido. Tengo en cuenta las instrucciones, el rol de analista sénior y los datos de la sesión actual."]}
        ]
        
        # Agregar historial previo manteniendo la secuencia
        for turno in (historial_chat or []):
            if isinstance(turno, dict):
                r = "user" if turno.get("role") == "user" else "model"
                c = turno.get("content", "")
                if c:
                    mensajes_para_gemini.append({"role": r, "parts": [str(c)]})
            elif isinstance(turno, (list, tuple)) and len(turno) == 2:
                if turno[0]:
                    mensajes_para_gemini.append({"role": "user", "parts": [str(turno[0])]})
                if turno[1]:
                    mensajes_para_gemini.append({"role": "model", "parts": [str(turno[1])]})

        # Pregunta del turno actual
        mensajes_para_gemini.append({"role": "user", "parts": [str(pregunta_actual)]})

        client = genai.Client(api_key=api_key)
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=mensajes_para_gemini,
        )
        return res.text
    except Exception as e:
        print("Error al llamar a Gemini:", e)
        return None

CONCEPTOS_RESPALDO = {
    "wacc": "WACC es el costo promedio ponderado de capital. Representa el rendimiento mínimo que debe generar una compañía sobre su base de activos existente para satisfacer a los acreedores y accionistas.",
    "eva": "EVA (Valor Económico Agregado). Mide el verdadero beneficio económico restante una vez deducido el costo total del capital invertido. EVA > 0 crea riqueza.",
    "roe": "ROE = Utilidad Neta / Patrimonio. Mide la rentabilidad del capital propio aportado por los socios o accionistas.",
    "roa": "ROA = Utilidad Neta / Activos Totales. Mide la eficiencia operativa con la que la gerencia utiliza los recursos totales.",
    "z altman": "Z de Altman es un modelo multivariado que predice el riesgo de insolvencia a 2 años. Z > 2.99 Zona Segura | 1.81 - 2.99 Zona Gris | < 1.81 Zona de Quiebra.",
    "van": "VAN descuenta los flujos de caja futuros a una tasa de oportunidad. Si VAN > 0 el proyecto genera valor neto por encima de la tasa exigida.",
    "tir": "TIR es la tasa de descuento intrínseca que hace el VAN igual a cero. Si la TIR supera el WACC o costo de capital, el proyecto es viable.",
}

def chatbot_responder(historial, pregunta, contexto=None):
    if not pregunta or not str(pregunta).strip():
        return "¡Hola! Soy FinanIA. Puedes consultarme conceptos financieros, pedirme análisis estratégicos o interpretar la empresa cargada."
    
    # 1. Intentar responder con Gemini
    llm_resp = responder_con_llm(historial, pregunta, contexto)
    if llm_resp:
        return llm_resp

    # 2. Respaldo si no hay conexión
    q = pregunta.lower().strip()
    for k, v in CONCEPTOS_RESPALDO.items():
        if k in q:
            return f"*(Modo sin API Key)* **{k.upper()}:** {v}"
    return "No se pudo contactar con Gemini. Revisa que `GEMINI_API_KEY` esté configurada en las Variables de Entorno de Render."

def chat_ui(hist, msg, ctx):
    if not msg or not str(msg).strip():
        return hist, ""
    resp = chatbot_responder(hist, msg, ctx or {})
    hist = list(hist or [])
    hist.append({"role": "user", "content": str(msg)})
    hist.append({"role": "assistant", "content": str(resp)})
    return hist, ""

# ============================================================
# DATOS Y CATÁLOGO
# ============================================================

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
        raise ValueError("Datos vacíos tras limpieza.")
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

# ============================================================
# CÁLCULOS FINANCIEROS Y DIAGNÓSTICO
# ============================================================

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

def calcular_tir(flujos):
    f = [float(x) for x in flujos]
    tir = npf.irr(f)
    if np.isnan(tir): raise ValueError("TIR no converge")
    return float(tir)

def calcular_van(flujos, tasa): return float(sum(x / (1 + _tasa(tasa)) ** t for t, x in enumerate(flujos)))

def calcular_wacc(ke, kd, e, d, tax):
    ke, kd, e, d = _tasa(ke), _tasa(kd), _pos(e, "E"), max(0.0, float(d))
    tax = max(0.0, min(1.0, float(tax)))
    v = e + d
    return (e / v) * ke + (d / v) * kd * (1 - tax)

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
    dupont = None if None in (mn, (ven/at if at else None), (at/pat if pat else None)) else (un/pat)

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

def metricas_mercado(serie, nombre="Activo"):
    s = serie.dropna()
    if len(s) < 10: raise ValueError("Pocos datos de precio.")
    ret = s.pct_change().dropna()
    mu, sig = float(ret.mean()), float(ret.std(ddof=1))
    vol_a = sig * np.sqrt(252)
    return {
        "nombre": nombre, "mu_diario": mu, "sigma_diario": sig,
        "volatilidad_anual": vol_a, "retorno_total": float(s.iloc[-1] / s.iloc[0] - 1),
        "retornos": ret, "serie": s
    }

def simulacion_decision(mu=0.0005, sigma=0.015, n=2000, umbral=0.30, horizonte=252):
    rng = np.random.default_rng(42)
    shocks = rng.normal(mu, sigma, size=(int(n), int(horizonte)))
    dist = np.prod(1 + shocks, axis=1) - 1
    p_bad, ret_e = float(np.mean(dist < 0)), float(np.mean(dist))
    decision = "rechazar" if p_bad > umbral else ("revisar" if p_bad > umbral / 2 else ("aceptar" if ret_e > 0 else "revisar"))
    detalle = f"**Decisión Simulación:** {decision.upper()}\n\n- Probabilidad de pérdida proyectada: {p_bad*100:.1f}%\n- Rendimiento anual esperado: {ret_e*100:.2f}%"
    return {"decision": decision, "probabilidad_desfavorable": p_bad, "retorno_esperado": ret_e, "distribucion": dist, "detalle": detalle}

def analisis_integrado(diag, pack_riesgo):
    razones = (diag or {}).get("razones") or {}
    z_info = (diag or {}).get("z_info") or {}
    nombre = (diag or {}).get("nombre") or "Empresa"
    score = 50.0
    z, rc, end, roe = razones.get("z"), razones.get("razon_corriente"), razones.get("endeudamiento"), razones.get("roe")
    if z is not None: score += 20 if z > 2.99 else (5 if z >= 1.81 else -25)
    if rc is not None: score += 10 if rc >= 1.5 else (-15 if rc < 1 else 0)
    if end is not None: score += -15 if end > 0.7 else (-5 if end > 0.45 else 5)
    if roe is not None: score += 10 if roe >= 0.12 else (-10 if roe < 0.05 else 3)
    score = float(np.clip(score, 0, 100))
    clasif = "saludable" if score >= 70 else ("precaucion" if score >= 45 else "alerta")
    md = f"### 🎯 Análisis Integrado — {nombre}\n\n**Score de Solvencia:** {score:.1f} / 100 ({clasif.upper()})"
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
    Actúa como asesor financiero senior. Redacta un informe ejecutivo integral y analítico (3-4 párrafos estructurados):
    - Diagnóstico de solvencia: {c} (Score: {score:.1f}/100)
    - Decisión Monte Carlo: {d}
    - Probabilidad de pérdida en 1 año: {p*100:.1f}%
    - Rendimiento esperado proyectado: {r*100:.1f}%
    
    Estructura:
    1. **Diagnóstico Integral:** Evalúa la estructura de capital y solvencia de la empresa.
    2. **Perfil Riesgo-Retorno:** Interpreta los resultados de la simulación y probabilidad de pérdida.
    3. **Recomendaciones Estratégicas:** Acciones concretas para mitigación de riesgos o decisiones de inversión.
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
        Paragraph("1. Diagnóstico Financiero:", styles['Heading2']),
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

# ============================================================
# INTERFAZ GRADIO (UI)
# ============================================================

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
            msg = gr.Textbox(label="Pregunta", placeholder="Pregunta sobre finanzas, métricas o la empresa cargada...")
            with gr.Row():
                btn_send = gr.Button("Enviar", variant="primary")
                btn_clr = gr.Button("Limpiar")

    # Enlaces de eventos
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
            {
                "z_info": (diag or {}).get("z_info"),
                "clasificacion": analisis_integrado(diag, riesgo).get("clasificacion"),
                "decision": (sim or {}).get("decision"),
                "nombre": (diag or {}).get("nombre"),
                "score": analisis_integrado(diag, riesgo).get("score"),
                "razones": (diag or {}).get("razones")
            }
        ),
        [st_diag, st_riesgo, st_sim],
        [md_int, st_integ_state, md_ia, st_ctx]
    )

    btn_pdf.click(generar_reporte_pdf, [st_nombre, st_diag, st_riesgo, st_sim, st_ctx], [file_pdf, md_int])
    btn_calc.click(run_calc_ui, [c_tipo, cv1, cv2, cv3, cv4, cv5], md_calc)
    
    # Chatbot interactivo
    btn_send.click(chat_ui, [chat, msg, st_ctx], [chat, msg])
    msg.submit(chat_ui, [chat, msg, st_ctx], [chat, msg])
    btn_clr.click(lambda: [], outputs=chat)

# Ejecución para Render
port = int(os.environ.get("PORT", 7860))
demo.launch(server_name="0.0.0.0", server_port=port)
