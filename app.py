 =====================================

_NIVEL_COLORES = {
    "bien": (COLORS["green_light"], COLORS["green"]),
    "atencion": (COLORS["yellow_light"], COLORS["yellow"]),
    "mal": (COLORS["red_light"], COLORS["red"]),
    "neutral": (COLORS["primary_light"], COLORS["primary"]),
}

def _tarjeta_indicador(icono, titulo, valor, nota, nivel="neutral"):
    bg, borde = _NIVEL_COLORES.get(nivel, _NIVEL_COLORES["neutral"])
    return (
        f'<div style="background:{bg};border-left:5px solid {borde};border-radius:12px;'
        f'padding:12px 14px;box-shadow:0 1px 2px rgba(15,23,42,0.06);">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="font-size:12.5px;font-weight:600;color:#334155;">{icono} {titulo}</span>'
        f'<span style="font-size:19px;font-weight:800;color:{borde};">{valor}</span>'
        f'</div>'
        f'<div style="font-size:11.5px;color:#64748B;margin-top:3px;">{nota}</div>'
        f'</div>'
    )

def _grid_tarjetas(tarjetas_html, columnas=2):
    filas = "\n".join(tarjetas_html)
    return (
        f'<div style="display:grid;grid-template-columns:repeat({columnas}, 1fr);'
        f'gap:10px;margin:10px 0;">\n{filas}\n</div>'
    )

def calcular_diagnostico(ac, pc, inv, un, ven, at, pat, pt, ur, uo, vm, nombre_empresa="Empresa"):
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
        z = 1.2*(ktn/at) + 1.4*(ur/at) + 3.3*(uo/at) + 0.6*(vm/pt) + 1.0*(ven/at)

    if z is None:
        z_info = {"zona": "No calculable", "color": COLORS["muted"], "rec": "Faltan datos."}
    elif z > 2.99:
        z_info = {"zona": "Zona Segura", "color": COLORS["green"], "rec": "✅ Situación sólida. Bajo riesgo de insolvencia."}
    elif z >= 1.81:
        z_info = {"zona": "Zona Gris", "color": COLORS["yellow"], "rec": "⚠️ Zona intermedia. Vigilar liquidez y deuda."}
    else:
        z_info = {"zona": "Zona de Riesgo", "color": COLORS["red"], "rec": "🔴 Riesgo elevado. Revisar liquidez y endeudamiento."}

    def p(x): return f"{x*100:.2f}%" if x is not None else "N/D"
    def n(x): return f"{x:,.2f}" if x is not None else "N/D"

    nivel_rc = "bien" if (rc is not None and rc >= 1.5) else "atencion" if (rc is not None and rc >= 1) else ("mal" if rc is not None else "neutral")
    nivel_end = "mal" if (end is not None and end > 0.7) else "atencion" if (end is not None and end > 0.45) else ("bien" if end is not None else "neutral")
    nivel_roe = "bien" if (roe_v is not None and roe_v >= 0.12) else "atencion" if (roe_v is not None and roe_v >= 0) else ("mal" if roe_v is not None else "neutral")
    nivel_roa = "mal" if (roa_v is not None and roa_v < 0) else "neutral"
    nivel_mn = "mal" if (mn is not None and mn < 0) else "neutral"

    tarjetas = [
        _tarjeta_indicador("💧", "Razón Corriente", n(rc), "Saludable si es mayor a 1.5", nivel_rc),
        _tarjeta_indicador("🧪", "Prueba Ácida", n(pa), "Liquidez sin depender de inventarios", "neutral"),
        _tarjeta_indicador("🧰", "Capital de Trabajo Neto", n(ktn), "Margen de seguridad operativo", "neutral"),
        _tarjeta_indicador("📈", "Margen Neto", p(mn), "Rentabilidad sobre ventas", nivel_mn),
        _tarjeta_indicador("🏭", "ROA", p(roa_v), "Rentabilidad de los activos", nivel_roa),
        _tarjeta_indicador("💼", "ROE", p(roe_v), "Rentabilidad para los accionistas", nivel_roe),
        _tarjeta_indicador("⚖️", "Endeudamiento", p(end), "% de activos financiados con deuda", nivel_end),
        _tarjeta_indicador("🧩", "ROE DuPont", p(dupont), "Descomposición del ROE", "neutral"),
    ]
    grid_html = _grid_tarjetas(tarjetas, columnas=2)

    z_card = (
        f'<div style="background:linear-gradient(135deg,{z_info["color"]}22,{z_info["color"]}11);'
        f'border:2px solid {z_info["color"]};border-radius:14px;padding:16px 18px;margin-top:6px;">'
        f'<div style="font-size:13px;color:#475569;font-weight:600;">🧮 Z de Altman (riesgo de quiebra)</div>'
        f'<div style="display:flex;align-items:baseline;gap:12px;margin-top:4px;">'
        f'<span style="font-size:28px;font-weight:800;color:{z_info["color"]};">{n(z)}</span>'
        f'<span style="font-size:16px;font-weight:700;color:{z_info["color"]};">{z_info["zona"]}</span>'
        f'</div>'
        f'<div style="font-size:12.5px;color:#334155;margin-top:6px;">{z_info["rec"]}</div>'
        f'</div>'
    )

    md = (
        f'<div style="font-size:15px;font-weight:700;color:#1E40AF;margin-bottom:8px;">'
        f'📊 Diagnóstico Financiero — {nombre_empresa}</div>\n'
        f'{grid_html}\n{z_card}'
    )

    razones = {
        "razon_corriente": rc, "prueba_acida": pa, "ktn": ktn, "margen_neto": mn,
        "roa": roa_v, "roe": roe_v, "endeudamiento": end, "dupont": dupont, "z": z,
    }
    return {"razones": razones, "z_info": z_info, "texto_md": md, "nombre": nombre_empresa}

# ============================================================
# RIESGOS Y MONTE CARLO
# ============================================================

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
        "retornos": ret, "n_obs": len(s), "serie": s,
    }

def prediccion_simple(serie, dias=30):
    s = serie.dropna()
    if len(s) < 20:
        return None
    ma20 = s.rolling(20).mean().iloc[-1]
    y = s.tail(60).values
    x = np.arange(len(y))
    coef = np.polyfit(x, y, 1)
    proyeccion = coef[0] * (len(y) + dias) + coef[1]
    cambio_pct = (proyeccion / s.iloc[-1] - 1) * 100
    return {
        "precio_actual": float(s.iloc[-1]),
        "ma20": float(ma20),
        "proyeccion_30d": float(proyeccion),
        "cambio_esperado_pct": float(cambio_pct),
        "tendencia": "alcista" if coef[0] > 0 else "bajista",
    }

def seis_riesgos(m=None, razones=None, sector="N/D"):
    m, razones = m or {}, razones or {}
    vol = m.get("volatilidad_anual")
    rc = razones.get("razon_corriente")
    end = razones.get("endeudamiento")
    roe = razones.get("roe")
    out = {}
    out["mercado"] = ("alto" if vol and vol > 0.45 else "medio" if vol and vol > 0.25 else "bajo", f"Vol {vol*100:.1f}%" if vol else "Sin precios")
    out["credito"] = ("alto" if end and end > 0.7 else "medio" if end and end > 0.45 else "bajo", f"Deuda {end*100:.0f}%" if end else "Sin dato")
    out["liquidez"] = ("alto" if rc and rc < 1 else "medio" if rc and rc < 1.5 else "bajo", f"RC {rc:.2f}" if rc else "Sin dato")
    sec = (sector or "").lower()
    alto = any(x in sec for x in ("energy", "retail", "auto", "airline"))
    out["operacional"] = ("medio" if alto else "bajo", f"Sector {sector}")
    out["legal"] = ("medio", "Regulación de valores / sector")
    out["reputacional"] = ("medio" if (roe is not None and roe < 0) else "bajo", "Según ROE y señales")
    return out

def texto_riesgos(m, riesgos, pred=None, nombre_empresa="Empresa"):
    nivel_vol = "mal" if m["volatilidad_anual"] > 0.45 else "atencion" if m["volatilidad_anual"] > 0.25 else "bien"
    nivel_dd = "mal" if m["max_drawdown"] < -0.30 else "atencion" if m["max_drawdown"] < -0.15 else "bien"
    nivel_ret = "bien" if m["retorno_total"] >= 0 else "mal"

    tarjetas_mercado = [
        _tarjeta_indicador("💵", "Retorno del periodo", f"{m['retorno_total']*100:+.2f}%", "Ganancia o pérdida total en el periodo", nivel_ret),
        _tarjeta_indicador("📊", "Volatilidad anual", f"{m['volatilidad_anual']*100:.2f}%", "Qué tanto oscila el precio al año", nivel_vol),
        _tarjeta_indicador("⚖️", "Coeficiente de Variación", f"{m['coeficiente_variacion']:.2f}", "Riesgo por cada unidad de retorno", "neutral"),
        _tarjeta_indicador("🛑", "VaR 1 día (95%)", f"{m['var_1d_95']*100:.2f}%", "Pérdida máxima esperada 19 de cada 20 días", "neutral"),
        _tarjeta_indicador("🛑", "VaR 1 día (99%)", f"{m['var_1d_99']*100:.2f}%", "Pérdida máxima esperada casi todos los días", "neutral"),
        _tarjeta_indicador("📉", "Máximo Drawdown", f"{m['max_drawdown']*100:.2f}%", "La peor caída desde un máximo histórico", nivel_dd),
    ]
    html = (
        f'<div style="font-size:15px;font-weight:700;color:#1E40AF;margin-bottom:8px;">'
        f'📈 Riesgo de Mercado — {nombre_empresa}</div>\n'
        f'{_grid_tarjetas(tarjetas_mercado, columnas=2)}\n'
    )

    labels = {"mercado": "1. Mercado", "credito": "2. Crédito", "liquidez": "3. Liquidez",
              "operacional": "4. Operacional", "legal": "5. Legal", "reputacional": "6. Reputacional"}
    em = {"bajo": "🟢", "medio": "🟡", "alto": "🔴"}
    nivel_map = {"bajo": "bien", "medio": "atencion", "alto": "mal"}
    tarjetas_riesgos = []
    for k, lab in labels.items():
        niv, det = riesgos[k]
        tarjetas_riesgos.append(_tarjeta_indicador(em.get(niv, "⚪"), lab, niv.upper(), det, nivel_map.get(niv, "neutral")))
    html += (
        f'<div style="font-size:15px;font-weight:700;color:#1E40AF;margin:14px 0 8px;">'
        f'🛡️ Los 6 Riesgos Empresariales — {nombre_empresa}</div>\n'
        f'{_grid_tarjetas(tarjetas_riesgos, columnas=3)}\n'
    )

    if pred:
        html += (
            f'<div style="background:{COLORS["primary_light"]};border-radius:12px;padding:14px 16px;margin-top:10px;">'
            f'<div style="font-size:13.5px;font-weight:700;color:{COLORS["primary"]};">🔮 Predicción simple (30 días) — {nombre_empresa}</div>'
            f'<div style="font-size:12.5px;color:#334155;margin-top:6px;">'
            f'Precio actual: <b>${pred["precio_actual"]:,.2f}</b> · '
            f'Media móvil 20 días: <b>${pred["ma20"]:,.2f}</b> · '
            f'Proyección 30 días: <b>${pred["proyeccion_30d"]:,.2f}</b> ({pred["cambio_esperado_pct"]:+.1f}%) · '
            f'Tendencia: <b>{pred["tendencia"].upper()}</b>'
            f'</div>'
            f'<div style="font-size:11px;color:#64748B;margin-top:6px;">⚠️ Proyección estadística simple. No es consejo de inversión.</div>'
            f'</div>'
        )
    return html

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
        motivo = f"P(pérdida)={p_bad*100:.1f}%, retorno esperado {ret_e*100:.1f}%"
    detalle = f"""**Decisión de la simulación: {decision.upper()}**

{motivo}

- Escenarios: {n:,} | Horizonte: {horizonte} días
- μ diario: {mu:.6f} | σ diario: {sigma:.6f}
- Retorno esperado: **{ret_e*100:.2f}%**
- P5: {np.percentile(dist,5)*100:.2f}% | P95: {np.percentile(dist,95)*100:.2f}%
"""
    return {"decision": decision, "probabilidad_desfavorable": p_bad,
            "retorno_esperado": ret_e, "distribucion": dist, "detalle": detalle,
            "n_escenarios": n, "horizonte": horizonte}

