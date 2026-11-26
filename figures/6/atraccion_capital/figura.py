"""Atracción de capital, empleo y evolución de las unidades económicas en Yucatán

viz_id: 6.atraccion_capital

Tabla de oro (`datos`): formato largo, una fila por serie, entidad y año.
  serie       "ied"       inversión extranjera directa anual, millones de dólares (Yucatán, Campeche, Quintana Roo)
              "unidades"  unidades económicas de Yucatán en cada corte del DENUE
              "empleo"    personal ocupado estimado de Yucatán en cada corte del DENUE
  entidad     Yucatán, Campeche o Quintana Roo (unidades y empleo solo de Yucatán)
  anio        año de la cifra (la IED solo con años de cuatro trimestres; DENUE: cortes de 2018 a 2026)
  valor       valor de la serie
  lugar       solo serie "ied": lugar de la entidad entre los 32 estados por IED acumulada del periodo
  de_estados  solo serie "ied": número de estados comparados (32)

El empleo es una estimación: el DENUE da el personal ocupado en rangos y se usa el punto medio de cada rango.
El lugar nacional se calcula en la limpieza con los 32 estados; en la tabla solo quedan las tres entidades de la península.

Fuente primaria: Secretaría de Economía, inversión extranjera directa por entidad federativa.
Fuente secundaria: DENUE (INEGI), unidades económicas y personal ocupado estimado.
"""

import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots

TITULO = "Atracción de capital, empleo y evolución de las unidades económicas en Yucatán"

TERRACOTA, MONTE, CENOTE = "#d9622b", "#1f8a70", "#2b7a9b"
CALIZA, TEXTO, TEXTO_2, REJILLA = "#f7f4ec", "#1d2a22", "#4f5b52", "#e4dfd2"
LETRA = "Source Sans 3, Helvetica Neue, Helvetica, Arial, sans-serif"
COLOR = {"Yucatán": TERRACOTA, "Campeche": CENOTE, "Quintana Roo": MONTE}


def _n(x):
    return f"{x:,.0f}".replace(",", " ")


def _mil(x):
    """Etiqueta corta para los paneles del DENUE: 146 384 -> "146 mil"."""
    return f"{x / 1000:,.0f} mil".replace(",", " ")


