"""3.alfabetizacion: La biblioteca de Yucatán.

Oro: una fila por municipio y periodo, con clave_municipio, municipio, anio,
adultos_alfabetizados, lat y lon (EPSG:4326). La cifra corresponde a las
personas alfabetizadas mediante el IEAEY.
"""

import math

import plotly.graph_objects as go
from plotly.subplots import make_subplots

TITULO = "Comparativa municipal de adultos alfabetizados"
PAPEL = "#f7f2e8"
TINTA = "#173c34"
VERDE = "#356f59"


def figura(datos) -> go.Figure:
    """El mapa compara municipios y el selector abre la ficha de cada libro."""
    fig = make_subplots(
        rows=1, cols=2, specs=[[{"type": "geo"}, {"type": "xy"}]],
        column_widths=[0.61, 0.39], horizontal_spacing=0.04,
    )
    fig.update_layout(
        template="plotly_white", paper_bgcolor=PAPEL, plot_bgcolor=PAPEL,
        font=dict(family="Georgia, serif", color=TINTA, size=14), height=570,
        margin=dict(l=25, r=25, t=110, b=74),
        title=dict(text=f"{TITULO}<br><sup>La biblioteca de Yucatán · "
                        "adultos alfabetizados mediante el IEAEY</sup>", x=0.04),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_geos(
        projection_type="mercator", lonaxis_range=[-90.75, -87.35],
        lataxis_range=[19.45, 21.8], showland=True, landcolor="#eee8da",
        showocean=True, oceancolor="#dceceb", showcountries=False,
        showcoastlines=False, showframe=False, bgcolor=PAPEL,
    )
    limites = datos.attrs.get("geojson") if datos is not None else None
    municipios = None
    if datos is not None and not datos.empty:
        periodo = datos["anio"].max()
        municipios = datos[datos["anio"] == periodo].sort_values("municipio")
        mayor = int(municipios["adultos_alfabetizados"].max())

    if limites:
        if municipios is None:
            ubicaciones = [f["id"] for f in limites["features"]]
            fig.add_trace(go.Choropleth(
                geojson=limites, locations=ubicaciones, z=[0] * len(ubicaciones),
                colorscale=[[0, "#e9e3d6"], [1, "#e9e3d6"]], showscale=False,
                marker_line_color="#b3b5a1", marker_line_width=0.6, hoverinfo="skip",
            ), row=1, col=1)
        else:
            fig.add_trace(go.Choropleth(
                geojson=limites, locations=municipios["clave_municipio"],
                z=municipios["adultos_alfabetizados"], zmin=0, zmax=max(1, mayor),
                text=municipios["municipio"],
                colorscale=[[0, "#e9e3d6"], [0.035, "#b9d4bb"],
                            [0.27, "#559479"], [1, "#153e34"]],
                colorbar=dict(title=dict(text="Adultos alfabetizados", side="top"),
                              orientation="h", x=0.305, y=-0.02, yanchor="top",
                              len=0.41, thickness=11),
                marker_line_color="#7d9990", marker_line_width=0.6,
                hovertemplate="<b>%{text}</b><br>%{z:,.0f} adultos alfabetizados<extra></extra>",
            ), row=1, col=1)
    if municipios is None:
        fig.add_annotation(text="Pendiente el archivo municipal del IEAEY.",
                           x=0.80, y=0.5, xref="paper", yref="paper", showarrow=False)
        return fig

    unidad = max(1, math.ceil(mayor / 240) * 10)
    inicial = municipios.sort_values("adultos_alfabetizados", ascending=False).iloc[0]
    if not limites:
        fig.add_trace(go.Scattergeo(
            lon=municipios["lon"], lat=municipios["lat"], mode="markers",
            marker=dict(
                size=11, symbol="square", color=municipios["adultos_alfabetizados"],
                colorscale=[[0, "#b0ccab"], [1, VERDE]], cmin=0, cmax=max(1, mayor),
                line=dict(width=0.6, color=TINTA),
            ),
            text=municipios["municipio"], customdata=municipios["adultos_alfabetizados"],
            hovertemplate="<b>%{text}</b><br>%{customdata:,.0f} adultos alfabetizados<extra></extra>",
            showlegend=False,
        ), row=1, col=1)

    def paginas(fila):
        cantidad = int(fila["adultos_alfabetizados"])
        enteros, resto = divmod(cantidad, unidad)
        fichas = ["Aa"] * enteros
        if resto:
            fichas.append(f"+{resto}")
        if not fichas:
            return dict(
                x=[0.53, 0.52], y=[0.91, 0.52],
                text=[f"<b>{fila['municipio']}</b><br>0 adultos", "Sin alfabetizaciones registradas"],
            )
        posiciones = [(0.13 + 0.14 * (i % 3) + 0.46 * (i // 12),
                       0.69 - 0.11 * ((i // 3) % 4))
                      for i in range(len(fichas))]
        return dict(
            x=[0.53, *[x for x, _ in posiciones]],
            y=[0.91, *[y for _, y in posiciones]],
            text=[f"<b>{fila['municipio']}</b><br>{cantidad:,} adultos",
                  *fichas],
        )

    indice_libro = len(fig.data)
    fig.add_trace(go.Scatter(
        **paginas(inicial), mode="text", textfont=dict(size=15, color=TINTA),
        hoverinfo="skip", showlegend=False,
    ), row=1, col=2)
    fig.update_xaxes(range=[0, 1.05], fixedrange=True)
    fig.update_yaxes(range=[0, 1.06], fixedrange=True)
    for izquierda, derecha in [(0.04, 0.52), (0.52, 1.00)]:
        fig.add_shape(type="rect", x0=izquierda, x1=derecha, y0=0.24, y1=0.79,
                      line=dict(color=VERDE, width=1.4), fillcolor="#fffdf6", layer="below")
    fig.add_annotation(
        x=0.52, y=0.13, text=f"{periodo} · Cada «Aa» representa {unidad} adultos<br>"
                             "«+n» indica los adultos restantes.<br>IEAEY · cuadro 6.22 del Anuario 2017",
        showarrow=False, font=dict(size=12),
    )
    fig.update_layout(updatemenus=[dict(
        x=0.64, xanchor="left", y=1.06, yanchor="bottom",
        name="municipios",
        active=municipios["clave_municipio"].tolist().index(inicial["clave_municipio"]),
        buttons=[
            dict(label=fila.municipio, method="restyle",
                 args=[{k: [v] for k, v in paginas(fila._asdict()).items()}, [indice_libro]])
            for fila in municipios.itertuples(index=False)
        ],
    )])
    return fig


def datos_locales(archivo):
    """Carga los conteos locales; el mapa también se conserva sin registros."""
    import pandas as pd
    from vista_previa import incluir_mapa, leer_tabla

    if archivo.is_file():
        return leer_tabla(archivo)
    return incluir_mapa(pd.DataFrame())


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from vista_previa import DATOS, abrir

    parser = argparse.ArgumentParser(description="Vista municipal de alfabetización.")
    parser.add_argument("--datos", type=Path, default=DATOS / "alfabetizacion.csv")
    parser.add_argument("--sin-abrir", action="store_true")
    args = parser.parse_args()
    if not args.datos.is_file() and args.datos != DATOS / "alfabetizacion.csv":
        parser.error(f"No se encontró el CSV: {args.datos}")
    abrir([figura(datos_locales(args.datos))], "alfabetizacion", args.sin_abrir)
