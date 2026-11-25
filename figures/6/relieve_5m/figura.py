"""Relieve y altura edificada de la zona metropolitana de Mérida vistos desde modelos de elevación de 5 m

viz_id: 6.relieve_5m

Recibe la tabla de oro (GeoDataFrame en EPSG:4326, formato largo con columna
`capa`) y dibuja una superficie 3D sobre la malla de 200 m:

- altura (Z): altura edificada de la celda, en metros (MDS - MDT por edificio,
  promedio ponderado por la huella);
- color: negocios del DENUE por celda, de 0 a 50 (50 o más en el tope).

Solo las celdas urbanas (al menos 5% del área construida) tienen altura; las
demás van a cero, aunque conservan el color de sus negocios. Las celdas sin cobertura del MDE
quedan vacías. El ráster de 5 m no llega aquí: solo la malla agregada.
"""

import numpy as np
import plotly.graph_objects as go

TITULO = "Relieve y altura edificada de la zona metropolitana de Mérida vistos desde modelos de elevación de 5 m"

# Paleta del ebook: caliza -> verde de monte -> agua de cenote -> terracota.
CALIZA_CLARA = "#EAE3D2"
CALIZA = "#CBBF9F"
MONTE_CLARO = "#6E9A6B"
MONTE = "#2F5D3A"
CENOTE = "#1F7A80"
TERRACOTA = "#C2562F"
TINTA = "#2B2A26"
TINTA_SUAVE = "#6B6457"
FONDO = "#FFFFFF"

ESCALA = [
    [0.00, CALIZA_CLARA],
    [0.04, CALIZA],
    [0.25, MONTE_CLARO],
    [0.50, MONTE],
    [0.75, CENOTE],
    [1.00, TERRACOTA],
]
TOPE_NEGOCIOS = 50
CELDA_KM = 0.2


def _matriz(celdas, columna, relleno):
    """Pasa una columna de la malla a una matriz filas x columnas."""
    f0, c0 = int(celdas["fila"].min()), int(celdas["columna"].min())
    nf = int(celdas["fila"].max()) - f0 + 1
    nc = int(celdas["columna"].max()) - c0 + 1
    m = np.full((nf, nc), np.nan)
    m[celdas["fila"].astype(int) - f0, celdas["columna"].astype(int) - c0] = celdas[columna].fillna(relleno)
    return m


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    celdas = datos[datos["capa"] == "celda"]
    resumen = datos[datos["capa"] == "resumen"].iloc[0]

    celdas = celdas.assign(altura_urbana=celdas["altura_m"].where(celdas["urbana"].astype(bool), 0.0))
    altura = _matriz(celdas, "altura_urbana", 0.0)
    negocios = _matriz(celdas, "negocios", 0.0)
    huella = _matriz(celdas, "huella_pct", 0.0)
    nf, nc = altura.shape
    x = np.arange(nc) * CELDA_KM
    y = np.arange(nf) * CELDA_KM
    color = np.clip(negocios, 0, TOPE_NEGOCIOS)
    detalle = np.dstack([negocios, huella])

    fig = go.Figure(
        go.Surface(
            x=x, y=y, z=altura, surfacecolor=color, customdata=detalle,
            colorscale=ESCALA, cmin=0, cmax=TOPE_NEGOCIOS,
            colorbar=dict(
                title=dict(text="Negocios por celda", side="right", font=dict(size=12, color=TINTA)),
                tickvals=[0, 10, 20, 30, 40, 50], ticktext=["0", "10", "20", "30", "40", "50 o más"],
                tickfont=dict(size=11, color=TINTA_SUAVE), thickness=14, len=0.55, x=0.93,
                outlinewidth=0,
            ),
            lighting=dict(ambient=0.75, diffuse=0.6, specular=0.05, roughness=0.9),
            lightposition=dict(x=-6e4, y=-6e4, z=1e5),
            hovertemplate=(
                "Altura edificada: %{z:.1f} m<br>Negocios: %{customdata[0]:.0f}"
                "<br>Huella construida: %{customdata[1]:.0f}% de la celda<extra></extra>"
            ),
            contours=dict(x=dict(highlight=False), y=dict(highlight=False), z=dict(highlight=False)),
        )
    )

    ancho_km, alto_km = nc * CELDA_KM, nf * CELDA_KM
    eje = dict(visible=False, showbackground=False, showspikes=False)
    fig.update_layout(
        title=dict(
            text=(
                f"{TITULO}<br><span style='font-size:13px;color:{TINTA_SUAVE}'>"
                f"{resumen['pct_menores_5m']:.0f}% de los edificios mide menos de 5 m · "
                f"celdas de 200 m</span>"
            ),
            x=0, xanchor="left", font=dict(size=17, color=TINTA),
        ),
        scene=dict(
            xaxis=eje, yaxis=eje, zaxis=dict(eje, range=[0, max(12.0, float(np.nanmax(altura)))]),
            aspectmode="manual",
            aspectratio=dict(x=1.25, y=1.25 * alto_km / ancho_km, z=0.3),
            camera=dict(eye=dict(x=-0.42, y=-1.02, z=0.62), center=dict(x=0, y=0.02, z=-0.18),
                        up=dict(x=0, y=0, z=1)),
            bgcolor=FONDO,
        ),
        font=dict(family="Open Sans, Verdana, Arial, sans-serif", color=TINTA),
        paper_bgcolor=FONDO,
        margin=dict(l=0, r=10, t=80, b=0),
        hoverlabel=dict(bgcolor=FONDO, font=dict(color=TINTA)),
        height=800,
    )
    return fig