def _ticks_mil(maximo):
    """Marcas del eje y de los paneles del DENUE en "mil" (0, 50 mil, 100 mil... 1 millón)."""
    bruto = maximo / 5
    base = 10 ** math.floor(math.log10(bruto))
    paso = next(m * base for m in (1, 2, 2.5, 5, 10) if m * base >= bruto)
    vals = [i * paso for i in range(int(maximo // paso) + 1)]
    texto = ["0" if v == 0 else (f"{v / 1e6:g} millón" if v == 1e6 else (f"{v / 1e6:g} millones" if v > 1e6 else _mil(v)))
             for v in vals]
    return vals, texto


def _separar(valores, minimo):
    orden = sorted(valores, key=valores.get)
    pos = {k: valores[k] for k in orden}
    for _ in range(40):
        movido = False
        for a, b in zip(orden, orden[1:]):
            if pos[b] - pos[a] < minimo:
                m = (pos[a] + pos[b]) / 2
                pos[a], pos[b] = m - minimo / 2, m + minimo / 2
                movido = True
        if not movido:
            break
    return pos


def _cambio(s):
    a, b = s.iloc[0], s.iloc[-1]
    return f"{(b / a - 1) * 100:+.0f}% entre {int(s.index[0])} y {int(s.index[-1])}"


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    d = datos.copy() if datos is not None and len(datos) else None
    uni = emp = None
    if d is not None:
        u = d[d.serie == "unidades"].sort_values("anio").set_index("anio").valor
        e = d[d.serie == "empleo"].sort_values("anio").set_index("anio").valor
        uni, emp = (u if len(u) else None), (e if len(e) else None)
    t_uni = "Unidades económicas" + (f": {_cambio(uni)}" if uni is not None and len(uni) > 1 else "")
    t_emp = "Personal ocupado estimado" + (f": {_cambio(emp)}" if emp is not None and len(emp) > 1 else "")
    fig = make_subplots(rows=2, cols=2, specs=[[{"colspan": 2}, None], [{}, {}]], row_heights=[0.56, 0.44],
                        vertical_spacing=0.15, horizontal_spacing=0.1,
                        subplot_titles=("Inversión extranjera directa por año, millones de dólares", t_uni, t_emp))
    fig.update_layout(
        title=dict(text=TITULO, x=0, xanchor="left", y=0.98, yanchor="top", font=dict(size=22, color=TEXTO), pad=dict(l=10)),
        separators=". ", width=1200, height=900, paper_bgcolor=CALIZA, plot_bgcolor=CALIZA, showlegend=False,
        font=dict(family=LETRA, size=14, color=TEXTO), margin=dict(l=80, r=250, t=110, b=60),
        hoverlabel=dict(bgcolor="white", font=dict(family=LETRA, color=TEXTO, size=13), bordercolor=REJILLA))
    fig.update_annotations(font=dict(size=14, color=TEXTO_2))
    if d is None:
        return fig

    # ---- panel 1: IED, tres entidades ----
    ied = d[d.serie == "ied"].sort_values(["entidad", "anio"])
    fin = int(ied.anio.max()) if len(ied) else 0
    finales, lugar = {}, {}
    for ent in ("Quintana Roo", "Campeche", "Yucatán"):
        s = ied[ied.entidad == ent]
        if s.empty:
            continue
        yuc = ent == "Yucatán"
        fig.add_trace(go.Scatter(x=s.anio, y=s.valor, mode="lines+markers", showlegend=False,
                                 line=dict(color=COLOR[ent], width=4 if yuc else 2.5),
                                 marker=dict(size=9 if yuc else 6, color=COLOR[ent], line=dict(color="white", width=1.5)),
                                 hovertemplate=f"<b>{ent}</b><br>%{{x}}: %{{y:,.0f}} millones de dólares<extra></extra>"), row=1, col=1)
        finales[ent] = float(s.valor.iloc[-1])
        lugar[ent] = (int(s.lugar.iloc[0]), int(s.de_estados.iloc[0]))
    if len(ied):
        rango = float(ied.valor.max() - min(ied.valor.min(), 0)) or 1.0
        for ent, y in _separar(finales, rango * 0.1).items():
            l, de = lugar[ent]
            fig.add_annotation(x=fin, y=y, xref="x", yref="y", showarrow=False, xanchor="left", xshift=10, align="left",
                               text=f"<b>{ent}</b><br>lugar {l} de {de} estados", bgcolor="rgba(247,244,236,0.85)",
                               font=dict(size=13, color=COLOR[ent]))
        y = ied[ied.entidad == "Yucatán"]
        if len(y):
            p = y.loc[y.valor.idxmax()]
            fig.add_annotation(x=p.anio, y=p.valor, xref="x", yref="y", showarrow=False, yshift=18,
                               text=f"<b>{_n(p.valor)}</b> en {int(p.anio)}", font=dict(size=13, color=TERRACOTA))
        anios = sorted(ied.anio.unique())
        fig.update_xaxes(tickmode="array", tickvals=anios, range=[min(anios) - 0.4, fin + 0.4], showgrid=False, linecolor=TEXTO_2,
                         tickfont=dict(size=12, color=TEXTO_2), row=1, col=1)
        fig.update_yaxes(gridcolor=REJILLA, zeroline=True, zerolinecolor=TEXTO_2, tickfont=dict(size=12, color=TEXTO_2),
                         range=[min(float(ied.valor.min()), 0) * 1.1 - rango * 0.02, float(ied.valor.max()) + rango * 0.14], row=1, col=1)

    # ---- paneles 2 y 3: Yucatán, cortes del DENUE ----
    for col, s, nombre in ((1, uni, "unidades"), (2, emp, "personas")):
        if s is None:
            continue
        fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines+markers+text", showlegend=False,
                                 line=dict(color=TERRACOTA, width=3), marker=dict(size=9, color=TERRACOTA, line=dict(color="white", width=1.5)),
                                 text=[_mil(v) for v in s.values], textposition="top center", textfont=dict(size=11, color=TEXTO_2),
                                 hovertemplate=f"%{{x}}: %{{y:,.0f}} {nombre}<extra></extra>", cliponaxis=False), row=2, col=col)
        fig.update_xaxes(tickmode="array", tickvals=list(s.index), showgrid=False, linecolor=TEXTO_2, tickfont=dict(size=11, color=TEXTO_2),
                         range=[s.index.min() - 0.6, s.index.max() + 0.6], row=2, col=col)
        tope = float(s.max()) * 1.18
        vals, texto = _ticks_mil(tope)
        fig.update_yaxes(gridcolor=REJILLA, rangemode="tozero", tickfont=dict(size=11, color=TEXTO_2), range=[0, tope],
                         tickmode="array", tickvals=vals, ticktext=texto, row=2, col=col)
    return fig
