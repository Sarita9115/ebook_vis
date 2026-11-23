"""Hitos documentados del gobierno universitario y cambios de rectoría.

viz_id: 1.gobierno_universitario

La cronología distingue hechos institucionales de registros documentales de
quién aparece como rector. No representa periodos completos de nombramiento.

Columnas opcionales de `datos`: anio, hito, detalle, tipo.
Si `datos` es None o está vacío, se usa la evidencia documental verificada
incluida en este módulo para permitir la visualización mientras se prepara oro.
"""

import pandas as pd
import plotly.graph_objects as go

_DATOS_BASE = [
    {
        "anio": 2016,
        "hito": "Creación de la UPY",
        "detalle": "El Decreto 337/2016 fue publicado el 28 de enero de 2016 y constituyó a la UPY como organismo público descentralizado.",
        "tipo": "Institucional",
        "evidencia": "Notas a los estados financieros de la UPY, 1T 2026.",
    },
    {
        "anio": 2018,
        "hito": "Gildardo Sánchez Ante",
        "detalle": "Figura como rector en el Manual de Control Interno fechado en julio de 2018.",
        "tipo": "Registro de rectoría",
        "evidencia": "Manual de Control Interno UPY, julio de 2018.",
    },
    {
        "anio": 2021,
        "hito": "Víctor Eduardo Espadas Aldana",
        "detalle": "Identificado como titular de la UPY en el Manual de Organización General generado el 20 de octubre de 2021.",
        "tipo": "Registro de rectoría",
        "evidencia": "Manual de Organización General UPY, 20 de octubre de 2021.",
    },
    {
        "anio": 2024,
        "hito": "Alfredo Martín Ulibarri Benítez",
        "detalle": "Aparece como rector en el organigrama general cuya última actualización indicada es el 1 de enero de 2024.",
        "tipo": "Registro de rectoría",
        "evidencia": "Organigrama General UPY, actualizado al 1 de enero de 2024.",
    },
    {
        "anio": 2026,
        "hito": "Raúl Aarón Rosado Castillo",
        "detalle": "Identificado como rector en el directorio del Gobierno del Estado consultado el 22 de noviembre de 2026. La fecha es de consulta, no de nombramiento.",
        "tipo": "Registro vigente consultado",
        "evidencia": "Directorio de funcionarios del Gobierno de Yucatán.",
    },
]


def figura(datos=None) -> go.Figure:
    """Devuelve una cronología de hitos institucionales y registros de rectoría."""
    if datos is None or (hasattr(datos, "empty") and datos.empty):
        df = pd.DataFrame(_DATOS_BASE)
    else:
        df = datos.copy() if hasattr(datos, "copy") else pd.DataFrame(datos)
        requeridas = {"anio", "hito", "detalle", "tipo"}
        faltantes = requeridas.difference(df.columns)
        if faltantes:
            raise ValueError(f"A datos le faltan columnas: {', '.join(sorted(faltantes))}")
        if "evidencia" not in df.columns:
            df["evidencia"] = "Registro suministrado en la tabla de oro."

    df = df.sort_values("anio").reset_index(drop=True)
    posiciones = [0.18 if i % 2 == 0 else -0.18 for i in range(len(df))]
    colores = ["#0F766E" if t == "Institucional" else "#6D28D9" for t in df["tipo"]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["anio"], y=[0] * len(df), mode="lines",
        line=dict(color="#94A3B8", width=3), hoverinfo="skip", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=df["anio"], y=[0] * len(df), mode="markers",
        marker=dict(size=17, color=colores, line=dict(color="white", width=2)),
        customdata=df[["hito", "detalle", "tipo", "evidencia"]].to_numpy(),
        hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[1]}<br>"
                       "Tipo: %{customdata[2]}<br>Fuente: %{customdata[3]}<extra></extra>"),
        showlegend=False,
    ))
    for i, row in df.iterrows():
        y = posiciones[i]
        fig.add_shape(type="line", x0=row["anio"], x1=row["anio"], y0=0, y1=y,
                      line=dict(color="#94A3B8", width=1, dash="dot"))
        fig.add_annotation(
            x=row["anio"], y=y, text=f"<b>{row['anio']}</b><br>{row['hito']}",
            showarrow=False, yshift=8 if y > 0 else -8,
            font=dict(size=11, color="#1E293B"), align="center",
            bgcolor="rgba(255,255,255,0.92)", bordercolor="#E2E8F0", borderwidth=1,
            borderpad=5,
        )

    fig.update_layout(
        title=dict(text="Gobierno universitario: hitos y registros documentales de rectoría", x=0.02),
        template="plotly_white", height=470, margin=dict(l=35, r=35, t=90, b=65),
        xaxis=dict(title="Año del documento o acontecimiento", tickmode="linear", dtick=2,
                   range=[df["anio"].min() - 0.7, df["anio"].max() + 0.7], showgrid=True,
                   gridcolor="#E2E8F0", zeroline=False),
        yaxis=dict(visible=False, range=[-0.38, 0.38]),
        annotations=[dict(
            x=0.01, y=-0.19, xref="paper", yref="paper", showarrow=False,
            text="Nota: los años indican la fecha de los documentos consultados; no acreditan por sí solos el inicio o fin de cada gestión.",
            font=dict(size=10, color="#475569"), align="left",
        )],
    )
    return fig
