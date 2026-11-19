"""Impacto por municipio ocasionado por la cría de cerdo en la península

viz_id: 2.cria_de_cerdo
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Impacto por municipio ocasionado por la cría de cerdo en la península")
    return fig
