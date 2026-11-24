"""3.natalidad: mapa anual y calendario mensual de certificados SINAC.

Oro: una fila por clave_municipio, anio y mes, con municipio, nacimientos,
lat y lon (EPSG:4326). Los meses sin fila se conservan como faltantes.
"""

import pandas as pd
import plotly.graph_objects as go

TITULO = "Natalidad en los municipios de Yucatán"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
TINTA = "#173c34"
PAPEL = "#f7f2e8"
AGUA = "#217f86"


def _base(titulo, lectura):
    fig = go.Figure()
    fig.update_layout(
        template="plotly_white", paper_bgcolor=PAPEL, plot_bgcolor=PAPEL,
        title=dict(text=f"{titulo}<br><sup>{lectura}</sup>", x=0.045),
        font=dict(family="Georgia, serif", color=TINTA, size=14),
        margin=dict(l=45, r=32, t=104, b=85), height=610,
        separators=",.",
    )
    return fig


def _sin_datos(fig):
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.add_annotation(
        text="Aún no hay datos municipales de SINAC para mostrar.",
        x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
    )
    return fig


def figura(datos) -> go.Figure:
    """El pulso de Yucatán. El control anual conserva la escala de áreas."""
    fig = _base(TITULO, "El pulso de Yucatán · nacimientos certificados por residencia de la madre · SINAC")
    if datos is None or datos.empty:
        return _sin_datos(fig)

    anual = (
        datos.groupby(["anio", "clave_municipio", "municipio", "lat", "lon"], as_index=False)
        .agg(nacimientos=("nacimientos", "sum"), meses=("mes", "nunique"))
    )
    anual = anual[anual["meses"] == 12]
    if anual.empty:
        return _sin_datos(fig)
    anios = sorted(anual["anio"].unique())
    escala = max(1, anual["nacimientos"].max()) * 2 / 58**2

    def burbujas(anio):
        sub = anual[anual["anio"] == anio].sort_values("nacimientos", ascending=False)
        return go.Scattergeo(
            lon=sub["lon"], lat=sub["lat"], mode="markers",
            text=sub["municipio"], customdata=sub[["nacimientos", "anio"]].to_numpy(),
            marker=dict(
                size=sub["nacimientos"], sizemode="area", sizeref=escala,
                color=AGUA, opacity=0.72, line=dict(color="#f4fbf9", width=1),
            ),
            hovertemplate="<b>%{text}</b><br>%{customdata[1]} · "
                          "%{customdata[0]:,.0f} nacimientos<extra></extra>",
            showlegend=False,
        )

    # Si la tabla de oro trae los límites, quedan integrados en el mismo mapa.
    limites = datos.attrs.get("geojson")
    if limites:
        fig.add_trace(go.Choropleth(
            geojson=limites, locations=[f["id"] for f in limites["features"]],
            z=[0] * len(limites["features"]),
            colorscale=[[0, "#e9e3d6"], [1, "#e9e3d6"]], showscale=False,
            marker_line_color="#b3b5a1", marker_line_width=0.6, hoverinfo="skip",
        ))
    indice_burbujas = len(fig.data)
    fig.add_trace(burbujas(anios[-1]))
    fig.update_geos(
        projection_type="mercator", lonaxis_range=[-90.75, -87.35],
        lataxis_range=[19.45, 21.8], showland=True, landcolor="#eee8da",
        showocean=True, oceancolor="#dceceb", showcountries=False,
        showcoastlines=False, showframe=False, bgcolor=PAPEL,
    )
    if len(anios) > 1:
        fig.frames = [
            go.Frame(name=str(anio), data=[burbujas(anio)], traces=[indice_burbujas])
            for anio in anios
        ]
        inmediato = dict(mode="immediate", frame=dict(duration=0, redraw=True),
                         transition=dict(duration=0))
        fig.update_layout(
            sliders=[dict(
                active=len(anios) - 1, x=0.15, len=0.83, y=0,
                currentvalue=dict(prefix="Año "),
                steps=[dict(label=str(anio), method="animate",
                            args=[[str(anio)], inmediato]) for anio in anios],
            )],
            updatemenus=[dict(
                type="buttons", direction="left", x=0, xanchor="left", y=0,
                buttons=[
                    dict(label="▶", method="animate", args=[None, dict(
                        fromcurrent=False, mode="immediate",
                        frame=dict(duration=520, redraw=True), transition=dict(duration=0),
                    )]),
                    dict(label="Ⅱ", method="animate", args=[[None], inmediato]),
                ],
            )],
        )
    else:
        fig.add_annotation(text=f"Año {anios[0]}", x=0, y=0, xref="paper",
                           yref="paper", showarrow=False)
    return fig


def figura_calendario(datos) -> go.Figure:
    """El calendario de los nacimientos. Cada celda representa mes y año."""
    fig = _base("El calendario de los nacimientos",
                "Selecciona un municipio y recorre sus meses por año")
    if datos is None or datos.empty:
        return _sin_datos(fig)

    anios = sorted(datos["anio"].unique())
    municipios = list(datos.groupby(["clave_municipio", "municipio"], sort=False))
    municipios.sort(key=lambda item: str(item[0][1]))
    mayor = max(1, datos["nacimientos"].max())
    inicial = max(range(len(municipios)),
                  key=lambda i: municipios[i][1]["nacimientos"].sum())

    def matriz(sub):
        return (
            sub.pivot(index="anio", columns="mes", values="nacimientos")
            .reindex(index=anios, columns=range(1, 13))
            .to_numpy()
        )

    clave_nombre, sub = municipios[inicial]
    fig.add_trace(go.Heatmap(
        x=MESES, y=anios, z=matriz(sub), name=clave_nombre[1],
        zmin=0, zmax=mayor, xgap=4, ygap=4, hoverongaps=False,
        colorscale=[[0, "#e7eee4"], [0.45, "#7cbdac"], [1, "#14666e"]],
        colorbar=dict(title="Nacimientos", thickness=14),
        hovertemplate="<b>%{fullData.name}</b><br>%{x} de %{y}<br>"
                      "%{z:,.0f} nacimientos<extra></extra>",
    ))
    fig.update_layout(updatemenus=[dict(
        x=0, xanchor="left", y=1.09, yanchor="bottom", active=inicial,
        buttons=[dict(label=nombre, method="restyle",
                      args=[{"z": [matriz(grupo)], "name": [nombre]}, [0]])
                 for (_, nombre), grupo in municipios],
    )])
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=MESES,
                     title_text="Mes de nacimiento", fixedrange=True)
    fig.update_yaxes(type="category", categoryorder="array", categoryarray=anios,
                     title_text="Año", fixedrange=True, showgrid=False)
    return fig


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from vista_previa import DATOS, abrir, leer_tabla

    parser = argparse.ArgumentParser(description="Vista municipal de nacimientos del SINAC.")
    parser.add_argument("--datos", type=Path, default=DATOS / "natalidad.csv")
    parser.add_argument("--vista", choices=("pulso", "calendario", "ambas"), default="ambas")
    parser.add_argument("--sin-abrir", action="store_true")
    args = parser.parse_args()
    if not args.datos.is_file():
        parser.error(f"No se encontró el CSV: {args.datos}")
    datos = leer_tabla(args.datos)
    graficas = []
    if args.vista in ("pulso", "ambas"):
        graficas.append(figura(datos))
    if args.vista in ("calendario", "ambas"):
        graficas.append(figura_calendario(datos))
    abrir(graficas, args.vista, args.sin_abrir)
