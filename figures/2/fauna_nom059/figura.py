"""La fauna de la península, en tu espacio

viz_id: 2.fauna_nom059

Modelos 3D de baja poligonía de especies de la península, con un selector a la
izquierda (como en la maqueta) y, debajo del modelo, el nombre científico, el
nombre común, una barra de gravedad y la categoría de riesgo de la NOM-059.

Fuentes (las muestra la plantilla, no van dentro de la figura):
    primaria     modelos GLB de baja poligonía (poly.pizza)
    secundaria   NOM-059-SEMARNAT-2010 (categorías de riesgo)

Tabla de oro (`datos`): una fila por especie.
    nombre        nombre común ("Jaguar")
    cientifico    nombre científico ("Panthera onca")
    categoria     categoría NOM-059: "P", "A", "Pr", "E" o su texto completo
    x, y, z       listas con las coordenadas de los vértices (eje z = arriba)
    i, j, k       listas con los índices de los vértices de cada triángulo
    colores_cara  opcional: lista de [r, g, b] (0-255), una por triángulo
    colores       opcional: lista de [r, g, b] (0-255), una por vértice

El GLB no viaja al navegador: `pipelines/2/oro_ingrid.py` lo convierte a malla y
deja esta tabla (el color de cada cara sale de la textura del modelo).
"""

import math

import numpy as np
import plotly.graph_objects as go

TITULO = "La fauna de la península, en tu espacio"

CALIZA, TEXTO, TEXTO_2 = "#f7f4ec", "#1d2a22", "#4f5b52"
VERDE, VERDE_CLARO = "#2f6b4f", "#e6e2d6"
LETRA = "Source Sans 3, Helvetica Neue, Helvetica, Arial, sans-serif"
COLOR_MODELO = "#9aa5a0"

# Categoría NOM-059 -> (texto, color, llenado de la barra).
# El llenado solo ordena la gravedad (E > P > A > Pr); no es un dato medido.
CATEGORIAS = {
    "E": ("Probablemente extinta en el medio silvestre", "#7a1f1f", 1.00),
    "P": ("En peligro de extinción", "#b85c45", 0.88),
    "A": ("Amenazada", "#d08a2e", 0.60),
    "PR": ("Sujeta a protección especial", "#c9a227", 0.35),
}
_TEXTO_A_CODIGO = {v[0].lower(): k for k, v in CATEGORIAS.items()}
SIN_CATEGORIA = ("Sin categoría en la NOM-059", "#8a8a8a", 0.0)


def _categoria(valor):
    """Devuelve (texto, color, llenado) para un código o un texto de categoría."""
    txt = str(valor).strip()
    codigo = txt.upper() if txt.upper() in CATEGORIAS else _TEXTO_A_CODIGO.get(txt.lower())
    return CATEGORIAS.get(codigo, SIN_CATEGORIA)


def _normaliza(x, y, z):
    """Centra el modelo y lo escala a una caja de lado 1 (todas las especies
    quedan a la misma escala visual, aunque el GLB original no lo esté)."""
    x, y, z = (np.asarray(v, dtype=float) for v in (x, y, z))
    centro = np.array([(v.max() + v.min()) / 2 for v in (x, y, z)])
    lado = max(v.max() - v.min() for v in (x, y, z)) or 1.0
    return (x - centro[0]) / lado, (y - centro[1]) / lado, (z - centro[2]) / lado


