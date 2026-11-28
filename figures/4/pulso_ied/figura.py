"""El pulso de la inversión extranjera: ritmo de la IED en Yucatán (2020-2025)

viz_id: 4.pulso_ied

Tabla de oro (`datos`): una fila por trimestre desde 2020.
  anio, trimestre, periodo ("2022-T2"), ied_mdd (IED del trimestre, millones de dólares),
  ied_anual_mdd (suma de los trimestres del año), ied_anual_se_mdd (cifra anual oficial de la SE, contraste),
  y los metadatos.

La figura es un monitor de signos vitales: cada latido es un trimestre y la altura del pico es la IED que llegó.
Un trimestre negativo (salieron más recursos de los que entraron) dibuja el latido hacia abajo.

Fuente primaria: Secretaría de Economía, Data México (IED por estado y trimestre, API pública).
Secundaria: Secretaría de Economía, estadística oficial de la IED por entidad federativa (cifras anuales).
"""
import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import estilo_equipo4 as e  # noqa: E402

TITULO = "El pulso de la inversión extranjera: ritmo de la IED en Yucatán (2020-2025)"

# Colores del monitor (la figura es una pantalla oscura dentro de la página clara).
FONDO = "#0D1714"
MARCO = "#1F2825"
REJILLA_FINA = "#16271F"
REJILLA_GRUESA = "#22392F"
VERDE = "#3BE38F"
AMBAR = "#F2B84B"
ROJO = "#FF6B5E"
TEXTO = "#D7F5E6"
TEXTO_2 = "#7FB59B"

# Paso a paso de la historia: qué años se encienden (None = el trazo completo).
PASOS = {1: [2020], 2: [2022], 3: [2024]}


def _latido(h: float, n: int = 160) -> tuple[np.ndarray, np.ndarray]:
    """Forma de un latido (onda P, complejo QRS y onda T) centrada en 0, con el pico R a la altura h."""
    t = np.linspace(-0.5, 0.5, n)
    s = 1 if h >= 0 else -1
    y = (8 * np.exp(-((t + 0.28) / 0.04) ** 2)          # P
         - s * 12 * np.exp(-((t + 0.05) / 0.012) ** 2)  # Q
         + h * np.exp(-(t / 0.018) ** 2)                # R
         - s * 22 * np.exp(-((t - 0.045) / 0.014) ** 2)  # S
         + 14 * np.exp(-((t - 0.25) / 0.06) ** 2))       # T
    return t, y


def _trazo(valores, posiciones):
    xs, ys = [], []
    for i, h in zip(posiciones, valores):
        t, y = _latido(h)
        xs.append(i + t)
        ys.append(y)
    return np.concatenate(xs), np.concatenate(ys)


