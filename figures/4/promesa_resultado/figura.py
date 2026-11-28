"""Promesa contra resultado: empleos anunciados y empleo formal en el IMSS

viz_id: 4.promesa_resultado

Tabla de oro (`datos`): dos filas.
  concepto ("prometido" | "registrado_imss"), empleos, proyectos, inversion_mdp, periodo, fecha_dato, fuente,
  enlace, pct_de_lo_prometido, y los metadatos.

Cada figura humana vale 1,000 empleos. Los trabajadores con casco son los empleos formales nuevos que registró
el IMSS; las siluetas punteadas son el resto de lo que se prometió en el anuncio de 2022.
La promesa sumaba empleos directos e indirectos; el IMSS solo cuenta empleo formal. La brecha es la pregunta,
no una conclusión.

Fuente primaria: Gobierno de Yucatán, anuncio de 245 proyectos de inversión privada (22 de junio de 2022).
Secundaria: IMSS, trabajadores asegurados en Yucatán (boletín del Gobierno de Yucatán, mayo de 2024).
"""
import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import estilo_equipo4 as e  # noqa: E402

TITULO = "Promesa contra resultado: empleos anunciados y empleo formal en el IMSS"
CASCO = "#F2B400"
FANTASMA = "#C9C6BE"
COLUMNAS = 20
UNIDAD = 1000  # empleos por figura

# Paso a paso: 1 = lo prometido, 2 = lo registrado; None = las dos lecturas juntas.
PASOS = {1: "prometido", 2: "registrado_imss"}


def _rect_redondo(x0, y0, w, h, r, n=5):
    """Contorno de un rectángulo con esquinas redondeadas, como lista de puntos cerrada."""
    xs, ys = [], []
    for cx, cy, a0 in [(x0 + w - r, y0 + r, -90), (x0 + w - r, y0 + h - r, 0), (x0 + r, y0 + h - r, 90),
                       (x0 + r, y0 + r, 180)]:
        a = np.radians(np.linspace(a0, a0 + 90, n))
        xs += list(cx + r * np.cos(a))
        ys += list(cy + r * np.sin(a))
    return xs + [xs[0]], ys + [ys[0]]


def _circulo(cx, cy, r, n=14):
    a = np.linspace(0, 2 * np.pi, n)
    return list(cx + r * np.cos(a)), list(cy + r * np.sin(a))


def _casco(cx, cy, r, n=10):
    a = np.linspace(0, np.pi, n)
    xs = list(cx + r * np.cos(a)) + [cx - r - 0.05, cx + r + 0.05, cx + r]
    ys = list(cy + r * np.sin(a)) + [cy, cy, cy]
    return xs, ys


def _juntar(formas):
    """Une varios polígonos en una sola traza (separados por None): un trazo por tipo, no uno por figura."""
    xs, ys = [], []
    for fx, fy in formas:
        xs += fx + [None]
        ys += fy + [None]
    return xs, ys