def interpretar_grafico_montecarlo(sim, nombre_empresa="la empresa"):
    if not sim:
        return ""
    p_bad = sim.get("probabilidad_desfavorable", 0) * 100
    ret_e = sim.get("retorno_esperado", 0) * 100
    n = sim.get("n_escenarios", 0)
    horizonte = sim.get("horizonte", 252)
    decision = sim.get("decision", "revisar")
    dist = sim.get("distribucion")
    p5 = np.percentile(dist, 5) * 100 if dist is not None else None
    p95 = np.percentile(dist, 95) * 100 if dist is not None else None

    veredicto = {
        "aceptar": "la balanza se inclina más hacia escenarios de ganancia que de pérdida",
        "revisar": "los resultados están repartidos de forma pareja entre ganar y perder, así que conviene analizarlo con calma",
        "rechazar": "una parte importante de los escenarios terminó en pérdida",
    }.get(decision, "los resultados son mixtos")

    partes = [
        f"**¿Qué significa esta gráfica?** Cada barra representa cuántos de los **{n:,} escenarios simulados** "
        f"(caminos posibles de precio a lo largo de {horizonte} días, aproximadamente un año) terminaron con ese "
        f"nivel de ganancia o pérdida.",
        f"La línea roja marca el punto de equilibrio (0%): todo lo que quede **a la izquierda** de esa línea son "
        f"escenarios donde se pierde dinero, y todo lo que quede **a la derecha** son escenarios donde se gana.",
        f"En este caso, de cada 100 escenarios probados, aproximadamente **{p_bad:.0f} terminaron en pérdida**, "
        f"y el resultado promedio esperado fue de **{ret_e:+.1f}%**.",
    ]
    if p5 is not None and p95 is not None:
        partes.append(
            f"En el peor 5% de los casos la pérdida rondó **{p5:.1f}%**, mientras que en el mejor 5% de los casos "
            f"la ganancia llegó a **{p95:.1f}%** — así de amplio puede ser el rango de resultados posibles."
        )
    partes.append(f"En resumen, para **{nombre_empresa}**, {veredicto}, por lo que la simulación sugiere **{decision.upper()}**.")
    return "\n\n".join(partes)

# ============================================================
# ANÁLISIS INTEGRADO
# ============================================================

def analisis_integrado(diag, pack_riesgo):
    razones = (diag or {}).get("razones") or {}
    z_info = (diag or {}).get("z_info") or {}
    m = (pack_riesgo or {}).get("metricas") or {}
    riesgos = (pack_riesgo or {}).get("riesgos") or {}
    nombre = (diag or {}).get("nombre") or m.get("nombre") or "Empresa"
    score = 50.0
    z, rc, end, roe, vol = razones.get("z"), razones.get("razon_corriente"), razones.get("endeudamiento"), razones.get("roe"), m.get("volatilidad_anual")
    if z is not None: score += 20 if z > 2.99 else (5 if z >= 1.81 else -25)
    if rc is not None: score += 10 if rc >= 1.5 else (-15 if rc < 1 else 0)
    if end is not None: score += -15 if end > 0.7 else (-5 if end > 0.45 else 5)
    if roe is not None: score += 10 if roe >= 0.12 else (-10 if roe < 0.05 else 3)
    if vol is not None: score += -15 if vol > 0.45 else (-5 if vol > 0.25 else 5)
    if riesgos:
        mapa = {"bajo": 20, "medio": 50, "alto": 80}
        avg = np.mean([mapa.get(v[0], 50) for v in riesgos.values()])
        score += (50 - avg) / 5
    score = float(np.clip(score, 0, 100))
    if score >= 70:
        clasif, color, msg = "saludable", COLORS["green"], "Diagnóstico **SALUDABLE**. Solidez y riesgo controlado."
    elif score >= 45:
        clasif, color, msg = "precaucion", COLORS["yellow"], "Diagnóstico en **PRECAUCIÓN**. Señales mixtas."
    else:
        clasif, color, msg = "alerta", COLORS["red"], "Diagnóstico en **ALERTA**. Vulnerabilidades materiales."

    val_z = f"{z:.2f}" if isinstance(z, (int, float)) else "N/D"
    val_zona = z_info.get('zona', 'N/D')
    val_rc = f"{rc:.2f}" if isinstance(rc, (int, float)) else "N/D"
    val_roe = f"{roe*100:.2f}%" if isinstance(roe, (int, float)) else "N/D"
    val_end = f"{end*100:.2f}%" if isinstance(end, (int, float)) else "N/D"
    val_vol = f"{vol*100:.2f}%" if isinstance(vol, (int, float)) else "N/D"

    md = f"""## 🎯 Análisis Integrado — **{nombre}** <span style="color:{color}">● {clasif.upper()}</span>

{msg}

**Score global: {score:.1f} / 100**

| Clave | Valor |
| :--- | :---: |
| Z Altman | {val_z} |
| Zona Z | {val_zona} |
| Razón corriente | {val_rc} |
| ROE | {val_roe} |
| Endeudamiento | {val_end} |
| Volatilidad | {val_vol} |
"""
    return {"clasificacion": clasif, "score": score, "texto_md": md, "z_info": z_info, "nombre": nombre, "razones": razones}

def interpretacion_narrativa(nombre_empresa, diag, pack, sim, integ):
    razones = (diag or {}).get("razones") or {}
    z_info = (diag or {}).get("z_info") or {}
    m = (pack or {}).get("metricas") or {}
    riesgos = (pack or {}).get("riesgos") or {}
    frases = []

    rc = razones.get("razon_corriente")
    if rc is not None:
        if rc >= 1.5:
            frases.append(f"Por cada $1 que la empresa debe pagar pronto, tiene ${rc:.2f} disponibles para cubrirlo, así que tiene un buen colchón para pagar sus deudas de corto plazo sin apuros.")
        elif rc >= 1:
            frases.append(f"Por cada $1 que debe pagar pronto, tiene ${rc:.2f} disponibles: alcanza, pero justo, por lo que conviene vigilar de cerca las fechas de pago.")
        else:
            frases.append(f"Por cada $1 que debe pagar pronto, solo tiene ${rc:.2f} disponibles: es decir, no le alcanzaría con lo que tiene a la mano para cubrir sus deudas más inmediatas, lo cual es una señal de alerta.")

    end = razones.get("endeudamiento")
    if end is not None:
        if end > 0.7:
            frases.append(f"De cada $100 en bienes y recursos que tiene la empresa, ${end*100:.0f} fueron financiados con préstamos o deudas — es un nivel alto.")
        elif end > 0.45:
            frases.append(f"De cada $100 en bienes y recursos, ${end*100:.0f} vienen de deuda: es un nivel moderado.")
        else:
            frases.append(f"De cada $100 en bienes y recursos, solo ${end*100:.0f} vienen de deuda: la empresa depende poco de préstamos.")

    roe = razones.get("roe")
    if roe is not None:
        if roe >= 0.12:
            frases.append(f"Por cada $100 que los dueños tienen invertidos, están ganando ${roe*100:.1f} al año: es una rentabilidad atractiva.")
        elif roe >= 0:
            frases.append(f"Por cada $100 invertidos por los dueños, la empresa les está devolviendo ${roe*100:.1f} al año: una ganancia modesta.")
        else:
            frases.append(f"Por cada $100 invertidos por los dueños, la empresa está perdiendo ${abs(roe)*100:.1f}.")

    if z_info:
        explicacion_zona = {
            "Zona Segura": "el riesgo de que la empresa quiebre en el corto/mediano plazo es bajo",
            "Zona Gris": "la empresa no está en peligro inmediato, pero tampoco está del todo firme",
            "Zona de Riesgo": "el modelo detecta señales similares a las de empresas que han tenido problemas serios",
        }.get(z_info.get("zona"), "")
        frases.append(f"El modelo Z de Altman la ubica en **{z_info.get('zona','N/D')}**; {explicacion_zona}.")

    vol = m.get("volatilidad_anual")
    if vol is not None:
        if vol > 0.45:
            frases.append(f"El precio de la acción sube y baja mucho ({vol*100:.1f}% de variación anual).")
        elif vol > 0.25:
            frases.append(f"El precio de la acción tiene movimientos moderados ({vol*100:.1f}% de variación anual).")
        elif vol:
            frases.append(f"El precio de la acción se mueve poco ({vol*100:.1f}% de variación anual).")

    if riesgos:
        labels = {"mercado": "de mercado", "credito": "de crédito", "liquidez": "de liquidez",
                  "operacional": "operacional", "legal": "legal/regulatorio", "reputacional": "reputacional"}
        altos = [labels.get(k, k) for k, v in riesgos.items() if v[0] == "alto"]
        if altos:
            frases.append(f"De los 6 riesgos, los que están en nivel más alto son: {', '.join(altos)}.")
        else:
            frases.append("Ninguno de los 6 riesgos está en nivel alto en este momento.")

    if sim:
        decision_txt = {
            "aceptar": "los números favorecen considerar la inversión",
            "revisar": "los resultados están parejos entre ganar y perder",
            "rechazar": "los números no favorecen invertir en este momento",
        }.get(sim.get("decision"), "")
        frases.append(f"La simulación Monte Carlo indica que {sim.get('probabilidad_desfavorable',0)*100:.0f} de cada 100 escenarios terminaron en pérdida, con retorno esperado de {sim.get('retorno_esperado',0)*100:+.1f}%. En otras palabras, {decision_txt}.")

    if integ:
        clasif_txt = {
            "saludable": "está en buen estado general",
            "precaucion": "muestra señales mixtas",
            "alerta": "tiene vulnerabilidades importantes",
        }.get(integ.get("clasificacion"), "")
        frases.append(f"Poniendo todo junto, {nombre_empresa} obtiene un puntaje de **{integ.get('score',0):.0f} sobre 100**, lo que significa que {clasif_txt}.")

    if not frases:
        return "No hay suficiente información para generar una interpretación. Completa Diagnóstico, Riesgos y Simulación."
    return " ".join(frases)

