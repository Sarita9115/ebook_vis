"""Inversión extranjera directa (IED) en Yucatán por país de origen

viz_id: 4.ied_por_pais

Tabla de oro (`datos`): una fila por país de origen y año.
  pais, pais_corto, anio, ied_mdd (IED neta, millones de dólares), lat, lon (país), dest_lat, dest_lon (Mérida),
  anio_completo, y los metadatos (viz_id, fuentes, institución, fecha de obtención, responsable).

Mapa de flujos: cada billete viaja por la ruta entre el país inversionista y Yucatán. Verde: inversión que llega.
Rojo, sobre ruta punteada: desinversión neta, dinero que se va. El área del billete es proporcional al monto y la
escala es fija para todo el periodo, así los años se comparan entre sí. Los montos sin país asignable no se
dibujan, pero se cuentan.

Animación (misma mecánica que la referencia del equipo, flujo_animacion.html): todos los billetes avanzan a la
misma velocidad y todos los países sueltan un billete en los mismos instantes; cada país arranca con un retraso
para que su primer billete llegue al mismo tiempo que el de la ruta más larga, y como todos sueltan el mismo
número, el último también coincide. La geometría se calcula en la proyección Natural Earth, en las mismas
unidades que la referencia (lienzo de 1000 × 540), y se convierte a lon/lat para que Plotly la dibuje.

La figura es estática (sirve para el PDF: muestra un instante a media animación). Para la web lleva en
`layout.meta["billetes"]` las rutas de cada periodo; app/assets/billetes.js anima solo las capas de billetes y
pulsos con Plotly.restyle, sin redibujar el mapa en cada cuadro.

Fuente primaria: Secretaría de Economía, IED por entidad federativa y país de origen (datos.gob.mx).
Secundaria: ficha estatal de Yucatán de la Secretaría de Economía.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import estilo_equipo4 as e  # noqa: E402

TITULO = "Inversión extranjera directa (IED) en Yucatán por país de origen"

# ---------------------------------------------------------------- constantes de la referencia (no cambiar a ojo)
W, H = 1000, 540
FRAME_MS = 10000        # duración de cada periodo a 1×
PAUSA_MS = 900          # respiro al final de cada periodo
VELOCIDAD = 0.25        # unidades del lienzo por ms, igual para todos los billetes
INTERVALO_MS = 330      # todos los países sueltan un billete en los mismos instantes
PULSO_MS = 550          # separación mínima entre pulsos en un mismo destino
RADIO_LLEGADA = 18      # los billetes desaparecen a esta distancia de la estrella
ANCHO_MAX, ANCHO_MIN, PROPORCION = 60, 10, 0.48
ESCALA_EXTREMOS = 0.3   # tamaño relativo al salir y al llegar
CURVA_BASE, CURVA_PASO, ANGULO_GRUPO = 0.3, 0.06, 0.14
INSTANTE_PDF_MS = 5200  # instante del primer periodo que muestra la imagen estática

IN, IN_OSC = "#2F9E5B", "#1D6B3B"
OUT, OUT_OSC = "#E34948", "#A52A29"
TIERRA = "#EEEDE8"


# ---------------------------------------------------------------- proyección Natural Earth (igual que d3)
def _ne(lon, lat):
    lam, phi = math.radians(lon), math.radians(lat)
    p2 = phi * phi
    p4 = p2 * p2
    x = lam * (0.8707 - 0.131979 * p2 + p4 * (-0.013791 + p4 * (0.003971 * p2 - 0.001529 * p4)))
    y = phi * (1.007226 + p2 * (0.015085 + p4 * (-0.044475 + 0.028874 * p2 - 0.005916 * p4)))
    return x, y


def _ne_inv(x, y):
    phi = y
    for _ in range(25):
        p2 = phi * phi
        p4 = p2 * p2
        d = ((phi * (1.007226 + p2 * (0.015085 + p4 * (-0.044475 + 0.028874 * p2 - 0.005916 * p4))) - y)
             / (1.007226 + p2 * (0.015085 * 3 + p4 * (-0.044475 * 7 + 0.028874 * 9 * p2 - 0.005916 * 11 * p4))))
        phi -= d
        if abs(d) < 1e-9:
            break
    p2 = phi * phi
    lam = x / (0.8707 + p2 * (-0.131979 + p2 * (-0.013791 + p2 * p2 * p2 * (0.003971 - 0.001529 * p2))))
    return math.degrees(lam), math.degrees(phi)


def _ajuste():
    """fitExtent([[0, 8], [W, H-4]]) de la referencia sobre el mismo multipunto."""
    pts = [_ne(lo, la) for lo, la in [(-130, -48), (150, -48), (-130, 80), (150, 80), (10, 80), (10, -48)]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    k = min(W / (max(xs) - min(xs)), (H - 12) / (max(ys) - min(ys)))
    x0 = (W - k * (max(xs) + min(xs))) / 2
    y0 = 8 + (H - 12 + k * (max(ys) + min(ys))) / 2
    return k, x0, y0


K, X0, Y0 = _ajuste()


def a_lienzo(lon, lat):
    x, y = _ne(lon, lat)
    return K * x + X0, -K * y + Y0


def a_geo(px, py):
    lon, lat = _ne_inv((px - X0) / K, -(py - Y0) / K)
    return lat, lon


# ---------------------------------------------------------------- geometría de rutas (igual que la referencia)
def _control(p, m, curv):
    vx, vy = p[0] - m[0], p[1] - m[1]
    return [m[0] + vx / 2 + vy * curv, max(-40, m[1] + vy / 2 - vx * curv)]


def _punto(a, c, b, t):
    u = 1 - t
    return [u * u * a[0] + 2 * u * t * c[0] + t * t * b[0], u * u * a[1] + 2 * u * t * c[1] + t * t * b[1]]


def _tangente(a, c, b, t):
    dx = 2 * (1 - t) * (c[0] - a[0]) + 2 * t * (b[0] - c[0])
    dy = 2 * (1 - t) * (c[1] - a[1]) + 2 * t * (b[1] - c[1])
    return math.degrees(math.atan2(dy, dx))


def _medir(a, c, b, n=80):
    acum, prev = [0.0], a
    for i in range(1, n + 1):
        q = _punto(a, c, b, i / n)
        acum.append(acum[-1] + math.hypot(q[0] - prev[0], q[1] - prev[1]))
        prev = q
    return acum


def _t_en_distancia(acum, dist):
    n = len(acum) - 1
    i = max(1, int(np.searchsorted(acum, dist, side="left")))
    if i > n:
        return 1.0
    return (i - 1 + (dist - acum[i - 1]) / ((acum[i] - acum[i - 1]) or 1)) / n


def _curvaturas(paises, m):
    """Abanico: rutas que salen casi en la misma dirección reciben curvaturas distintas (el más al norte, arriba)."""
    lista = sorted(((p, math.atan2(xy[1] - m[1], xy[0] - m[0])) for p, xy in paises.items()), key=lambda d: d[1])
    grupos = []
    for i, d in enumerate(lista):
        if i and d[1] - lista[i - 1][1] < ANGULO_GRUPO:
            grupos[-1].append(d)
        else:
            grupos.append([d])
    return {d[0]: CURVA_BASE + ((len(g) - 1) / 2 - i) * CURVA_PASO for g in grupos for i, d in enumerate(g)}


# ---------------------------------------------------------------- datos de cada periodo
def _flujos(datos, anios):
    d = datos[datos.anio.isin(anios)]
    con = d.dropna(subset=["lat"]).groupby(["pais", "pais_corto", "lat", "lon"], as_index=False).ied_mdd.sum()
    con = con[con.ied_mdd.abs() >= 0.05].sort_values("ied_mdd", key=abs, ascending=False).reset_index(drop=True)
    return con, float(d[d.lat.isna()].ied_mdd.sum())


def _fmt(v: float) -> str:
    return f"{'−' if v < 0 else ''}{abs(v):,.1f} mdd"


def _ancho(v, vmax):
    return max(ANCHO_MIN, ANCHO_MAX * math.sqrt(abs(v) / vmax))


def _rutas(con, merida, curvas, vmax):
    rutas = []
    for r in con.itertuples():
        p = a_lienzo(r.lon, r.lat)
        entra = r.ied_mdd > 0
        a, b = (p, merida) if entra else (merida, p)
        c = _control(p, merida, curvas[r.pais])
        acum = _medir(a, c, b)
        largo = acum[-1]
        rad = min(RADIO_LLEGADA, largo * 0.4)
        rutas.append(dict(pais=r.pais, corto=r.pais_corto, mdd=round(float(r.ied_mdd), 3), p=list(p), a=list(a),
                          b=list(b), c=c, entra=bool(entra), w=round(_ancho(r.ied_mdd, vmax), 2),
                          ini=0 if entra else rad, fin=largo - rad if entra else largo, acum=acum))
    return rutas


def _emisiones(rutas):
    """Calendario de salidas de un periodo: misma cadencia para todos; llegadas sincronizadas."""
    if not rutas:
        return []
    viaje = [(r["fin"] - r["ini"]) / VELOCIDAD for r in rutas]
    mx = max(viaje)
    n = max(1, int((FRAME_MS - mx) // INTERVALO_MS) + 1)
    return sorted(((mx - v + k * INTERVALO_MS, i) for i, v in enumerate(viaje) for k in range(n)))


def _billete(r, t, giro_extra=0.0):
    """Posición, giro, escala y opacidad del billete en la fracción t de su viaje (como la referencia)."""
    dist = r["ini"] + t * (r["fin"] - r["ini"])
    s = _t_en_distancia(r["acum"], dist)
    x, y = _punto(r["a"], r["c"], r["b"], s)
    giro = _tangente(r["a"], r["c"], r["b"], s) * 0.25 + giro_extra
    op = min(1, t / 0.06, (1 - t) / 0.15)
    esc = ESCALA_EXTREMOS + (1 - ESCALA_EXTREMOS) * math.sin(math.pi * t)
    return x, y, giro, esc, op


def _rect(cx, cy, w, h, giro):
    """Rectángulo girado en el lienzo, devuelto en lon/lat con el sentido de giro que plotly geo rellena."""
    g = math.radians(giro)
    cs, sn = math.cos(g), math.sin(g)
    pts = [a_geo(cx + dx * cs - dy * sn, cy + dx * sn + dy * cs)
           for dx, dy in [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]]
    area = sum(p[1] * q[0] - q[1] * p[0] for p, q in zip(pts, pts[1:] + pts[:1]))
    if area > 0:
        pts = pts[::-1]
    pts.append(pts[0])
    return [p[0] for p in pts], [p[1] for p in pts]


CAPAS = ("in0", "in1", "in2", "out0", "out1", "out2", "borde")


def _instantanea(rutas, en_frame, f_px):
    """Capas animadas en un instante del periodo (para la imagen estática; billetes.js hace lo mismo en vivo)."""
    cap = {k: ([], []) for k in CAPAS}
    sig = dict(lat=[], lon=[], tam=[], txt=[], col=[])
    for t0, i in _emisiones(rutas):
        r = rutas[i]
        t = (en_frame - t0) * VELOCIDAD / (r["fin"] - r["ini"])
        if t0 > en_frame or not 0 <= t < 1:
            continue
        x, y, giro, esc, op = _billete(r, t)
        w, h = r["w"] * esc, r["w"] * PROPORCION * esc
        nivel = 0 if op < 0.4 else 1 if op < 0.8 else 2
        la, lo = _rect(x, y, w, h, giro)
        clave = f"{'in' if r['entra'] else 'out'}{nivel}"
        cap[clave][0].extend([*la, None])
        cap[clave][1].extend([*lo, None])
        if r["w"] >= 18:
            la, lo = _rect(x, y, w - 5 * esc, h - 5 * esc, giro)
            cap["borde"][0].extend([*la, None])
            cap["borde"][1].extend([*lo, None])
            cl, co = a_geo(x, y)
            sig["lat"].append(cl)
            sig["lon"].append(co)
            sig["tam"].append(round(h * 0.6 * f_px, 1))
            sig["txt"].append(round(h * 0.48 * f_px, 1))
            sig["col"].append(f"rgba(255,255,255,{op:.2f})")
    return cap, sig


def _etiquetas(rutas):
    """Etiquetas de los países grandes primero; se omite la que choca con una ya puesta."""
    if not rutas:
        return []
    mx = max(abs(r["mdd"]) for r in rutas)
    puestas, salida = [], []
    for r in sorted((r for r in rutas if abs(r["mdd"]) >= 0.07 * mx), key=lambda r: -abs(r["mdd"])):
        w = 6.2 * len(r["corto"])
        if not any(abs(o[0][0] - r["p"][0]) < (w + o[1]) / 2 and abs(o[0][1] - r["p"][1]) < 15 for o in puestas):
            puestas.append((r["p"], w))
            salida.append(r)
    return salida


def _contador(etiqueta, entro, salio, sin, completo):
    sp = "&nbsp;"
    aviso = ("<span style='font-size:11px;color:#898781'>Año incompleto (último trimestre publicado)</span>"
             if not completo else " ")
    return (f'<span style="font-size:34px;color:{e.TINTA}"><b>{etiqueta}</b></span><br>{aviso}<br>'
            f"Entró{sp * 22}<b style='color:{IN_OSC}'>{_fmt(entro)}</b><br>"
            f"Salió{sp * 23}<b style='color:{OUT_OSC}'>{_fmt(-salio)}</b><br>"
            f"<span style='color:#E1E0D9'>───────────────────────</span><br>"
            f"Neto en el mapa{sp * 8}<b style='color:{e.TINTA}'>{_fmt(entro - salio)}</b><br>"
            f"<span style='font-size:11px;color:#898781'>Sin país asignable{sp * 7}{_fmt(sin)}</span>")


def _periodo(rutas, merida_geo, etiqueta, sin, completo, f_px, en_frame=None):
    """Trazas de un periodo, en el orden de capas de la referencia, e índices de las capas animadas."""
    tr, idx = [], {}
    grupos = {}
    for r in rutas:
        ancho = round((0.8 + 0.12 * r["w"]) * f_px * 2) / 2
        grupos.setdefault((r["entra"], ancho), []).append(r)
    for (entra, ancho), rs in sorted(grupos.items(), key=lambda kv: kv[0][1]):
        la, lo = [], []
        for r in rs:
            for k in range(41):
                y, x = a_geo(*_punto(r["a"], r["c"], r["b"], k / 40))
                la.append(round(y, 3))
                lo.append(round(x, 3))
            la.append(None)
            lo.append(None)
        tr.append(go.Scattergeo(lat=la, lon=lo, mode="lines", hoverinfo="skip", opacity=0.28,
                                line=dict(color=IN if entra else OUT, width=ancho, dash=None if entra else "dash")))
    nodos = [a_geo(*r["p"]) for r in rutas]
    tr.append(go.Scattergeo(
        lat=[n[0] for n in nodos], lon=[n[1] for n in nodos], mode="markers",
        customdata=[[r["corto"], _fmt(r["mdd"]) + ("" if r["entra"] else " (desinversión)")] for r in rutas],
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>",
        marker=dict(size=[2 * (3 + 0.16 * r["w"]) * f_px for r in rutas],
                    color=[IN if r["entra"] else OUT for r in rutas], line=dict(color="white", width=1.5))))

    if en_frame is not None:
        cap, sig = _instantanea(rutas, en_frame, f_px)
    else:
        cap, sig = {k: ([], []) for k in CAPAS}, dict(lat=[], lon=[], tam=[], txt=[], col=[])
    for clave, op in [("in0", 0.25), ("in1", 0.6), ("in2", 1.0), ("out0", 0.25), ("out1", 0.6), ("out2", 1.0)]:
        entra = clave.startswith("in")
        idx[clave] = len(tr)
        tr.append(go.Scattergeo(lat=cap[clave][0], lon=cap[clave][1], mode="lines", fill="toself", opacity=op,
                                fillcolor=IN if entra else OUT, hoverinfo="skip",
                                line=dict(color=IN_OSC if entra else OUT_OSC, width=1)))
    idx["borde"] = len(tr)
    tr.append(go.Scattergeo(lat=cap["borde"][0], lon=cap["borde"][1], mode="lines", hoverinfo="skip",
                            line=dict(color="rgba(255,255,255,0.55)", width=0.8)))
    idx["signo"] = len(tr)
    tr.append(go.Scattergeo(lat=sig["lat"], lon=sig["lon"], mode="markers+text", text=["$"] * len(sig["lat"]),
                            hoverinfo="skip",
                            textfont=dict(family=e.LETRA, size=sig["txt"] or 10, color=sig["col"] or "white",
                                          weight="bold"),
                            marker=dict(size=sig["tam"] or 1, color="rgba(29,107,59,0.55)", line=dict(width=0))))

    et = _etiquetas(rutas)
    pos = [a_geo(r["p"][0], r["p"][1] - 8 - 0.16 * r["w"]) for r in et]
    tr.append(go.Scattergeo(lat=[p[0] for p in pos], lon=[p[1] for p in pos], mode="text",
                            text=[r["corto"] for r in et], textposition="top center", hoverinfo="skip",
                            textfont=dict(family=e.LETRA, size=12, color=e.TINTA)))
    idx["pulso"] = len(tr)
    tr.append(go.Scattergeo(lat=[], lon=[], mode="markers", hoverinfo="skip",
                            marker=dict(symbol="circle-open", size=[], color=[], line=dict(width=2))))
    tr.append(go.Scattergeo(lat=[merida_geo[0]], lon=[merida_geo[1]], mode="markers+text", text=["<b>Yucatán</b>"],
                            textposition="middle left", hoverinfo="skip",
                            textfont=dict(family=e.LETRA, size=13, color=e.TINTA),
                            marker=dict(symbol="star", size=19, color=e.TINTA, line=dict(color="white", width=1.5))))
    entro = sum(max(0, r["mdd"]) for r in rutas)
    salio = sum(max(0, -r["mdd"]) for r in rutas)
    return tr, idx, _contador(etiqueta, entro, salio, sin, completo), entro - salio


def _anotacion(contador):
    return dict(text=contador, xref="paper", yref="paper", x=0.62, y=0.03, xanchor="left", yanchor="bottom",
                showarrow=False, align="left", bgcolor="rgba(252,252,251,0.92)", bordercolor="#E1E0D9",
                borderwidth=1, borderpad=12, font=dict(family=e.LETRA, size=13, color=e.TINTA_2))


def _leyenda():
    return dict(text=f"<span style='color:{IN}'>▬</span> Entra a Yucatán&nbsp;&nbsp;&nbsp;"
                     f"<span style='color:{OUT}'>▬</span> Sale de Yucatán&nbsp;&nbsp;&nbsp;"
                     "<span style='color:#898781'>Área del billete ∝ monto</span>",
                xref="paper", yref="paper", x=0.01, y=0.01, xanchor="left", yanchor="bottom",
                showarrow=False, font=dict(family=e.LETRA, size=12, color=e.TINTA_2))


def figura(datos, anios=None, modo: str = "acumulado", ancho_px: int = 1250) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro.

    anios: años a mostrar (por defecto 2020-2025). modo: "acumulado" (un periodo) o "anual" (año por año).
    ancho_px: ancho aproximado en pantalla, para que trazos y nodos guarden la proporción de la referencia.
    """
    fig = e.base(go.Figure(), TITULO, alto=int(ancho_px * H / W) + 40)
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
    if datos is None or len(datos) == 0:
        return fig
    anios = sorted(anios or range(2020, 2026))
    grupos = [[a] for a in anios] if modo == "anual" else [anios]
    merida_geo = (float(datos.dest_lat.iloc[0]), float(datos.dest_lon.iloc[0]))
    merida = a_lienzo(merida_geo[1], merida_geo[0])
    f_px = ancho_px / W

    calc = []
    for g in grupos:
        con, sin = _flujos(datos, g)
        calc.append((str(g[0]) if len(g) == 1 else f"{g[0]}–{g[-1]}", con, sin,
                     bool(datos[datos.anio.isin(g)].anio_completo.all())))
    vmax = max((c[1].ied_mdd.abs().max() for c in calc if len(c[1])), default=1)   # escala fija del periodo
    paises = {r.pais: a_lienzo(r.lon, r.lat) for c in calc for r in c[1].itertuples()}
    curvas = _curvaturas(paises, merida)

    animacion, primero = [], None
    for i, (etiqueta, con, sin, completo) in enumerate(calc):
        rutas = _rutas(con, merida, curvas, vmax)
        tr, idx, contador, neto = _periodo(rutas, merida_geo, etiqueta, sin, completo, f_px)
        animacion.append(dict(
            etiqueta=etiqueta, neto=round(neto, 3), neto_txt=_fmt(neto), idx=idx,
            anotaciones=[_anotacion(contador), _leyenda()],
            rutas=[{k: r[k] for k in ("pais", "a", "b", "c", "entra", "w", "ini", "fin", "mdd")} for r in rutas],
            data=json.loads(go.Figure(data=tr).to_json())["data"]))
        if i == 0:
            primero = (rutas, etiqueta, sin, completo)

    # Imagen estática: el primer periodo a media animación.
    tr, _, contador, _ = _periodo(primero[0], merida_geo, primero[1], primero[2], primero[3], f_px,
                                  en_frame=INSTANTE_PDF_MS)
    fig.add_traces(tr)
    fig.update_layout(
        annotations=[_anotacion(contador), _leyenda()],
        meta=dict(billetes=dict(
            id=f"{modo}-{anios[0]}-{anios[-1]}", grupos=animacion, lienzo=dict(K=K, X0=X0, Y0=Y0, W=W),
            constantes=dict(FRAME_MS=FRAME_MS, PAUSA_MS=PAUSA_MS, VELOCIDAD=VELOCIDAD, INTERVALO_MS=INTERVALO_MS,
                            PULSO_MS=PULSO_MS, PROPORCION=PROPORCION, ESCALA_EXTREMOS=ESCALA_EXTREMOS),
            colores=dict(IN=IN, IN_OSC=IN_OSC, OUT=OUT, OUT_OSC=OUT_OSC))))
    fig.update_geos(projection_type="natural earth", projection_rotation=dict(lon=0, lat=0, roll=0),
                    showland=True, landcolor=TIERRA, showocean=False, showcountries=True, countrycolor="white",
                    countrywidth=0.5, showcoastlines=False, showframe=False, showlakes=False, bgcolor="#FCFCFB",
                    lonaxis_range=[-130, 150], lataxis_range=[-48, 80])
    fig.update_layout(paper_bgcolor="#FCFCFB")
    return fig