def figura(datos, paso: int | None = None) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro.

    paso (1-3) enciende un año de la lectura guiada; None muestra el trazo completo.
    """
    fig = e.base(go.Figure(), TITULO, alto=600)
    fig.update_layout(paper_bgcolor=MARCO, plot_bgcolor=FONDO, font=dict(color=TEXTO_2),
                      title_font=dict(color="#F4FBF7"), margin=dict(l=30, r=230, t=80, b=50))
    if datos is None or len(datos) == 0:
        return fig

    d = datos.sort_values(["anio", "trimestre"]).reset_index(drop=True)
    pos = np.arange(len(d))
    v = d.ied_mdd.to_numpy(float)
    encendidos = PASOS.get(paso)
    foco = d.anio.isin(encendidos).to_numpy() if encendidos else np.ones(len(d), bool)

    # Trazo base: completo y brillante sin paso; tenue cuando un paso enciende solo un año.
    x, y = _trazo(v, pos)
    if encendidos:
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=VERDE, width=1.6), opacity=0.22,
                                 hoverinfo="skip"))
        x, y = _trazo(v[foco], pos[foco])
    for ancho, alfa in [(11, 0.06), (6, 0.13), (3.5, 0.25)]:  # resplandor del fósforo
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=VERDE, width=ancho), opacity=alfa,
                                 hoverinfo="skip", connectgaps=False))
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=VERDE, width=1.8), hoverinfo="skip",
                             connectgaps=False))

    # Puntos invisibles en cada pico: el tooltip del trimestre.
    oficial = d.ied_anual_se_mdd.map(lambda a: f"{a:,.1f} mdd" if a == a else "sin dato")
    fig.add_trace(go.Scatter(
        x=pos, y=v, mode="markers", marker=dict(size=18, color="rgba(0,0,0,0)"),
        customdata=np.c_[d.periodo, d.anio, d.ied_anual_mdd, oficial],
        hovertemplate=("<b>%{customdata[0]}</b><br>IED del trimestre: %{y:,.1f} mdd<br>"
                       "Total del año %{customdata[1]}: %{customdata[2]:,.1f} mdd<br>"
                       "Cifra anual oficial (SE): %{customdata[3]}<extra></extra>")))

    # Cifra sobre cada latido; el pico y el valor más bajo en negritas.
    imax, imin = int(np.argmax(v)), int(np.argmin(v))
    for i, h in enumerate(v):
        fuerte = i in (imax, imin)
        fig.add_annotation(x=i, y=h, text=f"<b>{h:,.0f}</b>" if fuerte else f"{h:,.0f}", showarrow=False,
                           yshift=14 if h >= 0 else -14, yanchor="bottom" if h >= 0 else "top",
                           font=dict(family=e.LETRA, size=13 if fuerte else 11,
                                     color=(ROJO if h < 0 else TEXTO) if foco[i] else TEXTO_2),
                           opacity=1 if foco[i] else 0.45)

    # Notas del monitor, ancladas a los datos.
    def nota(i, texto, color, dx, dy):
        fig.add_annotation(x=i, y=v[i], text=texto, showarrow=True, arrowhead=0, arrowcolor=color, arrowwidth=1,
                           ax=dx, ay=dy, align="left" if dx > 0 else "right",
                           xanchor="left" if dx > 0 else "right", font=dict(family=e.LETRA, size=12, color=color))

    if paso in (None, 2):
        nota(imax, "<b>¡taquicardia!</b><br>el trimestre más alto", VERDE, 40, 45)
    if paso in (None, 3) and v[imin] < 0:
        nota(imin, "<b>arritmia</b><br>salió más de lo que entró", ROJO, -70, 10)
    if paso in (None, 1):
        i20 = int(np.argmin(np.where(d.anio == 2020, v, np.inf)))
        nota(i20, "<b>pulso casi plano</b><br>pandemia", AMBAR, 20, -90)

    # Años: separadores y etiquetas debajo de cada grupo de trimestres.
    anios = d.groupby("anio").apply(lambda g: (g.index.min(), g.index.max()), include_groups=False)
    for (a0, a1) in list(anios)[1:]:
        fig.add_vline(x=a0 - 0.5, line=dict(color=REJILLA_GRUESA, width=1.5))
    centros = [(a0 + a1) / 2 for a0, a1 in anios]

    ymin, ymax = min(-60, v.min() - 50), v.max() + 60
    fig.update_xaxes(range=[-0.6, len(d) - 0.4], tickvals=centros, ticktext=[str(a) for a in anios.index],
                     ticks="", tickfont=dict(size=13, color=TEXTO_2), showgrid=False, linecolor=REJILLA_GRUESA,
                     minor=dict(dtick=0.25, showgrid=True, gridcolor=REJILLA_FINA, gridwidth=1))
    fig.update_yaxes(range=[ymin, ymax], dtick=100, gridcolor=REJILLA_GRUESA, ticksuffix="", showticklabels=True,
                     tickfont=dict(size=11, color=TEXTO_2), zeroline=True, zerolinecolor="#2E4A3E",
                     minor=dict(dtick=25, showgrid=True, gridcolor=REJILLA_FINA))
    fig.add_annotation(text="IED · millones de dólares por trimestre", xref="paper", yref="paper", x=0, y=1.0,
                       xanchor="left", yanchor="bottom", showarrow=False, font=dict(size=12, color=TEXTO_2))

    # Lecturas del monitor, a la derecha.
    ultimo = d.iloc[-1]
    lecturas = [("PROMEDIO POR TRIMESTRE", f"{v.mean():,.0f}", VERDE),
                (f"PICO · {d.periodo[imax]}", f"{v[imax]:,.0f}", VERDE),
                (f"ÚLTIMO · {ultimo.periodo}", f"{ultimo.ied_mdd:,.0f}", ROJO if ultimo.ied_mdd < 0 else AMBAR)]
    for k, (etiqueta, valor, color) in enumerate(lecturas):
        y0 = 0.95 - k * 0.32
        fig.add_annotation(text=etiqueta, xref="paper", yref="paper", x=1.03, y=y0, xanchor="left",
                           yanchor="top", showarrow=False, font=dict(size=11.5, color=TEXTO_2))
        fig.add_annotation(text=f"<b>{valor.replace('-', '−')}</b> <span style='font-size:13px'>mdd</span>",
                           xref="paper", yref="paper", x=1.03, y=y0 - 0.06, xanchor="left", yanchor="top",
                           showarrow=False, font=dict(size=38, color=color))
    fig.add_annotation(text="● REC", xref="paper", yref="paper", x=1.03, y=0.0, xanchor="left", yanchor="bottom",
                       showarrow=False, font=dict(size=11, color=ROJO))
    return fig