def grafico_resumen_asistente(ctx):
    ctx = ctx or {}
    score = ctx.get("score")
    riesgos = ctx.get("riesgos") or {}
    nombre = ctx.get("nombre") or "tu empresa"

    if score is None:
        fig, ax = plt.subplots(figsize=(4.6, 4.2))
        ax.axis("off")
        ax.text(0.5, 0.6, "📊", ha="center", va="center", fontsize=40)
        ax.text(0.5, 0.3, "Completa Diagnóstico → Riesgos → Análisis Integrado\npara ver aquí el resumen visual de tu empresa.",
                ha="center", va="center", fontsize=9.5, color=COLORS["muted"], wrap=True)
        plt.tight_layout()
        return fig

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(4.6, 5.6), gridspec_kw={"height_ratios": [1, 1.3]})
    color_score = COLORS["green"] if score >= 70 else COLORS["yellow"] if score >= 45 else COLORS["red"]
    ax1.pie([score, 100 - score], colors=[color_score, "#E2E8F0"], startangle=90, counterclock=False,
            wedgeprops={"width": 0.35, "edgecolor": "white"})
    ax1.text(0, 0, f"{score:.0f}\n/100", ha="center", va="center", fontsize=16, fontweight="bold")
    ax1.set_title(f"Score integrado — {nombre}", fontweight="bold", fontsize=11)

    if riesgos:
        labels = {"mercado": "Mercado", "credito": "Crédito", "liquidez": "Liquidez",
                  "operacional": "Operacional", "legal": "Legal", "reputacional": "Reputacional"}
        mapa_val = {"bajo": 1, "medio": 2, "alto": 3}
        mapa_col = {"bajo": COLORS["green"], "medio": COLORS["yellow"], "alto": COLORS["red"]}
        claves = list(labels.keys())
        vals = [mapa_val.get(riesgos.get(k, ("bajo",))[0], 1) for k in claves]
        cols = [mapa_col.get(riesgos.get(k, ("bajo",))[0], COLORS["muted"]) for k in claves]
        ax2.barh([labels[k] for k in claves], vals, color=cols)
        ax2.set_xlim(0, 3)
        ax2.set_xticks([1, 2, 3])
        ax2.set_xticklabels(["Bajo", "Medio", "Alto"])
        ax2.set_title("Semáforo de los 6 riesgos", fontweight="bold", fontsize=11)
        ax2.grid(True, alpha=0.3, axis="x")
    else:
        ax2.axis("off")
        ax2.text(0.5, 0.5, "Sin datos de riesgo aún", ha="center", va="center", color=COLORS["muted"])
    plt.tight_layout()
    return fig

# ============================================================
# REPORTES EN PDF (REPORTLAB)
# ============================================================

UNIVERSIDAD_PROYECTO = "Universidad de Nariño"
INTEGRANTES_PROYECTO = [
    "Claudia Jackeline Perafán Sánchez",
    "Karen Dayana Briñes Astaiza",
    "Karen Gissell Aza Fernández",
    "Harol Bladimir Tobar Arteaga",
]

_EMOJI_RE = _re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U00002100-\U0000214F"
    "\U0000FE0F"
    "]+"
)

def _limpiar_para_pdf(texto):
    if not texto:
        return ""
    t = str(texto)
    t = _EMOJI_RE.sub("", t)
    t = _re.sub(r"<[^>]+>", " ", t)
    t = _re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", t)
    t = _re.sub(r"\*(.*?)\*", r"<i>\1</i>", t)
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = t.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
    t = t.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
    t = "\n".join(_re.sub(r"[ \t]+", " ", linea).strip() for linea in t.split("\n"))
    return t.strip()

def _esc(texto):
    if texto is None:
        return ""
    t = str(texto)
    t = _EMOJI_RE.sub("", t)
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _nombre_archivo_seguro(nombre):
    base = str(nombre or "Empresa")
    base = (base.replace("á", "a").replace("é", "e").replace("í", "i")
                .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
                .replace("Á", "A").replace("É", "E").replace("Í", "I")
                .replace("Ó", "O").replace("Ú", "U").replace("Ñ", "N"))
    base = _re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_")
    return base or "Empresa"

def _crear_logo_financiero():
    d = Drawing(180, 70)
    d.add(Rect(0, 0, 180, 70, rx=8, ry=8, fillColor=colors.HexColor("#1E40AF"), strokeColor=None))
    barras = [(12, 18), (28, 28), (44, 22), (60, 38), (76, 45), (92, 35), (108, 52)]
    for x, h in barras:
        d.add(Rect(x, 12, 10, h, fillColor=colors.HexColor("#93C5FD"), strokeColor=None))
    d.add(Line(12, 20, 118, 58, strokeColor=colors.white, strokeWidth=2.2))
    d.add(String(130, 38, "RF", fontSize=22, fillColor=colors.white, fontName="Helvetica-Bold"))
    d.add(String(128, 18, "Robot", fontSize=8, fillColor=colors.HexColor("#BFDBFE"), fontName="Helvetica"))
    return d

def _fig_a_imagen_pdf(fig, ancho_cm=15.5):
    if fig is None:
        return None
    try:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor())
        buf.seek(0)
        ancho_in, alto_in = fig.get_size_inches()
        proporcion = (alto_in / ancho_in) if ancho_in else 0.5
        ancho = ancho_cm * cm
        alto = ancho * proporcion
        return RLImage(buf, width=ancho, height=alto)
    except Exception as e:
        print("No se pudo insertar una gráfica en el PDF:", e)
        return None

def _grafico_diagnostico_pdf(razones, nombre_empresa="Empresa"):
    if not razones:
        return None
    try:
        etiquetas, valores, colores_b = [], [], []
        pares = [
            ("Razón Corriente", razones.get("razon_corriente"), False),
            ("Endeudamiento %", razones.get("endeudamiento"), True),
            ("ROE %", razones.get("roe"), True),
            ("ROA %", razones.get("roa"), True),
            ("Margen Neto %", razones.get("margen_neto"), True),
        ]
        for nombre, valor, es_pct in pares:
            if valor is not None:
                etiquetas.append(nombre)
                valores.append(valor * 100 if es_pct else valor)
                colores_b.append(COLORS["red"] if valor < 0 else COLORS["primary"])
        if not etiquetas:
            return None
        fig, ax = plt.subplots(figsize=(7.5, 3))
        barras = ax.bar(etiquetas, valores, color=colores_b, alpha=0.9, edgecolor="white")
        ax.axhline(0, color=COLORS["muted"], lw=1)
        for b_, v_ in zip(barras, valores):
            ax.annotate(f"{v_:.1f}", (b_.get_x()+b_.get_width()/2, b_.get_height()),
                        ha="center", va="bottom" if v_ >= 0 else "top", fontsize=8, fontweight="bold")
        ax.set_title(f"Indicadores clave del diagnóstico — {nombre_empresa}", fontweight="bold", fontsize=11)
        ax.grid(True, alpha=0.3, axis="y")
        plt.xticks(rotation=12, ha="right", fontsize=8.5)
        plt.tight_layout()
        return fig
    except Exception as e:
        print("No se pudo generar el gráfico de diagnóstico:", e)
        return None

