"""Estilo editorial compartido por las figuras del equipo 4 (Inversión extranjera en Yucatán).

Paleta: la de referencia validada para daltonismo (slots en orden fijo). El color sigue a la entidad:
  IED de Yucatán = azul, participación / internacional = naranja, inversión que entra / turismo = aguamarina,
  inversión que sale = rojo, el resto (otras entidades, contexto) = gris cálido.
"""
import plotly.graph_objects as go

PAPEL = "#FBFAF7"        # superficie de la página
TINTA = "#1A1A19"        # texto principal
TINTA_2 = "#52514E"      # texto secundario
TINTA_3 = "#8A8880"      # texto apagado
REJILLA = "#E8E6E1"      # rejilla y ejes, una sombra fuera del papel
TIERRA = "#ECEAE4"       # continentes del mapa

AZUL = "#2A78D6"
NARANJA = "#EB6834"
AGUA = "#1BAF7A"
ROJO = "#E34948"
GRIS = "#C9C6BE"
AZUL_CLARO = "#E6F0FB"
ROJO_CLARO = "#FBEAEA"

LETRA = "'Source Sans 3', Inter, 'Helvetica Neue', Arial, sans-serif"
LETRA_TITULO = "'Source Serif 4', Georgia, 'Times New Roman', serif"


def base(fig: go.Figure, titulo: str, alto: int = 640, ancho: int | None = None) -> go.Figure:
    """Aplica el diseño editorial común: papel cálido, rejilla tenue, tipografía y tooltip."""
    fig.update_layout(
        title=dict(text=titulo, x=0.01, xanchor="left", y=0.98, yanchor="top",
                   font=dict(family=LETRA_TITULO, size=22, color=TINTA)),
        paper_bgcolor=PAPEL, plot_bgcolor=PAPEL, height=alto, width=ancho,
        font=dict(family=LETRA, size=13, color=TINTA_2),
        margin=dict(l=60, r=30, t=80, b=50),
        hoverlabel=dict(bgcolor="white", bordercolor=REJILLA, font=dict(family=LETRA, size=13, color=TINTA)),
        showlegend=False,
    )
    fig.update_xaxes(showgrid=False, linecolor=REJILLA, tickcolor=REJILLA, ticks="outside",
                     tickfont=dict(color=TINTA_2), title_font=dict(color=TINTA_2), zeroline=False)
    fig.update_yaxes(gridcolor=REJILLA, gridwidth=1, linecolor=REJILLA, tickfont=dict(color=TINTA_2),
                     title_font=dict(color=TINTA_2), zeroline=False)
    return fig


def titulos_izquierda(fig: go.Figure, n: int, tamano: int = 15) -> None:
    """Alinea a la izquierda de cada panel los títulos de make_subplots (vienen en el mismo orden que los ejes)."""
    ejes = ["xaxis"] + [f"xaxis{k}" for k in range(2, n + 1)]
    for a, eje in zip(fig.layout.annotations[:n], ejes):
        a.update(x=fig.layout[eje].domain[0], xanchor="left",
                 font=dict(family=LETRA, size=tamano, color=TINTA))


def nota(fig: go.Figure, texto: str, x: float, y: float, xref="x", yref="y", ax=40, ay=-40, **kw) -> None:
    """Anotación editorial: texto en tinta (nunca en el color de la serie) con una guía fina."""
    fig.add_annotation(x=x, y=y, xref=xref, yref=yref, text=texto, showarrow=True, arrowhead=0, arrowwidth=1,
                       arrowcolor=TINTA_3, ax=ax, ay=ay, align="left",
                       font=dict(family=LETRA, size=12.5, color=TINTA), bgcolor="rgba(251,250,247,0.85)", **kw)


def opacidad(activo: bool) -> float:
    """Énfasis paso a paso: el elemento activo completo, el resto en segundo plano."""
    return 1.0 if activo else 0.2