def figura(datos, paso: int | None = None) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro.

    paso 1 resalta lo prometido, paso 2 lo registrado en el IMSS; None muestra las dos lecturas.
    """
    fig = e.base(go.Figure(), TITULO, alto=640)
    fig.update_layout(margin=dict(l=20, r=20, t=80, b=30))
    if datos is None or len(datos) == 0:
        return fig

    d = datos.set_index("concepto")
    prometido, registrado = float(d.loc["prometido", "empleos"]), float(d.loc["registrado_imss", "empleos"])
    n_total, n_lleno = int(round(prometido / UNIDAD)), int(round(registrado / UNIDAD))
    filas = int(np.ceil(n_total / COLUMNAS))

    llenos, fantasmas, cascos, centros = [], [], [], []
    for i in range(n_total):
        r, c = divmod(i, COLUMNAS)
        x, y = c, filas - 1 - r
        cuerpo = _rect_redondo(x + 0.24, y + 0.06, 0.52, 0.42, 0.15)
        cabeza = _circulo(x + 0.5, y + 0.66, 0.15)
        (llenos if i < n_lleno else fantasmas).extend([cuerpo, cabeza])
        if i < n_lleno:
            cascos.append(_casco(x + 0.5, y + 0.70, 0.19))
        centros.append((x + 0.5, y + 0.4, i < n_lleno))

    resalta = PASOS.get(paso)
    op_lleno = 1.0 if resalta in (None, "registrado_imss") else 0.25
    op_fantasma = 1.0 if resalta in (None, "prometido") else 0.35

    fx, fy = _juntar(fantasmas)
    fig.add_trace(go.Scatter(x=fx, y=fy, mode="lines", fill="toself", fillcolor="rgba(201,198,190,0.10)",
                             line=dict(color=FANTASMA, width=1, dash="dot"), opacity=op_fantasma,
                             hoverinfo="skip"))
    lx, ly = _juntar(llenos)
    fig.add_trace(go.Scatter(x=lx, y=ly, mode="lines", fill="toself", fillcolor=e.NARANJA,
                             line=dict(color=e.NARANJA, width=0.5), opacity=op_lleno, hoverinfo="skip"))
    cx, cy = _juntar(cascos)
    fig.add_trace(go.Scatter(x=cx, y=cy, mode="lines", fill="toself", fillcolor=CASCO,
                             line=dict(color=CASCO, width=0.5), opacity=op_lleno, hoverinfo="skip"))

    # Tooltip por figura.
    reg, prom = d.loc["registrado_imss"], d.loc["prometido"]
    texto = [(f"<b>Empleo formal registrado</b><br>1,000 trabajadores nuevos asegurados en el IMSS<br>{reg.periodo}"
              if lleno else f"<b>Empleo prometido</b><br>1,000 empleos del anuncio de {int(prom.proyectos)} "
                            f"proyectos<br>que no aparecen en el IMSS") for _, _, lleno in centros]
    fig.add_trace(go.Scatter(x=[c[0] for c in centros], y=[c[1] for c in centros], mode="markers",
                             marker=dict(size=16, color="rgba(0,0,0,0)"), hovertext=texto,
                             hovertemplate="%{hovertext}<extra></extra>"))

    # Lectura a la derecha.
    pct = registrado / prometido
    proporcion = round(1 / pct) if pct > 0 else 0
    lado = [
        (0.97, f"<b>1 de cada {proporcion}</b>", 40, e.TINTA),
        (0.83, f"empleos prometidos aparece como<br>empleo formal en el IMSS ({pct:.0%})", 14, e.TINTA_2),
        (0.62, f"<b>{registrado / 1000:,.0f} mil con casco</b>", 17, e.TINTA),
        (0.55, f"empleos formales nuevos en el IMSS<br>({reg.periodo})", 12.5, e.TINTA_2),
        (0.40, f"<b>{(prometido - registrado) / 1000:,.0f} mil siluetas</b>", 17, e.TINTA),
        (0.33, f"del anuncio de {int(prom.proyectos)} proyectos<br>({prom.periodo})", 12.5, e.TINTA_2),
        (0.16, "<i>La promesa sumaba empleos directos e<br>indirectos; el IMSS solo cuenta el empleo<br>"
               "formal. La brecha es la pregunta, no<br>una conclusión.</i>", 12, e.TINTA_2),
    ]
    for y, t, tam, color in lado:
        fig.add_annotation(text=t, xref="paper", yref="paper", x=0.70, y=y, xanchor="left", yanchor="top",
                           align="left", showarrow=False, font=dict(family=e.LETRA, size=tam, color=color))
    fig.add_annotation(text="Cada figura = 1,000 empleos", xref="paper", yref="paper", x=0, y=1.0,
                       xanchor="left", yanchor="bottom", showarrow=False,
                       font=dict(family=e.LETRA, size=12.5, color=e.TINTA_3))

    fig.update_xaxes(visible=False, range=[-0.1, COLUMNAS + 0.1], domain=[0, 0.66])
    fig.update_yaxes(visible=False, range=[-0.1, filas + 0.1], scaleanchor="x", scaleratio=1)
    return fig