def generar_pdf(nombre_empresa, diag, pack, sim, integ, pred=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=1.4*cm, leftMargin=1.4*cm,
                            topMargin=1.2*cm, bottomMargin=1.2*cm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleCustom', parent=styles['Heading1'],
                                 fontSize=22, textColor=colors.HexColor("#1E40AF"),
                                 spaceAfter=6, alignment=TA_CENTER, fontName='Helvetica-Bold', leading=26)
    h2_style = ParagraphStyle('H2Custom', parent=styles['Heading2'],
                              fontSize=13, textColor=colors.HexColor("#2563EB"),
                              spaceBefore=8, spaceAfter=4, fontName='Helvetica-Bold')
    normal = ParagraphStyle('NormalCustom', parent=styles['Normal'],
                            fontSize=10, leading=13, alignment=TA_JUSTIFY, spaceAfter=3)
    small = ParagraphStyle('Small', parent=styles['Normal'],
                           fontSize=8.5, textColor=colors.HexColor("#64748B"), leading=11)
    uni_style = ParagraphStyle('Uni', parent=styles['Normal'],
                               fontSize=14, alignment=TA_CENTER,
                               textColor=colors.HexColor("#1E40AF"), fontName='Helvetica-Bold', spaceAfter=2)
    integrantes_style = ParagraphStyle('Integrantes', parent=styles['Normal'],
                                       fontSize=11, alignment=TA_CENTER,
                                       textColor=colors.HexColor("#334155"), leading=15, spaceAfter=2)
    caption_style = ParagraphStyle('Caption', parent=styles['Normal'],
                                   fontSize=9, alignment=TA_CENTER,
                                   textColor=colors.HexColor("#475569"), spaceBefore=2, spaceAfter=6)
    analisis_style = ParagraphStyle('Analisis', parent=styles['Normal'],
                                    fontSize=9.5, leading=12.5, alignment=TA_JUSTIFY,
                                    textColor=colors.HexColor("#1E293B"), spaceBefore=2, spaceAfter=6,
                                    backColor=colors.HexColor("#F1F5F9"), borderPadding=6)

    story = []
    nombre_seguro = _esc(nombre_empresa)

    story.append(_crear_logo_financiero())
    story.append(Spacer(1, 0.35*cm))
    story.append(Paragraph(_esc(UNIVERSIDAD_PROYECTO).upper(), uni_style))
    story.append(Spacer(1, 0.15*cm))
    story.append(Paragraph("<b>Integrantes del proyecto:</b>", integrantes_style))
    for nom in INTEGRANTES_PROYECTO:
        story.append(Paragraph(_esc(nom), integrantes_style))
    story.append(Spacer(1, 0.35*cm))
    story.append(Paragraph("ROBOT FINANCIERO INTELIGENTE", title_style))
    story.append(Paragraph("Informe de Análisis Financiero Integral",
                           ParagraphStyle('Sub', parent=styles['Normal'], fontSize=12,
                                          alignment=TA_CENTER, textColor=colors.HexColor("#64748B"), spaceAfter=4)))
    story.append(HRFlowable(width="100%", thickness=2.5, color=colors.HexColor("#2563EB"), spaceBefore=2, spaceAfter=6))
    story.append(Paragraph(f"<b>Empresa analizada:</b> {nombre_seguro}",
                           ParagraphStyle('Emp', parent=normal, fontSize=12, alignment=TA_CENTER, spaceAfter=2)))
    story.append(Paragraph(f"<b>Fecha del informe:</b> {date.today().strftime('%d/%m/%Y')}",
                           ParagraphStyle('Fec', parent=normal, fontSize=11, alignment=TA_CENTER, spaceAfter=4)))
    if integ:
        clasif = integ.get("clasificacion", "N/D").upper()
        score = integ.get("score", 0)
        col = {"saludable": "#059669", "precaucion": "#D97706", "alerta": "#DC2626"}.get(integ.get("clasificacion"), "#64748B")
        story.append(Paragraph(f"<b>Clasificación:</b> <font color='{col}'>{clasif}</font>  &nbsp;|&nbsp;  <b>Score global:</b> {score:.1f}/100",
                               ParagraphStyle('Clas', parent=normal, fontSize=11, alignment=TA_CENTER, spaceAfter=4)))
    story.append(Paragraph("Informe generado automáticamente · Uso educativo · No constituye consejo de inversión.", small))
    story.append(PageBreak())

    # 1. Diagnóstico
    story.append(Paragraph(f"1. Diagnóstico Financiero — {nombre_seguro}", h2_style))
    if diag and diag.get("texto_md"):
        txt = _limpiar_para_pdf(diag["texto_md"])
        for line in txt.split("\n")[:16]:
            if line.strip():
                story.append(Paragraph(line.strip()[:220], normal))

    img_diag = _fig_a_imagen_pdf(_grafico_diagnostico_pdf((diag or {}).get("razones"), nombre_empresa), ancho_cm=15.5)
    if img_diag:
        story.append(Spacer(1, 0.15*cm))
        story.append(img_diag)
        story.append(Paragraph(f"Gráfico de indicadores clave del diagnóstico — {nombre_seguro}", caption_style))
        razones = (diag or {}).get("razones") or {}
        analisis_diag = []
        if razones.get("razon_corriente") is not None:
            analisis_diag.append(f"La razón corriente ({razones['razon_corriente']:.2f}) indica la capacidad de pago a corto plazo.")
        if razones.get("endeudamiento") is not None:
            analisis_diag.append(f"El endeudamiento ({razones['endeudamiento']*100:.1f}%) muestra qué porcentaje de los activos se financia con deuda.")
        if razones.get("roe") is not None:
            analisis_diag.append(f"El ROE ({razones['roe']*100:.1f}%) refleja la rentabilidad generada para los accionistas.")
        if analisis_diag:
            story.append(Paragraph("<b>Análisis del gráfico:</b> " + " ".join(analisis_diag), analisis_style))

    if integ and integ.get("score") is not None:
        ctx_visual = {"score": integ.get("score"), "riesgos": (pack or {}).get("riesgos"), "nombre": nombre_empresa}
        fig_resumen = grafico_resumen_asistente(ctx_visual)
        img_resumen = _fig_a_imagen_pdf(fig_resumen, ancho_cm=9)
        if img_resumen:
            story.append(Spacer(1, 0.15*cm))
            story.append(img_resumen)
            story.append(Paragraph("Score integrado y semáforo de los 6 riesgos", caption_style))
            story.append(Paragraph(
                f"<b>Análisis del panel visual:</b> El score de {integ.get('score',0):.0f}/100 resume la salud financiera global. "
                f"Las barras del semáforo muestran el nivel de cada uno de los 6 riesgos empresariales (bajo = verde, medio = amarillo, alto = rojo).",
                analisis_style))

    # 2. Riesgos
    story.append(Paragraph("2. Análisis de Riesgos", h2_style))
    if pack and pack.get("riesgos"):
        data = [["Riesgo", "Nivel", "Detalle"]]
        for k, lab in {"mercado": "Mercado", "credito": "Crédito", "liquidez": "Liquidez",
                       "operacional": "Operacional", "legal": "Legal", "reputacional": "Reputacional"}.items():
            niv, det = pack["riesgos"].get(k, ("N/D", ""))
            data.append([lab, niv.upper(), _esc(det)])
        t = Table(data, colWidths=[3.5*cm, 2.5*cm, 9.5*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2563EB")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#F8FAFC")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.15*cm))

    img_riesgo = _fig_a_imagen_pdf((pack or {}).get("fig_riesgo"), ancho_cm=15.5)
    if img_riesgo:
        story.append(img_riesgo)
        story.append(Paragraph(f"Distribución de rendimientos diarios — {nombre_seguro}", caption_style))
        m = (pack or {}).get("metricas") or {}
        if m:
            story.append(Paragraph(
                f"<b>Análisis del histograma de rendimientos:</b> Muestra cómo se distribuyen las variaciones diarias del precio. "
                f"Volatilidad anualizada ≈ {m.get('volatilidad_anual',0)*100:.1f}%. "
                f"Máximo drawdown histórico: {m.get('max_drawdown',0)*100:.1f}%. "
                f"VaR 1 día (95%): {m.get('var_1d_95',0)*100:.2f}%. Una distribución más ancha indica mayor riesgo de mercado.",
                analisis_style))

    story.append(PageBreak())

    # 3. Simulación
    story.append(Paragraph("3. Simulación Monte Carlo y Asesoramiento", h2_style))
    if sim and sim.get("detalle"):
        for line in _limpiar_para_pdf(sim["detalle"]).split("\n"):
            if line.strip():
                story.append(Paragraph(line.strip(), normal))
    if pred:
        story.append(Paragraph(
            f"Predicción 30 días: ${pred['proyeccion_30d']:,.2f} ({pred['cambio_esperado_pct']:+.1f}%) — Tendencia {pred['tendencia']}",
            normal))

    img_mc = _fig_a_imagen_pdf((sim or {}).get("fig_mc"), ancho_cm=15.5)
    if img_mc:
        story.append(Spacer(1, 0.15*cm))
        story.append(img_mc)
        story.append(Paragraph("Distribución de escenarios — Simulación Monte Carlo", caption_style))
        if sim:
            p_bad = sim.get("probabilidad_desfavorable", 0) * 100
            ret_e = sim.get("retorno_esperado", 0) * 100
            story.append(Paragraph(
                f"<b>Análisis de la simulación Monte Carlo:</b> Se generaron {sim.get('n_escenarios',0):,} escenarios posibles. "
                f"Aproximadamente {p_bad:.0f}% terminaron en pérdida y el retorno esperado promedio fue {ret_e:+.1f}%. "
                f"La línea roja vertical marca el punto de equilibrio (0%). La decisión automática fue: <b>{sim.get('decision','N/D').upper()}</b>.",
                analisis_style))

    # 4. Interpretación
    story.append(Paragraph("4. Interpretación integral de resultados", h2_style))
    narrativa = _limpiar_para_pdf(interpretacion_narrativa(nombre_empresa, diag, pack, sim, integ))
    for parrafo in narrativa.split(". "):
        parrafo = parrafo.strip()
        if parrafo:
            texto = parrafo if parrafo.endswith(".") else parrafo + "."
            story.append(Paragraph(texto, normal))

    if integ:
        clasif = integ.get("clasificacion", "")
        consejo = {
            "saludable": f"{nombre_seguro} se ve en buen estado en general. Lo recomendable es seguir vigilando periódicamente su liquidez y su rentabilidad para mantener esta situación favorable.",
            "precaucion": f"{nombre_seguro} muestra señales mixtas. Se recomienda revisar de cerca el nivel de deuda y la volatilidad del precio antes de tomar decisiones importantes.",
            "alerta": f"{nombre_seguro} presenta puntos débiles que conviene resolver pronto, principalmente en capacidad de pago a corto plazo y nivel de deuda. Se sugiere actuar con cautela."
        }.get(clasif, "Se recomienda revisar los indicadores principales antes de tomar decisiones.")
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph("Asesoramiento final", h2_style))
        story.append(Paragraph(consejo, normal))

    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0")))
    story.append(Paragraph(f"{UNIVERSIDAD_PROYECTO} · Robot Financiero Inteligente · Datos Yahoo Finance · Uso educativo", small))
    doc.build(story)
    buffer.seek(0)
    return buffer

def crear_reporte_pdf(nombre, diag, pack, sim, ctx):
    if not REPORTLAB_OK:
        return None, "⚠️ No se pudo generar el PDF: la librería `reportlab` no está disponible en este entorno."
    if not diag and not pack:
        return None, "⚠️ Aún no hay datos suficientes. Ejecuta primero **Diagnóstico** y **Riesgos**."
    try:
        integ = (ctx or {}).get("integ") or {}
        pred = (pack or {}).get("prediccion")
        buffer = generar_pdf(nombre or "Empresa", diag or {}, pack or {}, sim or {}, integ, pred)
        nombre_archivo = f"Informe_{_nombre_archivo_seguro(nombre)}_{date.today().strftime('%Y%m%d')}.pdf"
        path = os.path.join(tempfile.gettempdir(), nombre_archivo)
        with open(path, "wb") as f:
            f.write(buffer.getvalue())
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return None, "⚠️ El PDF se generó vacío. Intenta nuevamente."
        return path, f"✅ Informe **{nombre_archivo}** generado con logo, nombres completos, gráficas e interpretación completa. Descárgalo abajo."
    except Exception as e:
        print("Error PDF:", e)
        return None, f"⚠️ Error al generar el PDF: {e}"

# ============================================================
# MERCADO Y PIPELINES
# ============================================================

def interpretar_tabla_cotizacion(tickers, ret, vol, dd, etiqueta):
    if not tickers:
        return ""
    mejor = max(tickers, key=lambda t: ret.get(t, -999))
    peor = min(tickers, key=lambda t: ret.get(t, 999))
    ganadoras = [t for t in tickers if ret.get(t, 0) >= 0]
    perdedoras = [t for t in tickers if ret.get(t, 0) < 0]
    vol_media = np.mean([vol.get(t, 0) for t in tickers]) * 100

    color_fondo = "#ECFDF5" if len(ganadoras) >= len(perdedoras) else "#FEF3C7" if len(ganadoras) > 0 else "#FEE2E2"
    color_borde = "#059669" if len(ganadoras) >= len(perdedoras) else "#D97706" if len(ganadoras) > 0 else "#DC2626"

    html = f'''
    <div style="background:{color_fondo};border:2px solid {color_borde};border-radius:14px;padding:14px 16px;
                box-shadow:0 2px 8px rgba(15,23,42,0.08);height:100%;">
      <div style="font-size:14px;font-weight:700;color:#1E40AF;margin-bottom:8px;">
        🧠 Interpretación del resumen de cotización
      </div>
      <div style="font-size:12.5px;color:#334155;line-height:1.55;">
        <p style="margin:0 0 6px 0;">En el periodo <b>{etiqueta}</b> se compararon <b>{len(tickers)}</b> empresas.</p>
        <p style="margin:0 0 6px 0;">• <b>Mejor desempeño:</b> {nombre_de(mejor)} ({ret.get(mejor,0):+.2f}%)</p>
        <p style="margin:0 0 6px 0;">• <b>Peor desempeño:</b> {nombre_de(peor)} ({ret.get(peor,0):+.2f}%)</p>
        <p style="margin:0 0 6px 0;">• {len(ganadoras)} cerraron en positivo y {len(perdedoras)} en negativo.</p>
        <p style="margin:0 0 6px 0;">• Volatilidad media del grupo: <b>{vol_media:.1f}%</b> anualizada.</p>
        <p style="margin:0;font-size:11px;color:#64748B;">
          ℹ️ Esta lectura se basa en datos históricos. No es una recomendación de inversión.
        </p>
      </div>
    </div>
    '''
    return html

def pipeline_mercado(opciones, periodo, anio=None):
    try:
        precios = descargar_precios(opciones, periodo, anio)
        etiqueta = _etiqueta_periodo(periodo, anio)
        tickers = list(precios.columns)
        base = precios.apply(lambda s: s.dropna().iloc[0])
        p100 = (precios / base) * 100
        rets = precios.pct_change().dropna(how="all")
        vol = rets.std() * np.sqrt(252)
        ret = (precios.iloc[-1] / base - 1) * 100
        dd = (precios / precios.cummax() - 1).min() * 100

        fig1, ax1 = plt.subplots(figsize=(9, 4.2))
        colores = [COLORS["primary"], COLORS["green"], COLORS["yellow"], COLORS["red"], "#7C3AED"]
        for i, c in enumerate(tickers):
            ax1.plot(p100.index, p100[c], lw=2.2, color=colores[i%5], label=nombre_de(c))
        ax1.axhline(100, color=COLORS["muted"], ls="--", lw=1)
        ax1.set_title(f"Performance Base 100 — {etiqueta}", fontweight="bold")
        ax1.legend(frameon=True, fancybox=True, fontsize=9)
        ax1.grid(True, alpha=0.4)
        plt.tight_layout()

        fig2, ax2 = plt.subplots(figsize=(9, 3.3))
        for i, c in enumerate(tickers):
            ax2.plot(rets.index, rets[c]*100, lw=0.9, alpha=0.85, color=colores[i%5], label=nombre_de(c))
        ax2.axhline(0, color=COLORS["muted"], ls="--")
        ax2.set_title("Variación diaria (%)", fontweight="bold")
        ax2.legend(frameon=True, fancybox=True, fontsize=8)
        ax2.grid(True, alpha=0.4)
        plt.tight_layout()

        md = "### Resumen tipo cotización\n\n| Símbolo | Empresa | Retorno | Volatilidad | Drawdown |\n| :---: | :--- | :---: | :---: | :---: |\n"
        for c in tickers:
            flecha = "▲" if ret[c] >= 0 else "▼"
            color = COLORS["green"] if ret[c] >= 0 else COLORS["red"]
            md += f"| **{c}** | {nombre_de(c)} | <span style='color:{color}'>{flecha} {ret[c]:+.2f}%</span> | {vol[c]*100:.2f}% | {dd[c]:.2f}% |\n"
        md += f"\n> Periodo analizado: **{etiqueta}**"

        interp_html = interpretar_tabla_cotizacion(tickers, ret, vol, dd, etiqueta)
        return fig1, fig2, md, interp_html, precios, tickers
    except Exception as e:
        fig, ax = plt.subplots(figsize=(6, 2))
        ax.text(0.5, 0.5, f"Error: {e}", ha="center", va="center", color=COLORS["red"])
        ax.axis("off")
        return fig, fig, f"### Error\n{e}", "", None, []

