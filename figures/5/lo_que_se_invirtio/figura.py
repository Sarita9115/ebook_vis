"""Lo que se invierte hoy
viz_id: 5.lo_que_se_invirtio

Sankey del sector educativo de Yucatán en 2025 (boceto del equipo):
sector educativo -> SEGEY (educación básica) y educación media superior y superior;
de ahí, a cada institución.

Tabla de oro (`datos`), un renglón por flujo:
    origen          p. ej. "Sector educativo"
    destino         p. ej. "Secretaría de Educación (SEGEY)"
    monto_millones  millones de pesos ejercidos en 2025
La raíz (el nodo que nunca es destino) es el total del sector.

La plantilla muestra fuentes, fecha y responsable; no van dentro de la figura.
"""
import pandas as pd
import plotly.graph_objects as go

TITULO = "Lo que se invierte hoy"  # debe coincidir con el título del subtema en el catálogo
CALIZA, TEXTO, TEXTO_2 = "#f7f4ec", "#1d2a22", "#4f5b52"
LETRA = "Source Sans 3, Helvetica Neue, Helvetica, Arial, sans-serif"
PALETA = ["#2f8c70", "#4590f5", "#e8833a", "#7f77dd"]


def _base() -> dict:
    return dict(
        title=dict(text=TITULO, x=0, xanchor="left", y=0.97, yanchor="top",
                   font=dict(size=22, color=TEXTO), pad=dict(l=10)),
        width=1100, height=720, paper_bgcolor=CALIZA, plot_bgcolor=CALIZA,
        font=dict(family=LETRA, size=14, color=TEXTO),
        margin=dict(l=30, r=60, t=80, b=30),
        hoverlabel=dict(bgcolor="white", font=dict(family=LETRA, color=TEXTO, size=13)),
    )


def _rgba(hex_, a) -> str:
    h = hex_.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(**_base())
    if datos is None or len(datos) == 0:
        return fig
    d = datos.copy()
    d["monto_millones"] = pd.to_numeric(d["monto_millones"], errors="coerce")
    d = d.dropna(subset=["monto_millones"])
    d = d[d["monto_millones"] > 0].reset_index(drop=True)
    if d.empty:
        return fig

    nombres = list(dict.fromkeys(list(d["origen"]) + list(d["destino"])))
    idx = {n: i for i, n in enumerate(nombres)}
    raiz = [n for n in nombres if n not in set(d["destino"])][0]
    total = d.loc[d["origen"] == raiz, "monto_millones"].sum()
    recibe = d.groupby("destino")["monto_millones"].sum()
    padre = dict(zip(d["destino"], d["origen"]))

    def profundidad(n):
        p = 0
        while n in padre:
            n = padre[n]
            p += 1
        return p

    prof = {n: profundidad(n) for n in nombres}
    max_prof = max(prof.values()) or 1

    # Posición: la SEGEY arriba, media superior abajo y las instituciones en la parte baja.
    por_nivel = {}
    for n in nombres:
        por_nivel.setdefault(prof[n], []).append(n)
    pos_x, pos_y = [], []
    for n in nombres:
        grupo, i = por_nivel[prof[n]], por_nivel[prof[n]].index(n)
        pos_x.append(0.02 + prof[n] * (0.74 / max_prof))
        if prof[n] == 0:
            pos_y.append(0.5)
        elif prof[n] == 1:
            pos_y.append(0.2 if i == 0 else 0.45 + (i / max(len(grupo) - 1, 1)) * 0.4)
        else:
            pos_y.append(0.5 + (i + 0.5) / len(grupo) * 0.47)

    ramas = list(d.loc[d["origen"] == raiz, "destino"])
    color_rama = {r: PALETA[i % len(PALETA)] for i, r in enumerate(ramas)}

    def color(n):
        if n == raiz:
            return "#555555"
        while n not in color_rama and n in padre:
            n = padre[n]
        return color_rama.get(n, "#999999")

    def etiqueta(n):
        v = total if n == raiz else recibe[n]
        extra = f" ({v / total:.0%})" if padre.get(n) == raiz else ""
        return f"{n}<br>${v:,.0f} M{extra}"

    fig.add_trace(go.Sankey(
        arrangement="snap", textfont=dict(family=LETRA, size=13, color=TEXTO),
        node=dict(label=[etiqueta(n) for n in nombres], x=pos_x, y=pos_y, pad=18, thickness=18,
                  line=dict(color=TEXTO, width=1), color=[color(n) for n in nombres],
                  hovertemplate="%{label}<extra></extra>"),
        link=dict(
            source=[idx[o] for o in d["origen"]], target=[idx[t] for t in d["destino"]],
            value=list(d["monto_millones"]),
            color=[_rgba(color(t), 0.35) for t in d["destino"]],
            customdata=[f"{v / total:.1%}" for v in d["monto_millones"]],
            hovertemplate="%{source.label} → %{target.label}"
                          "<br>$%{value:,.1f} millones"
                          "<br>%{customdata} del total del sector<extra></extra>"),
    ))
    return fig