def _barra_y_etiquetas(fila):
    """Shapes y anotaciones de la parte baja para una especie."""
    texto, color, llenado = _categoria(fila["categoria"])
    x0, x1, yb = 0.27, 0.99, 0.115
    # Ancho útil del lienzo en píxeles (1100 menos márgenes de 20 + 20).
    ancho_px = 1060
    # Etiqueta de categoría: un rectángulo de ancho fijo y el texto centrado encima.
    # (Un fondo de anotación se mide con otra fuente y el texto se sale.)
    w_px = int(len(texto) * 8.5 + 28)
    w = w_px / ancho_px
    shapes = [
        dict(type="rect", xref="paper", yref="paper", x0=x0, x1=x1, y0=yb, y1=yb + 0.012,
             fillcolor=VERDE_CLARO, line=dict(width=0), layer="below"),
        dict(type="rect", xref="paper", yref="paper", x0=x0, x1=x0 + (x1 - x0) * llenado,
             y0=yb, y1=yb + 0.012, fillcolor=color, line=dict(width=0)),
        dict(type="rect", xref="paper", yref="paper", x0=x0, x1=x0 + w,
             y0=0.02, y1=0.08, fillcolor=color, line=dict(width=0), layer="below"),
    ]
    # `width` + `align="left"` evita que el texto se centre y se corra a la izquierda.
    anots = [
        dict(xref="paper", yref="paper", x=x0, y=0.235, xanchor="left", yanchor="middle",
             width=600, align="left", showarrow=False,
             text=f"<b>{str(fila['cientifico']).upper()}</b>",
             font=dict(size=12, color="#a07a2a")),
        dict(xref="paper", yref="paper", x=x0, y=0.19, xanchor="left", yanchor="middle",
             width=600, align="left", showarrow=False,
             text=f"<b>{fila['nombre']}</b>", font=dict(size=26, color=TEXTO)),
        dict(xref="paper", yref="paper", x=x0 + w / 2, y=0.05, xanchor="center",
             yanchor="middle", width=w_px, align="center", showarrow=False,
             text=f"<b>{texto}</b>", font=dict(size=13, color="white")),
    ]
    return shapes, anots


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(
        title=dict(text=TITULO, x=0, xanchor="left", y=0.97, yanchor="top",
                   font=dict(size=22, color=TEXTO), pad=dict(l=10)),
        width=1100, height=720, paper_bgcolor=CALIZA, plot_bgcolor=CALIZA,
        font=dict(family=LETRA, size=14, color=TEXTO),
        margin=dict(l=20, r=20, t=80, b=20),
    )
    if datos is None or len(datos) == 0:
        return fig

    df = datos.reset_index(drop=True)
    n = len(df)

    # Una traza Mesh3d por especie; solo la primera está visible al abrir.
    for idx, fila in df.iterrows():
        x, y, z = _normaliza(fila["x"], fila["y"], fila["z"])
        malla = dict(
            x=x, y=y, z=z, i=fila["i"], j=fila["j"], k=fila["k"],
            flatshading=True, name=str(fila["nombre"]), showlegend=False,
            lighting=dict(ambient=0.55, diffuse=0.85, specular=0.1, roughness=0.9),
            lightposition=dict(x=200, y=-300, z=400),
            hoverinfo="text", text=f"{fila['nombre']} ({fila['cientifico']})",
            visible=(idx == 0), scene="scene",
        )
        por_cara = fila["colores_cara"] if "colores_cara" in df.columns else None
        por_vertice = fila["colores"] if "colores" in df.columns else None
        if por_cara is not None and len(por_cara) == len(fila["i"]):
            malla["facecolor"] = [f"rgb({int(r)},{int(g)},{int(b)})" for r, g, b in por_cara]
        elif por_vertice is not None and len(por_vertice) == len(x):
            malla["vertexcolor"] = np.asarray(por_vertice)
        else:
            malla["color"] = COLOR_MODELO
        fig.add_trace(go.Mesh3d(**malla))

    # Estado inicial (primera especie) y botones del selector.
    shapes0, anots0 = _barra_y_etiquetas(df.iloc[0])
    botones = []
    for idx, fila in df.iterrows():
        shapes, anots = _barra_y_etiquetas(fila)
        botones.append(dict(
            label=str(fila["nombre"]), method="update",
            args=[{"visible": [t == idx for t in range(n)]},
                  {"shapes": shapes, "annotations": anots}],
        ))

    eje = dict(visible=False, range=[-0.65, 0.65])
    fig.update_layout(
        shapes=shapes0, annotations=anots0,
        scene=dict(
            domain=dict(x=[0.25, 1.0], y=[0.28, 0.95]),
            xaxis=eje, yaxis=eje, zaxis=eje, aspectmode="cube",
            camera=dict(eye=dict(x=1.35, y=-1.35, z=0.55)),
            bgcolor="#1f4a38",
        ),
        updatemenus=[dict(
            type="buttons", direction="down", active=0, showactive=True,
            x=0.0, xanchor="left", y=0.90, yanchor="top",
            pad=dict(l=10, t=0, b=0, r=0),
            bgcolor="white", bordercolor="#d9d4c4",
            font=dict(size=14, color=TEXTO),
            buttons=botones,
        )],
    )
    return fig