def simular_inv(precios, tickers, monto, p1, p2, p3, p4, p5, periodo, anio=None):
    if precios is None or not tickers:
        fig, ax = plt.subplots(figsize=(6, 2.2))
        ax.text(0.5, 0.5, "Primero ejecuta el análisis de mercado.", ha="center", va="center", color=COLORS["muted"])
        ax.axis("off")
        return "Primero ejecuta el análisis de mercado.", fig
    try:
        etiqueta = _etiqueta_periodo(periodo, anio)
        pesos = np.array([float(x or 0) for x in (p1, p2, p3, p4, p5)[:len(tickers)]])
        if pesos.sum() <= 0:
            raise ValueError("Asigna porcentajes > 0")
        pesos = pesos / pesos.sum()
        monto = float(monto)
        filas, total = [], 0.0
        for t, w in zip(tickers, pesos):
            s = precios[t].dropna()
            inv = monto * w
            vf = inv * (s.iloc[-1] / s.iloc[0])
            total += vf
            filas.append((nombre_de(t), w*100, inv, vf, (vf/inv - 1)*100))
        md = f"### 💰 Resultado simulación de inversión — {etiqueta}\n\n"
        md += "| Empresa | % | Invertido | Final | Resultado |\n| :--- | :---: | :---: | :---: |\n"
        for n_, w, inv, vf, g in filas:
            c = COLORS["green"] if g >= 0 else COLORS["red"]
            md += f"| {n_} | {w:.0f}% | ${inv:,.2f} | ${vf:,.2f} | <span style='color:{c}'>{g:+.2f}%</span> |\n"
        gt = (total/monto - 1)*100
        c = COLORS["green"] if gt >= 0 else COLORS["red"]
        md += f"\n**Total:** ${monto:,.2f} → **${total:,.2f}**  |  Resultado global: <span style='color:{c}'>**{gt:+.2f}%**</span>\n\n"
        md += interpretar_simulacion_inversion(filas, gt, monto, total, etiqueta)
        nombres = [f[0] for f in filas]
        resultados = [f[4] for f in filas]
        colores_barras = [COLORS["green"] if r >= 0 else COLORS["red"] for r in resultados]
        fig, ax = plt.subplots(figsize=(7.5, 3.4))
        barras = ax.bar(nombres, resultados, color=colores_barras, alpha=0.9, edgecolor="white")
        ax.axhline(0, color=COLORS["muted"], lw=1)
        ax.set_title(f"Resultado por empresa — {etiqueta}", fontweight="bold")
        ax.set_ylabel("% de resultado")
        ax.grid(True, alpha=0.3, axis="y")
        for b, r in zip(barras, resultados):
            ax.annotate(f"{r:+.1f}%", (b.get_x() + b.get_width()/2, b.get_height()),
                        ha="center", va="bottom" if r >= 0 else "top", fontsize=9, fontweight="bold")
        plt.xticks(rotation=15, ha="right")
        plt.tight_layout()
        return md, fig
    except Exception as e:
        fig, ax = plt.subplots(figsize=(6, 2.2))
        ax.text(0.5, 0.5, f"Error: {e}", ha="center", va="center", color=COLORS["red"])
        ax.axis("off")
        return f"Error: {e}", fig

def cargar_estados(opcion):
    d = estados_yahoo(ticker_de(opcion))
    return (d["activo_corriente"], d["pasivo_corriente"], d["inventarios"], d["utilidad_neta"],
            d["ventas"], d["activos_totales"], d["patrimonio"], d["pasivo_total"],
            d["utilidades_retenidas"], d["utilidad_operativa"], d["valor_mercado_patrimonio"],
            d["mensaje"], d["sector"], d["nombre"])

def run_diag(ac, pc, inv, un, ven, at, pat, pt, ur, uo, vm, nombre):
    try:
        r = calcular_diagnostico(ac, pc, inv, un, ven, at, pat, pt, ur, uo, vm, nombre or "Empresa")
        return r["texto_md"], r
    except Exception as e:
        return f"<div style='color:#DC2626;'>⚠️ Error: {e}</div>", {}

def run_riesgo_completo(precios, tickers, diag, sector, nombre_empresa):
    try:
        if precios is None or not tickers:
            return "<div style='color:#64748B;'>Ejecuta primero Mercado con la misma empresa.</div>", {}, None, ""
        ticker_analisis = tickers[0]
        m = metricas_mercado(precios[ticker_analisis], nombre_empresa or ticker_analisis)
        riesgos = seis_riesgos(m, (diag or {}).get("razones"), sector or "N/D")
        pred = prediccion_simple(m["serie"])
        md = texto_riesgos(m, riesgos, pred, nombre_empresa or ticker_analisis)
        fig1, ax1 = plt.subplots(figsize=(7.5, 3.2))
        ax1.hist(m["retornos"]*100, bins=40, color=COLORS["primary"], alpha=0.85, edgecolor="white")
        ax1.set_title(f"Rendimientos diarios (%) — {nombre_empresa}", fontweight="bold")
        ax1.grid(True, alpha=0.3)
        plt.tight_layout()
        em = {"bajo": ("🟢", COLORS["green_light"], COLORS["green"]),
              "medio": ("🟡", COLORS["yellow_light"], COLORS["yellow"]),
              "alto": ("🔴", COLORS["red_light"], COLORS["red"])}
        cards = ""
        for k, lab in {"mercado": "Mercado", "credito": "Crédito", "liquidez": "Liquidez",
                       "operacional": "Operacional", "legal": "Legal", "reputacional": "Reputacional"}.items():
            niv, det = riesgos[k]
            icon, bg, border = em.get(niv, ("⚪", "#F1F5F9", "#94A3B8"))
            cards += f'<div style="background:{bg};border-left:5px solid {border};padding:12px 14px;border-radius:10px;margin-bottom:8px;"><div style="font-weight:700;font-size:14px;">{icon} {lab} — {niv.upper()}</div><div style="font-size:12px;color:#475569;margin-top:3px;">{det}</div></div>'
        tablero = f'<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:16px;"><div style="font-size:16px;font-weight:700;margin-bottom:12px;">🚦 Tablero de Alertas — {nombre_empresa}</div>{cards}</div>'
        return md, {"metricas": m, "riesgos": riesgos, "prediccion": pred, "fig_riesgo": fig1}, fig1, tablero
    except Exception as e:
        fig, ax = plt.subplots(figsize=(5, 2)); ax.axis("off")
        return f"<div style='color:#DC2626;'>⚠️ Error: {e}</div>", {}, fig, ""

def run_sim(pack, n, umbral):
    try:
        m = (pack or {}).get("metricas") or {}
        if not m:
            return "Calcula primero Riesgos.", {}, None, ""
        nombre_emp = m.get("nombre") or "la empresa"
        sim = simulacion_decision(m["mu_diario"], m["sigma_diario"], int(n or 2000), float(umbral or 0.3))
        fig, ax = plt.subplots(figsize=(7.5, 3.2))
        ax.hist(sim["distribucion"]*100, bins=40, color=COLORS["green"], alpha=0.85, edgecolor="white")
        ax.axvline(0, color=COLORS["red"], ls="--", lw=1.5)
        ax.set_title(f"Monte Carlo → {sim['decision'].upper()}", fontweight="bold")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        sim["fig_mc"] = fig
        interpretacion = interpretar_grafico_montecarlo(sim, nombre_emp)
        return sim["detalle"], sim, fig, interpretacion
    except Exception as e:
        fig, ax = plt.subplots(figsize=(5, 2)); ax.axis("off")
        return f"Error: {e}", {}, fig, ""

def run_integ(diag, pack, sim):
    try:
        if not diag or not pack:
            return "Completa Diagnóstico y Riesgos primero.", {}, {}
        integ = analisis_integrado(diag, pack)
        nombre = integ.get("nombre") or "Empresa"
        narrativa = interpretacion_narrativa(nombre, diag, pack, sim, integ)
        texto = integ["texto_md"] + f"\n\n#### 🧠 Interpretación\n{narrativa}"
        ctx = {
            "z_info": diag.get("z_info"),
            "clasificacion": integ.get("clasificacion"),
            "decision": (sim or {}).get("decision"),
            "score": integ.get("score"),
            "nombre": nombre,
            "integ": integ,
            "razones": (diag or {}).get("razones"),
            "riesgos": (pack or {}).get("riesgos"),
            "metricas": (pack or {}).get("metricas"),
            "sim": sim or {},
        }
        return texto, integ, ctx
    except Exception as e:
        return f"Error: {e}", {}, {}

def actualizar_ctx_mercado(ctx, precios, tickers, periodo, anio):
    ctx = dict(ctx or {})
    if precios is None or not tickers:
        return ctx
    etiqueta = _etiqueta_periodo(periodo, anio)
    resumen = []
    for t in tickers:
        try:
            s = precios[t].dropna()
            r = (s.iloc[-1] / s.iloc[0] - 1) * 100
            resumen.append(f"{nombre_de(t)} ({t}): {r:+.1f}%")
        except Exception:
            resumen.append(f"{nombre_de(t)} ({t})")
    ctx["mercado_comparado"] = {"periodo": etiqueta, "empresas": resumen}
    return ctx

def actualizar_ctx_calculadora(ctx, tipo, texto_resultado):
    ctx = dict(ctx or {})
    if tipo and texto_resultado:
        resumen = _re.sub(r"<[^>]+>", "", str(texto_resultado)).replace("**", "").strip()
        ctx["ultimo_calculo"] = f"{tipo}: {resumen[:200]}"
    return ctx

def interpretar_simulacion_inversion(filas, gt, monto, total, etiqueta):
    if not filas:
        return ""
    mejor = max(filas, key=lambda f: f[4])
    peor = min(filas, key=lambda f: f[4])
    ganancia_neta = total - monto
    veredicto = "positivo" if gt >= 0 else "negativo"
    return (
        f"**¿Qué significa este resultado?** Si hubieras invertido **${monto:,.2f}** en el periodo **{etiqueta}** "
        f"repartidos según los porcentajes elegidos, hoy tendrías aproximadamente **${total:,.2f}**, "
        f"es decir, un resultado {veredicto} de **{gt:+.2f}%** (${ganancia_neta:,.2f}).\n\n"
        f"La empresa que más aportó al resultado fue **{mejor[0]}** ({mejor[4]:+.2f}%), "
        f"mientras que la que menos aportó fue **{peor[0]}** ({peor[4]:+.2f}%).\n\n"
        f"ℹ️ Esta es una simulación histórica basada en precios pasados. Los resultados pasados no garantizan resultados futuros."
    )

# ============================================================
# CONSTANTES DE INTERFAZ (CSS, AÑOS, DEFINICIONES, CHAT)
# ============================================================

CSS = """
.gradio-container { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; }
.gr-button-primary { font-weight: 600; }
"""

OPCIONES_ANIO = ["Automático (usar periodo)"] + [str(y) for y in range(date.today().year, 1999, -1)]

