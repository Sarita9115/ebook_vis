"""Carreras, modalidades y acreditaciones de la UPY.

viz_id: 1.carreras_modalidades

Columnas de `datos`: programa, tsu, ingenieria, modalidad, fecha_hito, hito.
La oferta actual y la doble titulación se toman del portal institucional.
Los hitos de apertura de Ciberseguridad y acreditación de Robótica se apoyan
en publicaciones institucionales fechadas.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_DATOS_BASE = [
    {"programa": "Robótica Computacional", "tsu": "Mantenimiento y Programación de Robots", "ingenieria": "Ingeniería en Robótica Computacional", "modalidad": "Oferta vigente; modalidad no indicada en el resumen", "fecha_hito": "2022-11-01", "hito": "Acreditación CIEES (noviembre de 2022)"},
    {"programa": "Ciberseguridad", "tsu": "Redes", "ingenieria": "Ingeniería en Ciberseguridad", "modalidad": "Modalidad mixta anunciada; ficha también muestra presencial", "fecha_hito": "2022-03-15", "hito": "Anuncio de apertura para el ciclo 2022-2023"},
    {"programa": "Ciencia de Datos e Inteligencia Artificial", "tsu": "Ciencia de Datos", "ingenieria": "Ingeniería en Datos e Inteligencia Artificial", "modalidad": "Oferta vigente; modalidad no indicada en el resumen", "fecha_hito": "", "hito": "Oferta vigente en el portal institucional"},
    {"programa": "Sistemas Embebidos Computacionales", "tsu": "Microcontroladores", "ingenieria": "Ingeniería en Sistemas Embebidos Computacionales", "modalidad": "Oferta vigente; modalidad no indicada en el resumen", "fecha_hito": "", "hito": "Oferta vigente en el portal institucional"},
]


def figura(datos=None) -> go.Figure:
    """Construye la matriz de carreras/doble titulación y la línea de hitos."""
    if datos is None or (hasattr(datos, "empty") and datos.empty):
        df = pd.DataFrame(_DATOS_BASE)
    else:
        df = datos.copy() if hasattr(datos, "copy") else pd.DataFrame(datos)
        requeridas = {"programa", "tsu", "ingenieria", "modalidad", "fecha_hito", "hito"}
        faltantes = requeridas.difference(df.columns)
        if faltantes:
            raise ValueError(f"A datos le faltan columnas: {', '.join(sorted(faltantes))}")

    hitos = df[df["fecha_hito"].astype(str).str.len() > 0].copy()
    if not hitos.empty:
        hitos["fecha_hito"] = pd.to_datetime(hitos["fecha_hito"])
        hitos = hitos.sort_values("fecha_hito")

    fig = make_subplots(
        rows=2, cols=1, row_heights=[0.36, 0.64], vertical_spacing=0.16,
        specs=[[{"type": "xy"}], [{"type": "table"}]],
        subplot_titles=("Hitos de apertura y acreditación", "Oferta académica y doble titulación"),
    )
    if not hitos.empty:
        fig.add_trace(go.Scatter(
            x=hitos["fecha_hito"], y=[0] * len(hitos), mode="lines+markers+text",
            line=dict(color="#94A3B8", width=2),
            marker=dict(size=15, color=["#0F766E" if "Acreditación" in str(h) else "#6D28D9" for h in hitos["hito"]]),
            text=hitos["hito"], textposition="top center", textfont=dict(size=10),
            customdata=hitos[["programa", "modalidad"]].to_numpy(),
            hovertemplate="%{x|%d %b %Y}<br><b>%{text}</b><br>Programa: %{customdata[0]}<br>Modalidad: %{customdata[1]}<extra></extra>",
            showlegend=False,
        ), row=1, col=1)
    fig.add_trace(go.Table(
        header=dict(values=["Programa", "TSU", "Ingeniería", "Modalidad / observación"],
                    fill_color="#312E81", font=dict(color="white", size=11), align="left", height=34),
        cells=dict(values=[df["programa"], df["tsu"], df["ingenieria"], df["modalidad"]],
                   fill_color=[["#F8FAFC", "white"] * (len(df) // 2 + 1)],
                   font=dict(color="#1E293B", size=10), align="left", height=48),
    ), row=2, col=1)
    fig.update_layout(
        title=dict(text="Carreras, modalidades y acreditaciones de la UPY", x=0.02),
        template="plotly_white", height=780, margin=dict(l=35, r=35, t=105, b=95),
        annotations=list(fig.layout.annotations) + [dict(
            x=0.01, y=-0.12, xref="paper", yref="paper", showarrow=False,
            text="La UPY organiza su oferta en una ruta de doble titulación: TSU y posterior Ingeniería. La página de Ciberseguridad anuncia modalidad mixta, aunque en la misma ficha aparece también el formato presencial; se conserva la discrepancia de la fuente.",
            font=dict(size=10, color="#475569"), align="left",
        )],
    )
    fig.update_yaxes(visible=False, range=[-0.4, 0.5], row=1, col=1)
    fig.update_xaxes(title_text="Fecha del hito", row=1, col=1, showgrid=True, gridcolor="#E2E8F0")
    return fig
