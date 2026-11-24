"""Unidades económicas, empleo y producción en Yucatán (Censos Económicos 2019 y 2024)

viz_id: 4.censos_economicos

Tabla de oro (`datos`): una fila por municipio de Yucatán.
  municipio, cve_geo, ue_2018, ue_2023, personal_2018, personal_2023, produccion_mdp_2018, produccion_mdp_2023,
  cambio_ue_pct, cambio_personal_pct, cambio_produccion_mdp_pct, cuadrante, y los metadatos.
Los Censos 2019 y 2024 tienen como años de referencia 2018 y 2023.

Cada burbuja es un municipio: eje x, cambio en unidades económicas; eje y, cambio en personal ocupado;
área, personal ocupado en 2023. Los cuadrantes leen qué pasó con los negocios y el empleo.

Fuente primaria: INEGI, Censos Económicos 2024. Secundaria: INEGI, Censos Económicos 2019.
"""
import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import estilo_equipo4 as e  # noqa: E402

TITULO = "Unidades económicas, empleo y producción en Yucatán (Censos Económicos 2019 y 2024)"

ETIQUETADOS = ["Mérida", "Kanasín", "Umán", "Progreso", "Valladolid", "Tizimín", "Abalá", "Yaxcabá", "Mocochá"]
CUADRANTES = {  # texto, posición (x, y en papel), ancla
    "Expansión": ("<b>Expansión</b><br>más negocios y empleo", 0.995, 0.99, "right", "top"),
    "Concentración": ("<b>Concentración</b><br>menos negocios, más empleo", 0.005, 0.99, "left", "top"),
    "Fragmentación": ("<b>Fragmentación</b><br>más negocios, menos empleo", 0.995, 0.01, "right", "bottom"),
    "Retroceso": ("<b>Retroceso</b><br>menos negocios y empleo", 0.005, 0.01, "left", "bottom"),
}
# Paso a paso de la historia: qué municipios se resaltan en cada paso (None = figura completa).
PASOS = {
    1: lambda d: d.municipio.eq("Mérida"),
    2: lambda d: d.municipio.isin(["Kanasín", "Umán", "Progreso"]),
    3: lambda d: d.cambio_ue_pct.gt(60) | d.cambio_personal_pct.gt(100),
    4: lambda d: d.cuadrante.ne("Expansión"),
}


def figura(datos, paso: int | None = None) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = e.base(go.Figure(), TITULO, alto=660)
    if datos is None or len(datos) == 0:
        return fig
    d = datos.sort_values("personal_2023", ascending=False).reset_index(drop=True)
    foco = PASOS[paso](d) if paso in PASOS else np.ones(len(d), bool)

    x, y = d.cambio_ue_pct, d.cambio_personal_pct
    xmin, xmax = min(-30, x.min() - 8), x.max() + 12
    ymin, ymax = min(-35, y.min() - 8), y.max() + 15

    # Cuadrantes: fondo tenue; los dos de la izquierda (menos negocios) en rojo claro, como en el boceto.
    for x0, x1, y0, y1, c in [(0, xmax, 0, ymax, e.AZUL_CLARO), (xmin, 0, 0, ymax, e.ROJO_CLARO),
                              (0, xmax, ymin, 0, "#F1F5FA"), (xmin, 0, ymin, 0, e.ROJO_CLARO)]:
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=c, line_width=0, layer="below", opacity=0.7)
    fig.add_hline(y=0, line=dict(color="#BDB9B0", width=1))
    fig.add_vline(x=0, line=dict(color="#BDB9B0", width=1))
    for texto, px, py, xa, ya in CUADRANTES.values():
        fig.add_annotation(text=texto, xref="paper", yref="paper", x=px, y=py, xanchor=xa, yanchor=ya,
                           showarrow=False, align="left" if xa == "left" else "right",
                           font=dict(family=e.LETRA, size=12.5, color=e.TINTA_2))

    tam = 8 + 60 * np.sqrt(d.personal_2023 / d.personal_2023.max())
    datos_hover = np.c_[d.municipio, d.ue_2018, d.ue_2023, d.personal_2018, d.personal_2023,
                        d.produccion_mdp_2018, d.produccion_mdp_2023, d.cuadrante]
    plantilla = ("<b>%{customdata[0]}</b> · %{customdata[7]}<br>"
                 "Unidades económicas: %{customdata[1]:,.0f} → %{customdata[2]:,.0f} (%{x:+.0f} %)<br>"
                 "Personal ocupado: %{customdata[3]:,.0f} → %{customdata[4]:,.0f} (%{y:+.0f} %)<br>"
                 "Producción bruta: %{customdata[5]:,.0f} → %{customdata[6]:,.0f} millones de pesos"
                 "<extra>2018 → 2023</extra>")
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="markers", customdata=datos_hover, hovertemplate=plantilla,
        marker=dict(size=tam, sizemode="diameter", color=[e.AZUL if f else e.GRIS for f in foco],
                    opacity=[0.75 if f else 0.45 for f in foco], line=dict(color="white", width=1.5))))

    for r in d[d.municipio.isin(ETIQUETADOS) | (foco & (paso is not None) & (paso != 4))].itertuples():
        fig.add_annotation(x=r.cambio_ue_pct, y=r.cambio_personal_pct, text=r.municipio, showarrow=False,
                           yshift=-(10 + 30 * np.sqrt(r.personal_2023 / d.personal_2023.max())) if r.municipio in
                           ("Mérida", "Kanasín") else 12, font=dict(family=e.LETRA, size=12, color=e.TINTA))

    if paso == 1 or paso is None:
        m = d[d.municipio == "Mérida"].iloc[0]
        e.nota(fig, f"Mérida concentra {m.personal_2023 / d.personal_2023.sum():.0%} del empleo del estado,<br>"
                    f"pero creció apenas {m.cambio_personal_pct:+.1f} % en personal ocupado",
               m.cambio_ue_pct, m.cambio_personal_pct, ax=180, ay=60)

    fig.update_xaxes(title="Cambio en unidades económicas, 2018 → 2023", ticksuffix=" %", range=[xmin, xmax],
                     showgrid=True, gridcolor=e.REJILLA)
    fig.update_yaxes(title="Cambio en personal ocupado, 2018 → 2023", ticksuffix=" %", range=[ymin, ymax])
    fig.add_annotation(text="Área de la burbuja: personal ocupado en 2023", xref="paper", yref="paper", x=0,
                       y=1.035, xanchor="left", yanchor="bottom", showarrow=False,
                       font=dict(family=e.LETRA, size=12.5, color=e.TINTA_3))
    return fig