DEFINICIONES_CALC = {
    "Interés Simple": "**Interés Simple**: I = C × r × t. El interés se calcula siempre sobre el capital inicial, sin capitalizarse en el tiempo.",
    "Interés Compuesto": "**Interés Compuesto**: M = C × (1+r)ⁿ. Los intereses generados en cada periodo se reinvierten y también generan intereses.",
    "Valor Futuro": "**Valor Futuro (VF)**: VF = VP × (1+r)ⁿ. Indica cuánto valdrá hoy un capital dentro de *n* periodos a una tasa *r*.",
    "Valor Presente": "**Valor Presente (VP)**: VP = VF / (1+r)ⁿ. Indica cuánto vale hoy un monto que se recibirá en el futuro.",
    "Anualidad VP": "**Valor Presente de una Anualidad**: trae a valor presente una serie de cuotas iguales y periódicas.",
    "Anualidad VF": "**Valor Futuro de una Anualidad**: lleva a valor futuro una serie de cuotas iguales y periódicas.",
    "Amortización": "**Tabla de Amortización**: distribuye una deuda en cuotas iguales, separando interés y abono a capital en cada periodo.",
    "Conversión de tasas": "**Conversión de tasas**: convierte una tasa nominal o efectiva entre distintas frecuencias de capitalización.",
    "TIR": "**Tasa Interna de Retorno (TIR)**: tasa de descuento que hace que el VAN de un proyecto sea igual a cero.",
    "VAN": "**Valor Actual Neto (VAN)**: suma de los flujos de caja futuros descontados a una tasa, menos la inversión inicial.",
    "CAPM": "**CAPM**: Re = Rf + β×(Rm − Rf). Estima el retorno esperado de un activo según su riesgo sistemático (beta).",
    "WACC": "**WACC**: Costo Promedio Ponderado de Capital; combina el costo del equity y de la deuda según su peso en la estructura de capital.",
    "EVA": "**EVA (Valor Económico Agregado)**: EVA = NOPAT − (WACC × Capital invertido). Mide si la empresa genera valor por encima de su costo de capital.",
}

MENSAJE_BIENVENIDA = (
    "¡Hola! Soy **FinanIA**, tu asistente del Robot Financiero Inteligente. "
    "Puedo ayudarte a interpretar el diagnóstico financiero, los 6 riesgos, la simulación Monte Carlo y tus cálculos. "
    "Prueba preguntas como *'Analiza mi empresa'*, *'¿Puedo invertir?'* o *'Dame un resumen'*."
)

def _quitar_acentos(s):
    return "".join(c for c in _ud.normalize("NFD", s) if _ud.category(c) != "Mn")

def _respuesta_regla(pregunta, ctx, tema_anterior=None):
    ctx = ctx or {}
    q = _quitar_acentos(pregunta.lower())
    nombre = ctx.get("nombre") or "tu empresa"

    if "mas" in q or "cuentame" in q or "explica" in q:
        expansiones = {
            "analisis": lambda: interpretacion_narrativa(
                nombre, {"razones": ctx.get("razones") or {}, "z_info": ctx.get("z_info")},
                {"metricas": ctx.get("metricas"), "riesgos": ctx.get("riesgos")},
                ctx.get("sim"), ctx.get("integ") or {}),
            "invertir": lambda: (ctx.get("sim") or {}).get("detalle") or "Aún no hay una simulación Monte Carlo calculada.",
            "resumen": lambda: _contexto_a_texto(ctx),
            "mercado": lambda: "Puedes ver el detalle completo en la pestaña 'Mercado & Inversión', con el gráfico de desempeño y la volatilidad de cada empresa.",
        }
        if tema_anterior and tema_anterior in expansiones:
            return expansiones[tema_anterior](), tema_anterior
        return "Cuéntame primero qué te gustaría analizar: el diagnóstico, los riesgos, si conviene invertir, o un resumen general.", None

    if "resumen" in q or "resume" in q:
        return _contexto_a_texto(ctx), "resumen"

    if "invertir" in q or "inversion" in q:
        decision = ctx.get("decision")
        sim = ctx.get("sim") or {}
        if decision:
            mapa = {
                "aceptar": f"Según la simulación Monte Carlo, la balanza se inclina hacia escenarios de ganancia para **{nombre}**, con una probabilidad de pérdida de {sim.get('probabilidad_desfavorable',0)*100:.0f}%. Aun así, esto es un análisis estadístico, no asesoría financiera personalizada.",
                "revisar": f"Los resultados para **{nombre}** están repartidos casi por igual entre ganar y perder ({sim.get('probabilidad_desfavorable',0)*100:.0f}% de probabilidad de pérdida). Te recomendaría evaluar tu tolerancia al riesgo antes de decidir.",
                "rechazar": f"La simulación indica que una parte importante de los escenarios para **{nombre}** terminan en pérdida ({sim.get('probabilidad_desfavorable',0)*100:.0f}%), por lo que convendría ser cauteloso.",
            }
            return mapa.get(decision, "Aún no tengo suficiente información."), "invertir"
        return "Para responder eso necesito que primero completes Diagnóstico, Riesgos y la Simulación Monte Carlo en la pestaña correspondiente.", "invertir"

    if "analiz" in q or "diagnostic" in q:
        razones = ctx.get("razones") or {}
        if razones:
            return interpretacion_narrativa(
                nombre, {"razones": razones, "z_info": ctx.get("z_info")},
                {"metricas": ctx.get("metricas"), "riesgos": ctx.get("riesgos")},
                ctx.get("sim"), ctx.get("integ") or {}), "analisis"
        return "Todavía no has calculado el Diagnóstico de ninguna empresa. Ve a 'Diagnóstico & Riesgos', carga una empresa y presiona 'Calcular Diagnóstico'.", "analisis"

    if "compar" in q or ("mercado" in q and "empresa" in q):
        mc = ctx.get("mercado_comparado")
        if mc:
            return f"En el periodo **{mc['periodo']}** comparaste: " + "; ".join(mc["empresas"]) + ".", "mercado"
        return "Aún no has comparado empresas. Ve a la pestaña 'Mercado & Inversión'.", "mercado"

    if "calcul" in q or "ultimo" in q:
        uc = ctx.get("ultimo_calculo")
        if uc:
            return f"Tu último cálculo en la calculadora fue: {uc}", "calculo"
        return "Aún no has usado la calculadora financiera.", "calculo"

    return (
        "Puedo ayudarte a interpretar el Diagnóstico Financiero, los 6 Riesgos, la Simulación Monte Carlo y tus cálculos. "
        "Prueba preguntas como: *'Analiza mi empresa'*, *'¿Puedo invertir?'*, *'Dame un resumen'* o *'Cuéntame más'*."
    ), None

def _generar_respuesta(pregunta, ctx, tema_anterior=None):
    llm = responder_con_llm(pregunta, ctx)
    if llm:
        return llm, tema_anterior
    return _respuesta_regla(pregunta, ctx, tema_anterior)

def chat_ui(historial, mensaje, ctx, tema):
    historial = list(historial or [])
    mensaje = (mensaje or "").strip()
    if not mensaje:
        return historial, "", tema
    respuesta, nuevo_tema = _generar_respuesta(mensaje, ctx, tema)
    historial.append({"role": "user", "content": mensaje})
    historial.append({"role": "assistant", "content": respuesta})
    return historial, "", nuevo_tema

def iniciar_chat():
    return [{"role": "assistant", "content": MENSAJE_BIENVENIDA}], None

def sugerencia_rapida(pregunta, historial, ctx, tema):
    return chat_ui(historial, pregunta, ctx, tema)

def _fig_barra(etiquetas, valores, titulo):
    fig, ax = plt.subplots(figsize=(6, 3.4))
    colores_barras = [COLORS["primary"] if v >= 0 else COLORS["red"] for v in valores]
    barras = ax.bar([str(e) for e in etiquetas], valores, color=colores_barras, alpha=0.9, edgecolor="white")
    for b, v in zip(barras, valores):
        ax.annotate(f"{v:,.2f}", (b.get_x() + b.get_width() / 2, b.get_height()),
                    ha="center", va="bottom" if v >= 0 else "top", fontsize=8, fontweight="bold")
    ax.set_title(titulo, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    plt.xticks(rotation=10, ha="right")
    plt.tight_layout()
    return fig

def _calc_tab(tipo, a, b, c, d, e, ctx):
    try:
        if tipo == "Interés Simple":
            capital, tasa, tiempo = a, b, c
            interes, monto_final = interes_simple(capital, tasa, tiempo)
            md = f"### 💰 Interés Simple\n\n- Interés generado: **{fmt(interes)}**\n- Monto final: **{fmt(monto_final)}**"
            fig = _fig_barra(["Capital", "Interés", "Monto Final"], [capital, interes, monto_final], "Interés Simple")

        elif tipo == "Interés Compuesto":
            capital, tasa, periodos = a, b, _pos(c, "Periodos")
            interes, monto_final = interes_compuesto(capital, tasa, periodos)
            md = f"### 📈 Interés Compuesto\n\n- Interés generado: **{fmt(interes)}**\n- Monto final: **{fmt(monto_final)}**"
            n_int = max(1, int(periodos))
            xs = list(range(0, n_int + 1))
            ys = [capital * (1 + tasa) ** x for x in xs]
            fig, ax = plt.subplots(figsize=(6, 3.4))
            ax.plot(xs, ys, marker="o", color=COLORS["primary"], lw=2)
            ax.set_title("Crecimiento del capital", fontweight="bold")
            ax.set_xlabel("Periodo"); ax.set_ylabel("Monto")
            ax.grid(True, alpha=0.3)
            plt.tight_layout()

        elif tipo == "Valor Futuro":
            vp, tasa, periodos = a, b, c
            vf = valor_futuro(vp, tasa, periodos)
            md = f"### ⏩ Valor Futuro\n\n- VF = **{fmt(vf)}**"
            fig = _fig_barra(["VP", "VF"], [vp, vf], "Valor Presente vs Futuro")

        elif tipo == "Valor Presente":
            vf_, tasa, periodos = a, b, c
            vp = valor_presente(vf_, tasa, periodos)
            md = f"### ⏪ Valor Presente\n\n- VP = **{fmt(vp)}**"
            fig = _fig_barra(["VP", "VF"], [vp, vf_], "Valor Presente vs Futuro")

        elif tipo == "Anualidad VP":
            cuota, tasa, periodos, tipo_an = a, b, c, (d or "ordinaria")
            vp = vp_anualidad(cuota, tasa, periodos, tipo_an)
            md = f"### 📅 Anualidad — Valor Presente\n\n- VP = **{fmt(vp)}**\n- Tipo: {tipo_an}"
            fig = _fig_barra(["Cuota", "VP total"], [cuota, vp], "Anualidad VP")

        elif tipo == "Anualidad VF":
            cuota, tasa, periodos, tipo_an = a, b, c, (d or "ordinaria")
            vf = vf_anualidad(cuota, tasa, periodos, tipo_an)
            md = f"### 📅 Anualidad — Valor Futuro\n\n- VF = **{fmt(vf)}**\n- Tipo: {tipo_an}"
            fig = _fig_barra(["Cuota", "VF total"], [cuota, vf], "Anualidad VF")

        elif tipo == "Amortización":
            capital, tasa, periodos = a, b, c
            df, cuota = tabla_amortizacion(capital, tasa, periodos)
            total_interes = df["Interés"].sum()
            md = (f"### 🏦 Tabla de Amortización\n\n- Cuota fija: **{fmt(cuota)}**\n"
                  f"- Total de interés pagado: **{fmt(total_interes)}**\n"
                  f"- Total pagado: **{fmt(cuota * len(df))}**")
            fig, ax = plt.subplots(figsize=(6, 3.4))
            ax.plot(df["Periodo"], df["Saldo"], color=COLORS["primary"], lw=2, label="Saldo")
            ax.bar(df["Periodo"], df["Interés"], color=COLORS["red"], alpha=0.5, label="Interés")
            ax.bar(df["Periodo"], df["Amortización"], bottom=df["Interés"], color=COLORS["green"], alpha=0.5, label="Amortización")
            ax.set_title("Amortización del préstamo", fontweight="bold")
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)
            plt.tight_layout()

        elif tipo == "Conversión de tasas":
            tasa, freq_or, freq_des, tipo_tasa = a, b, c, (d or "nominal")
            ef, nom, efd = conversion_tasas(tasa, freq_or, freq_des, tipo_tasa)
            md = (f"### 🔄 Conversión de tasas\n\n- Tasa efectiva anual: **{ef*100:.4f}%**\n"
                  f"- Tasa nominal en la nueva frecuencia: **{nom*100:.4f}%**\n"
                  f"- Tasa efectiva verificada: **{efd*100:.4f}%**")
            fig = _fig_barra(["Ingresada", "Efectiva Anual", "Nominal Destino"], [tasa*100, ef*100, nom*100], "Comparación de tasas (%)")

        elif tipo == "TIR":
            flujos = [float(x.strip()) for x in str(d).split(",") if x.strip() != ""]
            tir = calcular_tir(flujos)
            md = f"### 📐 TIR\n\n- TIR calculada: **{tir*100:.2f}%**"
            fig = _fig_barra([f"F{i}" for i in range(len(flujos))], flujos, "Flujos de caja")

        elif tipo == "VAN":
            tasa = b
            flujos = [float(x.strip()) for x in str(d).split(",") if x.strip() != ""]
            van = calcular_van(flujos, tasa)
            md = f"### 📐 VAN\n\n- VAN a tasa {tasa*100:.2f}%: **{fmt(van)}**"
            fig = _fig_barra([f"F{i}" for i in range(len(flujos))], flujos, "Flujos de caja")

        elif tipo == "CAPM":
            rf, beta, rm = a, b, c
            capm = calcular_capm(rf, beta, rm)
            md = f"### 📉 CAPM\n\n- Retorno esperado: **{capm*100:.2f}%**"
            fig = _fig_barra(["Rf", "Retorno esperado", "Rm"], [rf*100, capm*100, rm*100], "CAPM (%)")

        elif tipo == "WACC":
            ke, kd, e_, d_, tax = a, b, c, d, e
            wacc = calcular_wacc(ke, kd, e_, d_, tax)
            md = f"### 🏗️ WACC\n\n- WACC = **{wacc*100:.2f}%**"
            fig = _fig_barra(["Equity", "Deuda"], [e_, d_], "Estructura de capital")

        elif tipo == "EVA":
            nopat, wacc_v, capital = a, b, c
            eva = calcular_eva(nopat, wacc_v, capital)
            md = f"### 💎 EVA\n\n- EVA = **{fmt(eva)}**"
            fig = _fig_barra(["NOPAT", "Costo de capital", "EVA"], [nopat, wacc_v * capital, eva], "EVA")

        else:
            return "Tipo de cálculo no reconocido.", None, ctx

        ctx = actualizar_ctx_calculadora(ctx, tipo, md)
        return md, fig, ctx
    except Exception as ex:
        fig, ax = plt.subplots(figsize=(5, 2)); ax.axis("off")
        ax.text(0.5, 0.5, f"Error: {ex}", ha="center", va="center", color=COLORS["red"])
        return f"⚠️ Error: {ex}", fig, ctx

