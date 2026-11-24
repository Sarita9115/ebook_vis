"""Herbario CICY, plantas vasculares

viz_id: 2.herbario_cicy

Tabla de oro (`datos`): una fila por estado y planta conocida de la península.
  estado, nombre_comun, especie, registros (ejemplares en el Herbario CICY),
  frac_presion (parte de esos registros en municipios con mucha presión),
  nom059 ("A" amenazada, "Pr" sujeta a protección especial, "" sin categoría),
  nivel ("Peligro", "Alerta", "Sin alerta"),
  especies_estado, frac_presion_estado (resumen del estado), municipios_presion

Nivel: Peligro = está en la NOM-059 y vive sobre todo (más de la mitad de sus registros) en
municipios con mucha presión; Alerta = solo una de las dos; Sin alerta = ninguna.
Municipio con mucha presión = más de 50 mil cerdos (Censo Agropecuario 2022) o más de 300
negocios que pueden dañar la naturaleza (DENUE).

Fuente primaria: Herbario CICY. Secundarias: NOM-059-SEMARNAT-2010, Censo Agropecuario 2022 y DENUE.
"""

import plotly.graph_objects as go

TITULO = "Herbario CICY, plantas vasculares"

TEXTO, SUAVE, REJILLA = "#1B2A3A", "#5A6876", "#E3E7EB"
LETRA = "DejaVu Sans, Helvetica Neue, Arial, sans-serif"
NIVEL = {  # color y grosor del borde
    "Peligro": ("#D32F2F", 5),
    "Alerta": ("#F57C00", 4),
    "Sin alerta": ("#C9D3CB", 1.5),
}
VERDES = {"Yucatán": ["#E3F1E1", "#CDE7C9"], "Campeche": ["#E6F0DC", "#D2E5C1"],
          "Quintana Roo": ["#DFF0EC", "#C6E4DD"]}
ORDEN = ["Yucatán", "Campeche", "Quintana Roo"]
NOM = {"A": "Amenazada (NOM-059)", "Pr": "Sujeta a protección especial (NOM-059)", "": "Sin categoría en la NOM-059"}


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(
        title=dict(text=f"<b>{TITULO}</b>", x=0.02, xanchor="left", y=0.97, font=dict(size=24, color=TEXTO)),
        width=1400, height=860, paper_bgcolor="white", font=dict(family=LETRA, size=13, color=TEXTO),
        margin=dict(l=20, r=20, t=175, b=130),
        hoverlabel=dict(bgcolor="white", font=dict(family=LETRA, color=TEXTO, size=13), bordercolor=REJILLA))
    if datos is None or len(datos) == 0:
        return fig

    fig.add_annotation(xref="paper", yref="paper", x=0, y=1.2, xanchor="left", showarrow=False,
                       text="Las plantas que están en juego en cada estado. Cada rectángulo es una planta conocida: "
                            "mientras más grande, más veces se ha registrado. El borde avisa cuáles corren más riesgo.",
                       font=dict(size=14, color=SUAVE))

    estados = [e for e in ORDEN if e in set(datos["estado"])]
    ancho, hueco = 1 / len(estados), 0.02
    for k, est in enumerate(estados):
        d = datos[datos["estado"] == est].sort_values("registros", ascending=False).reset_index(drop=True)
        etiqueta = [("⚠ " if n != "Sin alerta" else "") + (nom.replace(" ", "<br>", 1) if len(nom) > 11 else nom)
                    for nom, n in zip(d["nombre_comun"], d["nivel"])]
        fig.add_trace(go.Treemap(
            labels=etiqueta, parents=[""] * len(d), values=d["registros"], ids=[f"{est}|{e}" for e in d["especie"]],
            sort=True, branchvalues="total", tiling=dict(pad=4),
            marker=dict(colors=[VERDES[est][i % 2] for i in range(len(d))],
                        line=dict(color=[NIVEL[n][0] for n in d["nivel"]], width=[NIVEL[n][1] for n in d["nivel"]]),
                        pad=dict(t=2, l=2, r=2, b=2)),
            texttemplate="<b>%{label}</b><br>%{value} registros", textposition="middle center",
            textfont=dict(family=LETRA, color=TEXTO, size=14), insidetextfont=dict(size=14),
            customdata=list(zip(d["especie"], d["nivel"], d["nom059"].map(NOM), (d["frac_presion"] * 100).round())),
            hovertemplate="<b>%{label}</b> (<i>%{customdata[0]}</i>)<br>%{value} registros en " + est +
                          "<br>%{customdata[2]}<br>%{customdata[3]:.0f} % de sus registros en zonas con mucha presión"
                          "<br>Nivel: <b>%{customdata[1]}</b><extra></extra>",
            domain=dict(x=[k * ancho + (hueco if k else 0), (k + 1) * ancho - (hueco if k < len(estados) - 1 else 0)],
                        y=[0, 1]),
            root=dict(color="white"), pathbar=dict(visible=False),
        ))
        x0 = k * ancho + (hueco if k else 0)
        r = d.iloc[0]
        fig.add_annotation(xref="paper", yref="paper", x=x0, y=1.09, xanchor="left", yanchor="bottom",
                           showarrow=False, text=f"<b>{est.upper()}</b>", font=dict(size=19, color=TEXTO))
        fig.add_annotation(xref="paper", yref="paper", x=x0, y=1.075, xanchor="left", yanchor="top", showarrow=False,
                           text=f"{int(r.especies_estado):,} especies · {r.frac_presion_estado * 10:.0f} de cada 10 "
                                "registros en zonas con mucha presión", font=dict(size=12, color=SUAVE))

    # leyenda de niveles
    textos = {"Peligro": "Protegida por la ley (NOM-059) y vive sobre todo<br>en zonas con mucha presión",
              "Alerta": "Solo una de las dos: protegida por la ley<br>o vive sobre todo en zonas con mucha presión",
              "Sin alerta": "Ninguna de las dos"}
    for j, (niv, txt) in enumerate(textos.items()):
        x = j / 3
        color, grosor = NIVEL[niv]
        fig.add_shape(type="rect", xref="paper", yref="paper", x0=x, x1=x + 0.03, y0=-0.11, y1=-0.05,
                      line=dict(color=color, width=grosor), fillcolor="white")
        fig.add_annotation(xref="paper", yref="paper", x=x + 0.04, y=-0.045, xanchor="left", yanchor="top",
                           showarrow=False, align="left",
                           text=f"<b style='color:{color if niv != 'Sin alerta' else SUAVE}'>"
                                f"{'⚠ ' if niv != 'Sin alerta' else ''}{niv.upper()}</b><br>{txt}",
                           font=dict(size=11.5, color=TEXTO))
    n_pres = int(datos["municipios_presion"].iloc[0])
    fig.add_annotation(xref="paper", yref="paper", x=0, y=-0.155, xanchor="left", yanchor="top", showarrow=False,
                       text=f"<i>Zona con mucha presión = municipio con más de 50 mil cerdos o más de 300 negocios "
                            f"que pueden dañar la naturaleza ({n_pres} municipios).</i>",
                       font=dict(size=11.5, color=SUAVE))
    return fig