# ============================================================
# INTERFAZ GRADIO COMPLETA (UI)
# ============================================================

with gr.Blocks(title="Robot Financiero Inteligente") as demo:

    gr.HTML("""
    <div style="background:linear-gradient(135deg,#1E40AF,#2563EB);padding:20px 24px;border-radius:14px;margin-bottom:18px;">
      <div style="display:flex;align-items:center;gap:16px;">
        <div style="width:48px;height:48px;border-radius:12px;background:white;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:20px;color:#2563EB;">RF</div>
        <div>
          <div style="font-size:24px;font-weight:700;color:white;">Robot Financiero Inteligente</div>
          <div style="font-size:13px;color:#BFDBFE;">Diagnóstico · Riesgos · Predicciones · Simulación · PDF · Asistente Gemini</div>
        </div>
      </div>
    </div>
    """)

    st_precios = gr.State(None)
    st_tickers = gr.State([])
    st_diag = gr.State({})
    st_riesgo = gr.State({})
    st_sim = gr.State({})
    st_sector = gr.State("N/D")
    st_ctx = gr.State({})
    st_nombre = gr.State("Empresa")
    st_integ = gr.State({})
    st_chat_tema = gr.State(None)

    with gr.Tabs():

        with gr.Tab("📈 Mercado & Inversión"):
            gr.Markdown("### Compara hasta 5 empresas y simula una inversión")
            with gr.Row():
                sel_emp = gr.Dropdown(OPCIONES, multiselect=True, value=["Apple Inc. (AAPL)", "Netflix Inc. (NFLX)"], label="Empresas (1–5)", scale=3)
                sel_periodo = gr.Dropdown(["6 meses", "1 año", "2 años", "5 años", "10 años"], value="1 año", label="Periodo relativo", scale=1)
                sel_anio = gr.Dropdown(OPCIONES_ANIO, value="Automático (usar periodo)", label="O un año específico", scale=1)
                btn_mkt = gr.Button("Analizar Mercado", variant="primary", scale=1)
            gr.Markdown("_Si eliges un año específico, ese año manda sobre el periodo relativo._")
            with gr.Row():
                plot_p = gr.Plot()
                plot_r = gr.Plot()
            with gr.Row():
                md_mkt = gr.Markdown(scale=3)
                html_interp_mkt = gr.HTML(scale=2)
            gr.Markdown("#### 💰 Simulador de inversión histórica")
            with gr.Row():
                monto = gr.Number(10000, label="Monto USD")
                s1 = gr.Slider(0, 100, 50, label="% Emp 1")
                s2 = gr.Slider(0, 100, 50, label="% Emp 2")
                s3 = gr.Slider(0, 100, 0, label="% Emp 3")
                s4 = gr.Slider(0, 100, 0, label="% Emp 4")
                s5 = gr.Slider(0, 100, 0, label="% Emp 5")
            btn_inv = gr.Button("Simular inversión", variant="primary")
            with gr.Row():
                md_inv = gr.Markdown(scale=3)
                plot_inv = gr.Plot(scale=2)

        with gr.Tab("📋 Diagnóstico & Riesgos"):
            gr.Markdown("### Analiza **una sola empresa**")
            with gr.Row():
                sel_d = gr.Dropdown(OPCIONES_MANUAL, value="Costco Wholesale (COST)", label="Empresa", scale=3)
                btn_load = gr.Button("Cargar Yahoo Finance", variant="primary", scale=1)
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
                    vm = gr.Number(0, label="Market Cap")
            with gr.Row():
                btn_diag = gr.Button("1. Calcular Diagnóstico", variant="primary")
                btn_risk = gr.Button("2. Riesgos + Predicción + Alertas", variant="primary")
            with gr.Row():
                html_diag = gr.HTML()
                html_tablero = gr.HTML()
            html_risk = gr.HTML()
            plot_h = gr.Plot()
            gr.Markdown("#### 🎲 Simulación Monte Carlo")
            with gr.Row():
                n_esc = gr.Number(2000, label="Escenarios")
                umbral = gr.Slider(0.05, 0.50, 0.30, step=0.05, label="Umbral P(pérdida)")
                btn_sim = gr.Button("Simular decisión", variant="primary")
            md_sim = gr.Markdown()
            plot_mc = gr.Plot()
            md_mc_interpretacion = gr.Markdown(label="¿Qué significa esta gráfica?")
            gr.Markdown("#### 🎯 Análisis Integrado + Interpretación + PDF")
            btn_int = gr.Button("Generar Análisis Integrado", variant="primary")
            md_int = gr.Markdown()
            btn_pdf = gr.Button("📄 Descargar Informe PDF (con gráficas e interpretación)", variant="secondary")
            md_pdf_status = gr.Markdown()
            file_pdf = gr.File(label="Tu informe PDF")

        with gr.Tab("🧮 Calculadora Financiera"):
            gr.Markdown("### Elige el tipo de cálculo en su propia pestaña")
            with gr.Tabs():
                with gr.Tab("💰 Interés Simple"):
                    gr.Markdown(DEFINICIONES_CALC["Interés Simple"])
                    with gr.Row():
                        is_capital = gr.Number(1000000, label="Capital (C)")
                        is_tasa = gr.Number(0.12, label="Tasa por periodo (r)")
                        is_tiempo = gr.Number(2, label="Tiempo (t)")
                    btn_is = gr.Button("Calcular", variant="primary")
                    with gr.Row():
                        md_is = gr.Markdown(scale=2)
                        plot_is = gr.Plot(scale=3)

                with gr.Tab("📈 Interés Compuesto"):
                    gr.Markdown(DEFINICIONES_CALC["Interés Compuesto"])
                    with gr.Row():
                        ic_capital = gr.Number(1000000, label="Capital (C)")
                        ic_tasa = gr.Number(0.12, label="Tasa por periodo (r)")
                        ic_periodos = gr.Number(2, label="Periodos (n)")
                    btn_ic = gr.Button("Calcular", variant="primary")
                    with gr.Row():
                        md_ic = gr.Markdown(scale=2)
                        plot_ic = gr.Plot(scale=3)

                with gr.Tab("⏩ Valor Futuro"):
                    gr.Markdown(DEFINICIONES_CALC["Valor Futuro"])
                    with gr.Row():
                        vf_vp = gr.Number(1000000, label="Valor Presente (VP)")
                        vf_tasa = gr.Number(0.12, label="Tasa (r)")
                        vf_periodos = gr.Number(2, label="Periodos (n)")
                    btn_vf = gr.Button("Calcular", variant="primary")
                    with gr.Row():
                        md_vf = gr.Markdown(scale=2)
                        plot_vf = gr.Plot(scale=3)

                with gr.Tab("⏪ Valor Presente"):
                    gr.Markdown(DEFINICIONES_CALC["Valor Presente"])
                    with gr.Row():
                        vp_vf = gr.Number(1000000, label="Valor Futuro (VF)")
                        vp_tasa = gr.Number(0.12, label="Tasa (r)")
                        vp_periodos = gr.Number(2, label="Periodos (n)")
                    btn_vp = gr.Button("Calcular", variant="primary")
                    with gr.Row():
                        md_vp = gr.Markdown(scale=2)
                        plot_vp = gr.Plot(scale=3)

                with gr.Tab("📅 Anualidad VP"):
                    gr.Markdown(DEFINICIONES_CALC["Anualidad VP"])
                    with gr.Row():
                        avp_cuota = gr.Number(50000, label="Cuota")
                        avp_tasa = gr.Number(0.02, label="Tasa por periodo (r)")
                        avp_periodos = gr.Number(12, label="Periodos (n)")
                        avp_tipo = gr.Radio(["ordinaria", "anticipada"], value="ordinaria", label="Tipo")
                    btn_avp = gr.Button("Calcular", variant="primary")
                    with gr.Row():
                        md_avp = gr.Markdown(scale=2)
                        plot_avp = gr.Plot(scale=3)

                with gr.Tab("📅 Anualidad VF"):
                    gr.Markdown(DEFINICIONES_CALC["Anualidad VF"])
                    with gr.Row():
                        avf_cuota = gr.Number(50000, label="Cuota")
                        avf_tasa = gr.Number(0.02, label="Tasa por periodo (r)")
                        avf_periodos = gr.Number(12, label="Periodos (n)")
                        avf_tipo = gr.Radio(["ordinaria", "anticipada"], value="ordinaria", label="Tipo")
                    btn_avf = gr.Button("Calcular", variant="primary")
                    with gr.Row():
                        md_avf = gr.Markdown(scale=2)
                        plot_avf = gr.Plot(scale=3)

                with gr.Tab("🏦 Amortización"):
                    gr.Markdown(DEFINICIONES_CALC["Amortización"])
                    with gr.Row():
                        am_capital = gr.Number(10000000, label="Capital del préstamo")
                        am_tasa = gr.Number(0.02, label="Tasa por periodo (r)")
                        am_periodos = gr.Number(12, label="Número de cuotas (n)")
                    btn_am = gr.Button("Calcular", variant="primary")
                    with gr.Row():
                        md_am = gr.Markdown(scale=2)
                        plot_am = gr.Plot(scale=3)

                with gr.Tab("🔄 Conversión de tasas"):
                    gr.Markdown(DEFINICIONES_CALC["Conversión de tasas"])
                    with gr.Row():
                        ct_tasa = gr.Number(0.24, label="Tasa a convertir")
                        ct_freq_or = gr.Number(12, label="Frecuencia origen")
                        ct_freq_des = gr.Number(4, label="Frecuencia destino")
                        ct_tipo = gr.Radio(["nominal", "efectiva"], value="nominal", label="La tasa que ingresé es")
                    btn_ct = gr.Button("Calcular", variant="primary")
                    with gr.Row():
                        md_ct = gr.Markdown(scale=2)
                        plot_ct = gr.Plot(scale=3)

                with gr.Tab("📐 TIR"):
                    gr.Markdown(DEFINICIONES_CALC["TIR"])
                    tir_flujos = gr.Textbox("-1000000,300000,400000,500000", label="Flujos de caja separados por comas")
                    btn_tir = gr.Button("Calcular", variant="primary")
                    with gr.Row():
                        md_tir = gr.Markdown(scale=2)
                        plot_tir = gr.Plot(scale=3)

                with gr.Tab("📐 VAN"):
                    gr.Markdown(DEFINICIONES_CALC["VAN"])
                    with gr.Row():
                        van_tasa = gr.Number(0.10, label="Tasa de descuento")
                        van_flujos = gr.Textbox("-1000000,300000,400000,500000", label="Flujos de caja")
                    btn_van = gr.Button("Calcular", variant="primary")
                    with gr.Row():
                        md_van = gr.Markdown(scale=2)
                        plot_van = gr.Plot(scale=3)

                with gr.Tab("📉 CAPM"):
                    gr.Markdown(DEFINICIONES_CALC["CAPM"])
                    with gr.Row():
                        capm_rf = gr.Number(0.05, label="Rf — tasa libre de riesgo")
                        capm_beta = gr.Number(1.2, label="Beta (β)")
                        capm_rm = gr.Number(0.11, label="Rm — retorno del mercado")
                    btn_capm = gr.Button("Calcular", variant="primary")
                    with gr.Row():
                        md_capm = gr.Markdown(scale=2)
                        plot_capm = gr.Plot(scale=3)

                with gr.Tab("🏗️ WACC"):
                    gr.Markdown(DEFINICIONES_CALC["WACC"])
                    with gr.Row():
                        wacc_ke = gr.Number(0.14, label="Ke — costo del equity")
                        wacc_kd = gr.Number(0.09, label="Kd — costo de la deuda")
                        wacc_e = gr.Number(700000, label="E — valor del equity")
                        wacc_d = gr.Number(300000, label="D — valor de la deuda")
                        wacc_tax = gr.Number(0.25, label="Tasa de impuesto")
                    btn_wacc = gr.Button("Calcular", variant="primary")
                    with gr.Row():
                        md_wacc = gr.Markdown(scale=2)
                        plot_wacc = gr.Plot(scale=3)

                with gr.Tab("💎 EVA"):
                    gr.Markdown(DEFINICIONES_CALC["EVA"])
                    with gr.Row():
                        eva_nopat = gr.Number(150000, label="NOPAT")
                        eva_wacc = gr.Number(0.11, label="WACC")
                        eva_capital = gr.Number(1000000, label="Capital invertido")
                    btn_eva = gr.Button("Calcular", variant="primary")
                    with gr.Row():
                        md_eva = gr.Markdown(scale=2)
                        plot_eva = gr.Plot(scale=3)

        with gr.Tab("💬 Asistente Explicativo"):
            gr.Markdown("### Conversa con el asistente: recuerda lo que ya hiciste en otras pestañas")
            with gr.Row():
                with gr.Column(scale=3):
                    chat = gr.Chatbot(height=420, value=[{"role": "assistant", "content": MENSAJE_BIENVENIDA}])
                    msg = gr.Textbox(label="Tu pregunta", placeholder="¿Puedo invertir? | Dame un resumen | Qué empresas comparaste | cuéntame más")
                    with gr.Row():
                        btn_send = gr.Button("Enviar", variant="primary")
                        btn_clr = gr.Button("Limpiar conversación")
                    gr.Markdown("**Preguntas rápidas:**")
                    with gr.Row():
                        btn_q1 = gr.Button("Analiza mi empresa", size="sm")
                        btn_q2 = gr.Button("¿Puedo invertir?", size="sm")
                        btn_q3 = gr.Button("Dame un resumen", size="sm")
                        btn_q4 = gr.Button("Cuéntame más", size="sm")
                with gr.Column(scale=2):
                    plot_chat_resumen = gr.Plot(label="Resumen visual de la empresa")

    # Callbacks de UI
    btn_mkt.click(pipeline_mercado, [sel_emp, sel_periodo, sel_anio],
                  [plot_p, plot_r, md_mkt, html_interp_mkt, st_precios, st_tickers])
    btn_mkt.click(actualizar_ctx_mercado, [st_ctx, st_precios, st_tickers, sel_periodo, sel_anio], st_ctx)
    btn_inv.click(simular_inv, [st_precios, st_tickers, monto, s1, s2, s3, s4, s5, sel_periodo, sel_anio], [md_inv, plot_inv])

    btn_load.click(cargar_estados, sel_d, [ac, pc, inv, un, ven, at, pat, pt, ur, uo, vm, md_load, st_sector, st_nombre])
    btn_diag.click(run_diag, [ac, pc, inv, un, ven, at, pat, pt, ur, uo, vm, st_nombre], [html_diag, st_diag])
    btn_risk.click(run_riesgo_completo, [st_precios, st_tickers, st_diag, st_sector, st_nombre], [html_risk, st_riesgo, plot_h, html_tablero])
    btn_sim.click(run_sim, [st_riesgo, n_esc, umbral], [md_sim, st_sim, plot_mc, md_mc_interpretacion])

    # Sincronización completa de datos para Asistente y Resumen Visual
    btn_int.click(run_integ, [st_diag, st_riesgo, st_sim], [md_int, st_integ, st_ctx])
    btn_int.click(grafico_resumen_asistente, st_ctx, plot_chat_resumen)
    btn_pdf.click(crear_reporte_pdf, [st_nombre, st_diag, st_riesgo, st_sim, st_ctx], [file_pdf, md_pdf_status])

    btn_is.click(lambda a, b, c, ctx: _calc_tab("Interés Simple", a, b, c, 0, 0, ctx), [is_capital, is_tasa, is_tiempo, st_ctx], [md_is, plot_is, st_ctx])
    btn_ic.click(lambda a, b, c, ctx: _calc_tab("Interés Compuesto", a, b, c, 0, 0, ctx), [ic_capital, ic_tasa, ic_periodos, st_ctx], [md_ic, plot_ic, st_ctx])
    btn_vf.click(lambda a, b, c, ctx: _calc_tab("Valor Futuro", a, b, c, 0, 0, ctx), [vf_vp, vf_tasa, vf_periodos, st_ctx], [md_vf, plot_vf, st_ctx])
    btn_vp.click(lambda a, b, c, ctx: _calc_tab("Valor Presente", a, b, c, 0, 0, ctx), [vp_vf, vp_tasa, vp_periodos, st_ctx], [md_vp, plot_vp, st_ctx])
    btn_avp.click(lambda a, b, c, d, ctx: _calc_tab("Anualidad VP", a, b, c, d, 0, ctx), [avp_cuota, avp_tasa, avp_periodos, avp_tipo, st_ctx], [md_avp, plot_avp, st_ctx])
    btn_avf.click(lambda a, b, c, d, ctx: _calc_tab("Anualidad VF", a, b, c, d, 0, ctx), [avf_cuota, avf_tasa, avf_periodos, avf_tipo, st_ctx], [md_avf, plot_avf, st_ctx])
    btn_am.click(lambda a, b, c, ctx: _calc_tab("Amortización", a, b, c, 0, 0, ctx), [am_capital, am_tasa, am_periodos, st_ctx], [md_am, plot_am, st_ctx])
    btn_ct.click(lambda a, b, c, d, ctx: _calc_tab("Conversión de tasas", a, b, c, d, 0, ctx), [ct_tasa, ct_freq_or, ct_freq_des, ct_tipo, st_ctx], [md_ct, plot_ct, st_ctx])
    btn_tir.click(lambda d, ctx: _calc_tab("TIR", 0, 0, 0, d, 0, ctx), [tir_flujos, st_ctx], [md_tir, plot_tir, st_ctx])
    btn_van.click(lambda b, d, ctx: _calc_tab("VAN", 0, b, 0, d, 0, ctx), [van_tasa, van_flujos, st_ctx], [md_van, plot_van, st_ctx])
    btn_capm.click(lambda a, b, c, ctx: _calc_tab("CAPM", a, b, c, 0, 0, ctx), [capm_rf, capm_beta, capm_rm, st_ctx], [md_capm, plot_capm, st_ctx])
    btn_wacc.click(lambda a, b, c, d, e, ctx: _calc_tab("WACC", a, b, c, d, e, ctx), [wacc_ke, wacc_kd, wacc_e, wacc_d, wacc_tax, st_ctx], [md_wacc, plot_wacc, st_ctx])
    btn_eva.click(lambda a, b, c, ctx: _calc_tab("EVA", a, b, c, 0, 0, ctx), [eva_nopat, eva_wacc, eva_capital, st_ctx], [md_eva, plot_eva, st_ctx])

    btn_send.click(chat_ui, [chat, msg, st_ctx, st_chat_tema], [chat, msg, st_chat_tema])
    msg.submit(chat_ui, [chat, msg, st_ctx, st_chat_tema], [chat, msg, st_chat_tema])
    btn_clr.click(iniciar_chat, outputs=[chat, st_chat_tema])
    btn_q1.click(lambda h, c, t: sugerencia_rapida("Analiza mi empresa", h, c, t), [chat, st_ctx, st_chat_tema], [chat, msg, st_chat_tema])
    btn_q2.click(lambda h, c, t: sugerencia_rapida("¿Puedo invertir en mi empresa?", h, c, t), [chat, st_ctx, st_chat_tema], [chat, msg, st_chat_tema])
    btn_q3.click(lambda h, c, t: sugerencia_rapida("Dame un resumen", h, c, t), [chat, st_ctx, st_chat_tema], [chat, msg, st_chat_tema])
    btn_q4.click(lambda h, c, t: sugerencia_rapida("cuéntame más", h, c, t), [chat, st_ctx, st_chat_tema], [chat, msg, st_chat_tema])
    demo.load(grafico_resumen_asistente, st_ctx, plot_chat_resumen)

port = int(os.environ.get("PORT", 7860))
demo.launch(server_name="0.0.0.0", server_port=port, css=CSS,
            theme=gr.themes.Soft(primary_hue="blue", secondary_hue="emerald"))
